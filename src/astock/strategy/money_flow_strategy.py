"""资金面策略。

命中条件（可配置）：
- main_inflow_days: 要求最近 N 日主力净流入为正
- min_inflow_amount: 最近一日主力净流入金额下限（元）
"""

from __future__ import annotations

from .base import Strategy, StrategyResult
from .context import StrategyContext
from .registry import register_strategy


@register_strategy("money_flow")
class MoneyFlowStrategy(Strategy):
    def evaluate(self, ctx: StrategyContext) -> StrategyResult:
        flows = ctx.money_flows or []
        if not flows:
            return StrategyResult(passed=False, reason="缺少资金流数据")

        checks: dict[str, bool] = {}
        enabled = 0

        inflow_days = int(self.params.get("main_inflow_days", 0) or 0)
        if inflow_days > 0:
            enabled += 1
            tail = flows[-inflow_days:]
            checks["main_inflow_days"] = (
                len(tail) >= inflow_days
                and all(f.main_net_inflow > 0 for f in tail)
            )

        min_amount = self.params.get("min_inflow_amount")
        if min_amount is not None:
            enabled += 1
            last = flows[-1]
            checks["min_inflow_amount"] = last.main_net_inflow >= float(min_amount)

        if enabled == 0:
            return StrategyResult(passed=True, score=1.0, reason="未启用任何资金面项，视为全通过")

        hit = sum(1 for v in checks.values() if v)
        score = hit / enabled
        passed = score >= 0.5
        reason = f"资金面命中 {hit}/{enabled}: " + ", ".join(
            f"{k}={'✓' if v else '✗'}" for k, v in checks.items()
        )
        return StrategyResult(
            passed=passed,
            score=score,
            reason=reason,
            details={k: float(v) for k, v in checks.items()},
        )
