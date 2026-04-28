from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyOption(BaseModel):
    name: str


class MetaOptionResponse(BaseModel):
    datasources: List[str]
    storages: List[str]
    strategies: List[StrategyOption]
    defaults: Dict[str, Any]


class RunStrategyConfig(BaseModel):
    name: str
    enabled: bool = True
    weight: float = 1.0
    params: Dict[str, Any] = Field(default_factory=dict)


class RunOutputConfig(BaseModel):
    min_score: Optional[float] = None


class RunCreateRequest(BaseModel):
    limit: Optional[int] = None
    kline_days: int = 120
    output: RunOutputConfig = Field(default_factory=RunOutputConfig)
    strategies: List[RunStrategyConfig] = Field(default_factory=list)


class RunCreateResponse(BaseModel):
    run_id: str
    status: str
    result_count: int
