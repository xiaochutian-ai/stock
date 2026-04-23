"""存储后端注册表。"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .base import Repository

_REGISTRY: Dict[str, Type[Repository]] = {}


def register_repository(name: str):
    """类装饰器：注册 Repository 实现。"""

    def decorator(cls: Type[Repository]) -> Type[Repository]:
        if not issubclass(cls, Repository):
            raise TypeError(f"{cls} must subclass Repository")
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_repository(name: str, options: Optional[dict] = None) -> Repository:
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise ValueError(f"Unknown storage '{name}'. Available: {available}")
    return _REGISTRY[name](options=options)


def list_repositories() -> list:
    return sorted(_REGISTRY.keys())
