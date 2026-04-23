"""资金流向数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class MoneyFlow:
    """单日资金流向（单位：元）。

    正值为净流入，负值为净流出。
    """

    code: str
    trade_date: date
    main_net_inflow: float = 0.0        # 主力净流入
    super_large_net: float = 0.0        # 超大单净额
    large_net: float = 0.0              # 大单净额
    medium_net: float = 0.0             # 中单净额
    small_net: float = 0.0              # 小单净额
    north_bound_hold: Optional[float] = None  # 北向持股量（股），可选
