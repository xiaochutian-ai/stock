from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class MarketSnapshot:
    trend_score: float
    risk_appetite_score: float
    volatility_pressure: float
    notes: str


@dataclass(frozen=True)
class SectorSnapshot:
    name: str
    change_5d: float
    money_inflow_score: float
    leadership_score: float


@dataclass(frozen=True)
class StockCandidate:
    code: str
    name: str
    sector: str
    price_change_5d: float
    sector_change_5d: float
    above_ma5: bool
    above_ma10: bool
    above_ma20: bool
    ma_bullish: bool
    breakout: bool
    close_near_high: bool
    volume_ratio: float
    volume_vs_avg5: float
    turnover_rate: float
    amount_billion: float
    capital_inflow_positive: bool
    tail_strength: bool
    distance_to_support_pct: float
    is_accelerating_high: bool
    overhead_pressure_low: bool
    event_risk_low: bool
    reward_risk_ratio: float


@dataclass(frozen=True)
class RankedCandidate:
    rank: int
    candidate: StockCandidate
    total_score: float
    tag: str
    market_score: float
    sector_score: float
    technical_score: float
    capital_score: float
    risk_score: float
    highlights: Tuple[str, ...]


class ShortTermScorer:
    """A simple standalone scorer for short-term stock ranking demos."""

    def rank_candidates(
        self,
        market: MarketSnapshot,
        sectors: Dict[str, SectorSnapshot],
        stocks: Sequence[StockCandidate],
    ) -> List[RankedCandidate]:
        if not stocks:
            return []

        ranked: List[RankedCandidate] = []
        market_score = self._score_market(market)

        for stock in stocks:
            if stock.sector not in sectors:
                raise ValueError(f"不存在的板块: {stock.sector}")

            sector = sectors[stock.sector]
            sector_score = self._score_sector(sector, stock)
            technical_score = self._score_technical(stock)
            capital_score = self._score_capital(stock)
            risk_score = self._score_risk(stock)
            total_score = round(
                market_score * 0.15
                + sector_score * 0.25
                + technical_score * 0.30
                + capital_score * 0.20
                + risk_score * 0.10,
                2,
            )
            ranked.append(
                RankedCandidate(
                    rank=0,
                    candidate=stock,
                    total_score=total_score,
                    tag=self._tag(total_score),
                    market_score=round(market_score, 2),
                    sector_score=round(sector_score, 2),
                    technical_score=round(technical_score, 2),
                    capital_score=round(capital_score, 2),
                    risk_score=round(risk_score, 2),
                    highlights=self._build_highlights(stock, total_score),
                )
            )

        ranked.sort(key=lambda item: item.total_score, reverse=True)
        return [
            RankedCandidate(
                rank=index,
                candidate=item.candidate,
                total_score=item.total_score,
                tag=item.tag,
                market_score=item.market_score,
                sector_score=item.sector_score,
                technical_score=item.technical_score,
                capital_score=item.capital_score,
                risk_score=item.risk_score,
                highlights=item.highlights,
            )
            for index, item in enumerate(ranked, start=1)
        ]

    def _score_market(self, market: MarketSnapshot) -> float:
        return _clamp(
            market.trend_score * 0.5
            + market.risk_appetite_score * 0.35
            + (100 - market.volatility_pressure) * 0.15,
            0,
            100,
        )

    def _score_sector(self, sector: SectorSnapshot, stock: StockCandidate) -> float:
        score = (
            40
            + sector.change_5d * 4.0
            + stock.sector_change_5d * 2.0
            + sector.money_inflow_score * 0.18
            + sector.leadership_score * 0.14
        )
        return _clamp(score, 0, 100)

    def _score_technical(self, stock: StockCandidate) -> float:
        score = 20.0
        score += 8 if stock.above_ma5 else -6
        score += 8 if stock.above_ma10 else -6
        score += 10 if stock.above_ma20 else -8
        score += 14 if stock.ma_bullish else -6
        score += 12 if stock.breakout else 0
        score += 8 if stock.close_near_high else -3
        score += _clamp(stock.price_change_5d * 3.0, -12, 15)
        return _clamp(score, 0, 100)

    def _score_capital(self, stock: StockCandidate) -> float:
        score = 25.0
        score += _clamp((stock.volume_ratio - 1.0) * 14.0, -8, 12)
        score += _clamp((stock.volume_vs_avg5 - 1.0) * 18.0, -10, 15)
        score += _clamp(stock.turnover_rate * 1.3, 0, 18)
        score += _clamp(stock.amount_billion * 1.2, 0, 15)
        score += 10 if stock.capital_inflow_positive else -12
        score += 6 if stock.tail_strength else -4
        return _clamp(score, 0, 100)

    def _score_risk(self, stock: StockCandidate) -> float:
        score = 55.0
        score += 10 if stock.overhead_pressure_low else -12
        score += 8 if stock.event_risk_low else -18
        score += 6 if not stock.is_accelerating_high else -14
        score += _clamp(stock.reward_risk_ratio * 9.0, 0, 22)
        distance_gap = abs(stock.distance_to_support_pct - 4.0)
        score += _clamp(12.0 - distance_gap * 4.0, -10, 12)
        return _clamp(score, 0, 100)

    def _tag(self, total_score: float) -> str:
        if total_score >= 78:
            return "重点关注"
        if total_score >= 62:
            return "观察池"
        return "暂不推荐"

    def _build_highlights(self, stock: StockCandidate, total_score: float) -> Tuple[str, ...]:
        highlights: List[str] = []
        if stock.breakout:
            highlights.append("突破形态")
        if stock.ma_bullish and stock.above_ma20:
            highlights.append("均线多头")
        if stock.capital_inflow_positive:
            highlights.append("资金偏强")
        if stock.tail_strength:
            highlights.append("尾盘承接")
        if stock.reward_risk_ratio >= 2:
            highlights.append("盈亏比合格")
        if not highlights:
            highlights.append("缺少明显短线优势")
        if total_score < 62 and "风险偏高" not in highlights:
            highlights.append("风险偏高")
        return tuple(highlights[:3])


def build_sample_dataset() -> Tuple[MarketSnapshot, Dict[str, SectorSnapshot], List[StockCandidate]]:
    market = MarketSnapshot(
        trend_score=74.0,
        risk_appetite_score=68.0,
        volatility_pressure=34.0,
        notes="指数震荡偏强，情绪修复中，适合精选强势主线。",
    )
    sectors = {
        "AI算力": SectorSnapshot("AI算力", change_5d=7.8, money_inflow_score=86.0, leadership_score=83.0),
        "机器人": SectorSnapshot("机器人", change_5d=6.2, money_inflow_score=78.0, leadership_score=76.0),
        "创新药": SectorSnapshot("创新药", change_5d=4.5, money_inflow_score=73.0, leadership_score=70.0),
        "消费电子": SectorSnapshot("消费电子", change_5d=3.2, money_inflow_score=64.0, leadership_score=62.0),
        "光伏": SectorSnapshot("光伏", change_5d=-1.4, money_inflow_score=42.0, leadership_score=45.0),
        "地产链": SectorSnapshot("地产链", change_5d=-3.8, money_inflow_score=28.0, leadership_score=30.0),
    }
    stocks = [
        StockCandidate(
            code="600111",
            name="龙头算力",
            sector="AI算力",
            price_change_5d=11.8,
            sector_change_5d=7.8,
            above_ma5=True,
            above_ma10=True,
            above_ma20=True,
            ma_bullish=True,
            breakout=True,
            close_near_high=True,
            volume_ratio=1.9,
            volume_vs_avg5=1.8,
            turnover_rate=14.5,
            amount_billion=28.0,
            capital_inflow_positive=True,
            tail_strength=True,
            distance_to_support_pct=3.8,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=3.0,
        ),
        StockCandidate(
            code="300750",
            name="灵巧机器人",
            sector="机器人",
            price_change_5d=9.1,
            sector_change_5d=6.2,
            above_ma5=True,
            above_ma10=True,
            above_ma20=True,
            ma_bullish=True,
            breakout=True,
            close_near_high=True,
            volume_ratio=1.6,
            volume_vs_avg5=1.4,
            turnover_rate=11.0,
            amount_billion=19.0,
            capital_inflow_positive=True,
            tail_strength=True,
            distance_to_support_pct=4.8,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=2.5,
        ),
        StockCandidate(
            code="688222",
            name="创新药服务",
            sector="创新药",
            price_change_5d=6.4,
            sector_change_5d=4.5,
            above_ma5=True,
            above_ma10=True,
            above_ma20=False,
            ma_bullish=True,
            breakout=False,
            close_near_high=True,
            volume_ratio=1.3,
            volume_vs_avg5=1.2,
            turnover_rate=8.6,
            amount_billion=12.0,
            capital_inflow_positive=True,
            tail_strength=False,
            distance_to_support_pct=4.1,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=2.1,
        ),
        StockCandidate(
            code="002475",
            name="消费电子链",
            sector="消费电子",
            price_change_5d=3.8,
            sector_change_5d=3.2,
            above_ma5=True,
            above_ma10=True,
            above_ma20=False,
            ma_bullish=False,
            breakout=False,
            close_near_high=False,
            volume_ratio=1.1,
            volume_vs_avg5=1.0,
            turnover_rate=6.0,
            amount_billion=8.0,
            capital_inflow_positive=True,
            tail_strength=False,
            distance_to_support_pct=5.2,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=1.7,
        ),
        StockCandidate(
            code="601012",
            name="光伏反弹样本",
            sector="光伏",
            price_change_5d=1.5,
            sector_change_5d=-1.4,
            above_ma5=True,
            above_ma10=False,
            above_ma20=False,
            ma_bullish=False,
            breakout=False,
            close_near_high=False,
            volume_ratio=0.95,
            volume_vs_avg5=0.9,
            turnover_rate=4.3,
            amount_billion=6.5,
            capital_inflow_positive=False,
            tail_strength=False,
            distance_to_support_pct=7.8,
            is_accelerating_high=False,
            overhead_pressure_low=False,
            event_risk_low=True,
            reward_risk_ratio=1.2,
        ),
        StockCandidate(
            code="000736",
            name="地产博弈样本",
            sector="地产链",
            price_change_5d=-2.6,
            sector_change_5d=-3.8,
            above_ma5=False,
            above_ma10=False,
            above_ma20=False,
            ma_bullish=False,
            breakout=False,
            close_near_high=False,
            volume_ratio=0.72,
            volume_vs_avg5=0.7,
            turnover_rate=9.0,
            amount_billion=4.8,
            capital_inflow_positive=False,
            tail_strength=False,
            distance_to_support_pct=11.5,
            is_accelerating_high=True,
            overhead_pressure_low=False,
            event_risk_low=False,
            reward_risk_ratio=0.9,
        ),
    ]
    return market, sectors, stocks


def _iter_lines(results: Iterable[RankedCandidate]) -> Iterable[str]:
    yield "排名  代码      名称         板块       总分   标签      亮点"
    yield "-" * 80
    for item in results:
        yield (
            f"{item.rank:>2}   "
            f"{item.candidate.code:<8}"
            f"{item.candidate.name:<10}"
            f"{item.candidate.sector:<8}"
            f"{item.total_score:>6.2f}  "
            f"{item.tag:<8}"
            f"{' / '.join(item.highlights)}"
        )


def main() -> int:
    market, sectors, stocks = build_sample_dataset()
    scorer = ShortTermScorer()
    results = scorer.rank_candidates(market, sectors, stocks)

    print("短线候选股排序 Demo")
    print(f"市场观察: {market.notes}")
    print(f"样本数量: {len(stocks)}，板块数量: {len(sectors)}")
    print()
    for line in _iter_lines(results):
        print(line)
    print()
    print("标签说明: 重点关注 >= 78, 观察池 >= 62, 其余为暂不推荐")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
