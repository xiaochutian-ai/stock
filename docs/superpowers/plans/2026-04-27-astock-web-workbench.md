# astock Web Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first, frontend/backend-separated Web workbench for `astock` that can configure a screening run, execute it through the existing engine, show results, inspect stock details, and browse run history.

**Architecture:** Add a `src/astock/webapi/` backend package that wraps the existing `ScreeningEngine` with FastAPI and a Web-only history store, while keeping the engine as the single source of screening logic. Add a separate `frontend/` React + Vite application that consumes the backend API for metadata, runs, results, detail snapshots, and history review.

**Tech Stack:** Python 3.9+, FastAPI, Pydantic, `pytest`, `ruff`, React, TypeScript, Vite, Vitest, Testing Library

---

## File Structure

- Modify: `pyproject.toml`
  - Add FastAPI runtime dependencies for the backend API
- Modify: `.gitignore`
  - Ignore `frontend/node_modules`, `frontend/dist`, and `.superpowers/`
- Modify: `src/astock/engine/screener.py`
  - Add a structured run method that preserves list results and stock detail snapshots for the Web API
- Create: `src/astock/webapi/__init__.py`
  - Backend package entrypoint
- Create: `src/astock/webapi/app.py`
  - FastAPI application factory and router registration
- Create: `src/astock/webapi/schemas.py`
  - Request/response models used by routes and frontend DTOs
- Create: `src/astock/webapi/routes/meta.py`
  - `/api/meta/options`
- Create: `src/astock/webapi/routes/runs.py`
  - `/api/runs`, `/api/runs/{run_id}`, `/api/runs/{run_id}/results`, `/api/runs/{run_id}/results/{code}`
- Create: `src/astock/webapi/routes/history.py`
  - `/api/history`, `/api/history/{run_id}`
- Create: `src/astock/webapi/services/meta_service.py`
  - Registry/config-to-metadata transformation
- Create: `src/astock/webapi/services/run_service.py`
  - Settings mapping, run execution, snapshot shaping
- Create: `src/astock/webapi/services/history_service.py`
  - History access helpers over the Web history store
- Create: `src/astock/webapi/history_store.py`
  - SQLite-backed run snapshot persistence for the Web layer
- Create: `tests/webapi/conftest.py`
  - Shared FastAPI test client and mock provider fixtures
- Create: `tests/webapi/test_meta_api.py`
  - Metadata API coverage
- Create: `tests/webapi/test_runs_api.py`
  - Run creation, result list, and result detail API coverage
- Create: `tests/webapi/test_history_api.py`
  - History listing and history detail API coverage
- Create: `frontend/package.json`
  - Frontend dependency and script manifest
- Create: `frontend/tsconfig.json`
  - TypeScript compiler config
- Create: `frontend/vite.config.ts`
  - Vite + Vitest configuration
- Create: `frontend/index.html`
  - Vite HTML entry
- Create: `frontend/src/main.tsx`
  - React bootstrap
- Create: `frontend/src/App.tsx`
  - Top-level router/layout
- Create: `frontend/src/types/api.ts`
  - TypeScript DTOs mirroring backend responses
- Create: `frontend/src/api/client.ts`
  - Fetch wrappers for backend endpoints
- Create: `frontend/src/store/useWorkbenchStore.ts`
  - App state for config, runs, details, and history
- Create: `frontend/src/components/StrategyConfigForm.tsx`
  - Run configuration form
- Create: `frontend/src/components/ResultsTable.tsx`
  - Result list table
- Create: `frontend/src/components/StockDetailPanel.tsx`
  - Detail side panel with score and chart sections
- Create: `frontend/src/components/HistoryList.tsx`
  - History summary list
- Create: `frontend/src/pages/WorkbenchPage.tsx`
  - Workbench page composing form, results, and detail
- Create: `frontend/src/pages/HistoryPage.tsx`
  - History page composing history list and history detail
- Create: `frontend/src/__tests__/workbench.test.tsx`
  - Workbench flow coverage
- Create: `frontend/src/__tests__/history.test.tsx`
  - History page coverage
- Modify: `README.md`
  - Add Web startup instructions
- Reference: `docs/superpowers/specs/2026-04-27-astock-web-design.md`
  - Approved design specification

### Task 1: Add Backend API Dependencies And Failing Tests

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/webapi/conftest.py`
- Create: `tests/webapi/test_meta_api.py`
- Create: `tests/webapi/test_runs_api.py`
- Reference: `docs/superpowers/specs/2026-04-27-astock-web-design.md`

- [ ] **Step 1: Add backend API dependencies to `pyproject.toml`**

Update the dependency list to include FastAPI and an ASGI server:

```toml
[project]
dependencies = [
    "akshare>=1.12.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "pyyaml>=6.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
    "SQLAlchemy>=2.0.0",
    "tenacity>=8.0.0",
    "tqdm>=4.65.0",
    "openpyxl>=3.1.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
]
```

- [ ] **Step 2: Write the shared backend API test fixtures**

Create `tests/webapi/conftest.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astock.config import Settings
from astock.datasource.base import DataProvider
from astock.models import Board, Financial, KLine, MoneyFlow, Stock


class WebMockProvider(DataProvider):
    name = "mock"

    def list_stocks(self):
        return [
            Stock(code="600519", name="贵州茅台", board=Board.MAIN_BOARD),
            Stock(code="000001", name="平安银行", board=Board.MAIN_BOARD),
        ]

    def get_kline(self, code, start=None, end=None, adjust="qfq"):
        import pandas as pd

        index = pd.date_range(end="2026-04-27", periods=5, freq="B")
        df = pd.DataFrame(
            {
                "open": [10, 11, 12, 13, 14],
                "high": [10.5, 11.5, 12.5, 13.5, 14.5],
                "low": [9.5, 10.5, 11.5, 12.5, 13.5],
                "close": [10, 11, 12, 13, 14],
                "volume": [1000, 1100, 1200, 1300, 1400],
                "amount": [10000, 12100, 14400, 16900, 19600],
                "pct_change": [0.0, 10.0, 9.0, 8.0, 7.0],
                "turnover_rate": [1.0, 1.1, 1.2, 1.3, 1.4],
            },
            index=index,
        )
        df.index.name = "date"
        return KLine(code=code, df=df)

    def get_financial(self, code: str):
        return Financial(code=code, pe_ttm=20.0, pb=2.0, roe=0.15)

    def get_financials_batch(self, codes):
        return [Financial(code=code, pe_ttm=20.0, pb=2.0, roe=0.15) for code in codes]

    def get_money_flow(self, code: str, days: int = 5):
        return [
            MoneyFlow(code=code, trade_date=date(2026, 4, 25), main_net_inflow=1_000_000),
            MoneyFlow(code=code, trade_date=date(2026, 4, 26), main_net_inflow=1_500_000),
            MoneyFlow(code=code, trade_date=date(2026, 4, 27), main_net_inflow=2_000_000),
        ]


@pytest.fixture
def web_settings(tmp_path: Path) -> Settings:
    return Settings(
        datasource={"name": "mock"},
        storage={"name": "sqlite", "options": {"url": "sqlite:///:memory:"}},
        strategies=[
            {"name": "technical", "enabled": True, "weight": 0.4, "params": {"ma_bull": True}},
            {"name": "fundamental", "enabled": True, "weight": 0.3, "params": {"pe_max": 50}},
            {
                "name": "money_flow",
                "enabled": True,
                "weight": 0.3,
                "params": {"main_inflow_days": 3, "min_inflow_amount": 1000000},
            },
        ],
        market={"boards": ["main_board"], "exclude_st": True},
        output={"format": "console", "top_n": 10, "min_score": 0.1},
        logging_cfg={"level": "WARNING"},
    )


@pytest.fixture
def client(web_settings: Settings, tmp_path: Path):
    from astock.webapi.app import create_app

    history_path = tmp_path / "web_history.db"
    app = create_app(
        settings=web_settings,
        provider=WebMockProvider(),
        history_db_path=str(history_path),
    )
    return TestClient(app)
```

- [ ] **Step 3: Write the failing metadata API test**

Create `tests/webapi/test_meta_api.py`:

```python
from __future__ import annotations


def test_meta_options_returns_registry_data_and_defaults(client):
    response = client.get("/api/meta/options")

    assert response.status_code == 200
    payload = response.json()
    assert "sqlite" in payload["storages"]
    assert "akshare" in payload["datasources"]
    assert any(item["name"] == "technical" for item in payload["strategies"])
    assert payload["defaults"]["output"]["min_score"] == 0.1
```

- [ ] **Step 4: Write the failing run API tests**

Create `tests/webapi/test_runs_api.py`:

```python
from __future__ import annotations


def test_create_run_returns_run_id_and_succeeded_status(client):
    response = client.post(
        "/api/runs",
        json={
            "limit": 2,
            "kline_days": 60,
            "output": {"min_score": 0.1},
            "strategies": [
                {"name": "technical", "enabled": True, "weight": 0.4, "params": {"ma_bull": True}},
                {"name": "fundamental", "enabled": True, "weight": 0.3, "params": {"pe_max": 50}},
                {
                    "name": "money_flow",
                    "enabled": True,
                    "weight": 0.3,
                    "params": {"main_inflow_days": 3, "min_inflow_amount": 1000000},
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["result_count"] >= 1
    assert payload["run_id"]


def test_result_list_and_detail_are_available_after_run(client):
    create_response = client.post(
        "/api/runs",
        json={
            "limit": 2,
            "kline_days": 60,
            "output": {"min_score": 0.1},
            "strategies": [
                {"name": "technical", "enabled": True, "weight": 0.4, "params": {"ma_bull": True}},
                {"name": "fundamental", "enabled": True, "weight": 0.3, "params": {"pe_max": 50}},
                {
                    "name": "money_flow",
                    "enabled": True,
                    "weight": 0.3,
                    "params": {"main_inflow_days": 3, "min_inflow_amount": 1000000},
                },
            ],
        },
    )
    run_id = create_response.json()["run_id"]

    list_response = client.get(f"/api/runs/{run_id}/results")
    assert list_response.status_code == 200
    results = list_response.json()["items"]
    assert results[0]["code"]

    detail_response = client.get(f"/api/runs/{run_id}/results/{results[0]['code']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["stock"]["code"] == results[0]["code"]
    assert "strategies" in detail
    assert "kline" in detail
```

- [ ] **Step 5: Run the backend API tests and verify RED**

Run: `pytest tests/webapi/test_meta_api.py tests/webapi/test_runs_api.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'astock.webapi'` or an import error from `create_app`.

- [ ] **Step 6: Commit the red tests and dependency manifest**

```bash
git add pyproject.toml tests/webapi/conftest.py tests/webapi/test_meta_api.py tests/webapi/test_runs_api.py
git commit -m "test: add web api red tests"
```

### Task 2: Implement The Backend App, Meta Endpoint, And Run Endpoints

**Files:**
- Create: `src/astock/webapi/__init__.py`
- Create: `src/astock/webapi/app.py`
- Create: `src/astock/webapi/schemas.py`
- Create: `src/astock/webapi/routes/meta.py`
- Create: `src/astock/webapi/routes/runs.py`
- Create: `src/astock/webapi/services/meta_service.py`
- Create: `src/astock/webapi/services/run_service.py`
- Modify: `src/astock/engine/screener.py`
- Test: `tests/webapi/test_meta_api.py`
- Test: `tests/webapi/test_runs_api.py`

- [ ] **Step 1: Create the Web API package entrypoint**

Create `src/astock/webapi/__init__.py`:

```python
from .app import create_app

__all__ = ["create_app"]
```

- [ ] **Step 2: Define API request and response models**

Create `src/astock/webapi/schemas.py`:

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyConfigInput(BaseModel):
    name: str
    enabled: bool = True
    weight: float = 1.0
    params: Dict[str, Any] = Field(default_factory=dict)


class OutputConfigInput(BaseModel):
    min_score: float = 0.5


class RunRequest(BaseModel):
    datasource_name: Optional[str] = None
    storage_name: Optional[str] = None
    limit: Optional[int] = None
    kline_days: int = 120
    output: OutputConfigInput = Field(default_factory=OutputConfigInput)
    strategies: List[StrategyConfigInput]


class MetaOptionResponse(BaseModel):
    datasources: List[str]
    storages: List[str]
    strategies: List[Dict[str, Any]]
    defaults: Dict[str, Any]


class ResultItem(BaseModel):
    rank: int
    code: str
    name: str
    board: str
    total_score: float
    reasons: str
    score_breakdown: Dict[str, float]


class StrategyDetail(BaseModel):
    name: str
    passed: bool
    score: float
    reason: str
    details: Dict[str, Any]


class ResultDetail(BaseModel):
    stock: Dict[str, Any]
    summary: Dict[str, Any]
    strategies: List[StrategyDetail]
    kline: List[Dict[str, Any]]
    money_flows: List[Dict[str, Any]]


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    result_count: int
    params: Dict[str, Any]
```

- [ ] **Step 3: Extend `ScreeningEngine` to preserve detail snapshots**

Modify `src/astock/engine/screener.py` by adding a `run_with_details()` path next to the existing `run()`:

```python
    def run_with_details(self, limit: Optional[int] = None, kline_days: int = 120) -> dict:
        self._ensure_schema()
        stocks = self._prepare_universe(limit=limit)
        if not stocks:
            return {"results": [], "details": {}}

        financials_map = self._fetch_and_persist_financials(stocks)
        end = date.today()
        start = end - timedelta(days=kline_days * 2)
        need_kline = self._need_kline()
        need_money = self._need_money_flow()
        mf_days = self._max_money_flow_days() if need_money else 0

        results = []
        details = {}
        for stock in tqdm(stocks, desc="选股评估", ncols=80):
            kline = None
            money_flows = []
            if need_kline:
                kline = self.provider.get_kline(stock.code, start=start, end=end, adjust="qfq")
                if kline and len(kline) > 0:
                    self.repository.upsert_kline(kline)
            if need_money:
                money_flows = self.provider.get_money_flow(stock.code, days=mf_days)
                if money_flows:
                    self.repository.upsert_money_flows(money_flows)

            ctx = StrategyContext(
                stock=stock,
                kline=kline,
                financial=financials_map.get(stock.code),
                money_flows=money_flows,
            )
            snapshot = self._evaluate_one_with_snapshot(ctx)
            if snapshot is None:
                continue
            results.append(snapshot["result"])
            details[stock.code] = snapshot["detail"]

        results.sort(key=lambda item: item.get("total_score", 0.0), reverse=True)
        for idx, item in enumerate(results, start=1):
            item["rank"] = idx
            details[item["code"]]["summary"]["rank"] = idx
        return {"results": results, "details": details}
```

Also add `_evaluate_one_with_snapshot()` that keeps per-strategy `passed`, `score`, `reason`, and `details`, plus serialized `kline` rows and `money_flows`.

- [ ] **Step 4: Implement metadata and run services**

Create `src/astock/webapi/services/meta_service.py`:

```python
from __future__ import annotations

from astock.datasource import list_providers
from astock.storage import list_repositories
from astock.strategy import list_strategies


def build_meta_options(defaults: dict) -> dict:
    return {
        "datasources": list_providers(),
        "storages": list_repositories(),
        "strategies": [{"name": name} for name in list_strategies()],
        "defaults": defaults,
    }
```

Create `src/astock/webapi/services/run_service.py`:

```python
from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from astock.engine import ScreeningEngine


def build_runtime_settings(base_settings, request):
    settings = deepcopy(base_settings)
    if request.datasource_name:
        settings.datasource["name"] = request.datasource_name
    if request.storage_name:
        settings.storage["name"] = request.storage_name
    settings.strategies = [item.model_dump() for item in request.strategies]
    settings.output["min_score"] = request.output.min_score
    return settings


def execute_run(base_settings, request, provider=None, repository=None):
    settings = build_runtime_settings(base_settings, request)
    engine = ScreeningEngine(settings, provider=provider, repository=repository)
    snapshot = engine.run_with_details(limit=request.limit, kline_days=request.kline_days)
    return {
        "run_id": str(uuid4()),
        "status": "succeeded",
        "params": request.model_dump(),
        "results": snapshot["results"],
        "details": snapshot["details"],
    }
```

- [ ] **Step 5: Implement routes and the FastAPI app factory**

Create `src/astock/webapi/routes/meta.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Request

from astock.webapi.schemas import MetaOptionResponse
from astock.webapi.services.meta_service import build_meta_options

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/options", response_model=MetaOptionResponse)
def get_meta_options(request: Request):
    payload = build_meta_options(request.app.state.default_settings.model_dump())
    return MetaOptionResponse(**payload)
```

Create `src/astock/webapi/routes/runs.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from astock.webapi.schemas import ResultDetail, RunRequest, RunStatusResponse
from astock.webapi.services.run_service import execute_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunStatusResponse)
def create_run(payload: RunRequest, request: Request):
    run_snapshot = execute_run(
        base_settings=request.app.state.base_settings,
        request=payload,
        provider=request.app.state.provider,
        repository=request.app.state.repository,
    )
    request.app.state.run_cache[run_snapshot["run_id"]] = run_snapshot
    return RunStatusResponse(
        run_id=run_snapshot["run_id"],
        status=run_snapshot["status"],
        result_count=len(run_snapshot["results"]),
        params=run_snapshot["params"],
    )


@router.get("/{run_id}")
def get_run_status(run_id: str, request: Request):
    snapshot = request.app.state.run_cache.get(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": snapshot["run_id"],
        "status": snapshot["status"],
        "result_count": len(snapshot["results"]),
        "params": snapshot["params"],
    }


@router.get("/{run_id}/results")
def get_run_results(run_id: str, request: Request):
    snapshot = request.app.state.run_cache.get(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"items": snapshot["results"]}


@router.get("/{run_id}/results/{code}", response_model=ResultDetail)
def get_run_result_detail(run_id: str, code: str, request: Request):
    snapshot = request.app.state.run_cache.get(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="run not found")
    detail = snapshot["details"].get(code)
    if detail is None:
        raise HTTPException(status_code=404, detail="result not found")
    return ResultDetail(**detail)
```

Create `src/astock/webapi/app.py`:

```python
from __future__ import annotations

from fastapi import FastAPI

from astock.config import Settings
from astock.webapi.routes.meta import router as meta_router
from astock.webapi.routes.runs import router as runs_router


def create_app(settings: Settings, provider=None, repository=None, history_db_path: str = "data/web_history.db"):
    app = FastAPI(title="astock Web API")
    app.state.base_settings = settings
    app.state.default_settings = settings
    app.state.provider = provider
    app.state.repository = repository
    app.state.history_db_path = history_db_path
    app.state.run_cache = {}
    app.include_router(meta_router)
    app.include_router(runs_router)
    return app
```

- [ ] **Step 6: Run the backend API tests and verify GREEN**

Run: `pytest tests/webapi/test_meta_api.py tests/webapi/test_runs_api.py -q`

Expected: PASS with 3 passing tests.

- [ ] **Step 7: Run lint on the backend API files**

Run: `ruff check src/astock/webapi src/astock/engine/screener.py tests/webapi`

Expected: `All checks passed!`

- [ ] **Step 8: Commit the backend API implementation**

```bash
git add src/astock/webapi src/astock/engine/screener.py tests/webapi
git commit -m "feat: add astock web api skeleton"
```

### Task 3: Add Persistent Run History And History Endpoints

**Files:**
- Create: `src/astock/webapi/history_store.py`
- Create: `src/astock/webapi/services/history_service.py`
- Create: `src/astock/webapi/routes/history.py`
- Modify: `src/astock/webapi/routes/runs.py`
- Modify: `src/astock/webapi/app.py`
- Create: `tests/webapi/test_history_api.py`

- [ ] **Step 1: Write the failing history API test**

Create `tests/webapi/test_history_api.py`:

```python
from __future__ import annotations


def test_history_endpoints_return_saved_run_snapshots(client):
    create_response = client.post(
        "/api/runs",
        json={
            "limit": 2,
            "kline_days": 60,
            "output": {"min_score": 0.1},
            "strategies": [
                {"name": "technical", "enabled": True, "weight": 0.4, "params": {"ma_bull": True}},
                {"name": "fundamental", "enabled": True, "weight": 0.3, "params": {"pe_max": 50}},
                {
                    "name": "money_flow",
                    "enabled": True,
                    "weight": 0.3,
                    "params": {"main_inflow_days": 3, "min_inflow_amount": 1000000},
                },
            ],
        },
    )
    run_id = create_response.json()["run_id"]

    list_response = client.get("/api/history")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["run_id"] == run_id

    detail_response = client.get(f"/api/history/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["run_id"] == run_id
    assert detail["results"]
    assert detail["details"]
```

- [ ] **Step 2: Run the history test and verify RED**

Run: `pytest tests/webapi/test_history_api.py -q`

Expected: FAIL because `/api/history` is not implemented and runs are not yet persisted.

- [ ] **Step 3: Implement the SQLite-backed history store**

Create `src/astock/webapi/history_store.py`:

```python
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class HistoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )

    def save_run(self, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO web_runs
                (run_id, created_at, status, params_json, summary_json, results_json, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["run_id"],
                    payload["created_at"],
                    payload["status"],
                    json.dumps(payload["params"], ensure_ascii=False),
                    json.dumps(payload["summary"], ensure_ascii=False),
                    json.dumps(payload["results"], ensure_ascii=False),
                    json.dumps(payload["details"], ensure_ascii=False),
                ),
            )

    def list_runs(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id, created_at, status, summary_json FROM web_runs ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "run_id": run_id,
                "created_at": created_at,
                "status": status,
                **json.loads(summary_json),
            }
            for run_id, created_at, status, summary_json in rows
        ]

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, created_at, status, params_json, summary_json, results_json, details_json
                FROM web_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "created_at": row[1],
            "status": row[2],
            "params": json.loads(row[3]),
            "summary": json.loads(row[4]),
            "results": json.loads(row[5]),
            "details": json.loads(row[6]),
        }
```

- [ ] **Step 4: Implement history service and routes, then persist runs on create**

Create `src/astock/webapi/services/history_service.py`:

```python
from __future__ import annotations

from astock.webapi.history_store import HistoryStore


def list_history(store: HistoryStore) -> dict:
    return {"items": store.list_runs()}


def get_history_detail(store: HistoryStore, run_id: str) -> dict | None:
    return store.get_run(run_id)
```

Create `src/astock/webapi/routes/history.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from astock.webapi.services.history_service import get_history_detail, list_history

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def get_history(request: Request):
    return list_history(request.app.state.history_store)


@router.get("/{run_id}")
def get_history_run(run_id: str, request: Request):
    payload = get_history_detail(request.app.state.history_store, run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="history not found")
    return payload
```

Update `src/astock/webapi/app.py` to initialize the store:

```python
from astock.webapi.history_store import HistoryStore

app.state.history_store = HistoryStore(history_db_path)
```

Update `src/astock/webapi/routes/runs.py` to persist after creation:

```python
from datetime import datetime, timezone

summary = {
    "result_count": len(run_snapshot["results"]),
    "top_codes": [item["code"] for item in run_snapshot["results"][:5]],
}
request.app.state.history_store.save_run(
    {
        "run_id": run_snapshot["run_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": run_snapshot["status"],
        "params": run_snapshot["params"],
        "summary": summary,
        "results": run_snapshot["results"],
        "details": run_snapshot["details"],
    }
)
```

- [ ] **Step 5: Run the history API test and verify GREEN**

Run: `pytest tests/webapi/test_history_api.py -q`

Expected: PASS with 1 passing test.

- [ ] **Step 6: Run the full backend API suite**

Run: `pytest tests/webapi -q`

Expected: PASS with all Web API tests green.

- [ ] **Step 7: Commit the history persistence work**

```bash
git add src/astock/webapi tests/webapi
git commit -m "feat: persist web run history"
```

### Task 4: Scaffold The Frontend App And Write Failing UI Tests

**Files:**
- Modify: `.gitignore`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/__tests__/workbench.test.tsx`
- Create: `frontend/src/__tests__/history.test.tsx`

- [ ] **Step 1: Ignore frontend artifacts and visual-companion output**

Update `.gitignore`:

```gitignore
# Frontend artifacts
frontend/node_modules/
frontend/dist/

# Visual companion output
.superpowers/
```

- [ ] **Step 2: Create the frontend package manifest**

Create `frontend/package.json`:

```json
{
  "name": "astock-web-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.30.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.3.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "jsdom": "^25.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

- [ ] **Step 3: Add TypeScript and Vite config**

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

Create `frontend/vite.config.ts`:

```ts
import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
  server: {
    port: 5173,
  },
});
```

- [ ] **Step 4: Write the failing workbench UI test**

Create `frontend/src/__tests__/workbench.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";

import { WorkbenchPage } from "../pages/WorkbenchPage";

test("renders run form and result table regions", () => {
  render(<WorkbenchPage />);

  expect(screen.getByRole("heading", { name: "选股工作台" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始选股" })).toBeInTheDocument();
  expect(screen.getByText("结果列表")).toBeInTheDocument();
});
```

- [ ] **Step 5: Write the failing history UI test**

Create `frontend/src/__tests__/history.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";

import { HistoryPage } from "../pages/HistoryPage";

test("renders history page shell", () => {
  render(<HistoryPage />);

  expect(screen.getByRole("heading", { name: "运行历史" })).toBeInTheDocument();
  expect(screen.getByText("暂无历史记录")).toBeInTheDocument();
});
```

- [ ] **Step 6: Install frontend dependencies and run tests to verify RED**

Run:

```bash
cd frontend
npm install
npm test
```

Expected: FAIL because `WorkbenchPage` and `HistoryPage` do not exist yet.

- [ ] **Step 7: Commit the frontend scaffold and red tests**

```bash
git add .gitignore frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/src/__tests__
git commit -m "test: add frontend red tests"
```

### Task 5: Implement The Workbench Page, Store, And Results Table

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/store/useWorkbenchStore.ts`
- Create: `frontend/src/components/StrategyConfigForm.tsx`
- Create: `frontend/src/components/ResultsTable.tsx`
- Create: `frontend/src/pages/WorkbenchPage.tsx`
- Test: `frontend/src/__tests__/workbench.test.tsx`

- [ ] **Step 1: Define frontend DTOs**

Create `frontend/src/types/api.ts`:

```ts
export type StrategyConfigInput = {
  name: string;
  enabled: boolean;
  weight: number;
  params: Record<string, unknown>;
};

export type RunRequest = {
  limit?: number;
  kline_days: number;
  output: { min_score: number };
  strategies: StrategyConfigInput[];
};

export type ResultItem = {
  rank: number;
  code: string;
  name: string;
  board: string;
  total_score: number;
  reasons: string;
  score_breakdown: Record<string, number>;
};

export type RunStatus = {
  run_id: string;
  status: string;
  result_count: number;
  params: Record<string, unknown>;
};
```

- [ ] **Step 2: Implement the API client**

Create `frontend/src/api/client.ts`:

```ts
import type { ResultItem, RunRequest, RunStatus } from "../types/api";

const BASE_URL = "http://localhost:8000";

export async function fetchMetaOptions() {
  const response = await fetch(`${BASE_URL}/api/meta/options`);
  if (!response.ok) throw new Error("加载元数据失败");
  return response.json();
}

export async function createRun(payload: RunRequest): Promise<RunStatus> {
  const response = await fetch(`${BASE_URL}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("创建运行失败");
  return response.json();
}

export async function fetchRunResults(runId: string): Promise<{ items: ResultItem[] }> {
  const response = await fetch(`${BASE_URL}/api/runs/${runId}/results`);
  if (!response.ok) throw new Error("加载结果失败");
  return response.json();
}
```

- [ ] **Step 3: Implement the page state store**

Create `frontend/src/store/useWorkbenchStore.ts`:

```ts
import { createRun, fetchRunResults } from "../api/client";
import type { ResultItem, RunRequest, RunStatus } from "../types/api";

type WorkbenchState = {
  runStatus: RunStatus | null;
  results: ResultItem[];
  error: string | null;
  isSubmitting: boolean;
};

const state: WorkbenchState = {
  runStatus: null,
  results: [],
  error: null,
  isSubmitting: false,
};

export function getWorkbenchState() {
  return state;
}

export async function submitRun(payload: RunRequest) {
  state.isSubmitting = true;
  state.error = null;
  try {
    state.runStatus = await createRun(payload);
    const resultPayload = await fetchRunResults(state.runStatus.run_id);
    state.results = resultPayload.items;
  } catch (error) {
    state.error = error instanceof Error ? error.message : "运行失败";
  } finally {
    state.isSubmitting = false;
  }
}
```

- [ ] **Step 4: Implement the config form and results table**

Create `frontend/src/components/StrategyConfigForm.tsx`:

```tsx
type StrategyConfigFormProps = {
  onSubmit: () => void;
  isSubmitting: boolean;
};

export function StrategyConfigForm({ onSubmit, isSubmitting }: StrategyConfigFormProps) {
  return (
    <section>
      <h2>选股工作台</h2>
      <label>
        K 线天数
        <input defaultValue={120} name="kline_days" type="number" />
      </label>
      <button onClick={onSubmit} disabled={isSubmitting} type="button">
        {isSubmitting ? "运行中" : "开始选股"}
      </button>
    </section>
  );
}
```

Create `frontend/src/components/ResultsTable.tsx`:

```tsx
import type { ResultItem } from "../types/api";

type ResultsTableProps = {
  items: ResultItem[];
};

export function ResultsTable({ items }: ResultsTableProps) {
  return (
    <section>
      <h3>结果列表</h3>
      <table>
        <thead>
          <tr>
            <th>排名</th>
            <th>代码</th>
            <th>名称</th>
            <th>总分</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.code}>
              <td>{item.rank}</td>
              <td>{item.code}</td>
              <td>{item.name}</td>
              <td>{item.total_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 5: Implement the workbench page and app shell**

Create `frontend/src/pages/WorkbenchPage.tsx`:

```tsx
import { useState } from "react";

import { ResultsTable } from "../components/ResultsTable";
import { StrategyConfigForm } from "../components/StrategyConfigForm";
import { getWorkbenchState, submitRun } from "../store/useWorkbenchStore";

export function WorkbenchPage() {
  const [, forceRender] = useState(0);
  const state = getWorkbenchState();

  async function handleSubmit() {
    await submitRun({
      kline_days: 120,
      output: { min_score: 0.5 },
      strategies: [
        { name: "technical", enabled: true, weight: 0.4, params: { ma_bull: true } },
        { name: "fundamental", enabled: true, weight: 0.3, params: { pe_max: 50 } },
      ],
    });
    forceRender((value) => value + 1);
  }

  return (
    <main>
      <StrategyConfigForm onSubmit={handleSubmit} isSubmitting={state.isSubmitting} />
      {state.error ? <p>{state.error}</p> : null}
      <ResultsTable items={state.results} />
    </main>
  );
}
```

Create `frontend/src/App.tsx`:

```tsx
import { Link, Route, Routes } from "react-router-dom";

import { HistoryPage } from "./pages/HistoryPage";
import { WorkbenchPage } from "./pages/WorkbenchPage";

export default function App() {
  return (
    <>
      <nav>
        <Link to="/">工作台</Link>
        <Link to="/history">运行历史</Link>
      </nav>
      <Routes>
        <Route path="/" element={<WorkbenchPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Routes>
    </>
  );
}
```

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 6: Run the workbench test and verify GREEN**

Run:

```bash
cd frontend
npm test -- --runInBand
```

Expected: `workbench.test.tsx` passes.

- [ ] **Step 7: Commit the workbench UI**

```bash
git add frontend
git commit -m "feat: add workbench and results table"
```

### Task 6: Implement History Page, Detail Panel, And Frontend Data Loading

**Files:**
- Create: `frontend/src/components/StockDetailPanel.tsx`
- Create: `frontend/src/components/HistoryList.tsx`
- Create: `frontend/src/pages/HistoryPage.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/store/useWorkbenchStore.ts`
- Modify: `frontend/src/pages/WorkbenchPage.tsx`
- Test: `frontend/src/__tests__/history.test.tsx`

- [ ] **Step 1: Extend the frontend API client for detail and history**

Update `frontend/src/api/client.ts`:

```ts
export async function fetchResultDetail(runId: string, code: string) {
  const response = await fetch(`${BASE_URL}/api/runs/${runId}/results/${code}`);
  if (!response.ok) throw new Error("加载详情失败");
  return response.json();
}

export async function fetchHistoryList() {
  const response = await fetch(`${BASE_URL}/api/history`);
  if (!response.ok) throw new Error("加载历史失败");
  return response.json();
}

export async function fetchHistoryDetail(runId: string) {
  const response = await fetch(`${BASE_URL}/api/history/${runId}`);
  if (!response.ok) throw new Error("加载历史详情失败");
  return response.json();
}
```

- [ ] **Step 2: Add detail and history state to the store**

Update `frontend/src/store/useWorkbenchStore.ts`:

```ts
type WorkbenchState = {
  runStatus: RunStatus | null;
  results: ResultItem[];
  selectedCode: string | null;
  detail: Record<string, unknown> | null;
  historyItems: Array<Record<string, unknown>>;
  historyDetail: Record<string, unknown> | null;
  error: string | null;
  isSubmitting: boolean;
};

export async function loadDetail(runId: string, code: string) {
  state.selectedCode = code;
  state.detail = await fetchResultDetail(runId, code);
}

export async function loadHistory() {
  const payload = await fetchHistoryList();
  state.historyItems = payload.items;
}

export async function loadHistoryDetail(runId: string) {
  state.historyDetail = await fetchHistoryDetail(runId);
}
```

- [ ] **Step 3: Implement the detail panel and history list**

Create `frontend/src/components/StockDetailPanel.tsx`:

```tsx
type StockDetailPanelProps = {
  detail: Record<string, any> | null;
};

export function StockDetailPanel({ detail }: StockDetailPanelProps) {
  if (!detail) {
    return <aside>请选择一只股票查看详情</aside>;
  }
  return (
    <aside>
      <h3>{detail.stock.name}</h3>
      <p>代码: {detail.stock.code}</p>
      <p>策略数: {detail.strategies.length}</p>
      <p>K线点数: {detail.kline.length}</p>
      <p>资金流点数: {detail.money_flows.length}</p>
    </aside>
  );
}
```

Create `frontend/src/components/HistoryList.tsx`:

```tsx
type HistoryListProps = {
  items: Array<Record<string, any>>;
  onSelect: (runId: string) => void;
};

export function HistoryList({ items, onSelect }: HistoryListProps) {
  if (items.length === 0) {
    return <p>暂无历史记录</p>;
  }
  return (
    <ul>
      {items.map((item) => (
        <li key={item.run_id}>
          <button onClick={() => onSelect(item.run_id)} type="button">
            {item.run_id}
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: Implement the history page**

Create `frontend/src/pages/HistoryPage.tsx`:

```tsx
import { useEffect, useState } from "react";

import { HistoryList } from "../components/HistoryList";
import { getWorkbenchState, loadHistory, loadHistoryDetail } from "../store/useWorkbenchStore";

export function HistoryPage() {
  const [, forceRender] = useState(0);
  const state = getWorkbenchState();

  useEffect(() => {
    loadHistory().finally(() => forceRender((value) => value + 1));
  }, []);

  return (
    <main>
      <h1>运行历史</h1>
      <HistoryList
        items={state.historyItems}
        onSelect={(runId) =>
          loadHistoryDetail(runId).finally(() => forceRender((value) => value + 1))
        }
      />
      {state.historyDetail ? <pre>{JSON.stringify(state.historyDetail, null, 2)}</pre> : null}
    </main>
  );
}
```

- [ ] **Step 5: Wire the detail panel into the workbench page**

Update `frontend/src/pages/WorkbenchPage.tsx`:

```tsx
import { StockDetailPanel } from "../components/StockDetailPanel";
import { loadDetail } from "../store/useWorkbenchStore";

<ResultsTable items={state.results} />
<button
  type="button"
  onClick={() => {
    if (state.runStatus && state.results[0]) {
      loadDetail(state.runStatus.run_id, state.results[0].code).finally(() =>
        forceRender((value) => value + 1),
      );
    }
  }}
>
  查看首条详情
</button>
<StockDetailPanel detail={state.detail} />
```

- [ ] **Step 6: Run the history test and verify GREEN**

Run:

```bash
cd frontend
npm test
```

Expected: Both `workbench.test.tsx` and `history.test.tsx` pass.

- [ ] **Step 7: Commit the history and detail UI**

```bash
git add frontend
git commit -m "feat: add history and detail views"
```

### Task 7: Add Startup Docs And Run Full Verification

**Files:**
- Modify: `README.md`
- Test: `tests/webapi/test_meta_api.py`
- Test: `tests/webapi/test_runs_api.py`
- Test: `tests/webapi/test_history_api.py`
- Test: `tests/test_e2e.py`

- [ ] **Step 1: Document backend startup in `README.md`**

Append a Web section to `README.md`:

````md
## Web 工作台

### 启动后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn astock.webapi.app:create_app --factory --reload
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：`http://localhost:5173`
默认后端地址：`http://localhost:8000`
````

- [ ] **Step 2: Run the backend API test suite**

Run: `pytest tests/webapi -q`

Expected: PASS.

- [ ] **Step 3: Run the existing engine end-to-end test**

Run: `python3 tests/test_e2e.py`

Expected: Prints `✅ 端到端测试通过`.

- [ ] **Step 4: Run backend lint**

Run: `ruff check src/ tests/`

Expected: `All checks passed!`

- [ ] **Step 5: Run frontend build verification**

Run:

```bash
cd frontend
npm run build
```

Expected: Vite produces a production build without type errors.

- [ ] **Step 6: Commit docs and verification-ready changes**

```bash
git add README.md .gitignore
git commit -m "docs: add web workbench startup guide"
```

## Self-Review

- Spec coverage:
  - Frontend/backend directory split: covered in Tasks 1-6
  - Meta/options endpoint: covered in Task 1 tests and Task 2 implementation
  - Run creation, result list, and result detail: covered in Task 1 tests and Task 2 implementation
  - Run history persistence and history endpoints: covered in Task 3
  - Workbench page, result table, detail panel, and history page: covered in Tasks 4-6
  - Startup and verification instructions: covered in Task 7
- Placeholder scan:
  - No `TODO`, `TBD`, or unresolved placeholder markers remain in tasks
- Type consistency:
  - `RunRequest`, `RunStatusResponse`, `ResultItem`, `ResultDetail`, `HistoryStore`, and frontend DTO names are consistent across backend, frontend, and tests
