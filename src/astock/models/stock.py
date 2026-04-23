"""Stock 基础信息模型。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import date


class Board(str, Enum):
    """A 股板块枚举。"""

    MAIN_BOARD = "main_board"   # 主板 (沪市 60/沪 600、深市 000)
    SME_BOARD = "sme_board"     # 中小板 (002)
    CHINEXT = "chinext"         # 创业板 (300)
    STAR_MARKET = "star_market" # 科创板 (688)
    BSE = "bse"                 # 北交所 (8)

    @classmethod
    def from_code(cls, code: str) -> "Board":
        """根据股票代码推断板块。"""
        code = code.strip().zfill(6)
        if code.startswith(("600", "601", "603", "605")):
            return cls.MAIN_BOARD
        if code.startswith("000"):
            return cls.MAIN_BOARD
        if code.startswith("002"):
            return cls.SME_BOARD
        if code.startswith("300") or code.startswith("301"):
            return cls.CHINEXT
        if code.startswith("688"):
            return cls.STAR_MARKET
        if code.startswith(("8", "4")):
            return cls.BSE
        return cls.MAIN_BOARD


@dataclass(frozen=True)
class Stock:
    """A 股基础信息。

    Attributes:
        code: 6 位股票代码，例如 "600519"
        name: 股票名称，例如 "贵州茅台"
        board: 所属板块
        list_date: 上市日期
        is_st: 是否 ST 股
        industry: 所属行业（可选）
    """

    code: str
    name: str
    board: Board
    list_date: Optional[date] = None
    is_st: bool = False
    industry: Optional[str] = None

    @property
    def symbol(self) -> str:
        """返回带交易所前缀的代码，例如 sh600519 / sz000001。"""
        if self.board in (Board.MAIN_BOARD, Board.STAR_MARKET) and self.code.startswith(
            ("6", "688")
        ):
            return f"sh{self.code}"
        if self.board == Board.BSE:
            return f"bj{self.code}"
        return f"sz{self.code}"
