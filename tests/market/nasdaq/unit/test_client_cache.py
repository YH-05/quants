"""Unit tests for NasdaqClient cache helpers (client_cache module).

Tests cover:
- TTL constant value validation
- get_nasdaq_cache() returns a SQLiteCache instance

Test TODO List:
- [x] test_正常系_各TTL定数が期待する値を持つ
- [x] test_正常系_get_nasdaq_cacheがSQLiteCacheを返す

See Also
--------
market.nasdaq.client_cache : Cache helpers under test.
"""

from __future__ import annotations

from market.cache.cache import SQLiteCache
from market.nasdaq.client_cache import (
    ANALYST_EARNINGS_DATE_TTL,
    ANALYST_FORECAST_TTL,
    ANALYST_RATINGS_TTL,
    ANALYST_TARGET_PRICE_TTL,
    DIVIDEND_HISTORY_TTL,
    DIVIDENDS_CALENDAR_TTL,
    EARNINGS_CALENDAR_TTL,
    ETF_SCREENER_TTL,
    FINANCIALS_TTL,
    INSIDER_TRADES_TTL,
    INSTITUTIONAL_HOLDINGS_TTL,
    IPO_CALENDAR_TTL,
    MARKET_MOVERS_TTL,
    SEC_FILINGS_TTL,
    SHORT_INTEREST_TTL,
    SPLITS_CALENDAR_TTL,
    STOCK_CHART_TTL,
    STOCK_QUOTE_TTL,
    STOCK_SUMMARY_TTL,
    get_nasdaq_cache,
)

# =============================================================================
# TTL Constant Value Tests
# =============================================================================


class TestTTLConstants:
    """Validate TTL constant values match expected durations."""

    def test_正常系_EARNINGS_CALENDAR_TTLは24時間(self) -> None:
        """Earnings calendar TTL is 24 hours (86400 seconds)."""
        assert EARNINGS_CALENDAR_TTL == 86400

    def test_正常系_DIVIDENDS_CALENDAR_TTLは24時間(self) -> None:
        """Dividends calendar TTL is 24 hours."""
        assert DIVIDENDS_CALENDAR_TTL == 86400

    def test_正常系_SPLITS_CALENDAR_TTLは24時間(self) -> None:
        """Splits calendar TTL is 24 hours."""
        assert SPLITS_CALENDAR_TTL == 86400

    def test_正常系_IPO_CALENDAR_TTLは24時間(self) -> None:
        """IPO calendar TTL is 24 hours."""
        assert IPO_CALENDAR_TTL == 86400

    def test_正常系_STOCK_QUOTE_TTLは5分(self) -> None:
        """Stock quote TTL is 5 minutes (300 seconds)."""
        assert STOCK_QUOTE_TTL == 300

    def test_正常系_STOCK_SUMMARY_TTLは1時間(self) -> None:
        """Stock summary TTL is 1 hour (3600 seconds)."""
        assert STOCK_SUMMARY_TTL == 3600

    def test_正常系_STOCK_CHART_TTLは1時間(self) -> None:
        """Stock chart TTL is 1 hour."""
        assert STOCK_CHART_TTL == 3600

    def test_正常系_INSTITUTIONAL_HOLDINGS_TTLは7日(self) -> None:
        """Institutional holdings TTL is 7 days (604800 seconds)."""
        assert INSTITUTIONAL_HOLDINGS_TTL == 604800

    def test_正常系_INSIDER_TRADES_TTLは24時間(self) -> None:
        """Insider trades TTL is 24 hours."""
        assert INSIDER_TRADES_TTL == 86400

    def test_正常系_SEC_FILINGS_TTLは24時間(self) -> None:
        """SEC filings TTL is 24 hours."""
        assert SEC_FILINGS_TTL == 86400

    def test_正常系_FINANCIALS_TTLは24時間(self) -> None:
        """Financials TTL is 24 hours."""
        assert FINANCIALS_TTL == 86400

    def test_正常系_ANALYST_FORECAST_TTLは24時間(self) -> None:
        """Analyst forecast TTL is 24 hours."""
        assert ANALYST_FORECAST_TTL == 86400

    def test_正常系_ANALYST_RATINGS_TTLは24時間(self) -> None:
        """Analyst ratings TTL is 24 hours."""
        assert ANALYST_RATINGS_TTL == 86400

    def test_正常系_ANALYST_TARGET_PRICE_TTLは24時間(self) -> None:
        """Analyst target price TTL is 24 hours."""
        assert ANALYST_TARGET_PRICE_TTL == 86400

    def test_正常系_ANALYST_EARNINGS_DATE_TTLは12時間(self) -> None:
        """Analyst earnings date TTL is 12 hours (43200 seconds)."""
        assert ANALYST_EARNINGS_DATE_TTL == 43200

    def test_正常系_SHORT_INTEREST_TTLは24時間(self) -> None:
        """Short interest TTL is 24 hours."""
        assert SHORT_INTEREST_TTL == 86400

    def test_正常系_DIVIDEND_HISTORY_TTLは24時間(self) -> None:
        """Dividend history TTL is 24 hours."""
        assert DIVIDEND_HISTORY_TTL == 86400

    def test_正常系_MARKET_MOVERS_TTLは5分(self) -> None:
        """Market movers TTL is 5 minutes."""
        assert MARKET_MOVERS_TTL == 300

    def test_正常系_ETF_SCREENER_TTLは1時間(self) -> None:
        """ETF screener TTL is 1 hour."""
        assert ETF_SCREENER_TTL == 3600

    def test_正常系_全TTLが正の整数(self) -> None:
        """All TTL values are positive integers."""
        ttls = [
            EARNINGS_CALENDAR_TTL,
            DIVIDENDS_CALENDAR_TTL,
            SPLITS_CALENDAR_TTL,
            IPO_CALENDAR_TTL,
            STOCK_QUOTE_TTL,
            STOCK_SUMMARY_TTL,
            STOCK_CHART_TTL,
            INSTITUTIONAL_HOLDINGS_TTL,
            INSIDER_TRADES_TTL,
            SEC_FILINGS_TTL,
            FINANCIALS_TTL,
            ANALYST_FORECAST_TTL,
            ANALYST_RATINGS_TTL,
            ANALYST_TARGET_PRICE_TTL,
            ANALYST_EARNINGS_DATE_TTL,
            SHORT_INTEREST_TTL,
            DIVIDEND_HISTORY_TTL,
            MARKET_MOVERS_TTL,
            ETF_SCREENER_TTL,
        ]
        for ttl in ttls:
            assert isinstance(ttl, int)
            assert ttl > 0


# =============================================================================
# get_nasdaq_cache Tests
# =============================================================================


class TestGetNasdaqCache:
    """Tests for get_nasdaq_cache() factory function."""

    def test_正常系_get_nasdaq_cacheがSQLiteCacheを返す(self) -> None:
        """get_nasdaq_cache() returns a SQLiteCache instance."""
        cache = get_nasdaq_cache()
        assert isinstance(cache, SQLiteCache)

    def test_正常系_get_nasdaq_cacheが毎回新しいインスタンスを返す(self) -> None:
        """get_nasdaq_cache() returns a new instance on each call."""
        cache1 = get_nasdaq_cache()
        cache2 = get_nasdaq_cache()
        assert cache1 is not cache2
