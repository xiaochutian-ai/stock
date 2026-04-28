from __future__ import annotations


def test_meta_options_returns_registry_data_and_defaults(client):
    response = client.get("/api/meta/options")

    assert response.status_code == 200
    payload = response.json()
    assert "sqlite" in payload["storages"]
    assert "akshare" in payload["datasources"]
    assert any(item["name"] == "technical" for item in payload["strategies"])
    assert payload["defaults"]["output"]["min_score"] == 0.1
