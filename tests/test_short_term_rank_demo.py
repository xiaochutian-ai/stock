import importlib.util
import sys
import unicodedata
from dataclasses import replace
from pathlib import Path

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
    assert len(sectors) == 3
    assert results[0].total_score >= results[1].total_score >= results[2].total_score
    assert [item.rank for item in results] == [1, 2, 3, 4, 5, 6]
    assert results[0].tag == "重点关注"
    assert results[0].market_score >= 0
    assert results[0].sector_score >= 0
    assert results[0].trend_score >= 0
    assert results[0].flow_score >= 0
    assert results[0].risk_score >= 0
    assert results[0].reasons


def test_rank_candidates_assigns_expected_tags():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()

    results = scorer.rank_candidates(market, sectors, stocks)

    assert any(item.tag == "重点关注" for item in results)
    assert any(item.tag == "暂不推荐" for item in results)
    assert not any(item.tag == "观察池" for item in results)


def test_build_sample_dataset_matches_approved_design_shape():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()

    assert isinstance(market, demo.MarketSnapshot)
    assert len(sectors) == 3
    assert len(stocks) == 6
    assert {sector.name for sector in sectors} == {"AI算力", "机器人", "金融科技"}
    fintech_sector = next(sector for sector in sectors if sector.name == "金融科技")
    assert fintech_sector.change_1d_rank_pct == 0.22
    assert fintech_sector.change_3d_rank_pct == 0.18
    assert fintech_sector.up_stock_ratio == 0.58
    assert fintech_sector.limit_up_count == 1
    assert fintech_sector.has_catalyst is False


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


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def test_custom_weights_are_normalized_without_distorting_scores_or_tags():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    default_scorer = demo.ShortTermScorer()
    scaled_scorer = demo.ShortTermScorer(
        market_weight=20,
        sector_weight=25,
        trend_weight=25,
        flow_weight=20,
        risk_weight=10,
    )

    default_results = default_scorer.rank_candidates(market, sectors, stocks)
    scaled_results = scaled_scorer.rank_candidates(market, sectors, stocks)

    assert pytest.approx(
        scaled_scorer.market_weight
        + scaled_scorer.sector_weight
        + scaled_scorer.trend_weight
        + scaled_scorer.flow_weight
        + scaled_scorer.risk_weight
    ) == 1.0
    assert [item.total_score for item in scaled_results] == [
        item.total_score for item in default_results
    ]
    assert [item.tag for item in scaled_results] == [item.tag for item in default_results]


def test_rank_candidates_allows_negative_strong_stock_premium_for_weak_market():
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()
    weak_market = replace(market, strong_stock_premium=-1.5)

    results = scorer.rank_candidates(weak_market, sectors, stocks)
    market_score, reasons = scorer.score_market(weak_market)

    assert len(results) == len(stocks)
    assert market_score == 80
    assert "强势股平均溢价达标" not in reasons
    assert all(item.market_score == 80 for item in results)


def test_print_ranking_table_aligns_columns_for_cjk_content(capsys):
    demo = _load_demo_module()
    market, sectors, stocks = demo.build_sample_dataset()
    scorer = demo.ShortTermScorer()
    results = scorer.rank_candidates(market, sectors, stocks)

    demo.print_ranking_table(results[:4])

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    data_lines = lines[3:]

    reason_offsets = []
    for item, line in zip(results[:4], data_lines):
        reason_text = "、".join(item.reasons)
        reason_offsets.append(_display_width(line[: line.index(reason_text)]))

    assert len(set(reason_offsets)) == 1


def test_main_prints_ranked_candidates(capsys):
    demo = _load_demo_module()

    exit_code = demo.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "市场环境摘要" in captured.out
    assert "候选榜单" in captured.out
    assert "Top 3 明细" in captured.out
    assert "Total" in captured.out
    assert "Market" in captured.out
    assert "Sector" in captured.out
    assert "Trend" in captured.out
    assert "Flow" in captured.out
    assert "Risk" in captured.out
    assert "reason" in captured.out
    assert "风险提醒" in captured.out
