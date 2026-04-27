from __future__ import annotations

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


def test_create_run_returns_run_id_and_succeeded_status(client, run_payload):
    response = client.post("/api/runs", json=run_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["result_count"] >= 1
    assert payload["run_id"]


def test_result_list_and_detail_are_available_after_run(client, run_payload):
    create_response = client.post("/api/runs", json=run_payload)
    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]

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
