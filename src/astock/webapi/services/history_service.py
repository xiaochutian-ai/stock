from __future__ import annotations

from astock.webapi.history_store import HistoryStore


def list_history(store: HistoryStore) -> dict:
    return {"items": store.list_runs()}


def get_history_detail(store: HistoryStore, run_id: str) -> dict | None:
    return store.get_run(run_id)
