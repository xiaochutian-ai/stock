from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from astock.webapi.schemas import RunCreateRequest, RunCreateResponse
from astock.webapi.services.run_service import (
    create_run,
    get_run_result_detail,
    get_run_results,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunCreateResponse)
def create_run_endpoint(request: Request, payload: RunCreateRequest) -> RunCreateResponse:
    try:
        result = create_run(
            base_settings=request.app.state.base_settings,
            request=payload,
            provider=request.app.state.provider,
            repository=request.app.state.repository,
            run_cache=request.app.state.run_cache,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return RunCreateResponse(**result)


@router.get("/{run_id}/results")
def get_run_results_endpoint(request: Request, run_id: str) -> dict:
    try:
        items = get_run_results(
            run_id=run_id,
            base_settings=request.app.state.base_settings,
            provider=request.app.state.provider,
            repository=request.app.state.repository,
            run_cache=request.app.state.run_cache,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="run not found",
        ) from exc
    return {"items": items}


@router.get("/{run_id}/results/{code}")
def get_run_result_detail_endpoint(request: Request, run_id: str, code: str) -> dict:
    try:
        return get_run_result_detail(
            run_id=run_id,
            code=code,
            base_settings=request.app.state.base_settings,
            provider=request.app.state.provider,
            repository=request.app.state.repository,
            run_cache=request.app.state.run_cache,
        )
    except KeyError as exc:
        detail = str(exc).strip("'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        ) from exc
