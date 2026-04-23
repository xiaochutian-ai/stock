"""策略抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional

from .context import StrategyContext


@dataclass
class StrategyResult:
    """单只股票在某策略下的评估结果。

    Attributes:
        passed: 是否通过硬性筛选（布尔）
        score: 0 ~ 1 的归一化得分（未通过时通常 0）
        reason: 可读的原因/解释
        details: 策略自定义的额外信息（如命中哪个因子）
    """

    passed: bool
    score: float = 0.0
    reason: str = ""
    details: Dict[str, float] = field(default_factory=dict)


class Strategy(ABC):
    """选股策略抽象接口。

    策略只读取 StrategyContext，不负责数据拉取/落库（单一职责原则）。
    """

    #: 策略名称（供注册表和配置使用）
    name: str = ""

    def __init__(self, params: Optional[dict] = None, weight: float = 1.0):
        self.params = params or {}
        self.weight = float(weight)

    @abstractmethod
    def evaluate(self, ctx: StrategyContext) -> StrategyResult:
        """对一只股票进行评估，返回 StrategyResult。"""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Strategy name={self.name} weight={self.weight} params={self.params}>"
