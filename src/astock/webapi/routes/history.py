from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from astock.webapi.services.history_service import get_history_detail, list_history

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def get_history(request: Request) -> dict:
    return list_history(request.app.state.history_store)


@router.get("/{run_id}")
def get_history_run(run_id: str, request: Request) -> dict:
    payload = get_history_detail(request.app.state.history_store, run_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="history not found",
        )
    return payload
