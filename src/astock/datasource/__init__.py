"""数据源层：面向接口编程。

- base.py 定义 DataProvider 抽象接口（契约）
- registry.py 提供注册表 + 工厂方法
- *_provider.py 是具体实现，通过 @register_provider 装饰器自动注册

切换数据源只需修改配置文件中 datasource.name 字段。
"""

from .base import DataProvider
from .registry import get_provider, register_provider, list_providers

# 触发实现注册（import 即注册）
from . import akshare_provider  # noqa: F401
from . import baostock_provider  # noqa: F401

__all__ = [
    "DataProvider",
    "get_provider",
    "register_provider",
    "list_providers",
]
