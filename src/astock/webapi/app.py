from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI

from astock.config import Settings
from astock.datasource.base import DataProvider
from astock.storage.base import Repository
from astock.webapi.history_store import HistoryStore
from astock.webapi.routes.history import router as history_router
from astock.webapi.routes.meta import router as meta_router
from astock.webapi.routes.runs import router as runs_router
from astock.webapi.services.run_service import shutdown_run_tasks


def create_app(
    settings: Settings,
    provider: Optional[DataProvider] = None,
    repository: Optional[Repository] = None,
    history_db_path: Union[str, Path] = "data/web_history.db",
) -> FastAPI:
    """Create the minimal FastAPI app shell for the Web API."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        shutdown_run_tasks(app.state.run_tasks, app.state.run_cache)

    app = FastAPI(title="astock Web API", lifespan=lifespan)
    app.state.settings = settings
    app.state.base_settings = settings
    app.state.default_settings = settings
    app.state.provider = provider
    app.state.repository = repository
    app.state.history_db_path = Path(history_db_path)
    app.state.history_store = HistoryStore(app.state.history_db_path)
    app.state.run_cache = {}
    app.state.run_tasks = {}
    app.include_router(history_router)
    app.include_router(meta_router)
    app.include_router(runs_router)
    return app
