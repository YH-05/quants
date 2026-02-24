"""Tests for ca_strategy price_provider module.

PriceDataProvider is a Protocol for fetching daily close price data.
NullPriceDataProvider is a null implementation that returns empty dict.

Key behaviors:
- PriceDataProvider is a runtime_checkable Protocol
- NullPriceDataProvider satisfies the PriceDataProvider Protocol
- NullPriceDataProvider.fetch() always returns an empty dict
- Custom stub implementations satisfy the Protocol
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from dev.ca_strategy.price_provider import NullPriceDataProvider, PriceDataProvider


# =============================================================================
# PriceDataProvider Protocol
# =============================================================================
class TestPriceDataProviderProtocol:
    """PriceDataProvider Protocol tests."""

    def test_正常系_runtime_checkableである(self) -> None:
        """PriceDataProvider should be usable with isinstance checks."""
        assert isinstance(NullPriceDataProvider(), PriceDataProvider)

    def test_正常系_カスタムstub実装がProtocolを満たす(self) -> None:
        """A custom stub implementation should satisfy the Protocol."""

        class StubProvider:
            def fetch(
                self,
                tickers: list[str],
                start: date,
                end: date,
            ) -> dict[str, pd.Series]:
                return {
                    t: pd.Series([100.0], index=pd.DatetimeIndex([start]))
                    for t in tickers
                }

        stub = StubProvider()
        assert isinstance(stub, PriceDataProvider)

    def test_正常系_カスタムstub実装がデータを返す(self) -> None:
        """A custom stub implementation should return price data."""

        class StubProvider:
            def fetch(
                self,
                tickers: list[str],
                start: date,
                end: date,
            ) -> dict[str, pd.Series]:
                idx = pd.date_range(start, end, freq="B")
                return {t: pd.Series([100.0] * len(idx), index=idx) for t in tickers}

        stub = StubProvider()
        result = stub.fetch(
            tickers=["AAPL", "MSFT"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )
        assert set(result.keys()) == {"AAPL", "MSFT"}
        for series in result.values():
            assert isinstance(series, pd.Series)

    def test_異常系_fetchメソッドがないクラスはProtocolを満たさない(self) -> None:
        """A class without fetch method should not satisfy the Protocol."""

        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), PriceDataProvider)


# =============================================================================
# NullPriceDataProvider
# =============================================================================
class TestNullPriceDataProvider:
    """NullPriceDataProvider tests."""

    def test_正常系_空のdictを返す(self) -> None:
        """NullPriceDataProvider.fetch() should return an empty dict."""
        provider = NullPriceDataProvider()
        result = provider.fetch(
            tickers=["AAPL", "MSFT"],
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
        assert result == {}

    def test_正常系_空のtickerリストでも空dictを返す(self) -> None:
        """NullPriceDataProvider.fetch() with empty tickers returns empty dict."""
        provider = NullPriceDataProvider()
        result = provider.fetch(
            tickers=[],
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
        assert result == {}

    def test_正常系_PriceDataProviderProtocolを満たす(self) -> None:
        """NullPriceDataProvider should satisfy PriceDataProvider Protocol."""
        assert isinstance(NullPriceDataProvider(), PriceDataProvider)

    def test_正常系_返り値の型がdictである(self) -> None:
        """Return type should be dict[str, pd.Series]."""
        provider = NullPriceDataProvider()
        result = provider.fetch(
            tickers=["AAPL"],
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
        )
        assert isinstance(result, dict)
