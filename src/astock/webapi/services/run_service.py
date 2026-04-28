from __future__ import annotations

import threading
from datetime import datetime, timezone
from dataclasses import replace
from typing import Any, Dict, List
from uuid import uuid4

from astock.config import Settings
from astock.engine.screener import RunCancelledError, ScreeningEngine
from astock.strategy import get_strategy
from astock.webapi.schemas import RunCreateRequest


def create_run(
    base_settings: Settings,
    request: RunCreateRequest,
    provider: Any = None,
    repository: Any = None,
    run_cache: Dict[str, Dict[str, Any]] | None = None,
    run_tasks: Dict[str, Dict[str, Any]] | None = None,
    history_store: Any = None,
) -> Dict[str, Any]:
    strategy_configs = [item.model_dump() for item in request.strategies]
    for strategy in request.strategies:
        get_strategy(strategy.name, params=strategy.params, weight=strategy.weight)

    run_id = uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    response = {
        "run_id": run_id,
        "status": "pending",
        "result_count": 0,
    }
    params = {
        "limit": request.limit,
        "kline_days": request.kline_days,
        "output": {"min_score": request.output.min_score},
        "strategies": strategy_configs,
    }
    if run_cache is not None:
        run_cache[run_id] = {
            "status": "pending",
            "result_count": 0,
            "results": [],
            "details": {},
            "created_at": created_at,
            "params": params,
        }
    if run_tasks is None:
        return response

    cancel_event = threading.Event()
    worker = threading.Thread(
        target=_run_worker,
        args=(
            run_id,
            base_settings,
            request,
            provider,
            repository,
            run_cache,
            run_tasks,
            history_store,
            cancel_event,
        ),
        daemon=True,
        name=f"astock-run-{run_id}",
    )
    run_tasks[run_id] = {"thread": worker, "cancel_event": cancel_event}
    worker.start()
    return response


def get_run_results(
    *,
    run_id: str,
    base_settings: Settings,
    provider: Any,
    repository: Any,
    run_cache: Dict[str, Dict[str, Any]],
) -> List[dict]:
    snapshot = run_cache.get(run_id)
    if snapshot is None:
        raise KeyError("run not found")
    results = snapshot.get("results")
    if results is None:
        raise KeyError("run snapshot not found")
    return list(results)


def get_run_result_detail(
    *,
    run_id: str,
    code: str,
    base_settings: Settings,
    provider: Any,
    repository: Any,
    run_cache: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    snapshot = run_cache.get(run_id)
    if snapshot is None:
        raise KeyError("run not found")
    details = snapshot.get("details") or {}
    if code not in details:
        raise KeyError("result not found")
    return details[code]


def shutdown_run_tasks(
    run_tasks: Dict[str, Dict[str, Any]] | None,
    run_cache: Dict[str, Dict[str, Any]] | None,
    timeout: float = 1.0,
) -> None:
    if run_tasks is None:
        return
    for run_id, task in list(run_tasks.items()):
        cancel_event = task.get("cancel_event")
        thread = task.get("thread")
        snapshot = (run_cache or {}).get(run_id)
        if snapshot and snapshot.get("status") in {"pending", "running"}:
            snapshot["status"] = "cancelled"
        if cancel_event is not None:
            cancel_event.set()
        if thread is not None:
            thread.join(timeout=timeout)


def _run_worker(
    run_id: str,
    base_settings: Settings,
    request: RunCreateRequest,
    provider: Any,
    repository: Any,
    run_cache: Dict[str, Dict[str, Any]] | None,
    run_tasks: Dict[str, Dict[str, Any]],
    history_store: Any,
    cancel_event: threading.Event,
) -> None:
    assert run_cache is not None
    snapshot = run_cache[run_id]
    snapshot["status"] = "running"

    strategy_configs = [item.model_dump() for item in request.strategies]
    output = dict(base_settings.output)
    if request.output.min_score is not None:
        output["min_score"] = request.output.min_score

    run_settings = replace(
        base_settings,
        strategies=strategy_configs or base_settings.strategies,
        output=output,
    )

    try:
        engine = ScreeningEngine(
            settings=run_settings,
            provider=provider,
            repository=repository,
            cancel_checker=cancel_event.is_set,
        )
        results, details = engine.run_with_details(limit=request.limit, kline_days=request.kline_days)
        snapshot["status"] = "succeeded"
        snapshot["result_count"] = len(results)
        snapshot["results"] = results
        snapshot["details"] = details

        if history_store is not None:
            summary = {
                "result_count": snapshot["result_count"],
                "top_codes": [item["code"] for item in snapshot["results"][:5]],
            }
            history_store.save_run(
                {
                    "run_id": run_id,
                    "created_at": snapshot["created_at"],
                    "status": snapshot["status"],
                    "params": snapshot["params"],
                    "summary": summary,
                    "results": snapshot["results"],
                    "details": snapshot["details"],
                }
            )
    except RunCancelledError:
        snapshot["status"] = "cancelled"
        return
    except Exception as exc:
        snapshot["status"] = "failed"
        snapshot["error"] = str(exc)
        return
    finally:
        run_tasks.pop(run_id, None)
