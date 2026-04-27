# Short-Term Rank Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python demo script that scores multiple A-share stocks with a five-dimension short-term model and prints a ranked candidate list.

**Architecture:** Keep the implementation isolated in `scripts/short_term_rank_demo.py` with standard-library-only data classes, scoring logic, sample data, and console output helpers. Add a focused pytest file to verify scoring order, label thresholds, and empty-input behavior without coupling the script to the existing screening engine.

**Tech Stack:** Python 3.9+, `dataclasses`, `typing`, `pytest`

---

## File Structure

- Create: `scripts/short_term_rank_demo.py`
  - Standalone demo script with data classes, scorer, sample data, output helpers, and `main()`
- Create: `tests/test_short_term_rank_demo.py`
  - Focused tests for ranking, labels, validation, and empty-list handling
- Reference: `docs/superpowers/specs/2026-04-24-short-term-rank-demo-design.md`
  - Confirm implementation matches approved design

### Task 1: Add Focused Tests For The Demo Scorer

**Files:**
- Create: `tests/test_short_term_rank_demo.py`
- Reference: `docs/superpowers/specs/2026-04-24-short-term-rank-demo-design.md`

- [ ] **Step 1: Write the failing test file**

```python
from pathlib import Path
import importlib.util


def _load_demo_module():
    root = Path(__file__).resolve().parents[1]
    file_path = root / "scripts" / "short_term_rank_demo.py"
    spec = importlib.util.spec_from_file_location("short_term_rank_demo", file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rank_candidates_orders_by_total_score():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()

    results = scorer.rank_candidates(market, sectors, stocks)

    assert len(results) == 6
    assert results[0].total_score >= results[1].total_score >= results[2].total_score
    assert results[0].tag in {"重点关注", "观察池"}


def test_rank_candidates_assigns_expected_tags():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()

    results = scorer.rank_candidates(market, sectors, stocks)

    assert any(item.tag == "重点关注" for item in results)
    assert any(item.tag == "观察池" for item in results)
    assert any(item.tag == "暂不推荐" for item in results)


def test_rank_candidates_returns_empty_for_no_stocks():
    demo = _load_demo_module()
    market, sectors, _ = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()

    results = scorer.rank_candidates(market, sectors, [])

    assert results == []


def test_rank_candidates_rejects_unknown_sector():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()
    broken = demo.StockCandidate(
        code="999999",
        name="未知板块样本",
        sector="不存在的板块",
        price_change_5d=8.0,
        sector_change_5d=2.0,
        above_ma5=True,
        above_ma10=True,
        above_ma20=True,
        ma_bullish=True,
        breakout=True,
        close_near_high=True,
        volume_ratio=1.8,
        volume_vs_avg5=1.7,
        turnover_rate=12.0,
        amount_billion=25.0,
        capital_inflow_positive=True,
        tail_strength=True,
        distance_to_support_pct=3.0,
        is_accelerating_high=False,
        overhead_pressure_low=True,
        event_risk_low=True,
        reward_risk_ratio=2.5,
    )

    import pytest

    with pytest.raises(ValueError, match="不存在的板块"):
        scorer.rank_candidates(market, sectors, stocks + [broken])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_short_term_rank_demo.py -q`

Expected: FAIL with an error similar to `FileNotFoundError`, `AttributeError`, or `ModuleNotFoundError` because `scripts/short_term_rank_demo.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation skeleton**

Create `scripts/short_term_rank_demo.py` with the minimum public API used by the tests:

```python
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
```

- [ ] **Step 4: Run test to verify it still fails for the expected reason**

Run: `pytest tests/test_short_term_rank_demo.py -q`

Expected: FAIL with `NotImplementedError`, confirming the tests now reach the intended public API.

- [ ] **Step 5: Commit**

```bash
git add tests/test_short_term_rank_demo.py scripts/short_term_rank_demo.py
git commit -m "test: add coverage for short-term rank demo"
```

### Task 2: Implement The Standalone Demo Script

**Files:**
- Modify: `scripts/short_term_rank_demo.py`
- Test: `tests/test_short_term_rank_demo.py`

- [ ] **Step 1: Replace the skeleton with complete data models**

Implement the full data classes and result model:

```python
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
```

- [ ] **Step 2: Implement validation helpers and score clamping**

Add internal helpers that validate ratios, non-negative numeric fields, sector references, and weight sums:

```python
def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, score))


def _validate_ratio(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} 必须在 0 到 1 之间，实际为 {value}")


def _validate_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} 不能为负数，实际为 {value}")
```

- [ ] **Step 3: Implement `ShortTermScorer` weights and dimension scoring**

Fill in the scorer with the approved weights and five dimension methods:

```python
class ShortTermScorer:
    def __init__(
        self,
        market_weight: float = 0.20,
        sector_weight: float = 0.25,
        trend_weight: float = 0.25,
        flow_weight: float = 0.20,
        risk_weight: float = 0.10,
    ) -> None:
        self.market_weight = market_weight
        self.sector_weight = sector_weight
        self.trend_weight = trend_weight
        self.flow_weight = flow_weight
        self.risk_weight = risk_weight
        total = (
            self.market_weight
            + self.sector_weight
            + self.trend_weight
            + self.flow_weight
            + self.risk_weight
        )
        if total <= 0:
            raise ValueError("权重总和必须大于 0")

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
            reasons.append("上涨家数占比良好")
        if market.limit_up_count >= 70 and market.limit_down_count <= 10:
            score += 20
            reasons.append("涨停活跃且跌停可控")
        if market.strong_stock_premium >= 2.0:
            score += 20
            reasons.append("强势股次日溢价为正")
        return _clamp_score(score), reasons
```

Implement equivalent methods for `score_sector()`, `score_trend()`, `score_flow()`, and `score_risk()` using the approved thresholds from the design doc.

- [ ] **Step 4: Implement ranking, tagging, and explanation assembly**

Add ranking and explanation logic:

```python
    def rank_candidates(
        self,
        market: MarketSnapshot,
        sectors: Sequence[SectorSnapshot],
        stocks: Sequence[StockCandidate],
    ) -> List[ScoreBreakdown]:
        if not stocks:
            return []

        sector_map: Dict[str, SectorSnapshot] = {item.name: item for item in sectors}
        market_score, market_reasons = self.score_market(market)
        results: List[ScoreBreakdown] = []

        for stock in stocks:
            if stock.sector not in sector_map:
                raise ValueError(f"股票 {stock.code} 引用了不存在的板块: {stock.sector}")
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
                    reasons=(market_reasons[:1] + sector_reasons[:2] + trend_reasons[:2] + flow_reasons[:2]),
                    risk_notes=risk_notes,
                )
            )

        results.sort(key=lambda item: item.total_score, reverse=True)
        for index, item in enumerate(results, start=1):
            item.rank = index
        return results
```

- [ ] **Step 5: Implement sample data and console output helpers**

Add sample dataset and formatting helpers:

```python
def build_sample_dataset():
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
        SectorSnapshot("金融科技", 0.22, 0.18, 0.58, 1, False),
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
    header = (
        f"{'Rank':<4} {'Code':<8} {'Name':<10} {'Sector':<8} {'Total':>6} "
        f"{'Mkt':>5} {'Sec':>5} {'Trd':>5} {'Flow':>5} {'Risk':>5} {'Tag':<6}"
    )
    print(header)
    print("-" * len(header))
    for item in results:
        print(
            f"{item.rank:<4} {item.code:<8} {item.name:<10} {item.sector:<8} "
            f"{item.total_score:>6.2f} {item.market_score:>5.0f} {item.sector_score:>5.0f} "
            f"{item.trend_score:>5.0f} {item.flow_score:>5.0f} {item.risk_score:>5.0f} "
            f"{item.tag:<6}"
        )
    print()


def print_top_details(results: Sequence[ScoreBreakdown], top_n: int = 3) -> None:
    print(f"=== Top {top_n} 明细 ===")
    for item in results[:top_n]:
        print(f"[{item.rank}] {item.code} {item.name} ({item.tag})")
        print(
            f"总分={item.total_score:.2f} "
            f"市场={item.market_score:.0f} 板块={item.sector_score:.0f} "
            f"趋势={item.trend_score:.0f} 资金={item.flow_score:.0f} 风险={item.risk_score:.0f}"
        )
        print("入选原因: " + "、".join(item.reasons))
        if item.risk_notes:
            print("风险提醒: " + "、".join(item.risk_notes))
        else:
            print("风险提醒: 暂无显著额外风险")
        print()
```

Use simple string formatting with fixed-width columns so the script has no third-party dependencies.

- [ ] **Step 6: Implement `main()` and executable entrypoint**

Finalize the script with a `main()` function:

```python
def main() -> None:
    market, sectors, stocks = build_sample_dataset()
    scorer = ShortTermScorer()
    results = scorer.rank_candidates(market, sectors, stocks)
    market_score, _ = scorer.score_market(market)
    print_market_summary(market, market_score)
    print_ranking_table(results)
    print_top_details(results, top_n=3)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run the focused tests**

Run: `pytest tests/test_short_term_rank_demo.py -q`

Expected: PASS with 4 passing tests.

- [ ] **Step 8: Run the script for a smoke check**

Run: `python3 scripts/short_term_rank_demo.py`

Expected: Prints a market summary, a 6-row ranking table, and a Top 3 detail section with no traceback.

- [ ] **Step 9: Run lint and verify no new issues**

Run: `ruff check scripts/short_term_rank_demo.py tests/test_short_term_rank_demo.py`

Expected: `All checks passed!`

- [ ] **Step 10: Commit**

```bash
git add scripts/short_term_rank_demo.py tests/test_short_term_rank_demo.py
git commit -m "feat: add short-term ranking demo script"
```

## Self-Review

- Spec coverage:
  - Five scoring dimensions: covered in Task 2 Step 3
  - Sample market, sector, stock data: covered in Task 2 Step 5
  - Ranked output and Top 3 details: covered in Task 2 Steps 5-6
  - Error handling and empty-list behavior: covered in Task 1 and Task 2 Step 2
  - Validation commands: covered in Task 2 Steps 7-9
- Placeholder scan:
  - No `TODO`, `TBD`, ellipsis, or unresolved task references remain
- Type consistency:
  - `MarketSnapshot`, `SectorSnapshot`, `StockCandidate`, `ScoreBreakdown`, and `ShortTermScorer.rank_candidates()` are named consistently across all tasks
