"""akshare 数据源实现。

akshare 是免费开源的 A 股数据聚合库，无需 token。
官网: https://akshare.akfamily.xyz
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models import Board, Financial, KLine, MoneyFlow, Stock
from .base import DataProvider
from .registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("akshare")
class AkshareProvider(DataProvider):
    """基于 akshare 的 A 股数据源实现。"""

    def __init__(self, options: Optional[dict] = None):
        super().__init__(options)
        # 延迟导入：用户不用 akshare 时不强制要求安装
        try:
            import akshare as ak
        except ImportError as e:
            raise ImportError(
                "akshare 未安装，请运行: pip install akshare"
            ) from e
        self._ak = ak
        self._retry_times = int(self.options.get("retry", 3))

    # ---------------- 股票列表 ----------------
    def list_stocks(self) -> List[Stock]:
        """获取 A 股股票列表。

        分别从上交所和深交所接口拉取股票列表，再在本地拼接。
        """
        sh_df = self._call(self._ak.stock_info_sh_name_code, symbol="主板A股")
        sz_df = self._call(self._ak.stock_info_sz_name_code, symbol="A股列表")

        frames = []
        if sh_df is not None and not sh_df.empty:
            frames.append(
                sh_df.loc[:, ["证券代码", "证券简称"]].rename(
                    columns={"证券代码": "code", "证券简称": "name"}
                )
            )
        if sz_df is not None and not sz_df.empty:
            frames.append(
                sz_df.loc[:, ["A股代码", "A股简称"]].rename(
                    columns={"A股代码": "code", "A股简称": "name"}
                )
            )

        if not frames:
            return []

        df = pd.concat(frames, ignore_index=True)

        stocks: List[Stock] = []
        for _, row in df.iterrows():
            code = str(row.get("code", "")).zfill(6)
            name = str(row.get("name", "")).strip()
            if not code or not name:
                continue
            is_st = ("ST" in name.upper()) or ("*ST" in name.upper())
            stocks.append(
                Stock(
                    code=code,
                    name=name,
                    board=Board.from_code(code),
                    is_st=is_st,
                )
            )
        logger.info("akshare: 拉取到 %d 只股票", len(stocks))
        # stocks的详情写入到文件中
        with open("akshare_stocks.txt", "w", encoding="utf-8") as f:
            for s in stocks:
                f.write(f"{s.code}\t{s.name}\t{s.board.value}\t{s.is_st}\n")
        return stocks

    # ---------------- K 线 ----------------
    def get_kline(
        self,
        code: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        adjust: str = "qfq",
    ) -> KLine:
        end = end or date.today()
        start = start or (end - timedelta(days=365))

        df = self._call(
            self._ak.stock_zh_a_hist,
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust=adjust,
        )
        if df is None or df.empty:
            return KLine(code=code, df=pd.DataFrame())

        # akshare 的列名是中文，统一改成英文规范
        rename_map = {
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
            "涨跌幅": "pct_change",
            "换手率": "turnover_rate",
        }
        df = df.rename(columns=rename_map)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
        # 仅保留关心列（缺失列补 0）
        for col in ["open", "high", "low", "close", "volume", "amount",
                    "pct_change", "turnover_rate"]:
            if col not in df.columns:
                df[col] = 0.0
        df = df[["open", "high", "low", "close", "volume", "amount",
                 "pct_change", "turnover_rate"]].astype(float)
        return KLine(code=code, df=df)

    # ---------------- 财务 ----------------
    def get_financial(self, code: str) -> Financial:
        """获取最新财务指标。

        使用 stock_individual_info_em 获取总市值/流通市值 + 基础信息；
        使用 stock_financial_abstract 获取财务摘要。
        因为单只查询较慢，推荐引擎层使用批量接口。
        """
        fin = Financial(code=code)
        try:
            info_df = self._call(self._ak.stock_individual_info_em, symbol=code)
            if info_df is not None and not info_df.empty:
                info = dict(zip(info_df["item"], info_df["value"]))
                fin = Financial(
                    code=code,
                    total_market_cap=_safe_float(info.get("总市值")),
                    float_market_cap=_safe_float(info.get("流通市值")),
                )
        except Exception as e:
            logger.warning("akshare: 获取 %s 个股信息失败: %s", code, e)
        return fin

    def get_financials_batch(self, codes: List[str]) -> List[Financial]:
        """使用 stock_zh_a_spot_em 一次性拉全市场估值，比单只查询快 100+ 倍。"""
        df = self._call(self._ak.stock_zh_a_spot_em)

        if df is None or df.empty:
            logger.warning(
                "akshare: 批量行情快照拉取失败或为空，返回占位 Financial（PE/PB 缺失）"
            )
            return [Financial(code=c) for c in codes]

        df = df.copy()
        df["代码"] = df["代码"].astype(str).str.zfill(6)
        df = df.set_index("代码")
        result: List[Financial] = []
        for code in codes:
            if code not in df.index:
                result.append(Financial(code=code))
                continue
            row = df.loc[code]
            result.append(
                Financial(
                    code=code,
                    pe_ttm=_safe_float(row.get("市盈率-动态")),
                    pb=_safe_float(row.get("市净率")),
                    total_market_cap=_safe_float(row.get("总市值")),
                    float_market_cap=_safe_float(row.get("流通市值")),
                )
            )
        return result

    # ---------------- 资金流 ----------------
    def get_money_flow(self, code: str, days: int = 5) -> List[MoneyFlow]:
        """获取个股近 N 日资金流向。"""
        try:
            # akshare 资金流接口需要带 sh/sz 前缀
            market = _infer_market_prefix(code)
            df = self._call(
                self._ak.stock_individual_fund_flow,
                stock=code,
                market=market,
            )
        except Exception as e:
            logger.warning("akshare: 获取 %s 资金流失败: %s", code, e)
            return []

        if df is None or df.empty:
            return []

        df = df.tail(days)
        result: List[MoneyFlow] = []
        for _, row in df.iterrows():
            trade_date = _parse_date(row.get("日期"))
            if trade_date is None:
                continue
            result.append(
                MoneyFlow(
                    code=code,
                    trade_date=trade_date,
                    main_net_inflow=_safe_float(row.get("主力净流入-净额")) or 0.0,
                    super_large_net=_safe_float(row.get("超大单净流入-净额")) or 0.0,
                    large_net=_safe_float(row.get("大单净流入-净额")) or 0.0,
                    medium_net=_safe_float(row.get("中单净流入-净额")) or 0.0,
                    small_net=_safe_float(row.get("小单净流入-净额")) or 0.0,
                )
            )
        return result

    # ---------------- 工具 ----------------
    def _call(self, func, *args, **kwargs):
        """带重试的接口调用。"""

        @retry(stop=stop_after_attempt(self._retry_times), wait=wait_fixed(1))
        def _inner():
            return func(*args, **kwargs)

        try:
            return _inner()
        except Exception as e:
            logger.error("akshare 调用 %s 失败: %s", getattr(func, "__name__", func), e)
            return None


# ---------------- 模块级工具 ----------------
def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        if isinstance(v, str):
            v = v.replace(",", "").strip()
            if v in ("", "-", "--"):
                return None
        f = float(v)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _parse_date(v) -> Optional[date]:
    if v is None:
        return None
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None


def _infer_market_prefix(code: str) -> str:
    """根据股票代码推断 akshare 资金流接口需要的市场参数。"""
    code = code.zfill(6)
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("0", "2", "3")):
        return "sz"
    if code.startswith(("4", "8")):
        return "bj"
    return "sh"
