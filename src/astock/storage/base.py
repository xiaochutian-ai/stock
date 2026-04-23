"""存储层抽象接口。

上层只依赖 Repository 接口，不感知具体数据库。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import Financial, KLine, MoneyFlow, Stock


class Repository(ABC):
    """存储层抽象接口。

    所有后端（SQLite / MySQL / Postgres）实现都要遵循此契约。
    """

    name: str = ""

    def __init__(self, options: Optional[dict] = None):
        self.options = options or {}

    # ---------------- 连接/生命周期 ----------------
    @abstractmethod
    def init_schema(self) -> None:
        """初始化表结构（幂等）。"""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """释放连接。"""
        raise NotImplementedError

    # ---------------- 股票基础信息 ----------------
    @abstractmethod
    def upsert_stocks(self, stocks: List[Stock]) -> int:
        """批量 upsert 股票基础信息，返回成功条数。"""
        raise NotImplementedError

    @abstractmethod
    def list_stocks(self) -> List[Stock]:
        """读取全部股票基础信息。"""
        raise NotImplementedError

    # ---------------- K 线 ----------------
    @abstractmethod
    def upsert_kline(self, kline: KLine) -> int:
        """写入单只股票 K 线，返回写入条数。"""
        raise NotImplementedError

    @abstractmethod
    def get_kline(self, code: str) -> Optional[KLine]:
        """读取单只股票的完整 K 线。"""
        raise NotImplementedError

    # ---------------- 财务 ----------------
    @abstractmethod
    def upsert_financials(self, financials: List[Financial]) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_financial(self, code: str) -> Optional[Financial]:
        raise NotImplementedError

    # ---------------- 资金流 ----------------
    @abstractmethod
    def upsert_money_flows(self, flows: List[MoneyFlow]) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_money_flows(self, code: str, days: int = 5) -> List[MoneyFlow]:
        raise NotImplementedError
