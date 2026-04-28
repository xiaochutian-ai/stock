from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from astock.config import Settings
from astock.engine.screener import ScreeningEngine
from astock.models import Board, Stock
from astock.strategy.context import StrategyContext
from astock.webapi.schemas import RunCreateRequest


def _build_run_settings(base_settings: Settings, params: Dict[str, Any]) -> Settings:
    """Build a Settings instance for a stored run snapshot.

    The run_cache stores only a small params snapshot; results and details are recomputed
    on-demand to keep the cache lightweight.
    """
    strategies = params.get("strategies") or base_settings.strategies
    output = dict(base_settings.output)
    min_score = (params.get("output") or {}).get("min_score", None)
    if min_score is not None:
        output["min_score"] = min_score

    return replace(
        base_settings,
        strategies=strategies,
        output=output,
    )


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
    params = snapshot.get("params") or {}
    settings = _build_run_settings(base_settings, params)
    engine = ScreeningEngine(settings=settings, provider=provider, repository=repository)
    return engine.run(limit=params.get("limit"), kline_days=int(params.get("kline_days") or 120))


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
    params = snapshot.get("params") or {}
    settings = _build_run_settings(base_settings, params)
    engine = ScreeningEngine(settings=settings, provider=provider, repository=repository)

    # Ensure the code exists in the computed results (also implicitly validates params).
    results = engine.run(limit=params.get("limit"), kline_days=int(params.get("kline_days") or 120))
    if not any(item.get("code") == code for item in results):
        raise KeyError("result not found")

    # Minimal on-demand "detail" snapshot based on current provider data.
    stocks = provider.list_stocks() if provider is not None else []
    stock: Optional[Stock] = next((s for s in stocks if s.code == code), None)
    if stock is None:
        stock = Stock(code=code, name="", board=Board.from_code(code))

    kline_days = int(params.get("kline_days") or 120)
    end = date.today()
    start = end - timedelta(days=kline_days * 2)

    enabled_strategy_names = {s.name for s in engine.strategies}
    need_kline = "technical" in enabled_strategy_names
    need_money = "money_flow" in enabled_strategy_names

    kline = provider.get_kline(code, start=start, end=end, adjust="qfq") if need_kline else None
    financial = provider.get_financial(code) if provider is not None else None

    mf_days = 5
    if need_money:
        for strat in engine.strategies:
            if strat.name == "money_flow":
                mf_days = max(mf_days, int(strat.params.get("main_inflow_days", 0) or 0), 5)
    money_flows = provider.get_money_flow(code, days=mf_days) if need_money else []

    ctx = StrategyContext(stock=stock, kline=kline, financial=financial, money_flows=money_flows)
    strategies = []
    for strat in engine.strategies:
        res = strat.evaluate(ctx)
        strategies.append(
            {
                "name": strat.name,
                "passed": bool(res.passed),
                "score": float(res.score),
                "reason": res.reason,
                "details": dict(res.details or {}),
            }
        )

    kline_payload: Any = None
    if kline is not None and getattr(kline, "df", None) is not None:
        df = kline.df.copy()
        # Ensure json-serializable "date" column.
        df = df.reset_index().rename(columns={"index": "date"})
        df["date"] = df["date"].astype(str)
        kline_payload = {"code": code, "items": df.tail(120).to_dict(orient="records")}

    return {
        "stock": {"code": stock.code, "name": stock.name, "board": stock.board.value},
        "strategies": strategies,
        "kline": kline_payload,
    }
