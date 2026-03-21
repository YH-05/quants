"""Tests for market.polymarket.types module."""

import pytest

from market.polymarket.types import (
    PolymarketConfig,
    PriceInterval,
    RetryConfig,
)


class TestPolymarketConfig:
    """Tests for PolymarketConfig dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        config = PolymarketConfig()
        assert config.gamma_base_url == "https://gamma-api.polymarket.com"
        assert config.clob_base_url == "https://clob.polymarket.com"
        assert config.data_base_url == "https://data-api.polymarket.com"
        assert config.timeout == 30.0
        assert config.rate_limit_per_second == 1.5

    def test_正常系_カスタム値(self) -> None:
        config = PolymarketConfig(
            gamma_base_url="https://custom-gamma.example.com",
            clob_base_url="https://custom-clob.example.com",
            data_base_url="https://custom-data.example.com",
            timeout=60.0,
            rate_limit_per_second=5.0,
        )
        assert config.gamma_base_url == "https://custom-gamma.example.com"
        assert config.clob_base_url == "https://custom-clob.example.com"
        assert config.data_base_url == "https://custom-data.example.com"
        assert config.timeout == 60.0
        assert config.rate_limit_per_second == 5.0

    def test_正常系_frozen(self) -> None:
        config = PolymarketConfig()
        with pytest.raises(AttributeError):
            config.timeout = 60.0  # type: ignore[misc]

    def test_正常系_タイムアウト境界値_最小(self) -> None:
        config = PolymarketConfig(timeout=1.0)
        assert config.timeout == 1.0

    def test_正常系_タイムアウト境界値_最大(self) -> None:
        config = PolymarketConfig(timeout=300.0)
        assert config.timeout == 300.0

    def test_異常系_タイムアウトが範囲外_小さすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            PolymarketConfig(timeout=0.5)

    def test_異常系_タイムアウトが範囲外_大きすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            PolymarketConfig(timeout=400.0)

    def test_異常系_レートリミットが0以下(self) -> None:
        with pytest.raises(ValueError, match="rate_limit_per_second must be positive"):
            PolymarketConfig(rate_limit_per_second=0.0)

    def test_異常系_レートリミットが負数(self) -> None:
        with pytest.raises(ValueError, match="rate_limit_per_second must be positive"):
            PolymarketConfig(rate_limit_per_second=-1.0)

    def test_正常系_レートリミット境界値_最小正数(self) -> None:
        config = PolymarketConfig(rate_limit_per_second=0.01)
        assert config.rate_limit_per_second == 0.01


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_wait == 1.0
        assert config.max_wait == 30.0

    def test_正常系_カスタム値(self) -> None:
        config = RetryConfig(max_attempts=5, base_wait=2.0, max_wait=60.0)
        assert config.max_attempts == 5
        assert config.base_wait == 2.0
        assert config.max_wait == 60.0

    def test_正常系_frozen(self) -> None:
        config = RetryConfig()
        with pytest.raises(AttributeError):
            config.max_attempts = 5  # type: ignore[misc]

    def test_正常系_max_attempts境界値_最小(self) -> None:
        config = RetryConfig(max_attempts=1)
        assert config.max_attempts == 1

    def test_正常系_max_attempts境界値_最大(self) -> None:
        config = RetryConfig(max_attempts=10)
        assert config.max_attempts == 10

    def test_異常系_max_attemptsが範囲外_小さすぎ(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=0)

    def test_異常系_max_attemptsが範囲外_大きすぎ(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=11)

    def test_異常系_base_waitが負数(self) -> None:
        with pytest.raises(ValueError, match="base_wait must be non-negative"):
            RetryConfig(base_wait=-1.0)

    def test_異常系_max_waitが負数(self) -> None:
        with pytest.raises(ValueError, match="max_wait must be non-negative"):
            RetryConfig(max_wait=-1.0)


class TestPriceInterval:
    """Tests for PriceInterval enum."""

    def test_正常系_メンバー数(self) -> None:
        assert len(PriceInterval) == 7

    def test_正常系_全メンバーの値(self) -> None:
        assert PriceInterval.ONE_HOUR.value == "1h"
        assert PriceInterval.SIX_HOURS.value == "6h"
        assert PriceInterval.ONE_DAY.value == "1d"
        assert PriceInterval.ONE_WEEK.value == "1w"
        assert PriceInterval.ONE_MONTH.value == "1m"
        assert PriceInterval.MAX.value == "max"
        assert PriceInterval.ALL.value == "all"

    def test_正常系_文字列として使用可能(self) -> None:
        """PriceInterval is a str enum, so it can be used as a string."""
        interval = PriceInterval.ONE_DAY
        assert isinstance(interval, str)
        assert interval == "1d"

    def test_正常系_文字列から生成(self) -> None:
        interval = PriceInterval("1d")
        assert interval is PriceInterval.ONE_DAY

    def test_異常系_無効な値(self) -> None:
        with pytest.raises(ValueError):
            PriceInterval("invalid")
