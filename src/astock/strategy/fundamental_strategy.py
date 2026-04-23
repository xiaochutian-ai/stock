"""基本面策略。

命中条件（可配置）：
- pe_max: PE_TTM 上限
- pb_max: PB 上限
- roe_min: ROE 下限
- net_profit_yoy_min: 净利润同比增长率下限

打分：各因子命中项数 / 启用项数；缺失字段视为未命中（保守）。
"""

from __future__ import annotations

from .base import Strategy, StrategyResult
from .context import StrategyContext
from .registry import register_strategy


@register_strategy("fundamental")
class FundamentalStrategy(Strategy):
    def evaluate(self, ctx: StrategyContext) -> StrategyResult:
        fin = ctx.financial
        if fin is None:
            return StrategyResult(passed=False, reason="缺少财务数据")

        checks: dict[str, bool] = {}
        enabled = 0

        pe_max = self.params.get("pe_max")
        if pe_max is not None:
            enabled += 1
            checks["pe_max"] = (
                fin.pe_ttm is not None and 0 < fin.pe_ttm <= float(pe_max)
            )

        pb_max = self.params.get("pb_max")
        if pb_max is not None:
            enabled += 1
            checks["pb_max"] = fin.pb is not None and 0 < fin.pb <= float(pb_max)

        roe_min = self.params.get("roe_min")
        if roe_min is not None:
            enabled += 1
            # 注意：akshare 的 ROE 原始值若为百分比，需要按来源统一；
            # 这里按照 Financial 约定：ROE 是小数（如 0.15 表示 15%）
            checks["roe_min"] = fin.roe is not None and fin.roe >= float(roe_min)

        npy_min = self.params.get("net_profit_yoy_min")
        if npy_min is not None:
            enabled += 1
            checks["net_profit_yoy_min"] = (
                fin.net_profit_yoy is not None and fin.net_profit_yoy >= float(npy_min)
            )

        if enabled == 0:
            return StrategyResult(passed=True, score=1.0, reason="未启用任何基本面项，视为全通过")

        hit = sum(1 for v in checks.values() if v)
        score = hit / enabled
        passed = score >= 0.5
        reason = f"基本面命中 {hit}/{enabled}: " + ", ".join(
            f"{k}={'✓' if v else '✗'}" for k, v in checks.items()
        )
        return StrategyResult(
            passed=passed,
            score=score,
            reason=reason,
            details={k: float(v) for k, v in checks.items()},
        )
