from __future__ import annotations

from datetime import date

import pandas as pd

from astock.models import Board


def _import_provider():
    from astock.datasource.baostock_provider import BaostockProvider

    return BaostockProvider


class FakeResultSet:
    def __init__(self, fields: list[str], rows: list[list[str]], error_code: str = "0") -> None:
        self.fields = fields
        self._rows = rows
        self._idx = -1
        self.error_code = error_code
        self.error_msg = "success" if error_code == "0" else "error"

    def next(self) -> bool:
        self._idx += 1
        return self._idx < len(self._rows)

    def get_row_data(self) -> list[str]:
        return self._rows[self._idx]


class FakeBaoStock:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def query_all_stock(self, day: str):
        self.calls.append(("query_all_stock", day))
        return FakeResultSet(
            ["code", "code_name"],
            [
                ["sh.000001", "上证综合指数"],
                ["sh.600519", "贵州茅台"],
                ["sz.000001", "平安银行"],
                ["sz.300750", "宁德时代"],
                ["sz.000002", "*ST 测试"],
            ],
        )

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str,
        end_date: str,
        frequency: str,
        adjustflag: str,
    ):
        self.calls.append(
            (
                "query_history_k_data_plus",
                code,
                fields,
                start_date,
                end_date,
                frequency,
                adjustflag,
            )
        )
        return FakeResultSet(
            fields.split(","),
            [
                [
                    "2026-04-24",
                    code,
                    "10.0",
                    "11.0",
                    "9.8",
                    "10.8",
                    "9.9",
                    "120000",
                    "1300000",
                    adjustflag,
                    "2.5",
                    "1",
                    "9.09",
                    "18.3",
                    "3.2",
                    "1.9",
                    "0",
                ],
                [
                    "2026-04-25",
                    code,
                    "10.8",
                    "11.2",
                    "10.5",
                    "11.0",
                    "10.8",
                    "140000",
                    "1500000",
                    adjustflag,
                    "2.7",
                    "1",
                    "1.85",
                    "18.8",
                    "3.3",
                    "2.0",
                    "0",
                ],
            ],
        )

    def query_profit_data(self, code: str, year: int, quarter: int):
        self.calls.append(("query_profit_data", code, year, quarter))
        return FakeResultSet(
            ["code", "pubDate", "statDate", "roeAvg", "netProfitRatio"],
            [[code, "2026-04-20", "2025-12-31", "12.5", "18.7"]],
        )

    def query_growth_data(self, code: str, year: int, quarter: int):
        self.calls.append(("query_growth_data", code, year, quarter))
        return FakeResultSet(
            ["code", "pubDate", "statDate", "YOYNI", "YOYEquity", "YOYAsset", "YOYOr"],
            [[code, "2026-04-20", "2025-12-31", "16.2", "8.1", "5.0", "11.4"]],
        )


def make_provider(fake_bs: FakeBaoStock):
    provider_cls = _import_provider()
    provider = provider_cls.__new__(provider_cls)
    provider.options = {}
    provider._bs = fake_bs
    provider._retry_times = 1
    provider._logged_in = True
    provider._call = lambda func, *args, **kwargs: func(*args, **kwargs)
    return provider


def test_list_stocks_uses_baostock_rows():
    provider = make_provider(FakeBaoStock())

    stocks = provider.list_stocks()

    assert provider._bs.calls == [("query_all_stock", date.today().strftime("%Y-%m-%d"))]
    assert [stock.code for stock in stocks] == ["600519", "000001", "300750", "000002"]
    assert [stock.name for stock in stocks] == ["贵州茅台", "平安银行", "宁德时代", "*ST 测试"]
    assert stocks[0].board == Board.MAIN_BOARD
    assert stocks[2].board == Board.CHINEXT
    assert stocks[3].is_st is True
    assert all("指数" not in stock.name for stock in stocks)


def test_get_kline_normalizes_daily_fields():
    provider = make_provider(FakeBaoStock())

    kline = provider.get_kline("600519", start=date(2026, 4, 24), end=date(2026, 4, 25))

    expected_fields = (
        "date,code,open,high,low,close,preclose,volume,amount,adjustflag,"
        "turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,isST"
    )
    assert provider._bs.calls == [
        (
            "query_history_k_data_plus",
            "sh.600519",
            expected_fields,
            "2026-04-24",
            "2026-04-25",
            "d",
            "2",
        )
    ]
    assert list(kline.df.columns) == [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "pct_change",
        "turnover_rate",
    ]
    assert isinstance(kline.df.index, pd.DatetimeIndex)
    assert float(kline.df.iloc[-1]["close"]) == 11.0
    assert float(kline.df.iloc[-1]["pct_change"]) == 1.85
    assert float(kline.df.iloc[-1]["turnover_rate"]) == 2.7


def test_get_financial_merges_latest_market_and_report_data():
    provider = make_provider(FakeBaoStock())

    financial = provider.get_financial("600519")

    assert provider._bs.calls[0][0] == "query_history_k_data_plus"
    assert provider._bs.calls[1][:2] == ("query_profit_data", "sh.600519")
    assert provider._bs.calls[2][:2] == ("query_growth_data", "sh.600519")
    assert financial.code == "600519"
    assert financial.report_date == "2025-12-31"
    assert financial.pe_ttm == 18.8
    assert financial.pb == 3.3
    assert financial.ps_ttm == 2.0
    assert financial.roe == 0.125
    assert financial.net_margin == 0.187
    assert financial.revenue_yoy == 0.114
    assert financial.net_profit_yoy == 0.162
    assert financial.total_market_cap is None
    assert financial.float_market_cap is None


def test_get_money_flow_gracefully_degrades_to_empty_list():
    provider = make_provider(FakeBaoStock())

    flows = provider.get_money_flow("600519", days=5)

    assert flows == []
