from __future__ import annotations

import threading
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from astock.config import Settings
from astock.datasource.base import DataProvider
from astock.models import Board, Financial, KLine, MoneyFlow, Stock

def _run_payload():
    return {
        "limit": 2,
        "kline_days": 60,
        "output": {"min_score": 0.1},
        "strategies": [
            {"name": "technical", "enabled": True, "weight": 0.4, "params": {"ma_bull": True}},
            {"name": "fundamental", "enabled": True, "weight": 0.3, "params": {"pe_max": 50}},
            {
                "name": "money_flow",
                "enabled": True,
                "weight": 0.3,
                "params": {"main_inflow_days": 3, "min_inflow_amount": 1000000},
            },
        ],
    }


def _wait_for_terminal_snapshot(client, run_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snapshot = client.app.state.run_cache[run_id]
        if snapshot["status"] in {"succeeded", "failed", "cancelled"}:
            return snapshot
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach terminal state")


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        (lambda payload: payload["strategies"][0].__setitem__("weight", -0.1), "weight"),
        (lambda payload: payload["output"].__setitem__("min_score", 1.2), "min_score"),
        (lambda payload: payload.__setitem__("kline_days", 0), "kline_days"),
        (lambda payload: payload.__setitem__("limit", 0), "limit"),
    ],
)
def test_create_run_rejects_invalid_boundaries(client, mutate, expected_fragment):
    payload = _run_payload()
    mutate(payload)

    response = client.post("/api/runs", json=payload)

    assert response.status_code == 422
    assert expected_fragment in response.text


def test_create_run_maps_expected_domain_errors_to_bad_request(client):
    non_raising_client = TestClient(client.app, raise_server_exceptions=False)
    payload = _run_payload()
    payload["strategies"] = [{"name": "unknown", "enabled": True, "weight": 1.0, "params": {}}]

    response = non_raising_client.post("/api/runs", json=payload)

    assert response.status_code == 400
    assert "Unknown strategy" in response.text


def test_create_run_stores_results_and_details_snapshot_in_run_cache(client):
    response = client.post("/api/runs", json=_run_payload())

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    snapshot = _wait_for_terminal_snapshot(client, run_id)

    assert snapshot["status"] == "succeeded"
    assert snapshot["results"]
    assert len(snapshot["results"]) == snapshot["result_count"]

    first_code = snapshot["results"][0]["code"]
    assert first_code in snapshot["details"]
    detail = snapshot["details"][first_code]
    assert detail["stock"]["code"] == first_code
    assert "strategies" in detail
    assert "kline" in detail


class SlowShutdownProvider(DataProvider):
    name = "slow-shutdown"

    def __init__(self):
        self.block_event = threading.Event()

    def list_stocks(self):
        return [Stock(code="600519", name="贵州茅台", board=Board.MAIN_BOARD)]

    def get_kline(self, code, start=None, end=None, adjust="qfq"):
        _ = (code, start, end, adjust)
        self.block_event.wait(timeout=5)
        index = pd.date_range(start="2026-04-20", periods=5, freq="B")
        df = pd.DataFrame(
            {
                "open": [10, 11, 12, 13, 14],
                "high": [11, 12, 13, 14, 15],
                "low": [9, 10, 11, 12, 13],
                "close": [10.5, 11.5, 12.5, 13.5, 14.5],
                "volume": [1000, 1100, 1200, 1300, 1400],
                "amount": [10500, 12650, 15000, 17550, 20300],
                "pct_change": [0.0, 1.0, 1.0, 1.0, 1.0],
                "turnover_rate": [1, 1, 1, 1, 1],
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
            MoneyFlow(code=code, trade_date=pd.Timestamp("2026-04-27").date(), main_net_inflow=2_000_000)
            for _ in range(days)
        ]


def test_shutdown_cancels_inflight_runs(web_settings: Settings, tmp_path: Path):
    from astock.webapi.app import create_app

    provider = SlowShutdownProvider()
    history_path = tmp_path / "web_history.db"
    app = create_app(settings=web_settings, provider=provider, history_db_path=str(history_path))

    with TestClient(app) as client:
        response = client.post("/api/runs", json=_run_payload())
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        time.sleep(0.1)
        assert client.app.state.run_cache[run_id]["status"] in {"pending", "running"}

    snapshot = app.state.run_cache[run_id]
    assert snapshot["status"] == "cancelled"
