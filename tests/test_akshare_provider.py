from __future__ import annotations

import pandas as pd

from astock.datasource.akshare_provider import AkshareProvider
from astock.models import Board


class FakeAkshare:
    def __init__(self) -> None:
        self.calls = []

    def stock_info_a_code_name(self):
        raise AssertionError("should not call stock_info_a_code_name")

    def stock_info_sh_name_code(self, symbol: str = "主板A股"):
        self.calls.append(("sh", symbol))
        return pd.DataFrame(
            [
                {"证券代码": "600519", "证券简称": "贵州茅台"},
                {"证券代码": "603288", "证券简称": "海天味业"},
            ]
        )

    def stock_info_sz_name_code(self, symbol: str = "A股列表"):
        self.calls.append(("sz", symbol))
        return pd.DataFrame(
            [
                {"A股代码": "1", "A股简称": "平安银行"},
                {"A股代码": "300750", "A股简称": "宁德时代"},
                {"A股代码": "2", "A股简称": "*ST 测试"},
            ]
        )


def make_provider(fake_ak: FakeAkshare) -> AkshareProvider:
    provider = AkshareProvider.__new__(AkshareProvider)
    provider.options = {}
    provider._ak = fake_ak
    provider._retry_times = 1
    provider._call = lambda func, *args, **kwargs: func(*args, **kwargs)
    return provider


def test_list_stocks_merges_sh_and_sz_sources():
    provider = make_provider(FakeAkshare())

    stocks = provider.list_stocks()

    assert provider._ak.calls == [("sh", "主板A股"), ("sz", "A股列表")]
    assert [stock.code for stock in stocks] == [
        "600519",
        "603288",
        "000001",
        "300750",
        "000002",
    ]
    assert [stock.name for stock in stocks] == [
        "贵州茅台",
        "海天味业",
        "平安银行",
        "宁德时代",
        "*ST 测试",
    ]
    assert stocks[0].board == Board.MAIN_BOARD
    assert stocks[2].board == Board.MAIN_BOARD
    assert stocks[3].board == Board.CHINEXT
    assert stocks[4].is_st is True
