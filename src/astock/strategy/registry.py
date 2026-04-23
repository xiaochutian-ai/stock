"""策略注册表（Registry）。"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .base import Strategy

_REGISTRY: Dict[str, Type[Strategy]] = {}


def register_strategy(name: str):
    """类装饰器：把策略实现注册到全局注册表。"""

    def decorator(cls: Type[Strategy]) -> Type[Strategy]:
        if not issubclass(cls, Strategy):
            raise TypeError(f"{cls} must subclass Strategy")
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_strategy(name: str, params: Optional[dict] = None, weight: float = 1.0) -> Strategy:
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return _REGISTRY[name](params=params, weight=weight)


def list_strategies() -> list:
    return sorted(_REGISTRY.keys())
