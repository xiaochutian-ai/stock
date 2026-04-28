from __future__ import annotations

import time

import pytest


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


@pytest.fixture
def run_payload():
    return _run_payload()


def _wait_for_terminal_snapshot(client, run_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snapshot = client.app.state.run_cache[run_id]
        if snapshot["status"] in {"succeeded", "failed", "cancelled"}:
            return snapshot
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach terminal state")


def test_create_run_returns_run_id_and_async_status(client, run_payload):
    response = client.post("/api/runs", json=run_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"]
    assert payload["status"] in {"pending", "running", "succeeded"}

    snapshot = _wait_for_terminal_snapshot(client, payload["run_id"])
    assert snapshot["status"] == "succeeded"
    assert snapshot["result_count"] >= 1


def test_result_list_and_detail_are_available_after_run(client, run_payload):
    create_response = client.post("/api/runs", json=run_payload)
    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]
    _wait_for_terminal_snapshot(client, run_id)

    list_response = client.get(f"/api/runs/{run_id}/results")
    assert list_response.status_code == 200
    results = list_response.json()["items"]
    assert results
    assert results[0]["code"]

    detail_response = client.get(f"/api/runs/{run_id}/results/{results[0]['code']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["stock"]["code"] == results[0]["code"]
    assert "strategies" in detail
    assert "kline" in detail
