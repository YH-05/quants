"""Tests for market.polymarket.cache module.

Tests for TTL constants and get_polymarket_cache() helper.
"""

from market.polymarket.cache import (
    ACTIVE_PRICES_TTL,
    LEADERBOARD_TTL,
    METADATA_TTL,
    OI_TRADES_TTL,
    ORDERBOOK_TTL,
    RESOLVED_TTL,
    get_polymarket_cache,
)


class TestTTLConstants:
    """Tests for TTL constant values."""

    def test_正常系_ORDERBOOK_TTL(self) -> None:
        assert ORDERBOOK_TTL == 30

    def test_正常系_ACTIVE_PRICES_TTL(self) -> None:
        assert ACTIVE_PRICES_TTL == 60

    def test_正常系_OI_TRADES_TTL(self) -> None:
        assert OI_TRADES_TTL == 300

    def test_正常系_METADATA_TTL(self) -> None:
        assert METADATA_TTL == 3600

    def test_正常系_LEADERBOARD_TTL(self) -> None:
        assert LEADERBOARD_TTL == 3600

    def test_正常系_RESOLVED_TTL(self) -> None:
        assert RESOLVED_TTL == 2592000

    def test_正常系_TTL値は全て正の整数(self) -> None:
        for ttl in [
            ORDERBOOK_TTL,
            ACTIVE_PRICES_TTL,
            OI_TRADES_TTL,
            METADATA_TTL,
            LEADERBOARD_TTL,
            RESOLVED_TTL,
        ]:
            assert isinstance(ttl, int)
            assert ttl > 0

    def test_正常系_TTL値の昇順(self) -> None:
        """TTL values should increase from most volatile to least volatile data."""
        assert ORDERBOOK_TTL < ACTIVE_PRICES_TTL
        assert ACTIVE_PRICES_TTL < OI_TRADES_TTL
        assert OI_TRADES_TTL < METADATA_TTL
        assert METADATA_TTL <= LEADERBOARD_TTL
        assert LEADERBOARD_TTL < RESOLVED_TTL


class TestGetPolymarketCache:
    """Tests for get_polymarket_cache() function."""

    def test_正常系_キャッシュインスタンスを返す(self) -> None:
        from market.cache.cache import SQLiteCache

        cache = get_polymarket_cache()
        assert isinstance(cache, SQLiteCache)

    def test_正常系_毎回新しいインスタンス(self) -> None:
        cache1 = get_polymarket_cache()
        cache2 = get_polymarket_cache()
        assert cache1 is not cache2

    def test_正常系_デフォルトTTLが設定されている(self) -> None:
        cache = get_polymarket_cache()
        assert cache.config.ttl_seconds == ACTIVE_PRICES_TTL
