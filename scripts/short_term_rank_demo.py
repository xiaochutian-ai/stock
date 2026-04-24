from dataclasses import dataclass


@dataclass
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


class ShortTermScorer:
    def rank_candidates(self, market, sectors, stocks):
        if not stocks:
            return []
        raise NotImplementedError()


def build_sample_dataset():
    raise NotImplementedError()
