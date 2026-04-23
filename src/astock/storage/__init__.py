"""存储层：面向接口编程。

- base.py 定义 Repository 抽象接口
- registry.py 存储后端注册表
- sqlite_repo.py SQLite 实现（基于 SQLAlchemy，切换 MySQL 只需改 url）
"""

from .base import Repository
from .registry import get_repository, register_repository, list_repositories

from . import sqlite_repo  # noqa: F401  触发注册

__all__ = [
    "Repository",
    "get_repository",
    "register_repository",
    "list_repositories",
]
