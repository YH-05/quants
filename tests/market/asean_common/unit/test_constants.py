"""Tests for market.asean_common.constants module.

Tests verify all constant definitions for the ASEAN common module,
including AseanMarket enum, yfinance suffix mapping, screener exchange
mapping, screener market mapping, table name, DB path, and module exports.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] AseanMarket Enum: 6 members, str inheritance, values
- [x] YFINANCE_SUFFIX_MAP: all 6 markets mapped to correct suffixes
- [x] SCREENER_EXCHANGE_MAP: all 6 markets mapped to screener names
- [x] SCREENER_MARKET_MAP: all 6 markets mapped to screener market names
- [x] TABLE_TICKERS: non-empty string
- [x] DB_PATH: non-empty string with correct format
- [x] Final annotations: all non-enum constants annotated with typing.Final
"""

from typing import get_type_hints

from market.asean_common.constants import (
    DB_PATH,
    SCREENER_EXCHANGE_MAP,
    SCREENER_MARKET_MAP,
    TABLE_TICKERS,
    YFINANCE_SUFFIX_MAP,
    AseanMarket,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """constants モジュールが正常にインポートできること。"""
        from market.asean_common import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.asean_common import constants

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_allが6項目を含む(self) -> None:
        """__all__ が全6定数をエクスポートしていること。"""
        expected = {
            "AseanMarket",
            "DB_PATH",
            "SCREENER_EXCHANGE_MAP",
            "SCREENER_MARKET_MAP",
            "TABLE_TICKERS",
            "YFINANCE_SUFFIX_MAP",
        }
        assert set(__all__) == expected

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.asean_common import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


# =============================================================================
# AseanMarket Enum
# =============================================================================


class TestAseanMarketEnum:
    """Test AseanMarket Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """AseanMarket が str と Enum を継承していること。"""
        from enum import Enum

        assert issubclass(AseanMarket, str)
        assert issubclass(AseanMarket, Enum)

    def test_正常系_6つのメンバーを持つ(self) -> None:
        """AseanMarket が SGX, BURSA, SET, IDX, HOSE, PSE の6メンバーを持つこと。"""
        assert len(AseanMarket) == 6

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """AseanMarket の全メンバーの値が設計通りであること。"""
        assert AseanMarket.SGX.value == "SGX"
        assert AseanMarket.BURSA.value == "BURSA"
        assert AseanMarket.SET.value == "SET"
        assert AseanMarket.IDX.value == "IDX"
        assert AseanMarket.HOSE.value == "HOSE"
        assert AseanMarket.PSE.value == "PSE"

    def test_正常系_文字列として使用できる(self) -> None:
        """AseanMarket メンバーを文字列として直接使用できること。"""
        value: str = AseanMarket.SGX
        assert isinstance(value, str)
        assert value == "SGX"

    def test_正常系_全メンバー名が含まれている(self) -> None:
        """AseanMarket に全6市場が含まれていること。"""
        expected = {"SGX", "BURSA", "SET", "IDX", "HOSE", "PSE"}
        actual = {member.value for member in AseanMarket}
        assert actual == expected


# =============================================================================
# YFINANCE_SUFFIX_MAP
# =============================================================================


class TestYfinanceSuffixMap:
    """Test YFINANCE_SUFFIX_MAP constant."""

    def test_正常系_dictである(self) -> None:
        """YFINANCE_SUFFIX_MAP が dict であること。"""
        assert isinstance(YFINANCE_SUFFIX_MAP, dict)

    def test_正常系_全6市場が含まれている(self) -> None:
        """YFINANCE_SUFFIX_MAP が全6市場のエントリを含むこと。"""
        assert len(YFINANCE_SUFFIX_MAP) == 6
        for market in AseanMarket:
            assert market in YFINANCE_SUFFIX_MAP, (
                f"{market.value} is not in YFINANCE_SUFFIX_MAP"
            )

    def test_正常系_SGXのサフィックスが正しい(self) -> None:
        """SGX のサフィックスが .SI であること。"""
        assert YFINANCE_SUFFIX_MAP[AseanMarket.SGX] == ".SI"

    def test_正常系_BURSAのサフィックスが正しい(self) -> None:
        """BURSA のサフィックスが .KL であること。"""
        assert YFINANCE_SUFFIX_MAP[AseanMarket.BURSA] == ".KL"

    def test_正常系_SETのサフィックスが正しい(self) -> None:
        """SET のサフィックスが .BK であること。"""
        assert YFINANCE_SUFFIX_MAP[AseanMarket.SET] == ".BK"

    def test_正常系_IDXのサフィックスが正しい(self) -> None:
        """IDX のサフィックスが .JK であること。"""
        assert YFINANCE_SUFFIX_MAP[AseanMarket.IDX] == ".JK"

    def test_正常系_HOSEのサフィックスが正しい(self) -> None:
        """HOSE のサフィックスが .VN であること。"""
        assert YFINANCE_SUFFIX_MAP[AseanMarket.HOSE] == ".VN"

    def test_正常系_PSEのサフィックスが正しい(self) -> None:
        """PSE のサフィックスが .PS であること。"""
        assert YFINANCE_SUFFIX_MAP[AseanMarket.PSE] == ".PS"

    def test_正常系_全サフィックスがドットで始まる(self) -> None:
        """全サフィックスが . で始まること。"""
        for market, suffix in YFINANCE_SUFFIX_MAP.items():
            assert suffix.startswith("."), (
                f"Suffix for {market.value} does not start with '.': {suffix}"
            )

    def test_正常系_サフィックスに重複がない(self) -> None:
        """サフィックス値に重複がないこと。"""
        values = list(YFINANCE_SUFFIX_MAP.values())
        assert len(values) == len(set(values)), "Duplicate suffixes found"


# =============================================================================
# SCREENER_EXCHANGE_MAP
# =============================================================================


class TestScreenerExchangeMap:
    """Test SCREENER_EXCHANGE_MAP constant."""

    def test_正常系_dictである(self) -> None:
        """SCREENER_EXCHANGE_MAP が dict であること。"""
        assert isinstance(SCREENER_EXCHANGE_MAP, dict)

    def test_正常系_全6市場が含まれている(self) -> None:
        """SCREENER_EXCHANGE_MAP が全6市場のエントリを含むこと。"""
        assert len(SCREENER_EXCHANGE_MAP) == 6
        for market in AseanMarket:
            assert market in SCREENER_EXCHANGE_MAP, (
                f"{market.value} is not in SCREENER_EXCHANGE_MAP"
            )

    def test_正常系_値がstr型である(self) -> None:
        """SCREENER_EXCHANGE_MAP の値が全て str であること。"""
        for market, exchange in SCREENER_EXCHANGE_MAP.items():
            assert isinstance(exchange, str), (
                f"Value for {market.value} is not str: {type(exchange)}"
            )
            assert len(exchange.strip()) > 0, f"Value for {market.value} is empty"

    def test_正常系_値に重複がない(self) -> None:
        """SCREENER_EXCHANGE_MAP の値に重複がないこと。"""
        values = list(SCREENER_EXCHANGE_MAP.values())
        assert len(values) == len(set(values)), "Duplicate exchange names found"


# =============================================================================
# SCREENER_MARKET_MAP
# =============================================================================


class TestScreenerMarketMap:
    """Test SCREENER_MARKET_MAP constant."""

    def test_正常系_dictである(self) -> None:
        """SCREENER_MARKET_MAP が dict であること。"""
        assert isinstance(SCREENER_MARKET_MAP, dict)

    def test_正常系_全6市場が含まれている(self) -> None:
        """SCREENER_MARKET_MAP が全6市場のエントリを含むこと。"""
        assert len(SCREENER_MARKET_MAP) == 6
        for market in AseanMarket:
            assert market in SCREENER_MARKET_MAP, (
                f"{market.value} is not in SCREENER_MARKET_MAP"
            )

    def test_正常系_値がstr型である(self) -> None:
        """SCREENER_MARKET_MAP の値が全て str であること。"""
        for market, name in SCREENER_MARKET_MAP.items():
            assert isinstance(name, str), (
                f"Value for {market.value} is not str: {type(name)}"
            )
            assert len(name.strip()) > 0, f"Value for {market.value} is empty"

    def test_正常系_値が全て小文字である(self) -> None:
        """SCREENER_MARKET_MAP の値が全て小文字であること。"""
        for market, name in SCREENER_MARKET_MAP.items():
            assert name == name.lower(), (
                f"Value for {market.value} is not lowercase: {name}"
            )

    def test_正常系_値に重複がない(self) -> None:
        """SCREENER_MARKET_MAP の値に重複がないこと。"""
        values = list(SCREENER_MARKET_MAP.values())
        assert len(values) == len(set(values)), "Duplicate market names found"


# =============================================================================
# TABLE_TICKERS
# =============================================================================


class TestTableTickers:
    """Test TABLE_TICKERS constant."""

    def test_正常系_strである(self) -> None:
        """TABLE_TICKERS が str であること。"""
        assert isinstance(TABLE_TICKERS, str)

    def test_正常系_空でない(self) -> None:
        """TABLE_TICKERS が空文字列でないこと。"""
        assert len(TABLE_TICKERS.strip()) > 0

    def test_正常系_aseanを含む(self) -> None:
        """TABLE_TICKERS が asean を含むこと。"""
        assert "asean" in TABLE_TICKERS.lower()


# =============================================================================
# DB_PATH
# =============================================================================


class TestDBPath:
    """Test DB_PATH constant."""

    def test_正常系_strである(self) -> None:
        """DB_PATH が str であること。"""
        assert isinstance(DB_PATH, str)

    def test_正常系_空でない(self) -> None:
        """DB_PATH が空文字列でないこと。"""
        assert len(DB_PATH.strip()) > 0

    def test_正常系_data_processedを含む(self) -> None:
        """DB_PATH が data/processed パスを含むこと。"""
        assert "data/processed" in DB_PATH

    def test_正常系_duckdb拡張子を含む(self) -> None:
        """DB_PATH が .duckdb 拡張子を含むこと。"""
        assert DB_PATH.endswith(".duckdb")


# =============================================================================
# Final type annotations
# =============================================================================


class TestFinalAnnotations:
    """Test that non-enum constants have Final type annotations."""

    def test_正常系_非Enum定数にFinal型アノテーションが付与されている(self) -> None:
        """非Enum の __all__ 定数に typing.Final アノテーションが付与されていること。"""
        from market.asean_common import constants

        annotations = get_type_hints(constants, include_extras=True)

        non_enum_names = [name for name in __all__ if name != "AseanMarket"]

        for name in non_enum_names:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
