"""技术面策略。

命中条件（可配置）：
- ma_bull: 均线多头排列 MA5 > MA10 > MA20 > MA60
- macd_gold_cross: 近期出现 MACD 金叉
- rsi_range: RSI 在 [low, high] 区间内（默认 30~70）
- volume_burst: 当日放量

打分：命中项数 / 启用项数
"""

from __future__ import annotations

from ..indicators import (
    is_macd_gold_cross,
    is_ma_bull,
    is_volume_burst,
    rsi,
)
from .base import Strategy, StrategyResult
from .context import StrategyContext
from .registry import register_strategy


@register_strategy("technical")
class TechnicalStrategy(Strategy):
    def evaluate(self, ctx: StrategyContext) -> StrategyResult:
        if ctx.kline is None or ctx.kline.is_empty():
            return StrategyResult(passed=False, reason="缺少K线数据")

        if len(ctx.kline) < 30:
            return StrategyResult(passed=False, reason="K线数据不足30日")

        close = ctx.kline.close
        volume = ctx.kline.volume

        checks: dict[str, bool] = {}
        enabled = 0

        if self.params.get("ma_bull", True):
            enabled += 1
            checks["ma_bull"] = is_ma_bull(close)

        if self.params.get("macd_gold_cross", True):
            enabled += 1
            checks["macd_gold_cross"] = is_macd_gold_cross(close, lookback=3)

        rsi_range = self.params.get("rsi_range")
        if rsi_range:
            enabled += 1
            try:
                low, high = float(rsi_range[0]), float(rsi_range[1])
                last_rsi = float(rsi(close).iloc[-1])
                checks["rsi_range"] = low <= last_rsi <= high
            except Exception:
                checks["rsi_range"] = False

        if self.params.get("volume_burst", False):
            enabled += 1
            checks["volume_burst"] = is_volume_burst(volume)

        if enabled == 0:
            return StrategyResult(passed=True, score=1.0, reason="未启用任何技术项，视为全通过")

        hit = sum(1 for v in checks.values() if v)
        score = hit / enabled
        # 硬性门槛：至少命中一半才算 pass
        passed = score >= 0.5

        reason = f"技术面命中 {hit}/{enabled}: " + ", ".join(
            f"{k}={'✓' if v else '✗'}" for k, v in checks.items()
        )
        return StrategyResult(
            passed=passed,
            score=score,
            reason=reason,
            details={k: float(v) for k, v in checks.items()},
        )
