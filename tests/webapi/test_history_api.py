from __future__ import annotations

import time


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


def _wait_for_history_snapshot(client, run_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snapshot = client.app.state.run_cache[run_id]
        if snapshot["status"] == "succeeded":
            return snapshot
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not complete")


def test_history_endpoints_return_saved_run_snapshots(client):
    create_response = client.post("/api/runs", json=_run_payload())

    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]
    _wait_for_history_snapshot(client, run_id)

    list_response = client.get("/api/history")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["run_id"] == run_id

    detail_response = client.get(f"/api/history/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["run_id"] == run_id
    assert detail["results"]
    assert detail["details"]
