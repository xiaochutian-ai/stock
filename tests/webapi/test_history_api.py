from __future__ import annotations


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


def test_history_endpoints_return_saved_run_snapshots(client):
    create_response = client.post("/api/runs", json=_run_payload())

    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]

    list_response = client.get("/api/history")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["run_id"] == run_id

    detail_response = client.get(f"/api/history/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["run_id"] == run_id
    assert detail["results"]
    assert detail["details"]
