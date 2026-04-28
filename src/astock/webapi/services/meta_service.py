from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from astock.datasource import list_providers
from astock.storage import list_repositories
from astock.strategy import list_strategies


def build_meta_options(default_settings: Any) -> Dict[str, Any]:
    defaults = (
        asdict(default_settings)
        if is_dataclass(default_settings)
        else dict(default_settings)
    )
    return {
        "datasources": list_providers(),
        "storages": list_repositories(),
        "strategies": [{"name": name} for name in list_strategies()],
        "defaults": defaults,
    }
