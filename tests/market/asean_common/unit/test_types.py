"""Tests for market.asean_common.types module.

Tests verify the TickerRecord frozen dataclass definition,
including field types, frozen behaviour, __post_init__ auto-generation
of yfinance_ticker, and module exports.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] TickerRecord: frozen, all fields, field types
- [x] TickerRecord: __post_init__ auto-generates yfinance_ticker
- [x] TickerRecord: yfinance_ticker for each market suffix
- [x] TickerRecord: optional fields default to None
- [x] TickerRecord: is_active defaults to True
"""

from dataclasses import FrozenInstanceError

import pytest

from market.asean_common.constants import YFINANCE_SUFFIX_MAP, AseanMarket
from market.asean_common.types import (
    TickerRecord,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """types モジュールが正常にインポートできること。"""
        from market.asean_common import types

        assert types is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.asean_common import types

        for name in __all__:
            assert hasattr(types, name), f"{name} is not defined in types module"

    def test_正常系_allが1項目を含む(self) -> None:
        """__all__ が TickerRecord をエクスポートしていること。"""
        expected = {"TickerRecord"}
        assert set(__all__) == expected

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.asean_common import types

        assert types.__doc__ is not None
        assert len(types.__doc__) > 0


# =============================================================================
# TickerRecord dataclass
# =============================================================================


class TestTickerRecord:
    """Test TickerRecord frozen dataclass."""

    def _make_record(self, **overrides: object) -> TickerRecord:
        """Create a TickerRecord with default values."""
        defaults: dict[str, object] = {
            "ticker": "D05",
            "name": "DBS Group Holdings Ltd",
            "market": AseanMarket.SGX,
            "yfinance_suffix": ".SI",
        }
        defaults.update(overrides)
        return TickerRecord(**defaults)  # type: ignore[arg-type]

    def test_正常系_frozenである(self) -> None:
        """TickerRecord がフィールド変更不可であること。"""
        record = self._make_record()
        with pytest.raises(FrozenInstanceError):
            record.ticker = "U11"

    def test_正常系_必須フィールドで生成できる(self) -> None:
        """TickerRecord が必須フィールドのみで生成できること。"""
        record = self._make_record()
        assert record.ticker == "D05"
        assert record.name == "DBS Group Holdings Ltd"
        assert record.market == AseanMarket.SGX
        assert record.yfinance_suffix == ".SI"

    def test_正常系_yfinance_tickerが自動生成される(self) -> None:
        """__post_init__ で yfinance_ticker が ticker + yfinance_suffix で自動生成されること。"""
        record = self._make_record(ticker="D05", yfinance_suffix=".SI")
        assert record.yfinance_ticker == "D05.SI"

    def test_正常系_SGXのyfinance_tickerが正しい(self) -> None:
        """SGX 銘柄の yfinance_ticker が正しく生成されること。"""
        record = self._make_record(
            ticker="D05",
            market=AseanMarket.SGX,
            yfinance_suffix=".SI",
        )
        assert record.yfinance_ticker == "D05.SI"

    def test_正常系_BURSAのyfinance_tickerが正しい(self) -> None:
        """BURSA 銘柄の yfinance_ticker が正しく生成されること。"""
        record = self._make_record(
            ticker="1155",
            name="Maybank",
            market=AseanMarket.BURSA,
            yfinance_suffix=".KL",
        )
        assert record.yfinance_ticker == "1155.KL"

    def test_正常系_SETのyfinance_tickerが正しい(self) -> None:
        """SET 銘柄の yfinance_ticker が正しく生成されること。"""
        record = self._make_record(
            ticker="PTT",
            name="PTT Public Company Limited",
            market=AseanMarket.SET,
            yfinance_suffix=".BK",
        )
        assert record.yfinance_ticker == "PTT.BK"

    def test_正常系_IDXのyfinance_tickerが正しい(self) -> None:
        """IDX 銘柄の yfinance_ticker が正しく生成されること。"""
        record = self._make_record(
            ticker="BBCA",
            name="Bank Central Asia",
            market=AseanMarket.IDX,
            yfinance_suffix=".JK",
        )
        assert record.yfinance_ticker == "BBCA.JK"

    def test_正常系_HOSEのyfinance_tickerが正しい(self) -> None:
        """HOSE 銘柄の yfinance_ticker が正しく生成されること。"""
        record = self._make_record(
            ticker="VNM",
            name="Vinamilk",
            market=AseanMarket.HOSE,
            yfinance_suffix=".VN",
        )
        assert record.yfinance_ticker == "VNM.VN"

    def test_正常系_PSEのyfinance_tickerが正しい(self) -> None:
        """PSE 銘柄の yfinance_ticker が正しく生成されること。"""
        record = self._make_record(
            ticker="SM",
            name="SM Investments",
            market=AseanMarket.PSE,
            yfinance_suffix=".PS",
        )
        assert record.yfinance_ticker == "SM.PS"

    def test_正常系_オプショナルフィールドのデフォルトがNone(self) -> None:
        """sector, industry, market_cap, currency のデフォルトが None であること。"""
        record = self._make_record()
        assert record.sector is None
        assert record.industry is None
        assert record.market_cap is None
        assert record.currency is None

    def test_正常系_is_activeのデフォルトがTrue(self) -> None:
        """is_active のデフォルトが True であること。"""
        record = self._make_record()
        assert record.is_active is True

    def test_正常系_全フィールドを設定できる(self) -> None:
        """TickerRecord の全フィールドを設定して生成できること。"""
        record = TickerRecord(
            ticker="D05",
            name="DBS Group Holdings Ltd",
            market=AseanMarket.SGX,
            yfinance_suffix=".SI",
            sector="Financial Services",
            industry="Banks - Diversified",
            market_cap=80_000_000_000,
            currency="SGD",
            is_active=True,
        )
        assert record.ticker == "D05"
        assert record.name == "DBS Group Holdings Ltd"
        assert record.market == AseanMarket.SGX
        assert record.yfinance_suffix == ".SI"
        assert record.yfinance_ticker == "D05.SI"
        assert record.sector == "Financial Services"
        assert record.industry == "Banks - Diversified"
        assert record.market_cap == 80_000_000_000
        assert record.currency == "SGD"
        assert record.is_active is True

    def test_正常系_is_activeをFalseに設定できる(self) -> None:
        """is_active を False に設定して生成できること。"""
        record = self._make_record(is_active=False)
        assert record.is_active is False

    def test_正常系_全フィールドが存在する(self) -> None:
        """TickerRecord が設計通りの10フィールドを持つこと。"""
        record = self._make_record()
        expected_fields = [
            "ticker",
            "name",
            "market",
            "yfinance_suffix",
            "yfinance_ticker",
            "sector",
            "industry",
            "market_cap",
            "currency",
            "is_active",
        ]
        for field_name in expected_fields:
            assert hasattr(record, field_name), (
                f"Field {field_name} is not defined on TickerRecord"
            )

    def test_正常系_必須フィールドの型が正しい(self) -> None:
        """必須フィールドの型が設計通りであること。"""
        record = self._make_record()
        assert isinstance(record.ticker, str)
        assert isinstance(record.name, str)
        assert isinstance(record.market, AseanMarket)
        assert isinstance(record.yfinance_suffix, str)
        assert isinstance(record.yfinance_ticker, str)
        assert isinstance(record.is_active, bool)
