"""Unit tests for market.bloomberg module initialization.

TDD Red Phase: These tests are designed to fail initially.
The implementation (market.bloomberg) does not exist yet.

Test TODO List:
- [x] market.bloomberg module can be imported
- [x] All public classes are exported
- [x] All public functions are exported
- [x] __all__ is properly defined
- [x] ChunkConfig, EarningsInfo, IdentifierConversionResult are exported
"""


class TestModuleImport:
    """Tests for market.bloomberg module import."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """market.bloomberg モジュールがインポートできることを確認。"""
        import market.bloomberg

        assert market.bloomberg is not None

    def test_正常系_サブモジュールがインポートできる(self) -> None:
        """サブモジュールが正しくインポートできることを確認。"""
        from market.bloomberg import fetcher, types

        assert types is not None
        assert fetcher is not None

        # errors は market.errors に定義されている（market.bloomberg.errors は存在しない）
        import market.errors

        assert market.errors is not None


class TestPublicExports:
    """Tests for public API exports."""

    def test_正常系_BloombergFetcherがエクスポートされている(self) -> None:
        """BloombergFetcher がトップレベルでエクスポートされていることを確認。"""
        from market.bloomberg import BloombergFetcher

        assert BloombergFetcher is not None

    def test_正常系_型定義がエクスポートされている(self) -> None:
        """型定義がトップレベルでエクスポートされていることを確認。"""
        from market.bloomberg import (
            BloombergDataResult,
            BloombergFetchOptions,
            DataSource,
            FieldInfo,
            IDType,
            NewsStory,
            OverrideOption,
            Periodicity,
        )

        assert IDType is not None
        assert Periodicity is not None
        assert DataSource is not None
        assert BloombergFetchOptions is not None
        assert BloombergDataResult is not None
        assert OverrideOption is not None
        assert NewsStory is not None
        assert FieldInfo is not None

    def test_正常系_新規型定義がエクスポートされている(self) -> None:
        """新規追加の型定義がトップレベルでエクスポートされていることを確認。"""
        from market.bloomberg import (
            ChunkConfig,
            EarningsInfo,
            IdentifierConversionResult,
        )

        assert ChunkConfig is not None
        assert EarningsInfo is not None
        assert IdentifierConversionResult is not None

    def test_正常系_エラークラスがエクスポートされている(self) -> None:
        """エラークラスがトップレベルでエクスポートされていることを確認。"""
        from market.bloomberg import (
            BloombergConnectionError,
            BloombergDataError,
            BloombergError,
            BloombergSessionError,
            BloombergValidationError,
            ErrorCode,
        )

        assert BloombergError is not None
        assert BloombergConnectionError is not None
        assert BloombergSessionError is not None
        assert BloombergDataError is not None
        assert BloombergValidationError is not None
        assert ErrorCode is not None


class TestAllDefinition:
    """Tests for __all__ definition."""

    def test_正常系___all__が定義されている(self) -> None:
        """__all__ が定義されていることを確認。"""
        import market.bloomberg

        assert hasattr(market.bloomberg, "__all__")
        assert isinstance(market.bloomberg.__all__, list)

    def test_正常系___all__に主要クラスが含まれている(self) -> None:
        """__all__ に主要クラスが含まれていることを確認。"""
        import market.bloomberg

        expected_exports = [
            "BloombergFetcher",
            "BloombergFetchOptions",
            "BloombergDataResult",
            "IDType",
            "Periodicity",
            "BloombergError",
            "BloombergConnectionError",
            "BloombergSessionError",
            "BloombergDataError",
            "BloombergValidationError",
            "ChunkConfig",
            "EarningsInfo",
            "IdentifierConversionResult",
        ]

        for export in expected_exports:
            assert export in market.bloomberg.__all__, f"{export} not in __all__"


class TestTypeConsistency:
    """Tests for type consistency with market package."""

    def test_正常系_DataSourceがmarket_typesと一致(self) -> None:
        """Bloomberg DataSource が market.types の DataSource と互換性があることを確認。"""
        from market.bloomberg.types import DataSource as BloombergDataSource
        from market.types import DataSource as MarketDataSource

        # Bloomberg should be a valid value in both
        assert BloombergDataSource.BLOOMBERG.value == "bloomberg"
        assert MarketDataSource.BLOOMBERG.value == "bloomberg"

    def test_正常系_エラー階層がExceptionを継承(self) -> None:
        """全てのエラークラスが Exception を継承していることを確認。"""
        from market.bloomberg import (
            BloombergConnectionError,
            BloombergDataError,
            BloombergError,
            BloombergSessionError,
            BloombergValidationError,
        )

        assert issubclass(BloombergError, Exception)
        assert issubclass(BloombergConnectionError, BloombergError)
        assert issubclass(BloombergSessionError, BloombergError)
        assert issubclass(BloombergDataError, BloombergError)
        assert issubclass(BloombergValidationError, BloombergError)
