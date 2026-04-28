from __future__ import annotations

from fastapi import APIRouter, Request

from astock.webapi.schemas import MetaOptionResponse
from astock.webapi.services.meta_service import build_meta_options

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/options", response_model=MetaOptionResponse)
def get_meta_options(request: Request) -> MetaOptionResponse:
    payload = build_meta_options(request.app.state.default_settings)
    return MetaOptionResponse(**payload)
