"""DataProvider 抽象接口（契约）。

所有数据源实现必须遵循本接口，策略层/引擎层只依赖这个抽象，不感知具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from ..models import Stock, KLine, Financial, MoneyFlow


class DataProvider(ABC):
    """A 股数据源抽象接口。

    子类只需实现本接口即可被引擎使用，遵循里氏替换原则（LSP）。
    """

    #: 数据源名称（用于注册表查找）
    name: str = ""

    def __init__(self, options: Optional[dict] = None):
        self.options = options or {}

    # ---------------- 股票列表 ----------------
    @abstractmethod
    def list_stocks(self) -> List[Stock]:
        """返回全部 A 股列表（基础信息）。"""
        raise NotImplementedError

    # ---------------- 行情 ----------------
    @abstractmethod
    def get_kline(
        self,
        code: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        adjust: str = "qfq",
    ) -> KLine:
        """获取日 K 线。

        Args:
            code: 6 位股票代码
            start: 起始日期（含），默认 None 表示最早
            end: 结束日期（含），默认 None 表示最近
            adjust: 复权方式，"qfq"/"hfq"/""
        """
        raise NotImplementedError

    # ---------------- 财务 ----------------
    @abstractmethod
    def get_financial(self, code: str) -> Financial:
        """获取最新一期财务指标。"""
        raise NotImplementedError

    def get_financials_batch(self, codes: List[str]) -> List[Financial]:
        """批量获取财务指标（默认实现为循环，子类可用批量接口覆盖以加速）。"""
        return [self.get_financial(c) for c in codes]

    # ---------------- 资金流 ----------------
    @abstractmethod
    def get_money_flow(self, code: str, days: int = 5) -> List[MoneyFlow]:
        """获取最近 N 日资金流向。"""
        raise NotImplementedError

    # ---------------- 其他可选 ----------------
    def close(self) -> None:
        """释放资源（如关闭 HTTP session）。默认空实现。"""
        return None
