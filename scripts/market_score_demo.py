from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from astock.analytics.market_scoring import (  # noqa: E402
    MarketRegimeStrategy,
    build_sample_market_dataset,
)


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
    print()
    print("=== 分项解释 ===")
    for section in (result.trend, result.volume, result.breadth):
        print(f"[{section.name}] {section.comment}")
        for factor in section.factors:
            print(f"- {factor.name}: value={factor.value:.4f}, score={factor.score:.2f}, {factor.comment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
