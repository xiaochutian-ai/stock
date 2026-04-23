"""领域数据模型（DTO），跨层共享。

所有字段都用 dataclass 定义，保持轻量、可序列化，不依赖任何框架。
"""

from .stock import Stock, Board
from .quote import Quote, KLine
from .financial import Financial
from .money_flow import MoneyFlow

__all__ = [
    "Stock",
    "Board",
    "Quote",
    "KLine",
    "Financial",
    "MoneyFlow",
]
