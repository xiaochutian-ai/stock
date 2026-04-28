from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict
from uuid import uuid4

from astock.config import Settings
from astock.engine.screener import ScreeningEngine
from astock.webapi.schemas import RunCreateRequest


def create_run(
    base_settings: Settings,
    request: RunCreateRequest,
    provider: Any = None,
    repository: Any = None,
    run_cache: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    strategy_configs = [item.model_dump() for item in request.strategies]
    output = dict(base_settings.output)
    if request.output.min_score is not None:
        output["min_score"] = request.output.min_score

    run_settings = replace(
        base_settings,
        strategies=strategy_configs or base_settings.strategies,
        output=output,
    )
    engine = ScreeningEngine(
        settings=run_settings,
        provider=provider,
        repository=repository,
    )
    results = engine.run(limit=request.limit, kline_days=request.kline_days)

    run_id = uuid4().hex
    payload = {
        "run_id": run_id,
        "status": "succeeded",
        "result_count": len(results),
    }
    if run_cache is not None:
        run_cache[run_id] = {
            "status": payload["status"],
            "result_count": payload["result_count"],
            "params": {
                "limit": request.limit,
                "kline_days": request.kline_days,
                "output": {"min_score": request.output.min_score},
                "strategies": strategy_configs,
            },
        }
    return payload
