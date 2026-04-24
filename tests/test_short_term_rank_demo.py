from pathlib import Path
import importlib.util
import sys

import pytest


def _load_demo_module():
    root = Path(__file__).resolve().parents[1]
    file_path = root / "scripts" / "short_term_rank_demo.py"
    spec = importlib.util.spec_from_file_location("short_term_rank_demo", file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
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

    with pytest.raises(ValueError, match="不存在的板块"):
        scorer.rank_candidates(market, sectors, stocks + [broken])


def test_main_prints_ranked_candidates(capsys):
    demo = _load_demo_module()

    exit_code = demo.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "短线候选股排序 Demo" in captured.out
    assert "代码" in captured.out
    assert "重点关注" in captured.out
