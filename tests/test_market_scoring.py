import importlib.util
import sys
from pathlib import Path

import pytest


def _load_scoring_module():
    root = Path(__file__).resolve().parents[1]
    file_path = root / "src" / "astock" / "analytics" / "market_scoring.py"
    spec = importlib.util.spec_from_file_location("market_scoring", file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_demo_module():
    root = Path(__file__).resolve().parents[1]
    file_path = root / "scripts" / "market_score_demo.py"
    spec = importlib.util.spec_from_file_location("market_score_demo", file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_strong_market_is_classified_as_strong():
    scoring = _load_scoring_module()
    dataset = scoring.build_sample_market_dataset()

    result = scoring.MarketRegimeStrategy().evaluate(dataset)

    assert result.regime == "强势"
    assert result.total_score >= 70
    assert result.trend.score > result.volume.score - 20


def test_weak_market_is_classified_as_weak():
    scoring = _load_scoring_module()
    dataset = scoring.build_weak_market_dataset()

    result = scoring.MarketRegimeStrategy().evaluate(dataset)

    assert result.regime == "弱势"
    assert result.total_score < 40


def test_short_history_uses_neutral_fallback_instead_of_crashing():
    scoring = _load_scoring_module()
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
    scoring = _load_scoring_module()
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


def test_demo_main_prints_composite_scores_and_regime(capsys):
    demo = _load_demo_module()

    exit_code = demo.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "趋势分" in captured.out
    assert "成交量分" in captured.out
    assert "宽度分" in captured.out
    assert "总分" in captured.out
    assert "市场状态" in captured.out
