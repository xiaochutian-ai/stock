from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class MarketSnapshot:
    index_above_ma5: bool
    index_above_ma10: bool
    advancers_ratio: float
    limit_up_count: int
    limit_down_count: int
    strong_stock_premium: float


@dataclass(frozen=True)
class SectorSnapshot:
    name: str
    change_1d_rank_pct: float
    change_3d_rank_pct: float
    up_stock_ratio: float
    limit_up_count: int
    has_catalyst: bool


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


@dataclass
class ScoreBreakdown:
    code: str
    name: str
    sector: str
    market_score: float
    sector_score: float
    trend_score: float
    flow_score: float
    risk_score: float
    total_score: float
    tag: str
    reasons: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    rank: int = 0


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, score))


def _validate_ratio(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} 必须在 0 到 1 之间，实际为 {value}")


def _validate_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} 不能为负数，实际为 {value}")


def _validate_weights(weights: Sequence[Tuple[str, float]]) -> None:
    total = 0.0
    for name, value in weights:
        if value < 0:
            raise ValueError(f"{name} 不能为负数，实际为 {value}")
        total += value
    if total <= 0:
        raise ValueError("权重总和必须大于 0")


def _validate_market_snapshot(market: MarketSnapshot) -> None:
    _validate_ratio("advancers_ratio", market.advancers_ratio)
    _validate_non_negative("limit_up_count", market.limit_up_count)
    _validate_non_negative("limit_down_count", market.limit_down_count)
    _validate_non_negative("strong_stock_premium", market.strong_stock_premium)


def _validate_sector_snapshot(sector: SectorSnapshot) -> None:
    _validate_ratio("change_1d_rank_pct", sector.change_1d_rank_pct)
    _validate_ratio("change_3d_rank_pct", sector.change_3d_rank_pct)
    _validate_ratio("up_stock_ratio", sector.up_stock_ratio)
    _validate_non_negative("limit_up_count", sector.limit_up_count)


def _validate_stock_candidate(stock: StockCandidate) -> None:
    _validate_non_negative("volume_ratio", stock.volume_ratio)
    _validate_non_negative("volume_vs_avg5", stock.volume_vs_avg5)
    _validate_non_negative("turnover_rate", stock.turnover_rate)
    _validate_non_negative("amount_billion", stock.amount_billion)
    _validate_non_negative("distance_to_support_pct", stock.distance_to_support_pct)
    _validate_non_negative("reward_risk_ratio", stock.reward_risk_ratio)


def _validate_sector_references(
    stocks: Sequence[StockCandidate], sector_map: Dict[str, SectorSnapshot]
) -> None:
    for stock in stocks:
        if stock.sector not in sector_map:
            raise ValueError(f"股票 {stock.code} 引用了不存在的板块: {stock.sector}")


def _score_tag(total_score: float) -> str:
    if total_score >= 80:
        return "重点关注"
    if total_score >= 70:
        return "观察池"
    return "暂不推荐"


class ShortTermScorer:
    def __init__(
        self,
        market_weight: float = 0.20,
        sector_weight: float = 0.25,
        trend_weight: float = 0.25,
        flow_weight: float = 0.20,
        risk_weight: float = 0.10,
    ) -> None:
        _validate_weights(
            [
                ("market_weight", market_weight),
                ("sector_weight", sector_weight),
                ("trend_weight", trend_weight),
                ("flow_weight", flow_weight),
                ("risk_weight", risk_weight),
            ]
        )
        self.market_weight = market_weight
        self.sector_weight = sector_weight
        self.trend_weight = trend_weight
        self.flow_weight = flow_weight
        self.risk_weight = risk_weight

    def score_market(self, market: MarketSnapshot) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        if market.index_above_ma5:
            score += 20
            reasons.append("大盘站上 5 日线")
        if market.index_above_ma10:
            score += 20
            reasons.append("大盘站上 10 日线")
        if market.advancers_ratio >= 0.60:
            score += 20
            reasons.append("上涨家数占比达到强势阈值")
        if market.limit_up_count >= 70 and market.limit_down_count <= 10:
            score += 20
            reasons.append("涨停活跃且跌停可控")
        if market.strong_stock_premium >= 2.0:
            score += 20
            reasons.append("强势股平均溢价达标")
        return _clamp_score(score), reasons

    def score_sector(self, sector: SectorSnapshot) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        if sector.change_1d_rank_pct <= 0.10:
            score += 25
            reasons.append("板块 1 日涨幅排名前 10%")
        if sector.change_3d_rank_pct <= 0.10:
            score += 25
            reasons.append("板块 3 日涨幅排名前 10%")
        if sector.limit_up_count >= 2:
            score += 20
            reasons.append("板块涨停数达到阈值")
        if sector.up_stock_ratio >= 0.70:
            score += 15
            reasons.append("板块上涨家数占比高")
        if sector.has_catalyst:
            score += 15
            reasons.append("板块存在催化")
        return _clamp_score(score), reasons

    def score_trend(self, stock: StockCandidate) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        if stock.price_change_5d - stock.sector_change_5d >= 5:
            score += 25
            reasons.append("个股相对板块超额收益显著")
        if stock.above_ma5 and stock.above_ma10 and stock.above_ma20:
            score += 20
            reasons.append("同时站上 MA5/MA10/MA20")
        if stock.ma_bullish:
            score += 20
            reasons.append("均线多头结构成立")
        if stock.breakout:
            score += 20
            reasons.append("处于突破形态")
        if stock.close_near_high:
            score += 15
            reasons.append("收盘接近阶段高点")
        return _clamp_score(score), reasons

    def score_flow(self, stock: StockCandidate) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        if stock.volume_ratio >= 1.5:
            score += 20
            reasons.append("量比放大")
        if stock.volume_vs_avg5 >= 1.5:
            score += 25
            reasons.append("较 5 日均量明显放大")
        if 8 <= stock.turnover_rate <= 25:
            score += 20
            reasons.append("换手率处于活跃区间")
        if 10 <= stock.amount_billion <= 80:
            score += 20
            reasons.append("成交额满足短线容量要求")
        if stock.capital_inflow_positive and stock.tail_strength:
            score += 15
            reasons.append("资金净流入且尾盘承接强")
        return _clamp_score(score), reasons

    def score_risk(self, stock: StockCandidate) -> Tuple[float, List[str], List[str]]:
        score = 0.0
        reasons: List[str] = []
        risk_notes: List[str] = []
        if stock.distance_to_support_pct <= 5:
            score += 30
            reasons.append("距离支撑位较近")
        else:
            risk_notes.append("距离支撑位偏远")
        if not stock.is_accelerating_high:
            score += 20
            reasons.append("未出现加速赶顶")
        else:
            risk_notes.append("存在加速赶顶迹象")
        if stock.overhead_pressure_low:
            score += 20
            reasons.append("上方抛压较轻")
        else:
            risk_notes.append("上方抛压偏大")
        if stock.event_risk_low:
            score += 15
            reasons.append("事件风险较低")
        else:
            risk_notes.append("事件风险需重点跟踪")
        if stock.reward_risk_ratio >= 2.0:
            score += 15
            reasons.append("盈亏比达到 2.0 以上")
        else:
            risk_notes.append("盈亏比不足 2.0")
        return _clamp_score(score), reasons, risk_notes

    def rank_candidates(
        self,
        market: MarketSnapshot,
        sectors: Sequence[SectorSnapshot],
        stocks: Sequence[StockCandidate],
    ) -> List[ScoreBreakdown]:
        if not stocks:
            return []

        _validate_market_snapshot(market)
        for sector in sectors:
            _validate_sector_snapshot(sector)
        for stock in stocks:
            _validate_stock_candidate(stock)

        sector_map: Dict[str, SectorSnapshot] = {item.name: item for item in sectors}
        _validate_sector_references(stocks, sector_map)

        market_score, market_reasons = self.score_market(market)
        results: List[ScoreBreakdown] = []

        for stock in stocks:
            sector_score, sector_reasons = self.score_sector(sector_map[stock.sector])
            trend_score, trend_reasons = self.score_trend(stock)
            flow_score, flow_reasons = self.score_flow(stock)
            risk_score, risk_reasons, risk_notes = self.score_risk(stock)
            total_score = round(
                market_score * self.market_weight
                + sector_score * self.sector_weight
                + trend_score * self.trend_weight
                + flow_score * self.flow_weight
                + risk_score * self.risk_weight,
                2,
            )
            reasons = (
                market_reasons[:1]
                + sector_reasons[:2]
                + trend_reasons[:2]
                + flow_reasons[:2]
                + risk_reasons[:1]
            )
            if not reasons:
                reasons = ["缺少显著入选理由"]
            results.append(
                ScoreBreakdown(
                    code=stock.code,
                    name=stock.name,
                    sector=stock.sector,
                    market_score=market_score,
                    sector_score=sector_score,
                    trend_score=trend_score,
                    flow_score=flow_score,
                    risk_score=risk_score,
                    total_score=total_score,
                    tag=_score_tag(total_score),
                    reasons=reasons,
                    risk_notes=risk_notes,
                )
            )

        results.sort(key=lambda item: (-item.total_score, item.code))
        for index, item in enumerate(results, start=1):
            item.rank = index
        return results


def build_sample_dataset() -> Tuple[MarketSnapshot, List[SectorSnapshot], List[StockCandidate]]:
    market = MarketSnapshot(
        index_above_ma5=True,
        index_above_ma10=True,
        advancers_ratio=0.67,
        limit_up_count=82,
        limit_down_count=4,
        strong_stock_premium=2.8,
    )
    sectors = [
        SectorSnapshot("AI算力", 0.03, 0.04, 0.78, 3, True),
        SectorSnapshot("机器人", 0.06, 0.08, 0.72, 2, True),
        SectorSnapshot("金融科技", 0.09, 0.12, 0.71, 1, False),
    ]
    stocks = [
        StockCandidate(
            code="300001",
            name="算力龙头A",
            sector="AI算力",
            price_change_5d=14.0,
            sector_change_5d=7.5,
            above_ma5=True,
            above_ma10=True,
            above_ma20=True,
            ma_bullish=True,
            breakout=True,
            close_near_high=True,
            volume_ratio=2.2,
            volume_vs_avg5=1.9,
            turnover_rate=15.0,
            amount_billion=38.0,
            capital_inflow_positive=True,
            tail_strength=True,
            distance_to_support_pct=3.5,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=2.8,
        ),
        StockCandidate(
            code="300002",
            name="算力跟风B",
            sector="AI算力",
            price_change_5d=9.0,
            sector_change_5d=7.5,
            above_ma5=True,
            above_ma10=True,
            above_ma20=False,
            ma_bullish=False,
            breakout=False,
            close_near_high=True,
            volume_ratio=1.4,
            volume_vs_avg5=1.3,
            turnover_rate=11.0,
            amount_billion=22.0,
            capital_inflow_positive=True,
            tail_strength=False,
            distance_to_support_pct=6.2,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=1.9,
        ),
        StockCandidate(
            code="002001",
            name="机器人前排C",
            sector="机器人",
            price_change_5d=12.0,
            sector_change_5d=6.0,
            above_ma5=True,
            above_ma10=True,
            above_ma20=True,
            ma_bullish=True,
            breakout=True,
            close_near_high=True,
            volume_ratio=1.8,
            volume_vs_avg5=1.6,
            turnover_rate=18.0,
            amount_billion=26.0,
            capital_inflow_positive=True,
            tail_strength=True,
            distance_to_support_pct=4.1,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=2.4,
        ),
        StockCandidate(
            code="002002",
            name="机器人高标D",
            sector="机器人",
            price_change_5d=18.0,
            sector_change_5d=6.0,
            above_ma5=True,
            above_ma10=True,
            above_ma20=True,
            ma_bullish=True,
            breakout=True,
            close_near_high=True,
            volume_ratio=2.5,
            volume_vs_avg5=2.2,
            turnover_rate=28.0,
            amount_billion=31.0,
            capital_inflow_positive=True,
            tail_strength=True,
            distance_to_support_pct=8.5,
            is_accelerating_high=True,
            overhead_pressure_low=False,
            event_risk_low=True,
            reward_risk_ratio=1.6,
        ),
        StockCandidate(
            code="600001",
            name="金融科技E",
            sector="金融科技",
            price_change_5d=8.0,
            sector_change_5d=3.0,
            above_ma5=True,
            above_ma10=True,
            above_ma20=True,
            ma_bullish=False,
            breakout=False,
            close_near_high=False,
            volume_ratio=1.6,
            volume_vs_avg5=1.5,
            turnover_rate=9.0,
            amount_billion=14.0,
            capital_inflow_positive=True,
            tail_strength=True,
            distance_to_support_pct=4.8,
            is_accelerating_high=False,
            overhead_pressure_low=True,
            event_risk_low=True,
            reward_risk_ratio=2.1,
        ),
        StockCandidate(
            code="600002",
            name="弱势样本F",
            sector="金融科技",
            price_change_5d=2.0,
            sector_change_5d=3.0,
            above_ma5=False,
            above_ma10=False,
            above_ma20=False,
            ma_bullish=False,
            breakout=False,
            close_near_high=False,
            volume_ratio=0.9,
            volume_vs_avg5=0.8,
            turnover_rate=4.5,
            amount_billion=6.0,
            capital_inflow_positive=False,
            tail_strength=False,
            distance_to_support_pct=9.0,
            is_accelerating_high=False,
            overhead_pressure_low=False,
            event_risk_low=True,
            reward_risk_ratio=1.2,
        ),
    ]
    return market, sectors, stocks


def print_market_summary(market: MarketSnapshot, market_score: float) -> None:
    print("=== 市场环境摘要 ===")
    print(f"市场环境分: {market_score:.2f}")
    print(f"上涨家数占比: {market.advancers_ratio:.0%}")
    print(f"涨停/跌停家数: {market.limit_up_count}/{market.limit_down_count}")
    print(f"强势股平均溢价: {market.strong_stock_premium:.2f}%")
    print()


def print_ranking_table(results: Sequence[ScoreBreakdown]) -> None:
    print("=== 候选榜单 ===")
    if not results:
        print("候选股票列表为空")
        print()
        return

    header = (
        f"{'Rank':<4} {'Code':<8} {'Name':<10} {'Sector':<8} {'Total':>6} "
        f"{'Market':>6} {'Sector':>6} {'Trend':>6} {'Flow':>6} {'Risk':>6} {'Tag':<6} reason"
    )
    print(header)
    print("-" * len(header))
    for item in results:
        print(
            f"{item.rank:<4} {item.code:<8} {item.name:<10} {item.sector:<8} "
            f"{item.total_score:>6.2f} {item.market_score:>6.0f} {item.sector_score:>6.0f} "
            f"{item.trend_score:>6.0f} {item.flow_score:>6.0f} {item.risk_score:>6.0f} "
            f"{item.tag:<6} {'、'.join(item.reasons)}"
        )
    print()


def print_top_details(results: Sequence[ScoreBreakdown], top_n: int = 3) -> None:
    print(f"=== Top {top_n} 明细 ===")
    if not results:
        print("暂无可展示标的")
        print()
        return

    for item in results[:top_n]:
        print(f"[{item.rank}] {item.code} {item.name} ({item.tag})")
        print(
            f"总分={item.total_score:.2f} "
            f"Market={item.market_score:.0f} Sector={item.sector_score:.0f} "
            f"Trend={item.trend_score:.0f} Flow={item.flow_score:.0f} Risk={item.risk_score:.0f}"
        )
        print("入选原因: " + "、".join(item.reasons))
        if item.risk_notes:
            print("风险提醒: " + "、".join(item.risk_notes))
        else:
            print("风险提醒: 暂无显著额外风险")
        print()


def main() -> int:
    market, sectors, stocks = build_sample_dataset()
    scorer = ShortTermScorer()
    results = scorer.rank_candidates(market, sectors, stocks)
    market_score, _ = scorer.score_market(market)
    print_market_summary(market, market_score)
    print_ranking_table(results)
    print_top_details(results, top_n=3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
