"""Unit tests for market.alphavantage.types module.

Tests cover:
- AlphaVantageConfig: default values, custom values, validation, api_key repr,
  frozen immutability
- RetryConfig: default values, custom values, validation, frozen immutability
- FetchOptions: default values, custom values, frozen immutability
- All 7 Enum classes: member values match Alpha Vantage API parameters,
  str inheritance, member counts

See Also
--------
market.alphavantage.types : Implementation under test.
tests.market.jquants.unit.test_types : Similar test pattern for J-Quants types.
tests.market.nasdaq.unit.test_types : Similar test pattern for NASDAQ types.
"""

import pytest

from market.alphavantage.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_REQUESTS_PER_HOUR,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_TIMEOUT,
)
from market.alphavantage.types import (
    AlphaVantageConfig,
    CryptoFunction,
    EconomicIndicator,
    FetchOptions,
    ForexFunction,
    FundamentalFunction,
    Interval,
    OutputSize,
    RetryConfig,
    TimeSeriesFunction,
)

# =============================================================================
# AlphaVantageConfig Tests
# =============================================================================


class TestAlphaVantageConfig:
    """Tests for AlphaVantageConfig frozen dataclass."""

    def test_正常系_デフォルト値で生成できる(self) -> None:
        config = AlphaVantageConfig()
        assert config.api_key == ""
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.polite_delay == DEFAULT_POLITE_DELAY
        assert config.delay_jitter == DEFAULT_DELAY_JITTER
        assert config.requests_per_minute == DEFAULT_REQUESTS_PER_MINUTE
        assert config.requests_per_hour == DEFAULT_REQUESTS_PER_HOUR

    def test_正常系_カスタム値で生成できる(self) -> None:
        config = AlphaVantageConfig(
            api_key="test-key-123",
            timeout=10.0,
            polite_delay=1.0,
            delay_jitter=0.1,
            requests_per_minute=5,
            requests_per_hour=100,
        )
        assert config.api_key == "test-key-123"
        assert config.timeout == 10.0
        assert config.polite_delay == 1.0
        assert config.delay_jitter == 0.1
        assert config.requests_per_minute == 5
        assert config.requests_per_hour == 100

    def test_正常系_api_keyがreprに含まれない(self) -> None:
        config = AlphaVantageConfig(api_key="secret-key-abc")
        repr_str = repr(config)
        assert "secret-key-abc" not in repr_str
        assert "api_key" not in repr_str

    def test_正常系_境界値_timeoutの最小値(self) -> None:
        config = AlphaVantageConfig(timeout=1.0)
        assert config.timeout == 1.0

    def test_正常系_境界値_timeoutの最大値(self) -> None:
        config = AlphaVantageConfig(timeout=300.0)
        assert config.timeout == 300.0

    def test_正常系_境界値_polite_delayがゼロ(self) -> None:
        config = AlphaVantageConfig(polite_delay=0.0)
        assert config.polite_delay == 0.0

    def test_正常系_境界値_polite_delayの最大値(self) -> None:
        config = AlphaVantageConfig(polite_delay=60.0)
        assert config.polite_delay == 60.0

    def test_正常系_境界値_delay_jitterがゼロ(self) -> None:
        config = AlphaVantageConfig(delay_jitter=0.0)
        assert config.delay_jitter == 0.0

    def test_正常系_境界値_delay_jitterの最大値(self) -> None:
        config = AlphaVantageConfig(delay_jitter=30.0)
        assert config.delay_jitter == 30.0

    def test_正常系_境界値_requests_per_minuteの最小値(self) -> None:
        config = AlphaVantageConfig(requests_per_minute=1)
        assert config.requests_per_minute == 1

    def test_正常系_境界値_requests_per_minuteの最大値(self) -> None:
        config = AlphaVantageConfig(requests_per_minute=1000)
        assert config.requests_per_minute == 1000

    def test_正常系_境界値_requests_per_hourの最小値(self) -> None:
        config = AlphaVantageConfig(requests_per_hour=1)
        assert config.requests_per_hour == 1

    def test_正常系_境界値_requests_per_hourの最大値(self) -> None:
        config = AlphaVantageConfig(requests_per_hour=10000)
        assert config.requests_per_hour == 10000

    def test_異常系_timeoutが小さすぎるとValueError(self) -> None:
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            AlphaVantageConfig(timeout=0.5)

    def test_異常系_timeoutが大きすぎるとValueError(self) -> None:
        with pytest.raises(
            ValueError, match=r"timeout must be between 1\.0 and 300\.0"
        ):
            AlphaVantageConfig(timeout=301.0)

    def test_異常系_polite_delayが負でValueError(self) -> None:
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            AlphaVantageConfig(polite_delay=-0.1)

    def test_異常系_polite_delayが大きすぎるとValueError(self) -> None:
        with pytest.raises(
            ValueError, match=r"polite_delay must be between 0\.0 and 60\.0"
        ):
            AlphaVantageConfig(polite_delay=61.0)

    def test_異常系_delay_jitterが負でValueError(self) -> None:
        with pytest.raises(
            ValueError, match=r"delay_jitter must be between 0\.0 and 30\.0"
        ):
            AlphaVantageConfig(delay_jitter=-0.1)

    def test_異常系_delay_jitterが大きすぎるとValueError(self) -> None:
        with pytest.raises(
            ValueError, match=r"delay_jitter must be between 0\.0 and 30\.0"
        ):
            AlphaVantageConfig(delay_jitter=31.0)

    def test_異常系_requests_per_minuteがゼロでValueError(self) -> None:
        with pytest.raises(
            ValueError, match="requests_per_minute must be between 1 and 1000"
        ):
            AlphaVantageConfig(requests_per_minute=0)

    def test_異常系_requests_per_minuteが大きすぎるとValueError(self) -> None:
        with pytest.raises(
            ValueError, match="requests_per_minute must be between 1 and 1000"
        ):
            AlphaVantageConfig(requests_per_minute=1001)

    def test_異常系_requests_per_hourがゼロでValueError(self) -> None:
        with pytest.raises(
            ValueError, match="requests_per_hour must be between 1 and 10000"
        ):
            AlphaVantageConfig(requests_per_hour=0)

    def test_異常系_requests_per_hourが大きすぎるとValueError(self) -> None:
        with pytest.raises(
            ValueError, match="requests_per_hour must be between 1 and 10000"
        ):
            AlphaVantageConfig(requests_per_hour=10001)

    def test_エッジケース_frozenで属性変更不可(self) -> None:
        config = AlphaVantageConfig(api_key="test")
        with pytest.raises(AttributeError):
            config.api_key = "changed"

    def test_エッジケース_frozenでtimeout変更不可(self) -> None:
        config = AlphaVantageConfig()
        with pytest.raises(AttributeError):
            config.timeout = 99.0


# =============================================================================
# RetryConfig Tests
# =============================================================================


class TestRetryConfig:
    """Tests for RetryConfig frozen dataclass."""

    def test_正常系_デフォルト値で生成できる(self) -> None:
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.exponential_base == 2.0
        assert config.max_delay == 30.0
        assert config.initial_delay == 1.0
        assert config.jitter is True

    def test_正常系_カスタム値で生成できる(self) -> None:
        config = RetryConfig(
            max_attempts=5,
            exponential_base=3.0,
            max_delay=60.0,
            initial_delay=0.5,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.exponential_base == 3.0
        assert config.max_delay == 60.0
        assert config.initial_delay == 0.5
        assert config.jitter is False

    def test_正常系_境界値_max_attemptsの最小値(self) -> None:
        config = RetryConfig(max_attempts=1)
        assert config.max_attempts == 1

    def test_正常系_境界値_max_attemptsの最大値(self) -> None:
        config = RetryConfig(max_attempts=10)
        assert config.max_attempts == 10

    def test_異常系_max_attemptsがゼロでValueError(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            RetryConfig(max_attempts=0)

    def test_異常系_max_attemptsが大きすぎるとValueError(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            RetryConfig(max_attempts=11)

    def test_エッジケース_frozenで属性変更不可(self) -> None:
        config = RetryConfig()
        with pytest.raises(AttributeError):
            config.max_attempts = 5


# =============================================================================
# FetchOptions Tests
# =============================================================================


class TestFetchOptions:
    """Tests for FetchOptions frozen dataclass."""

    def test_正常系_デフォルト値で生成できる(self) -> None:
        options = FetchOptions()
        assert options.use_cache is True
        assert options.force_refresh is False

    def test_正常系_カスタム値で生成できる(self) -> None:
        options = FetchOptions(use_cache=False, force_refresh=True)
        assert options.use_cache is False
        assert options.force_refresh is True

    def test_エッジケース_frozenで属性変更不可(self) -> None:
        options = FetchOptions()
        with pytest.raises(AttributeError):
            options.use_cache = False


# =============================================================================
# OutputSize Enum Tests
# =============================================================================


class TestOutputSize:
    """Tests for OutputSize Enum."""

    def test_正常系_COMPACT値がAPIパラメータと一致(self) -> None:
        assert OutputSize.COMPACT.value == "compact"

    def test_正常系_FULL値がAPIパラメータと一致(self) -> None:
        assert OutputSize.FULL.value == "full"

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(OutputSize.COMPACT, str)
        assert OutputSize.COMPACT.value == "compact"

    def test_正常系_メンバー数が2(self) -> None:
        assert len(OutputSize) == 2


# =============================================================================
# Interval Enum Tests
# =============================================================================


class TestInterval:
    """Tests for Interval Enum."""

    def test_正常系_全メンバーの値がAPIパラメータと一致(self) -> None:
        expected = {
            "ONE_MIN": "1min",
            "FIVE_MIN": "5min",
            "FIFTEEN_MIN": "15min",
            "THIRTY_MIN": "30min",
            "SIXTY_MIN": "60min",
        }
        for name, value in expected.items():
            assert Interval[name].value == value

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(Interval.ONE_MIN, str)
        assert Interval.SIXTY_MIN.value == "60min"

    def test_正常系_メンバー数が5(self) -> None:
        assert len(Interval) == 5


# =============================================================================
# TimeSeriesFunction Enum Tests
# =============================================================================


class TestTimeSeriesFunction:
    """Tests for TimeSeriesFunction Enum."""

    def test_正常系_全メンバーの値がAPIパラメータと一致(self) -> None:
        expected = {
            "DAILY": "TIME_SERIES_DAILY",
            "DAILY_ADJUSTED": "TIME_SERIES_DAILY_ADJUSTED",
            "WEEKLY": "TIME_SERIES_WEEKLY",
            "MONTHLY": "TIME_SERIES_MONTHLY",
            "INTRADAY": "TIME_SERIES_INTRADAY",
        }
        for name, value in expected.items():
            assert TimeSeriesFunction[name].value == value

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(TimeSeriesFunction.DAILY, str)
        assert TimeSeriesFunction.DAILY.value == "TIME_SERIES_DAILY"

    def test_正常系_メンバー数が5(self) -> None:
        assert len(TimeSeriesFunction) == 5


# =============================================================================
# FundamentalFunction Enum Tests
# =============================================================================


class TestFundamentalFunction:
    """Tests for FundamentalFunction Enum."""

    def test_正常系_全メンバーの値がAPIパラメータと一致(self) -> None:
        expected = {
            "OVERVIEW": "OVERVIEW",
            "INCOME_STATEMENT": "INCOME_STATEMENT",
            "BALANCE_SHEET": "BALANCE_SHEET",
            "CASH_FLOW": "CASH_FLOW",
            "EARNINGS": "EARNINGS",
        }
        for name, value in expected.items():
            assert FundamentalFunction[name].value == value

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(FundamentalFunction.OVERVIEW, str)
        assert FundamentalFunction.OVERVIEW.value == "OVERVIEW"

    def test_正常系_メンバー数が5(self) -> None:
        assert len(FundamentalFunction) == 5


# =============================================================================
# ForexFunction Enum Tests
# =============================================================================


class TestForexFunction:
    """Tests for ForexFunction Enum."""

    def test_正常系_全メンバーの値がAPIパラメータと一致(self) -> None:
        expected = {
            "EXCHANGE_RATE": "CURRENCY_EXCHANGE_RATE",
            "FX_DAILY": "FX_DAILY",
            "FX_WEEKLY": "FX_WEEKLY",
            "FX_MONTHLY": "FX_MONTHLY",
        }
        for name, value in expected.items():
            assert ForexFunction[name].value == value

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(ForexFunction.EXCHANGE_RATE, str)
        assert ForexFunction.EXCHANGE_RATE.value == "CURRENCY_EXCHANGE_RATE"

    def test_正常系_メンバー数が4(self) -> None:
        assert len(ForexFunction) == 4


# =============================================================================
# CryptoFunction Enum Tests
# =============================================================================


class TestCryptoFunction:
    """Tests for CryptoFunction Enum."""

    def test_正常系_全メンバーの値がAPIパラメータと一致(self) -> None:
        expected = {
            "DAILY": "DIGITAL_CURRENCY_DAILY",
            "WEEKLY": "DIGITAL_CURRENCY_WEEKLY",
            "MONTHLY": "DIGITAL_CURRENCY_MONTHLY",
        }
        for name, value in expected.items():
            assert CryptoFunction[name].value == value

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(CryptoFunction.DAILY, str)
        assert CryptoFunction.DAILY.value == "DIGITAL_CURRENCY_DAILY"

    def test_正常系_メンバー数が3(self) -> None:
        assert len(CryptoFunction) == 3


# =============================================================================
# EconomicIndicator Enum Tests
# =============================================================================


class TestEconomicIndicator:
    """Tests for EconomicIndicator Enum."""

    def test_正常系_全メンバーの値がAPIパラメータと一致(self) -> None:
        expected = {
            "REAL_GDP": "REAL_GDP",
            "CPI": "CPI",
            "INFLATION": "INFLATION",
            "UNEMPLOYMENT": "UNEMPLOYMENT",
            "TREASURY_YIELD": "TREASURY_YIELD",
            "FEDERAL_FUNDS_RATE": "FEDERAL_FUNDS_RATE",
        }
        for name, value in expected.items():
            assert EconomicIndicator[name].value == value

    def test_正常系_str継承で文字列として使用可能(self) -> None:
        assert isinstance(EconomicIndicator.REAL_GDP, str)
        assert EconomicIndicator.REAL_GDP.value == "REAL_GDP"

    def test_正常系_メンバー数が6(self) -> None:
        assert len(EconomicIndicator) == 6
