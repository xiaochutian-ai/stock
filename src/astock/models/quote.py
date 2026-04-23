"""行情数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd


@dataclass(frozen=True)
class Quote:
    """单日行情快照。"""

    code: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float       # 成交量（股）
    amount: float       # 成交额（元）
    pct_change: float   # 涨跌幅（%）
    turnover_rate: float = 0.0  # 换手率（%）


@dataclass
class KLine:
    """K 线序列（一只股票的历史行情）。

    内部用 pandas.DataFrame 承载，字段固定：
    date, open, high, low, close, volume, amount, pct_change, turnover_rate
    """

    code: str
    df: pd.DataFrame  # index=date, columns=[open, high, low, close, volume, amount, ...]

    def __len__(self) -> int:
        return len(self.df)

    def is_empty(self) -> bool:
        """K 线是否为空（无数据）。"""
        return self.df is None or self.df.empty

    @property
    def close(self) -> pd.Series:
        """收盘价序列（按时间升序）。"""
        return self.df["close"]

    @property
    def open(self) -> pd.Series:
        """开盘价序列。"""
        return self.df["open"]

    @property
    def high(self) -> pd.Series:
        """最高价序列。"""
        return self.df["high"]

    @property
    def low(self) -> pd.Series:
        """最低价序列。"""
        return self.df["low"]

    @property
    def volume(self) -> pd.Series:
        """成交量序列。"""
        return self.df["volume"]

    @property
    def amount(self) -> pd.Series:
        """成交额序列。"""
        return self.df["amount"]

    @property
    def latest(self) -> Quote:
        """返回最近一个交易日的 Quote。"""
        if self.df.empty:
            raise ValueError(f"KLine for {self.code} is empty")
        last = self.df.iloc[-1]
        return Quote(
            code=self.code,
            trade_date=pd.to_datetime(self.df.index[-1]).date(),
            open=float(last.get("open", 0) or 0),
            high=float(last.get("high", 0) or 0),
            low=float(last.get("low", 0) or 0),
            close=float(last.get("close", 0) or 0),
            volume=float(last.get("volume", 0) or 0),
            amount=float(last.get("amount", 0) or 0),
            pct_change=float(last.get("pct_change", 0) or 0),
            turnover_rate=float(last.get("turnover_rate", 0) or 0),
        )

    def tail_closes(self, n: int) -> List[float]:
        """返回最近 n 日收盘价（升序）。"""
        return self.df["close"].tail(n).tolist()
