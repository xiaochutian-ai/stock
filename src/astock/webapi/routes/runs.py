from __future__ import annotations

from fastapi import APIRouter, Request

from astock.webapi.schemas import RunCreateRequest, RunCreateResponse
from astock.webapi.services.run_service import create_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunCreateResponse)
def create_run_endpoint(request: Request, payload: RunCreateRequest) -> RunCreateResponse:
    result = create_run(
        base_settings=request.app.state.base_settings,
        request=payload,
        provider=request.app.state.provider,
        repository=request.app.state.repository,
        run_cache=request.app.state.run_cache,
    )
    return RunCreateResponse(**result)
