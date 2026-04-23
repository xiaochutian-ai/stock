"""策略执行上下文。

引擎把所有可能用到的数据打包成一个 context，传给每个策略。
策略按需取用，避免每个策略自己反复访问数据源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..models import Financial, KLine, MoneyFlow, Stock


@dataclass
class StrategyContext:
    """单只股票进入策略评估时的上下文。"""

    stock: Stock
    kline: Optional[KLine] = None
    financial: Optional[Financial] = None
    money_flows: List[MoneyFlow] = field(default_factory=list)
