"""Unit tests for market.polymarket package integration (__init__.py).

Tests that all public API exports are accessible from the package
and that existing market-level exports include Polymarket entries.

Acceptance Criteria (Issue #3816)
---------------------------------
- ``from market.polymarket import PolymarketClient, PolymarketConfig`` works.
- ``DataSource.POLYMARKET`` exists and equals ``'polymarket'``.
- ``ErrorCode`` has 4 ``POLYMARKET_*`` entries.
- ``from market import PolymarketClient`` works.
"""

from __future__ import annotations


class TestPolymarketPackageExports:
    """Test that market.polymarket __init__.py exports all public API."""

    def test_正常系_PolymarketClientがインポートできる(self) -> None:
        from market.polymarket import PolymarketClient

        assert PolymarketClient is not None

    def test_正常系_PolymarketConfigがインポートできる(self) -> None:
        from market.polymarket import PolymarketConfig

        assert PolymarketConfig is not None

    def test_正常系_RetryConfigがインポートできる(self) -> None:
        from market.polymarket import RetryConfig

        assert RetryConfig is not None

    def test_正常系_FetchOptionsがインポートできる(self) -> None:
        from market.polymarket import FetchOptions

        assert FetchOptions is not None

    def test_正常系_PriceIntervalがインポートできる(self) -> None:
        from market.polymarket import PriceInterval

        assert PriceInterval is not None

    def test_正常系_PolymarketSessionがインポートできる(self) -> None:
        from market.polymarket import PolymarketSession

        assert PolymarketSession is not None

    def test_正常系_レスポンスモデルがインポートできる(self) -> None:
        from market.polymarket import (
            OrderBook,
            OrderBookLevel,
            PolymarketEvent,
            PolymarketMarket,
            PricePoint,
            TradeRecord,
        )

        assert OrderBook is not None
        assert OrderBookLevel is not None
        assert PolymarketEvent is not None
        assert PolymarketMarket is not None
        assert PricePoint is not None
        assert TradeRecord is not None

    def test_正常系_エラークラスがインポートできる(self) -> None:
        from market.polymarket import (
            PolymarketAPIError,
            PolymarketError,
            PolymarketNotFoundError,
            PolymarketRateLimitError,
            PolymarketValidationError,
        )

        assert PolymarketAPIError is not None
        assert PolymarketError is not None
        assert PolymarketNotFoundError is not None
        assert PolymarketRateLimitError is not None
        assert PolymarketValidationError is not None

    def test_正常系_allが全公開APIを含む(self) -> None:
        import market.polymarket as pkg

        expected = {
            "FetchOptions",
            "OrderBook",
            "OrderBookLevel",
            "PolymarketAPIError",
            "PolymarketClient",
            "PolymarketConfig",
            "PolymarketError",
            "PolymarketEvent",
            "PolymarketMarket",
            "PolymarketNotFoundError",
            "PolymarketRateLimitError",
            "PolymarketSession",
            "PolymarketValidationError",
            "PriceInterval",
            "PricePoint",
            "RetryConfig",
            "TradeRecord",
        }
        assert set(pkg.__all__) == expected


class TestDataSourcePolymarket:
    """Test that DataSource enum includes POLYMARKET."""

    def test_正常系_DataSourceにPOLYMARKETが存在する(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "POLYMARKET")

    def test_正常系_POLYMARKET値がpolymarket文字列(self) -> None:
        from market.types import DataSource

        assert DataSource.POLYMARKET == "polymarket"
        assert DataSource.POLYMARKET.value == "polymarket"


class TestErrorCodePolymarket:
    """Test that ErrorCode enum includes 4 POLYMARKET_* entries."""

    def test_正常系_POLYMARKET_API_ERRORが存在する(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "POLYMARKET_API_ERROR")
        assert ErrorCode.POLYMARKET_API_ERROR.value == "POLYMARKET_API_ERROR"

    def test_正常系_POLYMARKET_RATE_LIMITが存在する(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "POLYMARKET_RATE_LIMIT")
        assert ErrorCode.POLYMARKET_RATE_LIMIT.value == "POLYMARKET_RATE_LIMIT"

    def test_正常系_POLYMARKET_VALIDATION_ERRORが存在する(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "POLYMARKET_VALIDATION_ERROR")
        assert (
            ErrorCode.POLYMARKET_VALIDATION_ERROR.value == "POLYMARKET_VALIDATION_ERROR"
        )

    def test_正常系_POLYMARKET_NOT_FOUNDが存在する(self) -> None:
        from market.errors import ErrorCode

        assert hasattr(ErrorCode, "POLYMARKET_NOT_FOUND")
        assert ErrorCode.POLYMARKET_NOT_FOUND.value == "POLYMARKET_NOT_FOUND"

    def test_正常系_POLYMARKET系が4エントリある(self) -> None:
        from market.errors import ErrorCode

        polymarket_codes = [
            member for member in ErrorCode if member.name.startswith("POLYMARKET_")
        ]
        assert len(polymarket_codes) == 4


class TestMarketPackagePolymarketExports:
    """Test that market top-level __init__.py re-exports Polymarket."""

    def test_正常系_marketからPolymarketClientがインポートできる(self) -> None:
        from market import PolymarketClient

        assert PolymarketClient is not None

    def test_正常系_marketからPolymarketConfigがインポートできる(self) -> None:
        from market import PolymarketConfig

        assert PolymarketConfig is not None

    def test_正常系_marketからPolymarketEventがインポートできる(self) -> None:
        from market import PolymarketEvent

        assert PolymarketEvent is not None

    def test_正常系_marketからPolymarketMarketがインポートできる(self) -> None:
        from market import PolymarketMarket

        assert PolymarketMarket is not None

    def test_正常系_marketからPolymarketエラーがインポートできる(self) -> None:
        from market import (
            PolymarketAPIError,
            PolymarketError,
            PolymarketNotFoundError,
            PolymarketRateLimitError,
            PolymarketValidationError,
        )

        assert PolymarketAPIError is not None
        assert PolymarketError is not None
        assert PolymarketNotFoundError is not None
        assert PolymarketRateLimitError is not None
        assert PolymarketValidationError is not None

    def test_正常系_market_allにPolymarketエントリが含まれる(self) -> None:
        import market

        polymarket_exports = {
            "PolymarketAPIError",
            "PolymarketClient",
            "PolymarketConfig",
            "PolymarketError",
            "PolymarketEvent",
            "PolymarketMarket",
            "PolymarketNotFoundError",
            "PolymarketRateLimitError",
            "PolymarketValidationError",
        }
        missing = polymarket_exports - set(market.__all__)
        assert not missing, f"Missing from market.__all__: {missing}"

    def test_正常系_marketからPolymarketエラーのreexportが同一オブジェクト(
        self,
    ) -> None:
        """Verify that market-level re-exports are the same objects."""
        from market import PolymarketError as MarketPolymarketError
        from market.polymarket.errors import (
            PolymarketError as OriginalPolymarketError,
        )

        assert MarketPolymarketError is OriginalPolymarketError
