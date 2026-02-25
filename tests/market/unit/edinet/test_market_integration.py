"""Tests for EDINET integration into the market package.

Validates that:
- ErrorCode has EDINET_API_ERROR and EDINET_RATE_LIMIT members.
- DataSource has EDINET_DB member with value 'edinet_db'.
- EDINET classes are importable from the market namespace.
- EDINET errors are re-exported from market.errors.
- __all__ lists include EDINET symbols.

Related Issue: #3678
"""

from __future__ import annotations


class TestErrorCodeEdinetEntries:
    """Test that ErrorCode includes EDINET-specific error codes."""

    def test_正常系_ErrorCodeにEDINET_API_ERRORが存在(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "EDINET_API_ERROR")
        assert ErrorCode.EDINET_API_ERROR.value == "EDINET_API_ERROR"

    def test_正常系_ErrorCodeにEDINET_RATE_LIMITが存在(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "EDINET_RATE_LIMIT")
        assert ErrorCode.EDINET_RATE_LIMIT.value == "EDINET_RATE_LIMIT"


class TestDataSourceEdinetDb:
    """Test that DataSource.EDINET_DB is available in market.types."""

    def test_正常系_DataSourceにEDINET_DBが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "EDINET_DB")
        assert DataSource.EDINET_DB.value == "edinet_db"

    def test_正常系_DataSource_EDINET_DBがNASDAQの次に定義(self) -> None:
        from market.types import DataSource

        members = list(DataSource)
        nasdaq_idx = members.index(DataSource.NASDAQ)
        edinet_idx = members.index(DataSource.EDINET_DB)
        assert edinet_idx == nasdaq_idx + 1


class TestMarketErrorsEdinetReExport:
    """Test that EDINET errors are re-exported from market.errors."""

    def test_正常系_EdinetErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import EdinetError

        assert EdinetError is not None

    def test_正常系_EdinetAPIErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import EdinetAPIError

        assert EdinetAPIError is not None

    def test_正常系_EdinetRateLimitErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import EdinetRateLimitError

        assert EdinetRateLimitError is not None

    def test_正常系_EdinetValidationErrorがmarket_errorsからインポート可能(
        self,
    ) -> None:
        from market.errors import EdinetValidationError

        assert EdinetValidationError is not None

    def test_正常系_EdinetParseErrorがmarket_errorsからインポート可能(self) -> None:
        from market.errors import EdinetParseError

        assert EdinetParseError is not None

    def test_正常系_EdinetError群が__all__に含まれる(self) -> None:
        import market.errors as errors_mod

        edinet_errors = {
            "EdinetAPIError",
            "EdinetError",
            "EdinetParseError",
            "EdinetRateLimitError",
            "EdinetValidationError",
        }
        assert edinet_errors.issubset(set(errors_mod.__all__))


class TestMarketInitEdinetReExport:
    """Test that EDINET symbols are re-exported from market.__init__."""

    def test_正常系_EdinetClientがmarketからインポート可能(self) -> None:
        from market import EdinetClient

        assert EdinetClient is not None

    def test_正常系_EdinetStorageがmarketからインポート可能(self) -> None:
        from market import EdinetStorage

        assert EdinetStorage is not None

    def test_正常系_EdinetSyncerがmarketからインポート可能(self) -> None:
        from market import EdinetSyncer

        assert EdinetSyncer is not None

    def test_正常系_EdinetConfigがmarketからインポート可能(self) -> None:
        from market import EdinetConfig

        assert EdinetConfig is not None

    def test_正常系_DailyRateLimiterがmarketからインポート可能(self) -> None:
        from market import DailyRateLimiter

        assert DailyRateLimiter is not None

    def test_正常系_EdinetErrorがmarketからインポート可能(self) -> None:
        from market import EdinetError

        assert EdinetError is not None

    def test_正常系_EdinetAPIErrorがmarketからインポート可能(self) -> None:
        from market import EdinetAPIError

        assert EdinetAPIError is not None

    def test_正常系_EdinetRateLimitErrorがmarketからインポート可能(self) -> None:
        from market import EdinetRateLimitError

        assert EdinetRateLimitError is not None

    def test_正常系_EdinetValidationErrorがmarketからインポート可能(self) -> None:
        from market import EdinetValidationError

        assert EdinetValidationError is not None

    def test_正常系_EdinetParseErrorがmarketからインポート可能(self) -> None:
        from market import EdinetParseError

        assert EdinetParseError is not None

    def test_正常系_EDINET関連シンボルがmarket___all__に含まれる(self) -> None:
        import market as market_mod

        edinet_symbols = {
            "DailyRateLimiter",
            "EdinetAPIError",
            "EdinetClient",
            "EdinetConfig",
            "EdinetError",
            "EdinetParseError",
            "EdinetRateLimitError",
            "EdinetStorage",
            "EdinetSyncer",
            "EdinetValidationError",
        }
        assert edinet_symbols.issubset(set(market_mod.__all__))

    def test_正常系_既存インポートが壊れていない(self) -> None:
        """Verify that existing imports still work after EDINET integration."""
        from market import (
            DataExporter,
            DataSource,
            ErrorCode,
            ExportError,
            MarketDataResult,
            ScreenerCollector,
            ScreenerFilter,
        )

        assert DataExporter is not None
        assert DataSource is not None
        assert ErrorCode is not None
        assert ExportError is not None
        assert MarketDataResult is not None
        assert ScreenerCollector is not None
        assert ScreenerFilter is not None
