"""Pytest configuration and shared fixtures for market.nasdaq test suite.

This module provides reusable fixtures for testing the NASDAQ Stock Screener
module and the NasdaqClient, including zero-delay configurations, mock HTTP
responses, mock sessions, mock caches, and complete NASDAQ API JSON response
mocks.  These fixtures are designed to be shared across all test directories
(unit, property, integration).

Fixtures
--------
sample_nasdaq_config : NasdaqConfig
    Test-friendly NasdaqConfig with zero delays and minimal timeout.
sample_retry_config : RetryConfig
    Test-friendly RetryConfig with single attempt and no jitter.
mock_curl_response : MagicMock
    MagicMock simulating a successful curl_cffi Response with status_code=200
    and a NASDAQ Screener JSON body.
mock_nasdaq_session : MagicMock
    MagicMock simulating a NasdaqSession instance with pre-configured
    get/get_with_retry methods.
sample_screener_api_response : dict[str, object]
    Complete NASDAQ Screener API JSON response mock containing 5 stocks.
mock_cache : MagicMock
    MagicMock simulating a SQLiteCache instance for NasdaqClient tests.
nasdaq_client : NasdaqClient
    A NasdaqClient instance with injected mock session and mock cache.
sample_envelope_response : dict[str, object]
    Standard NASDAQ API envelope response with rCode=200.

See Also
--------
tests.market.conftest : Parent-level market package fixtures.
market.nasdaq.types : NasdaqConfig and RetryConfig definitions.
market.nasdaq.session : NasdaqSession class.
market.nasdaq.client : NasdaqClient class.
tests.market.etfcom.conftest : Similar fixture pattern for the ETF.com module.
"""

from unittest.mock import MagicMock

import pytest

from market.nasdaq.client import NasdaqClient
from market.nasdaq.types import NasdaqConfig, RetryConfig

# =============================================================================
# Configuration fixtures
# =============================================================================


@pytest.fixture
def sample_nasdaq_config() -> NasdaqConfig:
    """Create a test-friendly NasdaqConfig with zero delays.

    All delay-related parameters are set to zero to avoid slow tests.
    Timeout is set to 5.0 seconds for fast failure in test environments.

    Returns
    -------
    NasdaqConfig
        A NasdaqConfig with polite_delay=0.0, delay_jitter=0.0,
        and timeout=5.0.
    """
    return NasdaqConfig(
        polite_delay=0.0,
        delay_jitter=0.0,
        user_agents=("TestAgent/1.0",),
        impersonate="chrome",
        timeout=5.0,
    )


@pytest.fixture
def sample_retry_config() -> RetryConfig:
    """Create a test-friendly RetryConfig with single attempt and no jitter.

    Minimizes retry overhead in tests while still allowing retry logic testing.

    Returns
    -------
    RetryConfig
        A RetryConfig with max_attempts=1, initial_delay=0.0,
        max_delay=0.0, exponential_base=2.0, jitter=False.
    """
    return RetryConfig(
        max_attempts=1,
        initial_delay=0.0,
        max_delay=0.0,
        exponential_base=2.0,
        jitter=False,
    )


# =============================================================================
# API response fixtures
# =============================================================================


@pytest.fixture
def sample_screener_api_response() -> dict[str, object]:
    """Create a complete NASDAQ Screener API JSON response mock with 5 stocks.

    Simulates the response from the ``/api/screener/stocks`` endpoint
    containing a ``data.table.rows`` structure with 5 stock records
    spanning different sectors, exchanges, and market caps.

    The response structure matches the actual NASDAQ API::

        {
            "data": {
                "table": {
                    "rows": [{"symbol": "AAPL", ...}, ...]
                }
            }
        }

    Returns
    -------
    dict[str, object]
        A dictionary matching the NASDAQ Screener API response structure
        with 5 stock records (AAPL, MSFT, GOOGL, AMZN, NVDA).
    """
    return {
        "data": {
            "table": {
                "rows": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc. Common Stock",
                        "lastsale": "$227.63",
                        "netchange": "-1.95",
                        "pctchange": "-0.849%",
                        "marketCap": "3,435,123,456,789",
                        "country": "United States",
                        "ipoyear": "1980",
                        "volume": "48,123,456",
                        "sector": "Technology",
                        "industry": "Computer Manufacturing",
                        "url": "/market-activity/stocks/aapl",
                    },
                    {
                        "symbol": "MSFT",
                        "name": "Microsoft Corporation Common Stock",
                        "lastsale": "$415.50",
                        "netchange": "2.30",
                        "pctchange": "0.557%",
                        "marketCap": "3,100,000,000,000",
                        "country": "United States",
                        "ipoyear": "1986",
                        "volume": "22,456,789",
                        "sector": "Technology",
                        "industry": "Computer Software: Prepackaged Software",
                        "url": "/market-activity/stocks/msft",
                    },
                    {
                        "symbol": "GOOGL",
                        "name": "Alphabet Inc. Class A Common Stock",
                        "lastsale": "$175.98",
                        "netchange": "0.85",
                        "pctchange": "0.486%",
                        "marketCap": "2,170,000,000,000",
                        "country": "United States",
                        "ipoyear": "2004",
                        "volume": "18,234,567",
                        "sector": "Technology",
                        "industry": "Computer Software: Programming, Data Processing",
                        "url": "/market-activity/stocks/googl",
                    },
                    {
                        "symbol": "AMZN",
                        "name": "Amazon.com, Inc. Common Stock",
                        "lastsale": "$186.42",
                        "netchange": "-0.73",
                        "pctchange": "-0.390%",
                        "marketCap": "1,950,000,000,000",
                        "country": "United States",
                        "ipoyear": "1997",
                        "volume": "35,678,901",
                        "sector": "Consumer Discretionary",
                        "industry": "Catalog/Specialty Distribution",
                        "url": "/market-activity/stocks/amzn",
                    },
                    {
                        "symbol": "NVDA",
                        "name": "NVIDIA Corporation Common Stock",
                        "lastsale": "$140.15",
                        "netchange": "3.42",
                        "pctchange": "2.502%",
                        "marketCap": "3,450,000,000,000",
                        "country": "United States",
                        "ipoyear": "1999",
                        "volume": "312,456,789",
                        "sector": "Technology",
                        "industry": "Semiconductors",
                        "url": "/market-activity/stocks/nvda",
                    },
                ],
            },
        },
    }


# =============================================================================
# Mock object fixtures
# =============================================================================


@pytest.fixture
def mock_curl_response(
    sample_screener_api_response: dict[str, object],
) -> MagicMock:
    """Create a MagicMock simulating a successful curl_cffi Response.

    The mock response has status_code=200 and a json() method that
    returns the ``sample_screener_api_response`` fixture data.

    Parameters
    ----------
    sample_screener_api_response : dict[str, object]
        Complete NASDAQ Screener API JSON response.

    Returns
    -------
    MagicMock
        A MagicMock with status_code=200, json(), text, and content
        attributes simulating a successful NASDAQ API response.
    """
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = sample_screener_api_response
    response.text = '{"data":{"table":{"rows":[...]}}}'
    response.content = b'{"data":{"table":{"rows":[...]}}}'
    response.headers = {"Content-Type": "application/json; charset=utf-8"}
    return response


@pytest.fixture
def mock_nasdaq_session(
    sample_nasdaq_config: NasdaqConfig,
    sample_retry_config: RetryConfig,
    mock_curl_response: MagicMock,
) -> MagicMock:
    """Create a MagicMock simulating a NasdaqSession instance.

    The mock session's get() and get_with_retry() methods return
    the mock_curl_response fixture by default.

    Parameters
    ----------
    sample_nasdaq_config : NasdaqConfig
        Zero-delay NASDAQ configuration.
    sample_retry_config : RetryConfig
        Single-attempt retry configuration.
    mock_curl_response : MagicMock
        Mock HTTP response with NASDAQ API JSON data.

    Returns
    -------
    MagicMock
        A MagicMock mimicking NasdaqSession with get/get_with_retry/
        rotate_session/close methods and context manager support.
    """
    session = MagicMock()
    session._config = sample_nasdaq_config
    session._retry_config = sample_retry_config
    session.get.return_value = mock_curl_response
    session.get_with_retry.return_value = mock_curl_response
    session.rotate_session.return_value = None
    session.close.return_value = None
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


# =============================================================================
# NasdaqClient fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a MagicMock simulating a SQLiteCache instance.

    The mock cache's get() method returns None by default (cache miss),
    and set() does nothing.

    Returns
    -------
    MagicMock
        A MagicMock mimicking SQLiteCache with get/set/delete/close methods.
    """
    cache = MagicMock()
    cache.get.return_value = None
    cache.set.return_value = None
    cache.delete.return_value = True
    cache.close.return_value = None
    return cache


@pytest.fixture
def nasdaq_client(
    mock_nasdaq_session: MagicMock,
    mock_cache: MagicMock,
) -> NasdaqClient:
    """Create a NasdaqClient with injected mock session and mock cache.

    The client's ``_owns_session`` is set to ``False`` to prevent
    closing the mock session on ``close()``.

    Parameters
    ----------
    mock_nasdaq_session : MagicMock
        Mock NasdaqSession instance.
    mock_cache : MagicMock
        Mock SQLiteCache instance.

    Returns
    -------
    NasdaqClient
        A NasdaqClient configured for testing.
    """
    client = NasdaqClient(session=mock_nasdaq_session, cache=mock_cache)
    return client


@pytest.fixture
def sample_envelope_response() -> dict[str, object]:
    """Create a standard NASDAQ API envelope response with rCode=200.

    Simulates the standard NASDAQ API JSON envelope structure::

        {
            "data": { "symbol": "AAPL", "summaryData": {...} },
            "message": null,
            "status": { "rCode": 200, "bCodeMessage": null }
        }

    Returns
    -------
    dict[str, object]
        A dictionary matching the NASDAQ API envelope structure.
    """
    return {
        "data": {
            "symbol": "AAPL",
            "summaryData": {
                "Exchange": {"label": "Exchange", "value": "NASDAQ-GS"},
                "Sector": {"label": "Sector", "value": "Technology"},
                "Industry": {"label": "Industry", "value": "Computer Manufacturing"},
                "OneYrTarget": {"label": "1 Year Target", "value": "$250.00"},
                "TodayHighLow": {
                    "label": "Today's High/Low",
                    "value": "$230.00/$225.00",
                },
                "ShareVolume": {
                    "label": "Share Volume",
                    "value": "48,123,456",
                },
                "MarketCap": {
                    "label": "Market Cap",
                    "value": "3,435,123,456,789",
                },
            },
        },
        "message": None,
        "status": {
            "rCode": 200,
            "bCodeMessage": None,
            "developerMessage": None,
        },
    }
