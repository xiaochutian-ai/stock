from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class StrategyOption(BaseModel):
    name: str


class MetaOptionResponse(BaseModel):
    datasources: List[str]
    storages: List[str]
    strategies: List[StrategyOption]
    defaults: Dict[str, Any]
