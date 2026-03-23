"""Unit tests for market.alphavantage.cache module.

Tests verify TTL constants and the get_alphavantage_cache factory function.

See Also
--------
market.alphavantage.cache : Module under test.
market.jquants.cache : Reference implementation with identical pattern.
market.cache.cache : Core SQLiteCache / create_persistent_cache base.
"""

from market.alphavantage.cache import (
    COMPANY_OVERVIEW_TTL,
    CRYPTO_TTL,
    ECONOMIC_INDICATOR_TTL,
    FOREX_TTL,
    FUNDAMENTALS_TTL,
    GLOBAL_QUOTE_TTL,
    TIME_SERIES_DAILY_TTL,
    TIME_SERIES_INTRADAY_TTL,
    get_alphavantage_cache,
)
from market.cache.cache import SQLiteCache

# ---------------------------------------------------------------------------
# TTL constant tests
# ---------------------------------------------------------------------------


class TestTTLConstants:
    """Verify each TTL constant has the correct value in seconds."""

    def test_正常系_TIME_SERIES_DAILY_TTLが24時間(self) -> None:
        assert TIME_SERIES_DAILY_TTL == 86400

    def test_正常系_TIME_SERIES_INTRADAY_TTLが1時間(self) -> None:
        assert TIME_SERIES_INTRADAY_TTL == 3600

    def test_正常系_FUNDAMENTALS_TTLが7日(self) -> None:
        assert FUNDAMENTALS_TTL == 604800

    def test_正常系_ECONOMIC_INDICATOR_TTLが24時間(self) -> None:
        assert ECONOMIC_INDICATOR_TTL == 86400

    def test_正常系_FOREX_TTLが24時間(self) -> None:
        assert FOREX_TTL == 86400

    def test_正常系_CRYPTO_TTLが24時間(self) -> None:
        assert CRYPTO_TTL == 86400

    def test_正常系_GLOBAL_QUOTE_TTLが5分(self) -> None:
        assert GLOBAL_QUOTE_TTL == 300

    def test_正常系_COMPANY_OVERVIEW_TTLが7日(self) -> None:
        assert COMPANY_OVERVIEW_TTL == 604800

    def test_正常系_全TTL定数が正の整数(self) -> None:
        ttl_values = [
            TIME_SERIES_DAILY_TTL,
            TIME_SERIES_INTRADAY_TTL,
            FUNDAMENTALS_TTL,
            ECONOMIC_INDICATOR_TTL,
            FOREX_TTL,
            CRYPTO_TTL,
            GLOBAL_QUOTE_TTL,
            COMPANY_OVERVIEW_TTL,
        ]
        for ttl in ttl_values:
            assert isinstance(ttl, int)
            assert ttl > 0


# ---------------------------------------------------------------------------
# Factory function tests
# ---------------------------------------------------------------------------


class TestGetAlphaVantageCache:
    """Verify the get_alphavantage_cache factory function."""

    def test_正常系_返り値がSQLiteCacheインスタンス(self) -> None:
        cache = get_alphavantage_cache()
        try:
            assert isinstance(cache, SQLiteCache)
        finally:
            cache.close()

    def test_正常系_キャッシュが有効化されている(self) -> None:
        cache = get_alphavantage_cache()
        try:
            assert cache.config.enabled is True
        finally:
            cache.close()

    def test_正常系_デフォルトTTLがTIME_SERIES_DAILY_TTL(self) -> None:
        cache = get_alphavantage_cache()
        try:
            assert cache.config.ttl_seconds == TIME_SERIES_DAILY_TTL
        finally:
            cache.close()

    def test_正常系_max_entriesが10000(self) -> None:
        cache = get_alphavantage_cache()
        try:
            assert cache.config.max_entries == 10000
        finally:
            cache.close()

    def test_正常系_複数回呼び出しで異なるインスタンスを返す(self) -> None:
        cache1 = get_alphavantage_cache()
        cache2 = get_alphavantage_cache()
        try:
            assert cache1 is not cache2
        finally:
            cache1.close()
            cache2.close()
