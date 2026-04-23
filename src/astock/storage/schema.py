"""SQLAlchemy ORM 模型定义（表结构 DDL）。

使用 SQLAlchemy 2.0 风格，确保同一套模型可同时适配 SQLite / MySQL / PostgreSQL。
"""

from __future__ import annotations

from sqlalchemy import Column, Date, Float, Integer, String, Boolean, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StockORM(Base):
    __tablename__ = "stocks"

    code = Column(String(8), primary_key=True)
    name = Column(String(32), nullable=False)
    board = Column(String(32), nullable=False)
    list_date = Column(Date, nullable=True)
    is_st = Column(Boolean, default=False)
    industry = Column(String(64), nullable=True)


class KLineORM(Base):
    __tablename__ = "klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(8), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    pct_change = Column(Float)
    turnover_rate = Column(Float)

    __table_args__ = (
        Index("uix_kline_code_date", "code", "trade_date", unique=True),
    )


class FinancialORM(Base):
    __tablename__ = "financials"

    code = Column(String(8), primary_key=True)
    report_date = Column(String(16), nullable=True)
    pe_ttm = Column(Float)
    pb = Column(Float)
    ps_ttm = Column(Float)
    dv_ratio = Column(Float)
    roe = Column(Float)
    gross_margin = Column(Float)
    net_margin = Column(Float)
    revenue_yoy = Column(Float)
    net_profit_yoy = Column(Float)
    total_market_cap = Column(Float)
    float_market_cap = Column(Float)


class MoneyFlowORM(Base):
    __tablename__ = "money_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(8), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    main_net_inflow = Column(Float, default=0.0)
    super_large_net = Column(Float, default=0.0)
    large_net = Column(Float, default=0.0)
    medium_net = Column(Float, default=0.0)
    small_net = Column(Float, default=0.0)
    north_bound_hold = Column(Float, nullable=True)

    __table_args__ = (
        Index("uix_mf_code_date", "code", "trade_date", unique=True),
    )
