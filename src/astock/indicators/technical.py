"""常用技术指标（纯 pandas 实现，零 C 扩展依赖）。

所有函数输入均为 pandas.Series（收盘价为主），输出也是 Series，
方便策略层按时间序列组合使用。
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


# ---------------- 基础指标 ----------------
def ma(close: pd.Series, n: int) -> pd.Series:
    """简单移动平均。"""
    return close.rolling(window=n, min_periods=1).mean()


def ema(close: pd.Series, n: int) -> pd.Series:
    """指数移动平均。"""
    return close.ewm(span=n, adjust=False).mean()


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 指标。

    Returns:
        (dif, dea, hist): 快慢差、平滑后 DEA、柱状图（hist = 2 * (dif - dea))
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = 2 * (dif - dea)
    return dif, dea, hist


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI 相对强弱指标。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)


def kdj(
    high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9,
    k_smooth: int = 3, d_smooth: int = 3,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ 随机指标。"""
    lowest = low.rolling(window=n, min_periods=1).min()
    highest = high.rolling(window=n, min_periods=1).max()
    denom = (highest - lowest).replace(0, np.nan)
    rsv = (close - lowest) / denom * 100
    rsv = rsv.fillna(50.0)
    k = rsv.ewm(alpha=1 / k_smooth, adjust=False).mean()
    d = k.ewm(alpha=1 / d_smooth, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def boll(close: pd.Series, n: int = 20, std_dev: float = 2.0):
    """布林带。"""
    mid = ma(close, n)
    std = close.rolling(window=n, min_periods=1).std().fillna(0)
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


# ---------------- 常见形态判断 ----------------
def is_ma_bull(close: pd.Series, periods=(5, 10, 20, 60)) -> bool:
    """均线多头排列：MA5 > MA10 > MA20 > MA60（默认）。"""
    if len(close) < max(periods):
        return False
    vals = [ma(close, p).iloc[-1] for p in periods]
    return all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))


def is_macd_gold_cross(close: pd.Series, lookback: int = 3) -> bool:
    """最近 lookback 日内是否出现 MACD 金叉（DIF 上穿 DEA）。"""
    dif, dea, _ = macd(close)
    if len(dif) < lookback + 1:
        return False
    # 在最近 lookback 日窗口内，存在某一日 DIF <= DEA 且下一日 DIF > DEA
    dif_arr = dif.values[-(lookback + 1):]
    dea_arr = dea.values[-(lookback + 1):]
    for i in range(len(dif_arr) - 1):
        if dif_arr[i] <= dea_arr[i] and dif_arr[i + 1] > dea_arr[i + 1]:
            return True
    return False


def is_volume_burst(volume: pd.Series, multiplier: float = 2.0, base_n: int = 5) -> bool:
    """放量突破：当日成交量 > 过去 base_n 日均量 * multiplier。"""
    if len(volume) < base_n + 1:
        return False
    base_avg = volume.iloc[-(base_n + 1):-1].mean()
    if base_avg <= 0:
        return False
    return float(volume.iloc[-1]) > base_avg * multiplier
