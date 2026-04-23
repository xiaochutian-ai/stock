"""策略层：插件化设计。

所有策略实现 Strategy 抽象接口，通过 @register_strategy 装饰器自动注册。
引擎根据配置动态组合多个策略，每个策略产生一个 0~1 的打分，最终加权合成总分。

扩展方式：
    新增一个策略类 → 继承 Strategy → @register_strategy("my_strategy")
    然后在 config/default.yaml 中添加即可被引擎发现。
"""

from .base import Strategy, StrategyResult
from .context import StrategyContext
from .registry import get_strategy, register_strategy, list_strategies

from . import technical_strategy  # noqa: F401
from . import fundamental_strategy  # noqa: F401
from . import money_flow_strategy  # noqa: F401

__all__ = [
    "Strategy",
    "StrategyResult",
    "StrategyContext",
    "get_strategy",
    "register_strategy",
    "list_strategies",
]
