from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
    assert "未配置任何启用的策略" in response.text


def test_create_run_only_stores_metadata_in_run_cache(client):
    response = client.post("/api/runs", json=_run_payload())

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    snapshot = client.app.state.run_cache[run_id]

    assert "results" not in snapshot
    assert snapshot["status"] == "succeeded"
    assert snapshot["result_count"] == response.json()["result_count"]
