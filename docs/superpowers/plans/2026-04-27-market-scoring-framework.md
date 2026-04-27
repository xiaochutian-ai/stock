# Market Scoring Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable A-share market scoring framework with technical factors, composite factors, and a regime strategy, plus a runnable demo script.

**Architecture:** Add a new `analytics` subpackage so the framework stays decoupled from the existing stock-screening strategy system. Keep the implementation layered: raw market snapshots feed bottom-level factors, composite scorers aggregate them into trend/volume/breadth, and a regime strategy turns them into a final score and label.

**Tech Stack:** Python 3.9+, `dataclasses`, `statistics`, `typing`, `pytest`

---

## File Structure

- Create: `src/astock/analytics/__init__.py`
  - Package entry for reusable analytics exports
- Create: `src/astock/analytics/market_scoring.py`
  - Core data models, factor calculator, composite scorer, and strategy
- Create: `scripts/market_score_demo.py`
  - Demo entrypoint with sample data and console output
- Create: `tests/test_market_scoring.py`
  - Focused behavior tests for factor calculation, regime labeling, fallback handling, and demo output
- Reference: `docs/superpowers/specs/2026-04-27-market-scoring-framework-design.md`
  - Approved feature design

### Task 1: Write The Failing Market Scoring Tests

**Files:**
- Create: `tests/test_market_scoring.py`
- Reference: `docs/superpowers/specs/2026-04-27-market-scoring-framework-design.md`

- [ ] **Step 1: Write the failing test file**

```python
import importlib.util
import sys
from pathlib import Path

import pytest


def _load_module():
    root = Path(__file__).resolve().parents[1]
    file_path = root / "src" / "astock" / "analytics" / "market_scoring.py"
    spec = importlib.util.spec_from_file_location("market_scoring", file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_strong_market_is_classified_as_strong():
    scoring = _load_module()
    dataset = scoring.build_sample_market_dataset()

    result = scoring.MarketRegimeStrategy().evaluate(dataset)

    assert result.regime == "强势"
    assert result.total_score >= 70


def test_weak_market_is_classified_as_weak():
    scoring = _load_module()
    dataset = scoring.build_weak_market_dataset()

    result = scoring.MarketRegimeStrategy().evaluate(dataset)

    assert result.regime == "弱势"
    assert result.total_score < 40


def test_short_history_uses_neutral_fallback_instead_of_crashing():
    scoring = _load_module()
    dataset = scoring.MarketDataset(
        bars=[
            scoring.MarketBar("2026-04-25", close=100.0, volume=1000.0),
            scoring.MarketBar("2026-04-26", close=101.0, volume=1100.0),
        ],
        breadth=[
            scoring.BreadthSnapshot(
                "2026-04-26",
                advancers=2600,
                decliners=2400,
                new_highs=120,
                new_lows=80,
                stocks_above_ma20=2800,
                total_stocks=5200,
            )
        ],
    )

    result = scoring.MarketRegimeStrategy().evaluate(dataset)

    assert 0 <= result.trend.score <= 100
    assert 0 <= result.volume.score <= 100
    assert 0 <= result.breadth.score <= 100
    assert result.regime in {"强势", "震荡", "弱势"}


def test_missing_breadth_for_latest_trade_date_raises_error():
    scoring = _load_module()
    dataset = scoring.MarketDataset(
        bars=[scoring.MarketBar("2026-04-26", close=100.0, volume=1000.0)],
        breadth=[
            scoring.BreadthSnapshot(
                "2026-04-25",
                advancers=2500,
                decliners=2500,
                new_highs=50,
                new_lows=50,
                stocks_above_ma20=2600,
                total_stocks=5200,
            )
        ],
    )

    with pytest.raises(ValueError, match="最新交易日"):
        scoring.MarketRegimeStrategy().evaluate(dataset)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/test_market_scoring.py -q`

Expected: FAIL with `FileNotFoundError` or import-related failure because `src/astock/analytics/market_scoring.py` does not exist yet.

- [ ] **Step 3: Commit the red test**

```bash
git add tests/test_market_scoring.py
git commit -m "test: add market scoring framework coverage"
```

### Task 2: Implement The Analytics Framework

**Files:**
- Create: `src/astock/analytics/__init__.py`
- Create: `src/astock/analytics/market_scoring.py`
- Test: `tests/test_market_scoring.py`

- [ ] **Step 1: Create the analytics package entrypoint**

```python
from .market_scoring import (
    BreadthSnapshot,
    CompositeFactorResult,
    FactorValue,
    MarketBar,
    MarketDataset,
    MarketRegimeStrategy,
    MarketScoreResult,
    build_sample_market_dataset,
    build_weak_market_dataset,
)

__all__ = [
    "BreadthSnapshot",
    "CompositeFactorResult",
    "FactorValue",
    "MarketBar",
    "MarketDataset",
    "MarketRegimeStrategy",
    "MarketScoreResult",
    "build_sample_market_dataset",
    "build_weak_market_dataset",
]
```

- [ ] **Step 2: Create the core data models and score helpers**

Implement `src/astock/analytics/market_scoring.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List, Sequence


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
```

- [ ] **Step 3: Implement bottom-level factor calculation**

Add a `MarketFactorCalculator` with methods:

```python
class MarketFactorCalculator:
    def latest_breadth(self, dataset: MarketDataset) -> BreadthSnapshot:
        ...

    def factor_close_above_ma20(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_ma20_above_ma60(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_momentum_20d(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_volume_ratio_20d(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_up_day_volume_ratio(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_advancers_ratio(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_new_high_ratio(self, dataset: MarketDataset) -> FactorValue:
        ...

    def factor_above_ma20_ratio(self, dataset: MarketDataset) -> FactorValue:
        ...
```

Rules:
- Empty `bars` -> `ValueError("指数行情不能为空")`
- Empty `breadth` -> `ValueError("市场宽度不能为空")`
- Latest bar date missing in breadth -> `ValueError("最新交易日缺少对应的市场宽度快照")`
- Insufficient history for moving windows -> return neutral score `50.0`

- [ ] **Step 4: Implement composite factor scoring**

Create `CompositeFactorScorer`:

```python
class CompositeFactorScorer:
    def __init__(self, calculator: MarketFactorCalculator | None = None) -> None:
        self.calculator = calculator or MarketFactorCalculator()

    def score_trend(self, dataset: MarketDataset) -> CompositeFactorResult:
        ...

    def score_volume(self, dataset: MarketDataset) -> CompositeFactorResult:
        ...

    def score_breadth(self, dataset: MarketDataset) -> CompositeFactorResult:
        ...
```

Use weights:
- Trend: `0.35`, `0.35`, `0.30`
- Volume: `0.50`, `0.50`
- Breadth: `0.40`, `0.25`, `0.35`

- [ ] **Step 5: Implement regime strategy**

Create `MarketRegimeStrategy.evaluate()`:

```python
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
        regime = "强势" if total_score >= 70 else "震荡" if total_score >= 40 else "弱势"
        return MarketScoreResult(...)
```

- [ ] **Step 6: Add sample datasets**

Add:

```python
def build_sample_market_dataset() -> MarketDataset:
    ...


def build_weak_market_dataset() -> MarketDataset:
    ...
```

The strong sample should have rising closes, healthy volume, and strong breadth so the score lands in `强势`.

The weak sample should have falling closes, weak volume participation, and poor breadth so the score lands in `弱势`.

- [ ] **Step 7: Run the tests and verify GREEN**

Run: `pytest tests/test_market_scoring.py -q`

Expected: PASS with 4 passing tests.

### Task 3: Add The Demo Script And Smoke Coverage

**Files:**
- Create: `scripts/market_score_demo.py`
- Modify: `tests/test_market_scoring.py`

- [ ] **Step 1: Write a failing smoke test for the demo output**

Append to `tests/test_market_scoring.py`:

```python
def test_demo_main_prints_composite_scores_and_regime(capsys):
    root = Path(__file__).resolve().parents[1]
    file_path = root / "scripts" / "market_score_demo.py"
    spec = importlib.util.spec_from_file_location("market_score_demo", file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    exit_code = module.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "趋势分" in captured.out
    assert "成交量分" in captured.out
    assert "宽度分" in captured.out
    assert "市场状态" in captured.out
```

- [ ] **Step 2: Run the new test and verify RED**

Run: `pytest tests/test_market_scoring.py::test_demo_main_prints_composite_scores_and_regime -q`

Expected: FAIL with `FileNotFoundError` because `scripts/market_score_demo.py` does not exist yet.

- [ ] **Step 3: Implement the demo script**

Create `scripts/market_score_demo.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from astock.analytics.market_scoring import MarketRegimeStrategy, build_sample_market_dataset


def main() -> int:
    dataset = build_sample_market_dataset()
    result = MarketRegimeStrategy().evaluate(dataset)
    print("=== 大盘走势打分 ===")
    print(f"趋势分: {result.trend.score:.2f}")
    print(f"成交量分: {result.volume.score:.2f}")
    print(f"宽度分: {result.breadth.score:.2f}")
    print(f"总分: {result.total_score:.2f}")
    print(f"市场状态: {result.regime}")
    print(f"摘要: {result.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_market_scoring.py -q`

Expected: PASS with all tests green.

- [ ] **Step 5: Run the demo script**

Run: `python3 scripts/market_score_demo.py`

Expected: Prints trend, volume, breadth, total score, and regime without traceback.

- [ ] **Step 6: Run lint**

Run: `ruff check src/astock/analytics scripts/market_score_demo.py tests/test_market_scoring.py`

Expected: `All checks passed!`

## Self-Review

- Spec coverage:
  - Layered factor -> composite -> strategy structure: covered in Task 2 Steps 2-5
  - Reusable analytics module and demo script: covered in Task 2 Step 1 and Task 3 Step 3
  - Strong/weak market examples: covered in Task 2 Step 6
  - Fallback and input validation behavior: covered in Task 1 and Task 2 Step 3
  - Demo output validation: covered in Task 3
- Placeholder scan:
  - No `TODO`, `TBD`, or unresolved references remain
- Type consistency:
  - `MarketDataset`, `MarketRegimeStrategy`, `CompositeFactorScorer`, and `FactorValue` names are used consistently across tasks
