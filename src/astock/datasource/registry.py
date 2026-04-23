"""数据源注册表（Registry Pattern）。

提供 @register_provider 装饰器用于自动注册实现类，以及 get_provider 工厂方法。
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .base import DataProvider

_REGISTRY: Dict[str, Type[DataProvider]] = {}


def register_provider(name: str):
    """类装饰器：把 DataProvider 实现注册到全局注册表。

    Example:
        @register_provider("akshare")
        class AkshareProvider(DataProvider): ...
    """

    def decorator(cls: Type[DataProvider]) -> Type[DataProvider]:
        if not issubclass(cls, DataProvider):
            raise TypeError(f"{cls} must subclass DataProvider")
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_provider(name: str, options: Optional[dict] = None) -> DataProvider:
    """根据名称构造数据源实例（工厂方法）。"""
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise ValueError(
            f"Unknown datasource '{name}'. Available: {available}"
        )
    return _REGISTRY[name](options=options)


def list_providers() -> list:
    """返回已注册的数据源名称列表。"""
    return sorted(_REGISTRY.keys())
