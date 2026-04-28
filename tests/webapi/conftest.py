from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from astock.config import Settings
from astock.datasource.base import DataProvider
from astock.models import Board, Financial, KLine, MoneyFlow, Stock


class WebMockProvider(DataProvider):
    name = "mock"

    def list_stocks(self):
        return [
            Stock(code="600519", name="贵州茅台", board=Board.MAIN_BOARD),
            Stock(code="000001", name="平安银行", board=Board.MAIN_BOARD),
        ]

    def get_kline(self, code, start=None, end=None, adjust="qfq"):
        _ = adjust
        end_date = end or date(2026, 4, 27)
        start_date = start or (end_date - timedelta(days=240))
        index = pd.date_range(start=start_date, end=end_date, freq="B")
        if len(index) == 0:
            index = pd.DatetimeIndex([pd.Timestamp(end_date)])
        periods = len(index)
        close = [10.0 + i * 0.2 for i in range(periods)]
        df = pd.DataFrame(
            {
                "open": [price - 0.1 for price in close],
                "high": [price + 0.3 for price in close],
                "low": [price - 0.3 for price in close],
                "close": close,
                "volume": [1000 + i * 100 for i in range(periods)],
                "amount": [price * (1000 + i * 100) for i, price in enumerate(close)],
                "pct_change": [0.0] + [
                    (close[i] - close[i - 1]) / close[i - 1] * 100 for i in range(1, periods)
                ],
                "turnover_rate": [1.0 + i * 0.05 for i in range(periods)],
            },
            index=index,
        )
        df.index.name = "date"
        return KLine(code=code, df=df)

    def get_financial(self, code: str):
        return Financial(code=code, pe_ttm=20.0, pb=2.0, roe=0.15)

    def get_financials_batch(self, codes):
        return [Financial(code=code, pe_ttm=20.0, pb=2.0, roe=0.15) for code in codes]

    def get_money_flow(self, code: str, days: int = 5):
        end_date = date(2026, 4, 27)
        return [
            MoneyFlow(
                code=code,
                trade_date=end_date - timedelta(days=days - i - 1),
                main_net_inflow=1_000_000 + i * 500_000,
            )
            for i in range(days)
        ]


@pytest.fixture
def web_settings() -> Settings:
    return Settings(
        datasource={"name": "mock"},
        storage={"name": "sqlite", "options": {"url": "sqlite:///:memory:"}},
        strategies=[
            {"name": "technical", "enabled": True, "weight": 0.4, "params": {"ma_bull": True}},
            {"name": "fundamental", "enabled": True, "weight": 0.3, "params": {"pe_max": 50}},
            {
                "name": "money_flow",
                "enabled": True,
                "weight": 0.3,
                "params": {"main_inflow_days": 3, "min_inflow_amount": 1000000},
            },
        ],
        market={"boards": ["main_board"], "exclude_st": True},
        output={"format": "console", "top_n": 10, "min_score": 0.1},
        logging_cfg={"level": "WARNING"},
    )


@pytest.fixture
def client(web_settings: Settings, tmp_path: Path):
    from astock.webapi.app import create_app

    history_path = tmp_path / "web_history.db"
    app = create_app(
        settings=web_settings,
        provider=WebMockProvider(),
        history_db_path=str(history_path),
    )
    return TestClient(app)
