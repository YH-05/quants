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

        assert callable(PolymarketClient)

    def test_正常系_PolymarketConfigがインポートできる(self) -> None:
        from market.polymarket import PolymarketConfig

        assert callable(PolymarketConfig)

    def test_正常系_RetryConfigがインポートできる(self) -> None:
        from market.polymarket import RetryConfig

        assert callable(RetryConfig)

    def test_正常系_FetchOptionsがインポートできる(self) -> None:
        from market.polymarket import FetchOptions

        assert callable(FetchOptions)

    def test_正常系_PriceIntervalがインポートできる(self) -> None:
        from market.polymarket import PriceInterval

        assert callable(PriceInterval)

    def test_正常系_PolymarketSessionがインポートできる(self) -> None:
        from market.polymarket import PolymarketSession

        assert callable(PolymarketSession)

    def test_正常系_レスポンスモデルがインポートできる(self) -> None:
        from market.polymarket import (
            OrderBook,
            OrderBookLevel,
            PolymarketEvent,
            PolymarketMarket,
            PricePoint,
            TradeRecord,
        )

        assert callable(OrderBook)
        assert callable(OrderBookLevel)
        assert callable(PolymarketEvent)
        assert callable(PolymarketMarket)
        assert callable(PricePoint)
        assert callable(TradeRecord)

    def test_正常系_エラークラスがインポートできる(self) -> None:
        from market.polymarket import (
            PolymarketAPIError,
            PolymarketError,
            PolymarketNotFoundError,
            PolymarketRateLimitError,
            PolymarketValidationError,
        )

        assert callable(PolymarketAPIError)
        assert callable(PolymarketError)
        assert callable(PolymarketNotFoundError)
        assert callable(PolymarketRateLimitError)
        assert callable(PolymarketValidationError)

    def test_正常系_PolymarketStorageがインポートできる(self) -> None:
        from market.polymarket import PolymarketStorage

        assert callable(PolymarketStorage)

    def test_正常系_get_polymarket_storageがインポートできる(self) -> None:
        from market.polymarket import get_polymarket_storage

        assert callable(get_polymarket_storage)

    def test_正常系_allが全公開APIを含む(self) -> None:
        import market.polymarket as pkg

        expected = {
            "CollectionResult",
            "FetchOptions",
            "OrderBook",
            "OrderBookLevel",
            "PolymarketAPIError",
            "PolymarketClient",
            "PolymarketCollector",
            "PolymarketConfig",
            "PolymarketError",
            "PolymarketEvent",
            "PolymarketMarket",
            "PolymarketNotFoundError",
            "PolymarketRateLimitError",
            "PolymarketSession",
            "PolymarketStorage",
            "PolymarketValidationError",
            "PriceInterval",
            "PricePoint",
            "RetryConfig",
            "TradeRecord",
            "get_polymarket_storage",
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

        assert callable(PolymarketClient)

    def test_正常系_marketからPolymarketConfigがインポートできる(self) -> None:
        from market import PolymarketConfig

        assert callable(PolymarketConfig)

    def test_正常系_marketからPolymarketEventがインポートできる(self) -> None:
        from market import PolymarketEvent

        assert callable(PolymarketEvent)

    def test_正常系_marketからPolymarketMarketがインポートできる(self) -> None:
        from market import PolymarketMarket

        assert callable(PolymarketMarket)

    def test_正常系_marketからPolymarketエラーがインポートできる(self) -> None:
        from market import (
            PolymarketAPIError,
            PolymarketError,
            PolymarketNotFoundError,
            PolymarketRateLimitError,
            PolymarketValidationError,
        )

        assert callable(PolymarketAPIError)
        assert callable(PolymarketError)
        assert callable(PolymarketNotFoundError)
        assert callable(PolymarketRateLimitError)
        assert callable(PolymarketValidationError)

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
