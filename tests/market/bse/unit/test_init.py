"""Tests for market.bse.__init__.py and market package BSE integration.

Validates that:
- All BSE public API symbols are importable from ``market.bse``.
- ``DataSource.BSE`` is defined with value ``'bse'``.
- BSE error codes exist in ``ErrorCode``.
- BSE errors are re-exported from ``market.errors``.
- BSE symbols are re-exported from ``market.__init__``.
"""

from __future__ import annotations


class TestBsePackageReExports:
    """Test that market.bse re-exports all public API symbols."""

    def test_正常系_QuoteCollectorがインポート可能(self) -> None:
        from market.bse import QuoteCollector

        assert QuoteCollector is not None

    def test_正常系_BseSessionがインポート可能(self) -> None:
        from market.bse import BseSession

        assert BseSession is not None

    def test_正常系_BhavcopyCollectorがインポート可能(self) -> None:
        from market.bse import BhavcopyCollector

        assert BhavcopyCollector is not None

    def test_正常系_IndexCollectorがインポート可能(self) -> None:
        from market.bse import IndexCollector

        assert IndexCollector is not None

    def test_正常系_CorporateCollectorがインポート可能(self) -> None:
        from market.bse import CorporateCollector

        assert CorporateCollector is not None

    def test_正常系_BseConfigがインポート可能(self) -> None:
        from market.bse import BseConfig

        assert BseConfig is not None

    def test_正常系_RetryConfigがインポート可能(self) -> None:
        from market.bse import RetryConfig

        assert RetryConfig is not None

    def test_正常系_全Enumがインポート可能(self) -> None:
        from market.bse import BhavcopyType, IndexName, ScripGroup

        assert BhavcopyType is not None
        assert ScripGroup is not None
        assert IndexName is not None

    def test_正常系_BseError群がインポート可能(self) -> None:
        from market.bse import (
            BseAPIError,
            BseError,
            BseParseError,
            BseRateLimitError,
            BseValidationError,
        )

        assert BseError is not None
        assert BseAPIError is not None
        assert BseRateLimitError is not None
        assert BseParseError is not None
        assert BseValidationError is not None

    def test_正常系_データ型がインポート可能(self) -> None:
        from market.bse import (
            Announcement,
            CorporateAction,
            FinancialResult,
            ScripQuote,
        )

        assert ScripQuote is not None
        assert FinancialResult is not None
        assert Announcement is not None
        assert CorporateAction is not None

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.bse as bse_mod

        for name in bse_mod.__all__:
            assert hasattr(bse_mod, name), (
                f"{name} is in __all__ but not importable from market.bse"
            )


class TestDataSourceBse:
    """Test that DataSource.BSE is available in market.types."""

    def test_正常系_DataSourceにBSEが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "BSE")
        assert DataSource.BSE.value == "bse"


class TestMarketErrorsBseReExport:
    """Test that BSE errors are re-exported from market.errors."""

    def test_正常系_BseErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import BseError

        assert BseError is not None

    def test_正常系_BseAPIErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import BseAPIError

        assert BseAPIError is not None

    def test_正常系_BseRateLimitErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import BseRateLimitError

        assert BseRateLimitError is not None

    def test_正常系_BseParseErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import BseParseError

        assert BseParseError is not None

    def test_正常系_BseValidationErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import BseValidationError

        assert BseValidationError is not None

    def test_正常系_ErrorCodeにBSE関連コードが存在(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "BSE_API_ERROR")
        assert hasattr(ErrorCode, "BSE_RATE_LIMIT")
        assert hasattr(ErrorCode, "BSE_PARSE_ERROR")
        assert hasattr(ErrorCode, "BSE_VALIDATION_ERROR")

    def test_正常系_BseError群が__all__に含まれる(self) -> None:
        import market.errors as errors_mod

        bse_errors = {
            "BseAPIError",
            "BseError",
            "BseParseError",
            "BseRateLimitError",
            "BseValidationError",
        }
        assert bse_errors.issubset(set(errors_mod.__all__))


class TestMarketInitBseReExport:
    """Test that BSE symbols are re-exported from market.__init__."""

    def test_正常系_QuoteCollectorがmarketからインポート可能(self) -> None:
        from market import QuoteCollector

        assert QuoteCollector is not None

    def test_正常系_BseSessionがmarketからインポート可能(self) -> None:
        from market import BseSession

        assert BseSession is not None

    def test_正常系_BseErrorがmarketからインポート可能(self) -> None:
        from market import BseError

        assert BseError is not None

    def test_正常系_BseAPIErrorがmarketからインポート可能(self) -> None:
        from market import BseAPIError

        assert BseAPIError is not None

    def test_正常系_BseRateLimitErrorがmarketからインポート可能(self) -> None:
        from market import BseRateLimitError

        assert BseRateLimitError is not None

    def test_正常系_BseParseErrorがmarketからインポート可能(self) -> None:
        from market import BseParseError

        assert BseParseError is not None

    def test_正常系_BseValidationErrorがmarketからインポート可能(self) -> None:
        from market import BseValidationError

        assert BseValidationError is not None

    def test_正常系_BSE関連シンボルがmarket___all__に含まれる(self) -> None:
        import market as market_mod

        bse_symbols = {
            "BseAPIError",
            "BseError",
            "BseParseError",
            "BseRateLimitError",
            "BseSession",
            "BseValidationError",
            "QuoteCollector",
        }
        assert bse_symbols.issubset(set(market_mod.__all__))
