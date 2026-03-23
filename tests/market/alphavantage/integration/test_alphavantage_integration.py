"""Integration tests for Alpha Vantage API client.

These tests require a valid Alpha Vantage API key set via the
``ALPHA_VANTAGE_API_KEY`` environment variable.  When the key is not
present the entire module is skipped with ``pytest.skip``.

The tests exercise the real Alpha Vantage API through
``AlphaVantageClient`` and verify:

- ``get_daily``: DataFrame shape, column names, DatetimeIndex-compatible
  date column, and float OHLCV values.
- ``get_global_quote``: dict keys and value types for real-time quotes.
- ``get_company_overview``: dict keys and numeric type conversions.
- Rate limiter integration (requests stay within 25 req/min).
- Cache hit on the second call for the same symbol.

Run with::

    ALPHA_VANTAGE_API_KEY=<your-key> uv run pytest \
        tests/market/alphavantage/integration/ -m integration -v

See Also
--------
tests.market.jquants.integration.test_jquants_integration :
    Reference pattern for live API integration tests.
market.alphavantage.client : The client under test.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

import pandas as pd
import pytest

from market.alphavantage.client import AlphaVantageClient
from market.alphavantage.types import AlphaVantageConfig, FetchOptions, RetryConfig

# ---------------------------------------------------------------------------
# Module-level marker: every test in this file is an integration test
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Test symbol (IBM is used by Alpha Vantage demo key)
# ---------------------------------------------------------------------------
_TEST_SYMBOL: str = "IBM"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_api_key() -> bool:
    """Return ``True`` if the Alpha Vantage API key is available."""
    return bool(os.environ.get("ALPHA_VANTAGE_API_KEY"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Generator[AlphaVantageClient]:
    """Create an ``AlphaVantageClient`` with real credentials.

    The fixture is module-scoped so that the rate limiter state is shared
    across all tests in this file, preventing accidental rate-limit
    violations.

    Yields
    ------
    AlphaVantageClient
        A configured client using the real API key from the environment.
    """
    if not _has_api_key():
        pytest.skip("ALPHA_VANTAGE_API_KEY not set -- skipping live API tests")

    config = AlphaVantageConfig(
        # Use environment variable (api_key="" triggers env lookup)
        api_key="",
        polite_delay=3.0,
        delay_jitter=1.0,
        timeout=30.0,
        requests_per_minute=25,
        requests_per_hour=500,
    )
    retry = RetryConfig(
        max_attempts=3,
        initial_delay=2.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
    )
    av_client = AlphaVantageClient(config=config, retry_config=retry)
    yield av_client
    av_client.close()


# ===========================================================================
# Test classes
# ===========================================================================


class TestGetDaily:
    """Integration tests for ``get_daily`` (TIME_SERIES_DAILY)."""

    @pytest.mark.skipif(not _has_api_key(), reason="No ALPHA_VANTAGE_API_KEY")
    def test_正常系_日足データのDataFrame形状とカラム(
        self,
        client: AlphaVantageClient,
    ) -> None:
        """Verify that get_daily returns a DataFrame with expected structure.

        Checks:
        - Return type is pd.DataFrame
        - At least 1 row of data
        - Required OHLCV columns are present
        - Numeric columns contain float values
        """
        df = client.get_daily(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=False),
        )

        assert isinstance(df, pd.DataFrame), "Expected pd.DataFrame"
        assert len(df) > 0, "Expected at least 1 row of data"

        # Check required columns
        expected_columns = {"date", "open", "high", "low", "close", "volume"}
        actual_columns = set(df.columns)
        assert expected_columns.issubset(actual_columns), (
            f"Missing columns: {expected_columns - actual_columns}"
        )

        # Check that date column contains parseable dates
        dates = pd.to_datetime(df["date"])
        assert len(dates) > 0, "Dates should be parseable as datetime"

        # Check that OHLCV columns contain numeric values
        for col in ["open", "high", "low", "close", "volume"]:
            assert df[col].dtype in (
                float,
                "float64",
            ), f"Column '{col}' should be float, got {df[col].dtype}"


class TestGetGlobalQuote:
    """Integration tests for ``get_global_quote`` (GLOBAL_QUOTE)."""

    @pytest.mark.skipif(not _has_api_key(), reason="No ALPHA_VANTAGE_API_KEY")
    def test_正常系_リアルタイムクオートのキーと型(
        self,
        client: AlphaVantageClient,
    ) -> None:
        """Verify that get_global_quote returns a dict with expected keys.

        Checks:
        - Return type is dict
        - Contains expected keys (symbol, price, volume, etc.)
        - Numeric fields are float (after parser normalization)
        """
        quote: dict[str, Any] = client.get_global_quote(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=False),
        )

        assert isinstance(quote, dict), "Expected dict"
        assert len(quote) > 0, "Expected non-empty dict"

        # After normalization, keys should not have number prefixes
        # Expected keys (without number prefix): symbol, open, high, low,
        # price, volume, latest trading day, previous close, change,
        # change percent
        expected_keys = {"symbol", "price", "volume"}
        actual_keys = set(quote.keys())
        assert expected_keys.issubset(actual_keys), (
            f"Missing keys: {expected_keys - actual_keys}"
        )

        # Price should be a numeric value
        price = quote.get("price")
        assert isinstance(price, (int, float)), (
            f"Expected numeric price, got {type(price)}"
        )
        assert price > 0, f"Expected positive price, got {price}"


class TestGetCompanyOverview:
    """Integration tests for ``get_company_overview`` (OVERVIEW)."""

    @pytest.mark.skipif(not _has_api_key(), reason="No ALPHA_VANTAGE_API_KEY")
    def test_正常系_企業概要のキーと型(
        self,
        client: AlphaVantageClient,
    ) -> None:
        """Verify that get_company_overview returns expected company data.

        Checks:
        - Return type is dict
        - Contains expected keys (Symbol, Name, Sector, etc.)
        - Numeric fields (MarketCapitalization, PERatio, EPS) are float
        """
        overview: dict[str, Any] = client.get_company_overview(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=False),
        )

        assert isinstance(overview, dict), "Expected dict"
        assert len(overview) > 0, "Expected non-empty dict"

        # Check required string keys
        expected_string_keys = {"Symbol", "Name", "Exchange", "Sector"}
        actual_keys = set(overview.keys())
        assert expected_string_keys.issubset(actual_keys), (
            f"Missing keys: {expected_string_keys - actual_keys}"
        )

        # Symbol should match the requested symbol
        assert overview["Symbol"] == _TEST_SYMBOL

        # Check that numeric fields are converted to float by the parser
        for numeric_key in ("MarketCapitalization", "PERatio", "EPS"):
            if numeric_key in overview:
                value = overview[numeric_key]
                assert isinstance(value, (int, float)), (
                    f"Expected numeric {numeric_key}, got {type(value)}: {value}"
                )


class TestRateLimiterIntegration:
    """Integration tests for rate limiter behaviour during live API calls."""

    @pytest.mark.skipif(not _has_api_key(), reason="No ALPHA_VANTAGE_API_KEY")
    def test_正常系_レートリミッター統合動作(
        self,
        client: AlphaVantageClient,
    ) -> None:
        """Verify that the rate limiter does not cause request failures.

        Makes two sequential API calls and verifies both succeed without
        rate-limit errors.  The polite delay and rate limiter should keep
        us well within the 25 req/min limit.
        """
        # First call
        df1 = client.get_daily(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=False),
        )
        assert isinstance(df1, pd.DataFrame)
        assert len(df1) > 0

        # Second call (different endpoint to avoid identical cache keys)
        quote = client.get_global_quote(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=False),
        )
        assert isinstance(quote, dict)
        assert len(quote) > 0


class TestCacheIntegration:
    """Integration tests for cache hit/miss behaviour with real API data."""

    @pytest.mark.skipif(not _has_api_key(), reason="No ALPHA_VANTAGE_API_KEY")
    def test_正常系_キャッシュヒットで2回目は高速(
        self,
        client: AlphaVantageClient,
    ) -> None:
        """Verify that the second call hits cache and is faster.

        Makes two calls to get_daily for the same symbol.  The first call
        populates the cache; the second call should hit cache and return
        significantly faster (no network round-trip).
        """
        # First call: cache miss (fetches from API)
        start_first = time.monotonic()
        df1 = client.get_daily(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=True, force_refresh=True),
        )
        elapsed_first = time.monotonic() - start_first

        assert isinstance(df1, pd.DataFrame)
        assert len(df1) > 0

        # Second call: cache hit (should be much faster)
        start_second = time.monotonic()
        df2 = client.get_daily(
            _TEST_SYMBOL,
            options=FetchOptions(use_cache=True, force_refresh=False),
        )
        elapsed_second = time.monotonic() - start_second

        assert isinstance(df2, pd.DataFrame)
        assert len(df2) > 0

        # Cache hit should be fast (no API round-trip)
        # AIDEV-NOTE: Use absolute upper bound instead of relative speed comparison
        # to avoid flaky tests when first call is cached by external layers.
        assert elapsed_second < 0.5, (
            f"Cache hit should complete within 0.5s, took {elapsed_second:.3f}s"
        )
