from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import List, Sequence


@dataclass(frozen=True)
class MarketBar:
    trade_date: str
    close: float
    volume: float


@dataclass(frozen=True)
class BreadthSnapshot:
    trade_date: str
    advancers: int
    decliners: int
    new_highs: int
    new_lows: int
    stocks_above_ma20: int
    total_stocks: int


@dataclass(frozen=True)
class MarketDataset:
    bars: Sequence[MarketBar]
    breadth: Sequence[BreadthSnapshot]


@dataclass(frozen=True)
class FactorValue:
    name: str
    value: float
    score: float
    comment: str


@dataclass(frozen=True)
class CompositeFactorResult:
    name: str
    score: float
    factors: Sequence[FactorValue] = field(default_factory=tuple)
    comment: str = ""


@dataclass(frozen=True)
class MarketScoreResult:
    trend: CompositeFactorResult
    volume: CompositeFactorResult
    breadth: CompositeFactorResult
    total_score: float
    regime: str
    summary: str


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _safe_ratio(numerator: float, denominator: float, fallback: float = 0.5) -> float:
    if denominator <= 0:
        return fallback
    return numerator / denominator


def _neutral_factor(name: str, comment: str) -> FactorValue:
    return FactorValue(name=name, value=0.5, score=50.0, comment=comment)


def _score_from_unit_interval(value: float) -> float:
    return _clamp_score(value * 100.0)


def _score_from_centered_ratio(
    value: float,
    lower: float,
    middle: float,
    upper: float,
) -> float:
    if value <= lower:
        return 0.0
    if value >= upper:
        return 100.0
    if value == middle:
        return 50.0
    if value < middle:
        return _clamp_score((value - lower) / (middle - lower) * 50.0)
    return _clamp_score(50.0 + (value - middle) / (upper - middle) * 50.0)


def _mean_close(bars: Sequence[MarketBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    return mean(bar.close for bar in bars[-window:])


def _mean_volume(bars: Sequence[MarketBar], window: int) -> float | None:
    if len(bars) < window:
        return None
    return mean(bar.volume for bar in bars[-window:])


class MarketFactorCalculator:
    def _validate_dataset(self, dataset: MarketDataset) -> None:
        if not dataset.bars:
            raise ValueError("指数行情不能为空")
        if not dataset.breadth:
            raise ValueError("市场宽度不能为空")

    def latest_breadth(self, dataset: MarketDataset) -> BreadthSnapshot:
        self._validate_dataset(dataset)
        latest_trade_date = dataset.bars[-1].trade_date
        for snapshot in dataset.breadth:
            if snapshot.trade_date == latest_trade_date:
                return snapshot
        raise ValueError("最新交易日缺少对应的市场宽度快照")

    def factor_close_above_ma20(self, dataset: MarketDataset) -> FactorValue:
        self._validate_dataset(dataset)
        ma20 = _mean_close(dataset.bars, 20)
        if ma20 is None:
            return _neutral_factor("close_above_ma20", "样本不足 20 日，使用中性趋势分")
        latest_close = dataset.bars[-1].close
        score = 100.0 if latest_close > ma20 else 0.0
        comment = "最新收盘价站上 MA20" if score == 100.0 else "最新收盘价仍在 MA20 下方"
        return FactorValue("close_above_ma20", latest_close / ma20, score, comment)

    def factor_ma20_above_ma60(self, dataset: MarketDataset) -> FactorValue:
        self._validate_dataset(dataset)
        ma20 = _mean_close(dataset.bars, 20)
        ma60 = _mean_close(dataset.bars, 60)
        if ma20 is None or ma60 is None:
            return _neutral_factor("ma20_above_ma60", "样本不足 60 日，使用中性中期趋势分")
        score = 100.0 if ma20 > ma60 else 0.0
        comment = "MA20 位于 MA60 上方" if score == 100.0 else "MA20 仍在 MA60 下方"
        return FactorValue("ma20_above_ma60", ma20 / ma60, score, comment)

    def factor_momentum_20d(self, dataset: MarketDataset) -> FactorValue:
        self._validate_dataset(dataset)
        if len(dataset.bars) < 21:
            return _neutral_factor("momentum_20d", "样本不足 21 日，使用中性动量分")
        latest_close = dataset.bars[-1].close
        base_close = dataset.bars[-21].close
        momentum = _safe_ratio(latest_close, base_close, fallback=1.0) - 1.0
        score = _score_from_centered_ratio(momentum, -0.10, 0.0, 0.10)
        comment = f"20 日动量为 {momentum:.2%}"
        return FactorValue("momentum_20d", momentum, score, comment)

    def factor_volume_ratio_20d(self, dataset: MarketDataset) -> FactorValue:
        self._validate_dataset(dataset)
        avg_volume = _mean_volume(dataset.bars, 20)
        if avg_volume is None:
            return _neutral_factor("volume_ratio_20d", "样本不足 20 日，使用中性量能分")
        ratio = _safe_ratio(dataset.bars[-1].volume, avg_volume, fallback=1.0)
        score = _score_from_centered_ratio(ratio, 0.60, 1.0, 1.50)
        comment = f"最新成交量为 20 日均量的 {ratio:.2f} 倍"
        return FactorValue("volume_ratio_20d", ratio, score, comment)

    def factor_up_day_volume_ratio(self, dataset: MarketDataset) -> FactorValue:
        self._validate_dataset(dataset)
        if len(dataset.bars) < 2:
            return _neutral_factor("up_day_volume_ratio", "样本不足 2 日，使用中性上涨量能分")
        lookback = dataset.bars[-10:] if len(dataset.bars) >= 10 else dataset.bars
        total_volume = sum(bar.volume for bar in lookback)
        up_day_volume = 0.0
        for previous, current in zip(lookback, lookback[1:]):
            if current.close > previous.close:
                up_day_volume += current.volume
        ratio = _safe_ratio(up_day_volume, total_volume, fallback=0.5)
        score = _score_from_unit_interval(ratio)
        comment = f"近端上涨日成交量占比 {ratio:.2%}"
        return FactorValue("up_day_volume_ratio", ratio, score, comment)

    def factor_advancers_ratio(self, dataset: MarketDataset) -> FactorValue:
        snapshot = self.latest_breadth(dataset)
        total = snapshot.advancers + snapshot.decliners
        ratio = _safe_ratio(snapshot.advancers, total, fallback=0.5)
        score = _score_from_unit_interval(ratio)
        comment = f"上涨家数占比 {ratio:.2%}"
        return FactorValue("advancers_ratio", ratio, score, comment)

    def factor_new_high_ratio(self, dataset: MarketDataset) -> FactorValue:
        snapshot = self.latest_breadth(dataset)
        total = snapshot.new_highs + snapshot.new_lows
        ratio = _safe_ratio(snapshot.new_highs, total, fallback=0.5)
        score = _score_from_unit_interval(ratio)
        comment = f"创新高占比 {ratio:.2%}"
        return FactorValue("new_high_ratio", ratio, score, comment)

    def factor_above_ma20_ratio(self, dataset: MarketDataset) -> FactorValue:
        snapshot = self.latest_breadth(dataset)
        ratio = _safe_ratio(snapshot.stocks_above_ma20, snapshot.total_stocks, fallback=0.5)
        score = _score_from_unit_interval(ratio)
        comment = f"站上 MA20 个股占比 {ratio:.2%}"
        return FactorValue("above_ma20_ratio", ratio, score, comment)


class CompositeFactorScorer:
    def __init__(self, calculator: MarketFactorCalculator | None = None) -> None:
        self.calculator = calculator or MarketFactorCalculator()

    def _combine(
        self,
        name: str,
        factors: Sequence[FactorValue],
        weights: Sequence[float],
        comment: str,
    ) -> CompositeFactorResult:
        score = sum(factor.score * weight for factor, weight in zip(factors, weights))
        return CompositeFactorResult(name=name, score=round(_clamp_score(score), 2), factors=factors, comment=comment)

    def score_trend(self, dataset: MarketDataset) -> CompositeFactorResult:
        factors = (
            self.calculator.factor_close_above_ma20(dataset),
            self.calculator.factor_ma20_above_ma60(dataset),
            self.calculator.factor_momentum_20d(dataset),
        )
        return self._combine("trend", factors, (0.35, 0.35, 0.30), "趋势因子聚合结果")

    def score_volume(self, dataset: MarketDataset) -> CompositeFactorResult:
        factors = (
            self.calculator.factor_volume_ratio_20d(dataset),
            self.calculator.factor_up_day_volume_ratio(dataset),
        )
        return self._combine("volume", factors, (0.50, 0.50), "成交量因子聚合结果")

    def score_breadth(self, dataset: MarketDataset) -> CompositeFactorResult:
        factors = (
            self.calculator.factor_advancers_ratio(dataset),
            self.calculator.factor_new_high_ratio(dataset),
            self.calculator.factor_above_ma20_ratio(dataset),
        )
        return self._combine("breadth", factors, (0.40, 0.25, 0.35), "宽度因子聚合结果")


class MarketRegimeStrategy:
    def __init__(
        self,
        trend_weight: float = 0.40,
        volume_weight: float = 0.25,
        breadth_weight: float = 0.35,
        scorer: CompositeFactorScorer | None = None,
    ) -> None:
        self.trend_weight = trend_weight
        self.volume_weight = volume_weight
        self.breadth_weight = breadth_weight
        self.scorer = scorer or CompositeFactorScorer()

    def evaluate(self, dataset: MarketDataset) -> MarketScoreResult:
        trend = self.scorer.score_trend(dataset)
        volume = self.scorer.score_volume(dataset)
        breadth = self.scorer.score_breadth(dataset)
        total_score = round(
            trend.score * self.trend_weight
            + volume.score * self.volume_weight
            + breadth.score * self.breadth_weight,
            2,
        )
        if total_score >= 70:
            regime = "强势"
        elif total_score >= 40:
            regime = "震荡"
        else:
            regime = "弱势"
        summary = (
            f"趋势 {trend.score:.1f}，成交量 {volume.score:.1f}，宽度 {breadth.score:.1f}，"
            f"当前市场状态为{regime}"
        )
        return MarketScoreResult(
            trend=trend,
            volume=volume,
            breadth=breadth,
            total_score=total_score,
            regime=regime,
            summary=summary,
        )


def _build_market_dataset(
    closes: Sequence[float],
    volumes: Sequence[float],
    breadth_values: Sequence[tuple[int, int, int, int, int, int]],
) -> MarketDataset:
    bars: List[MarketBar] = []
    breadth: List[BreadthSnapshot] = []
    for index, (close, volume) in enumerate(zip(closes, volumes), start=1):
        trade_date = f"2026-{index:03d}"
        bars.append(MarketBar(trade_date=trade_date, close=close, volume=volume))
    for index, values in enumerate(breadth_values, start=1):
        trade_date = f"2026-{index:03d}"
        breadth.append(BreadthSnapshot(trade_date, *values))
    return MarketDataset(bars=bars, breadth=breadth)


def build_sample_market_dataset() -> MarketDataset:
    closes = [3000.0 + index * 9.0 for index in range(70)]
    volumes = [1000.0 + index * 7.0 for index in range(70)]
    breadth_values = [
        (3200 + index * 3, 1500 - min(index, 200), 100 + index, 40, 3300 + index * 4, 5200)
        for index in range(70)
    ]
    breadth_values[-1] = (3800, 1100, 220, 20, 3900, 5200)
    return _build_market_dataset(closes, volumes, breadth_values)


def build_weak_market_dataset() -> MarketDataset:
    closes = [3400.0 - index * 9.0 for index in range(70)]
    volumes = [1500.0 - index * 6.0 for index in range(70)]
    breadth_values = [
        (1800 - min(index * 2, 700), 3000 + index * 2, 40, 120 + index, 2000 - min(index * 5, 900), 5200)
        for index in range(70)
    ]
    breadth_values[-1] = (1100, 3800, 15, 220, 1200, 5200)
    return _build_market_dataset(closes, volumes, breadth_values)
