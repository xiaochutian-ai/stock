"""选股引擎：编排数据拉取、策略评估、结果聚合。

职责：
    1. 根据 Settings 构造 DataProvider / Repository / Strategy 列表
    2. 拉取（或从仓库读取）全市场股票 → 过滤市场/板块/ST
    3. 对每只股票：拉取 K 线、财务、资金流 → 组装 StrategyContext
    4. 依次跑所有策略，综合加权打分，按阈值过滤
    5. 返回排序好的结果列表

性能考量：
    - 财务数据使用 DataProvider.get_financials_batch 批量拉取
      （具体实现按数据源可重写批量接口以加速，避免 N+1 查询）
    - K 线/资金流为逐只拉取，展示进度条
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

from tqdm import tqdm

from ..config import Settings
from ..datasource import DataProvider, get_provider
from ..models import Stock
from ..storage import Repository, get_repository
from ..strategy import Strategy, StrategyContext, get_strategy

logger = logging.getLogger(__name__)


class ScreeningEngine:
    """选股引擎。

    构造完成后通过 run() 返回结果列表。
    """

    def __init__(
        self,
        settings: Settings,
        provider: Optional[DataProvider] = None,
        repository: Optional[Repository] = None,
    ):
        self.settings = settings

        # 数据源（依赖注入，便于测试）
        if provider is None:
            ds_cfg = settings.datasource or {}
            provider = get_provider(
                ds_cfg.get("name", "akshare"),
                options=ds_cfg.get("options", {}),
            )
        self.provider = provider

        # 存储（依赖注入）
        if repository is None:
            st_cfg = settings.storage or {}
            repository = get_repository(
                st_cfg.get("name", "sqlite"),
                options=st_cfg.get("options", {}),
            )
        self.repository = repository
        self._schema_ready = False

        # 策略组合
        self.strategies: List[Strategy] = []
        for s_cfg in settings.strategies or []:
            if not s_cfg.get("enabled", True):
                continue
            name = s_cfg.get("name")
            if not name:
                continue
            try:
                strat = get_strategy(
                    name,
                    params=s_cfg.get("params", {}),
                    weight=float(s_cfg.get("weight", 1.0)),
                )
                self.strategies.append(strat)
            except ValueError as e:
                logger.warning("跳过未知策略: %s", e)

        if not self.strategies:
            raise ValueError("未配置任何启用的策略，引擎无法运行")

    # ---------------- 主流程 ----------------
    def run(self, limit: Optional[int] = None, kline_days: int = 120) -> List[dict]:
        """执行选股流程。

        Args:
            limit: 仅评估前 N 只股票（用于调试，None 表示全市场）
            kline_days: 拉取最近多少日 K 线供技术面策略使用

        Returns:
            按综合分数降序排列的结果列表（每项为 dict）
        """
        # 0) 确保存储就绪（幂等）
        self._ensure_schema()

        # 1) 股票池
        stocks = self._prepare_universe(limit=limit)
        if not stocks:
            logger.warning("股票池为空")
            return []

        # 2) 批量财务
        financials_map = self._fetch_and_persist_financials(stocks)

        # 3) 逐只评估
        end = date.today()
        start = end - timedelta(days=kline_days * 2)  # 留足交易日

        results: List[dict] = []
        need_kline = self._need_kline()
        need_money = self._need_money_flow()
        mf_days = self._max_money_flow_days() if need_money else 0

        for stock in tqdm(stocks, desc="选股评估", ncols=80):
            item = self._process_single_stock(
                stock=stock,
                financial=financials_map.get(stock.code),
                need_kline=need_kline,
                need_money=need_money,
                kline_start=start,
                kline_end=end,
                mf_days=mf_days,
            )
            if item is not None:
                results.append(item)

        # 4) 综合打分排序
        results.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
        for i, item in enumerate(results, start=1):
            item["rank"] = i
        logger.info("选股完成：通过 %d 只", len(results))
        return results

    # ---------------- 子步骤 ----------------
    def _ensure_schema(self) -> None:
        """幂等初始化存储 schema（首次 run() 时建表）。"""
        if self._schema_ready:
            return
        self.repository.init_schema()
        self._schema_ready = True

    def _fetch_and_persist_financials(self, stocks: List[Stock]) -> dict:
        """批量拉取财务并落库，返回 code -> Financial 映射。

        失败时记录警告并返回空映射，不打断后续流程。
        """
        try:
            fins = self.provider.get_financials_batch([s.code for s in stocks])
        except Exception as e:
            logger.warning("批量拉取财务失败: %s", e)
            return {}

        try:
            self.repository.upsert_financials(fins)
        except Exception as e:
            logger.warning("批量财务落库失败: %s", e)

        logger.info("批量拉取财务完成: %d 条", len(fins))
        return {f.code: f for f in fins}

    def _process_single_stock(
        self,
        stock: Stock,
        financial,
        need_kline: bool,
        need_money: bool,
        kline_start: date,
        kline_end: date,
        mf_days: int,
    ) -> Optional[dict]:
        """对单只股票：拉取所需数据 → 组装 context → 跑策略。

        所有网络/IO 异常都在此吞掉（返回 None），不影响批量评估。
        """
        kline = None
        money_flows: list = []

        if need_kline:
            try:
                kline = self.provider.get_kline(
                    stock.code, start=kline_start, end=kline_end, adjust="qfq"
                )
                if kline and len(kline) > 0:
                    self.repository.upsert_kline(kline)
            except Exception as e:
                logger.debug("K线拉取失败 %s: %s", stock.code, e)

        if need_money:
            try:
                money_flows = self.provider.get_money_flow(stock.code, days=mf_days)
                if money_flows:
                    self.repository.upsert_money_flows(money_flows)
            except Exception as e:
                logger.debug("资金流拉取失败 %s: %s", stock.code, e)

        ctx = StrategyContext(
            stock=stock,
            kline=kline,
            financial=financial,
            money_flows=money_flows,
        )
        return self._evaluate_one(ctx)

    def _prepare_universe(self, limit: Optional[int]) -> List[Stock]:
        """准备候选股票池（含市场、ST、次新过滤）。"""
        market_cfg = self.settings.market or {}
        boards = set(market_cfg.get("boards", []))
        exclude_st = bool(market_cfg.get("exclude_st", True))
        exclude_new = int(market_cfg.get("exclude_new_stock_days", 0) or 0)

        stocks = self.provider.list_stocks()
        # 落库一份基础信息，便于后续离线使用
        try:
            self.repository.upsert_stocks(stocks)
        except Exception as e:
            logger.warning("股票基础信息落库失败: %s", e)

        today = date.today()
        filtered: List[Stock] = []
        for s in stocks:
            if exclude_st and s.is_st:
                continue
            if boards and s.board.value not in boards:
                continue
            if exclude_new > 0 and s.list_date:
                age_days = (today - s.list_date).days
                if age_days < exclude_new:
                    continue
            filtered.append(s)

        logger.info(
            "股票池过滤: 原始 %d, 过滤后 %d (boards=%s, st=%s)",
            len(stocks), len(filtered), boards or "ALL", exclude_st,
        )
        if limit and limit > 0:
            filtered = filtered[:limit]
        return filtered

    def _evaluate_one(self, ctx: StrategyContext) -> Optional[dict]:
        """对单只股票跑所有策略，综合加权得分。

        语义：
        - 每个策略产出 (passed, score, reason)
        - total_score = Σ(weight_i * score_i) / Σ(weight_i)
        - 硬性门槛：至少有一个策略 pass，且综合得分 >= min_score
          （默认 min_score=0.5，可通过 output.min_score 配置）
        """
        total_weight = sum(s.weight for s in self.strategies) or 1.0
        total_score = 0.0
        reasons = []
        any_passed = False
        detail_scores = {}

        for strat in self.strategies:
            res = strat.evaluate(ctx)
            if res.passed:
                any_passed = True
            total_score += res.score * strat.weight
            detail_scores[strat.name] = res.score
            reasons.append(f"[{strat.name}] {res.reason}")

        normalized_score = total_score / total_weight
        min_score = float(self.settings.output.get("min_score", 0.5))

        if not any_passed or normalized_score < min_score:
            return None

        return {
            "code": ctx.stock.code,
            "name": ctx.stock.name,
            "board": ctx.stock.board.value,
            "total_score": round(normalized_score, 4),
            **{f"score_{k}": round(v, 4) for k, v in detail_scores.items()},
            "reasons": " | ".join(reasons),
        }

    # ---------------- 辅助 ----------------
    def _need_kline(self) -> bool:
        return any(s.name in ("technical",) for s in self.strategies)

    def _need_money_flow(self) -> bool:
        return any(s.name == "money_flow" for s in self.strategies)

    def _max_money_flow_days(self) -> int:
        days = 5
        for s in self.strategies:
            if s.name == "money_flow":
                days = max(days, int(s.params.get("main_inflow_days", 0) or 0), 5)
        return days
