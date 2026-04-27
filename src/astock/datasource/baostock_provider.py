"""baostock 数据源实现。

baostock 是免费开源的证券数据平台，无需注册。
官网: https://www.baostock.com
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Iterable, List, Optional, Tuple

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models import Board, Financial, KLine, MoneyFlow, Stock
from .base import DataProvider
from .registry import register_provider

logger = logging.getLogger(__name__)

_DAILY_KLINE_FIELDS = (
    "date,code,open,high,low,close,preclose,volume,amount,adjustflag,"
    "turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,isST"
)


@register_provider("baostock")
class BaostockProvider(DataProvider):
    """基于 baostock 的 A 股数据源实现。"""

    def __init__(self, options: Optional[dict] = None):
        super().__init__(options)
        try:
            import baostock as bs
        except ImportError as e:
            raise ImportError(
                "baostock 未安装，请运行: pip install baostock 或 pip install -e '.[baostock]'"
            ) from e

        self._bs = bs
        self._retry_times = int(self.options.get("retry", 3))
        self._logged_in = False
        self._login()

    # ---------------- 股票列表 ----------------
    def list_stocks(self) -> List[Stock]:
        rs = self._call(self._bs.query_all_stock, date.today().strftime("%Y-%m-%d"))
        df = self._resultset_to_df(rs)
        if df.empty:
            return []

        code_col = _pick_column(df, "code")
        name_col = _pick_column(df, "code_name", "name")
        if code_col is None or name_col is None:
            logger.warning("baostock: 股票列表缺少必要字段")
            return []

        stocks: List[Stock] = []
        for _, row in df.iterrows():
            raw_code = str(row.get(code_col, "")).strip()
            raw_name = str(row.get(name_col, "")).strip()
            if not _is_a_share_symbol(raw_code, raw_name):
                continue
            code = _strip_market_prefix(raw_code)
            if not _is_a_share_code(code) or not raw_name:
                continue
            name = raw_name
            stocks.append(
                Stock(
                    code=code,
                    name=name,
                    board=Board.from_code(code),
                    is_st="ST" in name.upper(),
                )
            )
        logger.info("baostock: 拉取到 %d 只股票", len(stocks))
        return stocks

    # ---------------- K 线 ----------------
    def get_kline(
        self,
        code: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        adjust: str = "qfq",
    ) -> KLine:
        end = end or date.today()
        start = start or (end - timedelta(days=365))

        rs = self._call(
            self._bs.query_history_k_data_plus,
            _to_baostock_code(code),
            _DAILY_KLINE_FIELDS,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "d",
            _map_adjustflag(adjust),
        )
        df = self._resultset_to_df(rs)
        if df.empty:
            return KLine(code=code, df=pd.DataFrame())

        rename_map = {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "amount": "amount",
            "pctChg": "pct_change",
            "turn": "turnover_rate",
        }
        df = df.rename(columns=rename_map)
        if "date" not in df.columns:
            return KLine(code=code, df=pd.DataFrame())

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        for col in [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "pct_change",
            "turnover_rate",
        ]:
            if col not in df.columns:
                df[col] = 0.0
            df[col] = df[col].map(lambda v: _safe_float(v) or 0.0)
        df = df[
            [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "pct_change",
                "turnover_rate",
            ]
        ].astype(float)
        return KLine(code=code, df=df)

    # ---------------- 财务 ----------------
    def get_financial(self, code: str) -> Financial:
        valuation_df = self._get_latest_valuation_df(code)
        report_date = None
        pe_ttm = None
        pb = None
        ps_ttm = None
        close_price = None

        if not valuation_df.empty:
            last = valuation_df.iloc[-1]
            report_date = _safe_str(last.get("date"))
            pe_ttm = _safe_float(last.get("peTTM"))
            pb = _safe_float(last.get("pbMRQ"))
            ps_ttm = _safe_float(last.get("psTTM"))
            close_price = _safe_float(last.get("close"))

        profit_row = self._get_latest_report_row(self._bs.query_profit_data, code)
        growth_row = self._get_latest_report_row(self._bs.query_growth_data, code)

        report_date = (
            _safe_str((profit_row or {}).get("statDate"))
            or _safe_str((growth_row or {}).get("statDate"))
            or report_date
        )

        return Financial(
            code=code,
            report_date=report_date,
            pe_ttm=pe_ttm,
            pb=pb,
            ps_ttm=ps_ttm,
            roe=_normalize_ratio((profit_row or {}).get("roeAvg")),
            gross_margin=_normalize_ratio((profit_row or {}).get("gpMargin")),
            net_margin=_normalize_ratio(
                (profit_row or {}).get("npMargin", (profit_row or {}).get("netProfitRatio"))
            ),
            revenue_yoy=_normalize_ratio((growth_row or {}).get("YOYOr")),
            net_profit_yoy=_normalize_ratio((growth_row or {}).get("YOYNI")),
            total_market_cap=_calc_market_cap(close_price, (profit_row or {}).get("totalShare")),
            float_market_cap=_calc_market_cap(close_price, (profit_row or {}).get("liqaShare")),
        )

    # ---------------- 资金流 ----------------
    def get_money_flow(self, code: str, days: int = 5) -> List[MoneyFlow]:
        logger.info(
            "baostock: %s 暂无原生资金流接口支持，get_money_flow(days=%s) 返回空列表",
            code,
            days,
        )
        return []

    # ---------------- 资源管理 ----------------
    def close(self) -> None:
        if not getattr(self, "_logged_in", False):
            return None
        try:
            self._bs.logout()
        except Exception as e:
            logger.warning("baostock: logout 失败: %s", e)
        finally:
            self._logged_in = False
        return None

    # ---------------- 工具 ----------------
    def _login(self) -> None:
        result = self._bs.login()
        if getattr(result, "error_code", "-1") != "0":
            raise RuntimeError(
                f"baostock 登录失败: {getattr(result, 'error_code', '?')} "
                f"{getattr(result, 'error_msg', 'unknown error')}"
            )
        self._logged_in = True

    def _call(self, func, *args, **kwargs):
        @retry(stop=stop_after_attempt(self._retry_times), wait=wait_fixed(1))
        def _inner():
            return func(*args, **kwargs)

        try:
            return _inner()
        except Exception as e:
            logger.error("baostock 调用 %s 失败: %s", getattr(func, "__name__", func), e)
            return None

    def _resultset_to_df(self, rs) -> pd.DataFrame:
        if rs is None:
            return pd.DataFrame()
        if getattr(rs, "error_code", "0") != "0":
            logger.warning(
                "baostock: 结果集错误 error_code=%s error_msg=%s",
                getattr(rs, "error_code", None),
                getattr(rs, "error_msg", None),
            )
            return pd.DataFrame()

        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        if not rows:
            return pd.DataFrame(columns=getattr(rs, "fields", []))
        return pd.DataFrame(rows, columns=getattr(rs, "fields", []))

    def _get_latest_valuation_df(self, code: str) -> pd.DataFrame:
        end = date.today()
        start = end - timedelta(days=30)
        rs = self._call(
            self._bs.query_history_k_data_plus,
            _to_baostock_code(code),
            _DAILY_KLINE_FIELDS,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "d",
            "2",
        )
        df = self._resultset_to_df(rs)
        if df.empty:
            return df
        if "date" in df.columns:
            df = df.sort_values("date")
        return df

    def _get_latest_report_row(self, func, code: str) -> Optional[dict]:
        symbol = _to_baostock_code(code)
        for year, quarter in _recent_quarters(date.today(), count=8):
            rs = self._call(func, symbol, year, quarter)
            df = self._resultset_to_df(rs)
            if df.empty:
                continue
            return df.iloc[-1].to_dict()
        return None


# ---------------- 模块级工具 ----------------
def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        if isinstance(v, str):
            v = v.replace(",", "").strip()
            if v in ("", "-", "--"):
                return None
        f = float(v)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _safe_str(v) -> Optional[str]:
    if v is None:
        return None
    text = str(v).strip()
    return text or None


def _normalize_ratio(v) -> Optional[float]:
    value = _safe_float(v)
    if value is None:
        return None
    if abs(value) > 1.0:
        return value / 100.0
    return value


def _calc_market_cap(price, shares) -> Optional[float]:
    px = _safe_float(price)
    qty = _safe_float(shares)
    if px is None or qty is None:
        return None
    return px * qty


def _pick_column(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _strip_market_prefix(code: str) -> str:
    text = str(code).strip().lower()
    if "." in text:
        text = text.split(".", 1)[1]
    return text.zfill(6)


def _to_baostock_code(code: str) -> str:
    raw = _strip_market_prefix(code)
    prefix = "sh" if raw.startswith(("5", "6", "9")) else "sz"
    if raw.startswith(("4", "8")):
        prefix = "bj"
    return f"{prefix}.{raw}"


def _is_a_share_code(code: str) -> bool:
    if not (code.isdigit() and len(code) == 6):
        return False
    return code.startswith(
        ("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "689", "4", "8")
    )


def _is_a_share_symbol(symbol: str, name: str) -> bool:
    text = str(symbol).strip().lower()
    stock_name = str(name).strip()
    if not text or not stock_name or "指数" in stock_name:
        return False
    if "." not in text:
        return _is_a_share_code(_strip_market_prefix(text))

    market, code = text.split(".", 1)
    code = code.zfill(6)
    if market == "sh":
        return code.startswith(("600", "601", "603", "605", "688", "689"))
    if market == "sz":
        return code.startswith(("000", "001", "002", "003", "300", "301"))
    if market == "bj":
        return code.startswith(("4", "8"))
    return False


def _map_adjustflag(adjust: str) -> str:
    if adjust == "hfq":
        return "1"
    if adjust == "qfq":
        return "2"
    return "3"


def _recent_quarters(today: date, count: int) -> Iterable[Tuple[int, int]]:
    quarter = ((today.month - 1) // 3) + 1
    year = today.year
    result = []
    for _ in range(count):
        result.append((year, quarter))
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    return result
