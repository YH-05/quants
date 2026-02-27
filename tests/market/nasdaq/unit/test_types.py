"""Tests for market.nasdaq.types module.

Tests verify all type definitions for the NASDAQ Stock Screener module,
including Enum groups (Exchange, MarketCap, Sector, Recommendation, Region,
Country), frozen dataclasses (NasdaqConfig, RetryConfig, ScreenerFilter,
StockRecord), the FilterCategory type alias, and the ScreenerFilter.to_params()
method.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] Exchange Enum: values, str inheritance, member count
- [x] MarketCap Enum: values, str inheritance, member count
- [x] Sector Enum: values, str inheritance, member count (11)
- [x] Recommendation Enum: values, str inheritance, member count
- [x] Region Enum: values, str inheritance, member count (8)
- [x] Country Enum: values, str inheritance, subset verification
- [x] NasdaqConfig: frozen, defaults from constants, field types
- [x] NasdaqConfig: timeout/polite_delay/delay_jitter 範囲検証
- [x] RetryConfig: frozen, defaults, field types
- [x] RetryConfig: max_attempts 範囲検証
- [x] ScreenerFilter: frozen, defaults, to_params() method
- [x] StockRecord: frozen, all fields, field types
- [x] FilterCategory: type alias exists
"""

from dataclasses import FrozenInstanceError
from enum import Enum

import pytest

from market.nasdaq.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENTS,
)
from market.nasdaq.types import (
    Country,
    Exchange,
    FilterCategory,
    MarketCap,
    NasdaqConfig,
    Recommendation,
    Region,
    RetryConfig,
    ScreenerFilter,
    Sector,
    StockRecord,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """types モジュールが正常にインポートできること。"""
        from market.nasdaq import types

        assert types is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.nasdaq import types

        for name in __all__:
            assert hasattr(types, name), f"{name} is not defined in types module"

    def test_正常系_allが12項目を含む(self) -> None:
        """__all__ が全12型定義をエクスポートしていること。"""
        expected = {
            "Country",
            "Exchange",
            "FilterCategory",
            "MarketCap",
            "NasdaqConfig",
            "Recommendation",
            "Region",
            "RetryConfig",
            "ScreenerFilter",
            "Sector",
            "StockRecord",
        }
        assert set(__all__) >= expected

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.nasdaq import types

        assert types.__doc__ is not None
        assert len(types.__doc__) > 0


# =============================================================================
# Exchange Enum
# =============================================================================


class TestExchangeEnum:
    """Test Exchange Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """Exchange が str と Enum を継承していること。"""
        assert issubclass(Exchange, str)
        assert issubclass(Exchange, Enum)

    def test_正常系_3つのメンバーを持つ(self) -> None:
        """Exchange が NASDAQ, NYSE, AMEX の3メンバーを持つこと。"""
        assert len(Exchange) == 3

    def test_正常系_NASDAQの値がnasdaq(self) -> None:
        """Exchange.NASDAQ の値が 'nasdaq' であること。"""
        assert Exchange.NASDAQ == "nasdaq"
        assert Exchange.NASDAQ.value == "nasdaq"

    def test_正常系_NYSEの値がnyse(self) -> None:
        """Exchange.NYSE の値が 'nyse' であること。"""
        assert Exchange.NYSE == "nyse"
        assert Exchange.NYSE.value == "nyse"

    def test_正常系_AMEXの値がamex(self) -> None:
        """Exchange.AMEX の値が 'amex' であること。"""
        assert Exchange.AMEX == "amex"
        assert Exchange.AMEX.value == "amex"

    def test_正常系_文字列として使用できる(self) -> None:
        """Exchange メンバーを文字列として直接使用できること。"""
        value: str = Exchange.NASDAQ
        assert isinstance(value, str)


# =============================================================================
# MarketCap Enum
# =============================================================================


class TestMarketCapEnum:
    """Test MarketCap Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """MarketCap が str と Enum を継承していること。"""
        assert issubclass(MarketCap, str)
        assert issubclass(MarketCap, Enum)

    def test_正常系_6つのメンバーを持つ(self) -> None:
        """MarketCap が MEGA, LARGE, MID, SMALL, MICRO, NANO の6メンバーを持つこと。"""
        assert len(MarketCap) == 6

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """MarketCap の全メンバーの値が設計通りであること。"""
        assert MarketCap.MEGA.value == "mega"
        assert MarketCap.LARGE.value == "large"
        assert MarketCap.MID.value == "mid"
        assert MarketCap.SMALL.value == "small"
        assert MarketCap.MICRO.value == "micro"
        assert MarketCap.NANO.value == "nano"


# =============================================================================
# Sector Enum
# =============================================================================


class TestSectorEnum:
    """Test Sector Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """Sector が str と Enum を継承していること。"""
        assert issubclass(Sector, str)
        assert issubclass(Sector, Enum)

    def test_正常系_11個のメンバーを持つ(self) -> None:
        """Sector が11セクターを持つこと。"""
        assert len(Sector) == 11

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """Sector の全メンバーの値が設計通りであること。"""
        expected = {
            "technology",
            "telecommunications",
            "health_care",
            "finance",
            "real_estate",
            "consumer_discretionary",
            "consumer_staples",
            "industrials",
            "basic_materials",
            "energy",
            "utilities",
        }
        actual = {member.value for member in Sector}
        assert actual == expected

    def test_正常系_TECHNOLOGYの値がtechnology(self) -> None:
        """Sector.TECHNOLOGY の値が 'technology' であること。"""
        assert Sector.TECHNOLOGY.value == "technology"

    def test_正常系_HEALTH_CAREの値がhealth_care(self) -> None:
        """Sector.HEALTH_CARE の値が 'health_care' であること。"""
        assert Sector.HEALTH_CARE.value == "health_care"


# =============================================================================
# Recommendation Enum
# =============================================================================


class TestRecommendationEnum:
    """Test Recommendation Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """Recommendation が str と Enum を継承していること。"""
        assert issubclass(Recommendation, str)
        assert issubclass(Recommendation, Enum)

    def test_正常系_5つのメンバーを持つ(self) -> None:
        """Recommendation が5メンバーを持つこと。"""
        assert len(Recommendation) == 5

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """Recommendation の全メンバーの値が設計通りであること。"""
        assert Recommendation.STRONG_BUY.value == "strong_buy"
        assert Recommendation.BUY.value == "buy"
        assert Recommendation.HOLD.value == "hold"
        assert Recommendation.SELL.value == "sell"
        assert Recommendation.STRONG_SELL.value == "strong_sell"


# =============================================================================
# Region Enum
# =============================================================================


class TestRegionEnum:
    """Test Region Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """Region が str と Enum を継承していること。"""
        assert issubclass(Region, str)
        assert issubclass(Region, Enum)

    def test_正常系_8つのメンバーを持つ(self) -> None:
        """Region が8メンバーを持つこと。"""
        assert len(Region) == 8

    def test_正常系_全メンバーの値が正しい(self) -> None:
        """Region の全メンバーの値が設計通りであること。"""
        expected = {
            "africa",
            "asia",
            "australia_and_south_pacific",
            "caribbean",
            "europe",
            "middle_east",
            "north_america",
            "south_america",
        }
        actual = {member.value for member in Region}
        assert actual == expected


# =============================================================================
# Country Enum
# =============================================================================


class TestCountryEnum:
    """Test Country Enum definition."""

    def test_正常系_strを継承している(self) -> None:
        """Country が str と Enum を継承していること。"""
        assert issubclass(Country, str)
        assert issubclass(Country, Enum)

    def test_正常系_主要国が含まれている(self) -> None:
        """Country に USA, CANADA, JAPAN が含まれていること。"""
        assert Country.USA.value == "united_states"
        assert Country.CANADA.value == "canada"
        assert Country.JAPAN.value == "japan"

    def test_正常系_文字列として使用できる(self) -> None:
        """Country メンバーを文字列として直接使用できること。"""
        value: str = Country.USA
        assert isinstance(value, str)


# =============================================================================
# NasdaqConfig dataclass
# =============================================================================


class TestNasdaqConfig:
    """Test NasdaqConfig frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """NasdaqConfig がフィールド変更不可であること。"""
        config = NasdaqConfig()
        with pytest.raises(FrozenInstanceError):
            config.polite_delay = 5.0  # type: ignore[misc]

    def test_正常系_デフォルト値がconstantsと一致(self) -> None:
        """NasdaqConfig のデフォルト値が constants の値と一致すること。"""
        config = NasdaqConfig()
        assert config.polite_delay == DEFAULT_POLITE_DELAY
        assert config.delay_jitter == DEFAULT_DELAY_JITTER
        assert config.timeout == DEFAULT_TIMEOUT

    def test_正常系_user_agentsのデフォルトがタプル(self) -> None:
        """NasdaqConfig の user_agents のデフォルトが空タプルであること。"""
        config = NasdaqConfig()
        assert isinstance(config.user_agents, tuple)
        assert config.user_agents == ()

    def test_正常系_impersonateのデフォルトがchrome(self) -> None:
        """NasdaqConfig の impersonate のデフォルトが 'chrome' であること。"""
        config = NasdaqConfig()
        assert config.impersonate == "chrome"

    def test_正常系_カスタム値で生成できる(self) -> None:
        """NasdaqConfig をカスタム値で生成できること。"""
        config = NasdaqConfig(
            polite_delay=3.0,
            delay_jitter=1.0,
            user_agents=("UA1", "UA2"),
            impersonate="chrome120",
            timeout=60.0,
        )
        assert config.polite_delay == 3.0
        assert config.delay_jitter == 1.0
        assert config.user_agents == ("UA1", "UA2")
        assert config.impersonate == "chrome120"
        assert config.timeout == 60.0

    def test_正常系_全フィールドが存在する(self) -> None:
        """NasdaqConfig が設計通りの5フィールドを持つこと。"""
        config = NasdaqConfig()
        assert hasattr(config, "polite_delay")
        assert hasattr(config, "delay_jitter")
        assert hasattr(config, "user_agents")
        assert hasattr(config, "impersonate")
        assert hasattr(config, "timeout")

    def test_正常系_境界値でtimeoutが受け入れられる(self) -> None:
        """timeout の境界値（1.0, 300.0）が受け入れられること。"""
        config_min = NasdaqConfig(timeout=1.0)
        assert config_min.timeout == 1.0
        config_max = NasdaqConfig(timeout=300.0)
        assert config_max.timeout == 300.0

    def test_異常系_timeoutが範囲外でValueError(self) -> None:
        """timeout が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            NasdaqConfig(timeout=0.5)
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            NasdaqConfig(timeout=301.0)

    def test_正常系_境界値でpolite_delayが受け入れられる(self) -> None:
        """polite_delay の境界値（0.0, 60.0）が受け入れられること。"""
        config_min = NasdaqConfig(polite_delay=0.0)
        assert config_min.polite_delay == 0.0
        config_max = NasdaqConfig(polite_delay=60.0)
        assert config_max.polite_delay == 60.0

    def test_異常系_polite_delayが範囲外でValueError(self) -> None:
        """polite_delay が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            NasdaqConfig(polite_delay=-0.1)
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            NasdaqConfig(polite_delay=61.0)

    def test_正常系_境界値でdelay_jitterが受け入れられる(self) -> None:
        """delay_jitter の境界値（0.0, 30.0）が受け入れられること。"""
        config_min = NasdaqConfig(delay_jitter=0.0)
        assert config_min.delay_jitter == 0.0
        config_max = NasdaqConfig(delay_jitter=30.0)
        assert config_max.delay_jitter == 30.0

    def test_異常系_delay_jitterが範囲外でValueError(self) -> None:
        """delay_jitter が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(
            ValueError, match=r"delay_jitter must be between 0\.0 and 30\.0"
        ):
            NasdaqConfig(delay_jitter=-0.1)
        with pytest.raises(
            ValueError, match=r"delay_jitter must be between 0\.0 and 30\.0"
        ):
            NasdaqConfig(delay_jitter=31.0)


# =============================================================================
# RetryConfig dataclass
# =============================================================================


class TestRetryConfig:
    """Test RetryConfig frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """RetryConfig がフィールド変更不可であること。"""
        config = RetryConfig()
        with pytest.raises(FrozenInstanceError):
            config.max_attempts = 10  # type: ignore[misc]

    def test_正常系_デフォルト値が正しい(self) -> None:
        """RetryConfig のデフォルト値が設計通りであること。"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_正常系_カスタム値で生成できる(self) -> None:
        """RetryConfig をカスタム値で生成できること。"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_正常系_全フィールドが存在する(self) -> None:
        """RetryConfig が設計通りの5フィールドを持つこと。"""
        config = RetryConfig()
        assert hasattr(config, "max_attempts")
        assert hasattr(config, "initial_delay")
        assert hasattr(config, "max_delay")
        assert hasattr(config, "exponential_base")
        assert hasattr(config, "jitter")

    def test_正常系_境界値でmax_attemptsが受け入れられる(self) -> None:
        """max_attempts の境界値（1, 10）が受け入れられること。"""
        config_min = RetryConfig(max_attempts=1)
        assert config_min.max_attempts == 1
        config_max = RetryConfig(max_attempts=10)
        assert config_max.max_attempts == 10

    def test_異常系_max_attemptsが範囲外でValueError(self) -> None:
        """max_attempts が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            RetryConfig(max_attempts=0)
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            RetryConfig(max_attempts=11)


# =============================================================================
# ScreenerFilter dataclass
# =============================================================================


class TestScreenerFilter:
    """Test ScreenerFilter frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """ScreenerFilter がフィールド変更不可であること。"""
        f = ScreenerFilter()
        with pytest.raises(FrozenInstanceError):
            f.exchange = Exchange.NASDAQ  # type: ignore[misc]

    def test_正常系_デフォルト値が正しい(self) -> None:
        """ScreenerFilter のデフォルト値が設計通りであること。"""
        f = ScreenerFilter()
        assert f.exchange is None
        assert f.marketcap is None
        assert f.sector is None
        assert f.recommendation is None
        assert f.region is None
        assert f.country is None
        assert f.limit == 0

    def test_正常系_to_paramsでデフォルトフィルターがlimitのみ返す(self) -> None:
        """デフォルト ScreenerFilter の to_params() が limit のみ返すこと。"""
        f = ScreenerFilter()
        params = f.to_params()
        assert params == {"limit": "0"}

    def test_正常系_to_paramsで全フィルターが反映される(self) -> None:
        """全フィルター設定時の to_params() が正しい dict を返すこと。"""
        f = ScreenerFilter(
            exchange=Exchange.NASDAQ,
            marketcap=MarketCap.MEGA,
            sector=Sector.TECHNOLOGY,
            recommendation=Recommendation.STRONG_BUY,
            region=Region.NORTH_AMERICA,
            country="united_states",
            limit=100,
        )
        params = f.to_params()
        assert params == {
            "exchange": "nasdaq",
            "marketcap": "mega",
            "sector": "technology",
            "recommendation": "strong_buy",
            "region": "north_america",
            "country": "united_states",
            "limit": "100",
        }

    def test_正常系_to_paramsでNoneフィルターが除外される(self) -> None:
        """None のフィルターが to_params() の結果に含まれないこと。"""
        f = ScreenerFilter(exchange=Exchange.NYSE)
        params = f.to_params()
        assert "exchange" in params
        assert "marketcap" not in params
        assert "sector" not in params
        assert "recommendation" not in params
        assert "region" not in params
        assert "country" not in params

    def test_正常系_to_paramsの値が全てstr型(self) -> None:
        """to_params() の戻り値の全キー・値が str であること。"""
        f = ScreenerFilter(
            exchange=Exchange.NASDAQ,
            marketcap=MarketCap.LARGE,
            limit=50,
        )
        params = f.to_params()
        for key, value in params.items():
            assert isinstance(key, str), f"Key {key!r} is not str"
            assert isinstance(value, str), f"Value {value!r} for key {key!r} is not str"

    def test_正常系_countryにstr値を指定できる(self) -> None:
        """country フィールドに任意の文字列を指定できること。"""
        f = ScreenerFilter(country="bermuda")
        params = f.to_params()
        assert params["country"] == "bermuda"

    def test_正常系_全フィールドが存在する(self) -> None:
        """ScreenerFilter が設計通りの7フィールドを持つこと。"""
        f = ScreenerFilter()
        assert hasattr(f, "exchange")
        assert hasattr(f, "marketcap")
        assert hasattr(f, "sector")
        assert hasattr(f, "recommendation")
        assert hasattr(f, "region")
        assert hasattr(f, "country")
        assert hasattr(f, "limit")


# =============================================================================
# StockRecord dataclass
# =============================================================================


class TestStockRecord:
    """Test StockRecord frozen dataclass."""

    def test_正常系_frozenである(self) -> None:
        """StockRecord がフィールド変更不可であること。"""
        record = StockRecord(
            symbol="AAPL",
            name="Apple Inc.",
            last_sale="$227.63",
            net_change="-1.95",
            pct_change="-0.849%",
            market_cap="3435123456789",
            country="United States",
            ipo_year="1980",
            volume="48123456",
            sector="Technology",
            industry="Computer Manufacturing",
            url="/market-activity/stocks/aapl",
        )
        with pytest.raises(FrozenInstanceError):
            record.symbol = "MSFT"  # type: ignore[misc]

    def test_正常系_全フィールドが正しく設定される(self) -> None:
        """StockRecord の全12フィールドが正しく設定されること。"""
        record = StockRecord(
            symbol="AAPL",
            name="Apple Inc. Common Stock",
            last_sale="$227.63",
            net_change="-1.95",
            pct_change="-0.849%",
            market_cap="3,435,123,456,789",
            country="United States",
            ipo_year="1980",
            volume="48,123,456",
            sector="Technology",
            industry="Computer Manufacturing",
            url="/market-activity/stocks/aapl",
        )
        assert record.symbol == "AAPL"
        assert record.name == "Apple Inc. Common Stock"
        assert record.last_sale == "$227.63"
        assert record.net_change == "-1.95"
        assert record.pct_change == "-0.849%"
        assert record.market_cap == "3,435,123,456,789"
        assert record.country == "United States"
        assert record.ipo_year == "1980"
        assert record.volume == "48,123,456"
        assert record.sector == "Technology"
        assert record.industry == "Computer Manufacturing"
        assert record.url == "/market-activity/stocks/aapl"

    def test_正常系_全フィールドがstr型(self) -> None:
        """StockRecord の全フィールドが str であること（APIレスポンスの生データ保持）。"""
        record = StockRecord(
            symbol="MSFT",
            name="Microsoft Corporation",
            last_sale="$420.00",
            net_change="2.50",
            pct_change="0.599%",
            market_cap="3,123,456,789,012",
            country="United States",
            ipo_year="1986",
            volume="25,000,000",
            sector="Technology",
            industry="Computer Software: Prepackaged Software",
            url="/market-activity/stocks/msft",
        )
        for field_name in [
            "symbol",
            "name",
            "last_sale",
            "net_change",
            "pct_change",
            "market_cap",
            "country",
            "ipo_year",
            "volume",
            "sector",
            "industry",
            "url",
        ]:
            assert isinstance(getattr(record, field_name), str), (
                f"Field {field_name} is not str"
            )


# =============================================================================
# FilterCategory type alias
# =============================================================================


class TestFilterCategory:
    """Test FilterCategory type alias."""

    def test_正常系_FilterCategoryが定義されている(self) -> None:
        """FilterCategory が types モジュールに定義されていること。"""
        from market.nasdaq import types

        assert hasattr(types, "FilterCategory")

    def test_正常系_allに含まれている(self) -> None:
        """FilterCategory が __all__ に含まれていること。"""
        assert "FilterCategory" in __all__
