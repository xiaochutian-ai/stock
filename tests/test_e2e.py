"""端到端测试：用内存 mock 的 DataProvider 验证策略/引擎/输出完整链路。

不依赖真实网络，保证核心逻辑在任何环境都能跑通。
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List

import numpy as np
import pandas as pd

from astock.config import Settings
from astock.datasource.base import DataProvider
from astock.engine import ScreeningEngine
from astock.models import Board, Financial, KLine, MoneyFlow, Stock
from astock.output import format_results

logging.basicConfig(level=logging.WARNING)


def _make_kline(code: str, days: int, trend: str = "up") -> KLine:
    """生成一条模拟 K 线。trend=up 会形成多头排列 + MACD 金叉。"""
    end = date.today()
    idx = pd.date_range(end=end, periods=days, freq="B")
    rng = np.random.RandomState(hash(code) & 0xFFFFFFFF)
    if trend == "up":
        base = np.linspace(10, 20, days) + rng.randn(days) * 0.2
    elif trend == "down":
        base = np.linspace(20, 10, days) + rng.randn(days) * 0.2
    else:
        base = 15 + rng.randn(days) * 0.5
    close = base
    df = pd.DataFrame(
        {
            "open": close + rng.randn(days) * 0.1,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": (1e6 + rng.rand(days) * 1e5),
            "amount": close * 1e6,
            "pct_change": np.concatenate([[0], np.diff(close) / close[:-1] * 100]),
            "turnover_rate": rng.rand(days) * 3,
        },
        index=idx,
    )
    df.index.name = "date"
    return KLine(code=code, df=df)


class MockProvider(DataProvider):
    name = "mock"

    def list_stocks(self) -> List[Stock]:
        return [
            Stock(code="600519", name="贵州茅台", board=Board.MAIN_BOARD),
            Stock(code="000001", name="平安银行", board=Board.MAIN_BOARD),
            Stock(code="300750", name="宁德时代", board=Board.CHINEXT),
            Stock(code="000651", name="格力电器", board=Board.MAIN_BOARD),
            Stock(code="600036", name="招商银行", board=Board.MAIN_BOARD),
        ]

    def get_kline(self, code, start=None, end=None, adjust="qfq") -> KLine:
        trend = "up" if code in ("600519", "300750", "600036") else "flat"
        return _make_kline(code, days=100, trend=trend)

    def get_financial(self, code: str) -> Financial:
        return Financial(code=code, pe_ttm=25.0, pb=3.0, roe=0.15)

    def get_financials_batch(self, codes):
        # 给不同股票不同的估值
        preset = {
            "600519": Financial(code="600519", pe_ttm=30.0, pb=8.0, roe=0.30),
            "000001": Financial(code="000001", pe_ttm=6.0, pb=0.6, roe=0.12),
            "300750": Financial(code="300750", pe_ttm=28.0, pb=5.0, roe=0.20),
            "000651": Financial(code="000651", pe_ttm=8.0, pb=2.0, roe=0.25),
            "600036": Financial(code="600036", pe_ttm=5.0, pb=0.9, roe=0.15),
        }
        return [preset.get(c, Financial(code=c)) for c in codes]

    def get_money_flow(self, code: str, days: int = 5) -> List[MoneyFlow]:
        end = date.today()
        # 让 600519 / 300750 连续 3 天净流入
        pattern = [1e7, 2e7, 5e6] if code in ("600519", "300750") else [-1e6, -5e6, -2e6]
        result = []
        for i, v in enumerate(pattern):
            result.append(
                MoneyFlow(
                    code=code,
                    trade_date=end - timedelta(days=len(pattern) - 1 - i),
                    main_net_inflow=v,
                )
            )
        return result


def main():
    settings = Settings(
        datasource={"name": "mock"},
        storage={"name": "sqlite", "options": {"url": "sqlite:///:memory:"}},
        strategies=[
            {"name": "technical", "enabled": True, "weight": 0.4,
             "params": {"ma_bull": True, "macd_gold_cross": True, "rsi_range": [20, 80]}},
            {"name": "fundamental", "enabled": True, "weight": 0.3,
             "params": {"pe_max": 50, "pb_max": 10, "roe_min": 0.10}},
            {"name": "money_flow", "enabled": True, "weight": 0.3,
             "params": {"main_inflow_days": 3, "min_inflow_amount": 1_000_000}},
        ],
        market={"boards": ["main_board", "chinext"], "exclude_st": True},
        output={"format": "console", "top_n": 10, "min_score": 0.5},
    )

    engine = ScreeningEngine(settings, provider=MockProvider())
    results = engine.run(kline_days=100)
    print(f"\n>>> 选出 {len(results)} 只股票")
    format_results(results, fmt="console", top_n=10)

    assert len(results) >= 1, "端到端测试失败：至少应该选出 1 只股票"
    # 600519 / 300750 满足全部三个维度，应排在前面
    top_codes = [r["code"] for r in results[:2]]
    assert "600519" in top_codes or "300750" in top_codes, \
        f"Top2 期望包含 600519/300750，实际 {top_codes}"
    print("\n✅ 端到端测试通过")


if __name__ == "__main__":
    main()
