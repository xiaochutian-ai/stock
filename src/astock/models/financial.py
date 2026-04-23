"""财务指标数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Financial:
    """股票财务指标快照（截至报告期）。

    字段缺失时为 None，策略需容错处理。
    """

    code: str
    report_date: Optional[str] = None   # 报告期，如 "2024-09-30"

    # 估值
    pe_ttm: Optional[float] = None      # 市盈率 TTM
    pb: Optional[float] = None          # 市净率
    ps_ttm: Optional[float] = None      # 市销率 TTM
    dv_ratio: Optional[float] = None    # 股息率（%）

    # 盈利能力
    roe: Optional[float] = None         # 净资产收益率（%）
    gross_margin: Optional[float] = None  # 毛利率（%）
    net_margin: Optional[float] = None  # 净利率（%）

    # 成长性
    revenue_yoy: Optional[float] = None     # 营收同比增长（%）
    net_profit_yoy: Optional[float] = None  # 净利润同比增长（%）

    # 规模
    total_market_cap: Optional[float] = None  # 总市值（元）
    float_market_cap: Optional[float] = None  # 流通市值（元）
