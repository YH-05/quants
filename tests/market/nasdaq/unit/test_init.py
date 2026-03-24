"""Tests for market.nasdaq.__init__.py public API re-exports.

Validates that all public symbols declared in Issue #3414 are importable
from the ``market.nasdaq`` namespace and that the ``__all__`` list is
consistent with the actual module exports.
"""

from __future__ import annotations


class TestNasdaqPackageReExports:
    """Test that market.nasdaq re-exports all public API symbols."""

    def test_正常系_ScreenerCollectorがインポート可能(self) -> None:
        from market.nasdaq import ScreenerCollector

        assert ScreenerCollector is not None

    def test_正常系_NasdaqSessionがインポート可能(self) -> None:
        from market.nasdaq import NasdaqSession

        assert NasdaqSession is not None

    def test_正常系_ScreenerFilterがインポート可能(self) -> None:
        from market.nasdaq import ScreenerFilter

        assert ScreenerFilter is not None

    def test_正常系_NasdaqConfigがインポート可能(self) -> None:
        from market.nasdaq import NasdaqConfig

        assert NasdaqConfig is not None

    def test_正常系_RetryConfigがインポート可能(self) -> None:
        from market.nasdaq import RetryConfig

        assert RetryConfig is not None

    def test_正常系_全Enumがインポート可能(self) -> None:
        from market.nasdaq import (
            Country,
            Exchange,
            MarketCap,
            Recommendation,
            Region,
            Sector,
        )

        assert Exchange is not None
        assert MarketCap is not None
        assert Sector is not None
        assert Recommendation is not None
        assert Region is not None
        assert Country is not None

    def test_正常系_NasdaqError群がインポート可能(self) -> None:
        from market.nasdaq import (
            NasdaqAPIError,
            NasdaqError,
            NasdaqParseError,
            NasdaqRateLimitError,
        )

        assert NasdaqError is not None
        assert NasdaqAPIError is not None
        assert NasdaqRateLimitError is not None
        assert NasdaqParseError is not None

    def test_正常系_StockRecordがインポート可能(self) -> None:
        from market.nasdaq import StockRecord

        assert StockRecord is not None

    def test_正常系___all__が全公開シンボルを含む(self) -> None:
        import market.nasdaq as nasdaq_mod

        expected_symbols = {
            # Client
            "NasdaqClient",
            # Client Types (18 types)
            "AnalystRatings",
            "AnalystSummary",
            "DividendCalendarRecord",
            "DividendRecord",
            "EarningsDate",
            "EarningsForecast",
            "EarningsForecastPeriod",
            "EarningsRecord",
            "EtfRecord",
            "FinancialStatement",
            "FinancialStatementRow",
            "InsiderTrade",
            "InstitutionalHolding",
            "IpoRecord",
            "MarketMover",
            "MoverSection",
            "NasdaqFetchOptions",
            "RatingCount",
            "ShortInterestRecord",
            "SplitRecord",
            "TargetPrice",
            # Client Cache
            "get_nasdaq_cache",
            # Screener
            "Country",
            "Exchange",
            "FilterCategory",
            "MarketCap",
            "NasdaqAPIError",
            "NasdaqConfig",
            "NasdaqError",
            "NasdaqParseError",
            "NasdaqRateLimitError",
            "NasdaqSession",
            "Recommendation",
            "Region",
            "RetryConfig",
            "ScreenerCollector",
            "ScreenerFilter",
            "Sector",
            "StockRecord",
        }
        assert set(nasdaq_mod.__all__) == expected_symbols

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.nasdaq as nasdaq_mod

        for name in nasdaq_mod.__all__:
            assert hasattr(nasdaq_mod, name), (
                f"{name} is in __all__ but not importable from market.nasdaq"
            )


class TestDataSourceNasdaq:
    """Test that DataSource.NASDAQ is available in market.types."""

    def test_正常系_DataSourceにNASDAQが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "NASDAQ")
        assert DataSource.NASDAQ.value == "nasdaq"

    def test_正常系_DataSource_NASDAQがETF_COMの次に定義(self) -> None:
        from market.types import DataSource

        members = list(DataSource)
        etfcom_idx = members.index(DataSource.ETF_COM)
        nasdaq_idx = members.index(DataSource.NASDAQ)
        assert nasdaq_idx == etfcom_idx + 1


class TestMarketErrorsNasdaqReExport:
    """Test that NASDAQ errors are re-exported from market.errors."""

    def test_正常系_NasdaqErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import NasdaqError

        assert NasdaqError is not None

    def test_正常系_NasdaqAPIErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import NasdaqAPIError

        assert NasdaqAPIError is not None

    def test_正常系_NasdaqRateLimitErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import NasdaqRateLimitError

        assert NasdaqRateLimitError is not None

    def test_正常系_NasdaqParseErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import NasdaqParseError

        assert NasdaqParseError is not None

    def test_正常系_ErrorCodeにNASDAQ関連コードが存在(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "NASDAQ_API_ERROR")
        assert hasattr(ErrorCode, "NASDAQ_RATE_LIMIT")
        assert hasattr(ErrorCode, "NASDAQ_PARSE_ERROR")

    def test_正常系_NasdaqError群が__all__に含まれる(self) -> None:
        import market.errors as errors_mod

        nasdaq_errors = {
            "NasdaqAPIError",
            "NasdaqError",
            "NasdaqParseError",
            "NasdaqRateLimitError",
        }
        assert nasdaq_errors.issubset(set(errors_mod.__all__))


class TestMarketInitNasdaqReExport:
    """Test that NASDAQ symbols are re-exported from market.__init__."""

    def test_正常系_ScreenerCollectorがmarketからインポート可能(self) -> None:
        from market import ScreenerCollector

        assert ScreenerCollector is not None

    def test_正常系_ScreenerFilterがmarketからインポート可能(self) -> None:
        from market import ScreenerFilter

        assert ScreenerFilter is not None

    def test_正常系_NasdaqErrorがmarketからインポート可能(self) -> None:
        from market import NasdaqError

        assert NasdaqError is not None

    def test_正常系_NasdaqAPIErrorがmarketからインポート可能(self) -> None:
        from market import NasdaqAPIError

        assert NasdaqAPIError is not None

    def test_正常系_NasdaqRateLimitErrorがmarketからインポート可能(self) -> None:
        from market import NasdaqRateLimitError

        assert NasdaqRateLimitError is not None

    def test_正常系_NasdaqParseErrorがmarketからインポート可能(self) -> None:
        from market import NasdaqParseError

        assert NasdaqParseError is not None

    def test_正常系_NASDAQ関連シンボルがmarket___all__に含まれる(self) -> None:
        import market as market_mod

        nasdaq_symbols = {
            "NasdaqAPIError",
            "NasdaqError",
            "NasdaqParseError",
            "NasdaqRateLimitError",
            "ScreenerCollector",
            "ScreenerFilter",
        }
        assert nasdaq_symbols.issubset(set(market_mod.__all__))
