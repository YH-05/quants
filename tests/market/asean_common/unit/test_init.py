"""Tests for market.asean_common.__init__.py public API exports.

Validates that:
- All asean_common public API symbols are importable from ``market.asean_common``.
- AseanMarket, TickerRecord, AseanTickerStorage and other key types are accessible.
- Error classes and screener functions are re-exported.
- __all__ is complete and consistent.

Test TODO List:
- [x] asean_common public API importability
- [x] __all__ completeness
- [x] Key types (AseanMarket, TickerRecord) importable
- [x] Storage class (AseanTickerStorage) importable
- [x] Error classes importable
- [x] Screener functions importable
- [x] Constants importable
"""

from __future__ import annotations


class TestAseanCommonPackageExports:
    """Test that market.asean_common re-exports all public API symbols."""

    def test_正常系_AseanMarketがインポート可能(self) -> None:
        from market.asean_common import AseanMarket

        assert AseanMarket is not None

    def test_正常系_TickerRecordがインポート可能(self) -> None:
        from market.asean_common import TickerRecord

        assert TickerRecord is not None

    def test_正常系_AseanTickerStorageがインポート可能(self) -> None:
        from market.asean_common import AseanTickerStorage

        assert AseanTickerStorage is not None

    def test_正常系_AseanErrorがインポート可能(self) -> None:
        from market.asean_common import AseanError

        assert AseanError is not None

    def test_正常系_AseanStorageErrorがインポート可能(self) -> None:
        from market.asean_common import AseanStorageError

        assert AseanStorageError is not None

    def test_正常系_AseanScreenerErrorがインポート可能(self) -> None:
        from market.asean_common import AseanScreenerError

        assert AseanScreenerError is not None

    def test_正常系_AseanLookupErrorがインポート可能(self) -> None:
        from market.asean_common import AseanLookupError

        assert AseanLookupError is not None

    def test_正常系_fetch_tickers_from_screenerがインポート可能(self) -> None:
        from market.asean_common import fetch_tickers_from_screener

        assert fetch_tickers_from_screener is not None

    def test_正常系_fetch_all_asean_tickersがインポート可能(self) -> None:
        from market.asean_common import fetch_all_asean_tickers

        assert fetch_all_asean_tickers is not None

    def test_正常系_YFINANCE_SUFFIX_MAPがインポート可能(self) -> None:
        from market.asean_common import YFINANCE_SUFFIX_MAP

        assert YFINANCE_SUFFIX_MAP is not None

    def test_正常系_SCREENER_EXCHANGE_MAPがインポート可能(self) -> None:
        from market.asean_common import SCREENER_EXCHANGE_MAP

        assert SCREENER_EXCHANGE_MAP is not None

    def test_正常系_SCREENER_MARKET_MAPがインポート可能(self) -> None:
        from market.asean_common import SCREENER_MARKET_MAP

        assert SCREENER_MARKET_MAP is not None

    def test_正常系_TABLE_TICKERSがインポート可能(self) -> None:
        from market.asean_common import TABLE_TICKERS

        assert TABLE_TICKERS is not None

    def test_正常系_DB_PATHがインポート可能(self) -> None:
        from market.asean_common import DB_PATH

        assert DB_PATH is not None

    def test_正常系___all__が定義されている(self) -> None:
        import market.asean_common as asean_mod

        assert hasattr(asean_mod, "__all__")
        assert isinstance(asean_mod.__all__, list)
        assert len(asean_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.asean_common as asean_mod

        for name in asean_mod.__all__:
            assert hasattr(asean_mod, name), (
                f"{name} is in __all__ but not importable from market.asean_common"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.asean_common as asean_mod

        expected = {
            # Constants
            "AseanMarket",
            "YFINANCE_SUFFIX_MAP",
            "SCREENER_EXCHANGE_MAP",
            "SCREENER_MARKET_MAP",
            "TABLE_TICKERS",
            "DB_PATH",
            # Types
            "TickerRecord",
            # Storage
            "AseanTickerStorage",
            # Errors
            "AseanError",
            "AseanStorageError",
            "AseanScreenerError",
            "AseanLookupError",
            # Screener functions
            "fetch_tickers_from_screener",
            "fetch_all_asean_tickers",
        }
        assert expected.issubset(set(asean_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(asean_mod.__all__)}"
        )

    def test_正常系_再エクスポートされた型が元モジュールと同一(self) -> None:
        """Re-exported symbols are the same objects as in their source modules."""
        from market.asean_common import AseanMarket as ReExported
        from market.asean_common.constants import AseanMarket as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたTickerRecordが元モジュールと同一(self) -> None:
        from market.asean_common import TickerRecord as ReExported
        from market.asean_common.types import TickerRecord as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたAseanTickerStorageが元モジュールと同一(
        self,
    ) -> None:
        from market.asean_common import AseanTickerStorage as ReExported
        from market.asean_common.storage import AseanTickerStorage as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.asean_common as asean_mod

        assert asean_mod.__doc__ is not None
        assert len(asean_mod.__doc__) > 0


class TestDataSourceAseanMembers:
    """Test that DataSource enum has ASEAN-related members."""

    def test_正常系_DataSourceにTRADINGVIEW_SCREENERが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "TRADINGVIEW_SCREENER")
        assert DataSource.TRADINGVIEW_SCREENER.value == "tradingview_screener"

    def test_正常系_DataSourceにVNSTOCKが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "VNSTOCK")
        assert DataSource.VNSTOCK.value == "vnstock"

    def test_正常系_DataSourceにIDX_BEIが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "IDX_BEI")
        assert DataSource.IDX_BEI.value == "idx_bei"

    def test_正常系_DataSourceにTHAIFINが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "THAIFIN")
        assert DataSource.THAIFIN.value == "thaifin"

    def test_正常系_DataSourceにPSE_APIが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "PSE_API")
        assert DataSource.PSE_API.value == "pse_api"

    def test_正常系_DataSourceにEODHDが存在(self) -> None:
        from market.types import DataSource

        assert hasattr(DataSource, "EODHD")
        assert DataSource.EODHD.value == "eodhd"

    def test_正常系_ASEAN関連DataSourceの値が全てstr型(self) -> None:
        from market.types import DataSource

        asean_sources = [
            DataSource.TRADINGVIEW_SCREENER,
            DataSource.VNSTOCK,
            DataSource.IDX_BEI,
            DataSource.THAIFIN,
            DataSource.PSE_API,
            DataSource.EODHD,
        ]
        for source in asean_sources:
            assert isinstance(source.value, str), (
                f"{source.name} value is not str: {type(source.value)}"
            )

    def test_正常系_既存DataSourceメンバーが変更されていない(self) -> None:
        """Existing DataSource members must not be altered."""
        from market.types import DataSource

        assert DataSource.YFINANCE.value == "yfinance"
        assert DataSource.FRED.value == "fred"
        assert DataSource.LOCAL.value == "local"
        assert DataSource.BLOOMBERG.value == "bloomberg"
        assert DataSource.FACTSET.value == "factset"
        assert DataSource.ETF_COM.value == "etfcom"
        assert DataSource.NASDAQ.value == "nasdaq"
        assert DataSource.EDINET_DB.value == "edinet_db"
        assert DataSource.BSE.value == "bse"
        assert DataSource.JQUANTS.value == "jquants"
        assert DataSource.EDINET_API.value == "edinet_api"
