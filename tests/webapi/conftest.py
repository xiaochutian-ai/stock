from __future__ import annotations

from datetime import date
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
        index = pd.date_range(end="2026-04-27", periods=5, freq="B")
        df = pd.DataFrame(
            {
                "open": [10, 11, 12, 13, 14],
                "high": [10.5, 11.5, 12.5, 13.5, 14.5],
                "low": [9.5, 10.5, 11.5, 12.5, 13.5],
                "close": [10, 11, 12, 13, 14],
                "volume": [1000, 1100, 1200, 1300, 1400],
                "amount": [10000, 12100, 14400, 16900, 19600],
                "pct_change": [0.0, 10.0, 9.0, 8.0, 7.0],
                "turnover_rate": [1.0, 1.1, 1.2, 1.3, 1.4],
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
        return [
            MoneyFlow(code=code, trade_date=date(2026, 4, 25), main_net_inflow=1_000_000),
            MoneyFlow(code=code, trade_date=date(2026, 4, 26), main_net_inflow=1_500_000),
            MoneyFlow(code=code, trade_date=date(2026, 4, 27), main_net_inflow=2_000_000),
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
