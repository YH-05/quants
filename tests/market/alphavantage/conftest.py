"""Pytest configuration and shared fixtures for market.alphavantage test suite.

This module provides reusable fixtures for testing the Alpha Vantage API
module, including zero-delay configurations, mock HTTP responses, mock
sessions, and complete Alpha Vantage API JSON response mocks.  These
fixtures are designed to be shared across all test directories
(unit, property, integration).

Fixtures
--------
sample_alphavantage_config : AlphaVantageConfig
    Test-friendly AlphaVantageConfig with zero delays and minimal timeout.
sample_retry_config : RetryConfig
    Test-friendly RetryConfig with single attempt and no jitter.
sample_time_series_response : dict[str, object]
    Alpha Vantage TIME_SERIES_DAILY JSON response mock with 5 data points.
sample_global_quote_response : dict[str, object]
    Alpha Vantage GLOBAL_QUOTE JSON response mock.
sample_overview_response : dict[str, object]
    Alpha Vantage OVERVIEW (company fundamentals) JSON response mock.
sample_earnings_response : dict[str, object]
    Alpha Vantage EARNINGS JSON response mock with quarterly/annual data.
sample_economic_indicator_response : dict[str, object]
    Alpha Vantage REAL_GDP JSON response mock with 4 data points.
mock_alphavantage_session : MagicMock
    MagicMock simulating an Alpha Vantage session with pre-configured
    get/get_with_retry methods.

See Also
--------
tests.market.conftest : Parent-level market package fixtures.
market.alphavantage.types : AlphaVantageConfig and RetryConfig definitions.
tests.market.nasdaq.conftest : Similar fixture pattern for the NASDAQ module.
"""

from unittest.mock import MagicMock

import pytest

from market.alphavantage.types import AlphaVantageConfig, RetryConfig

# =============================================================================
# Configuration fixtures
# =============================================================================


@pytest.fixture
def sample_alphavantage_config() -> AlphaVantageConfig:
    """Create a test-friendly AlphaVantageConfig with zero delays.

    All delay-related parameters are set to zero to avoid slow tests.
    Timeout is set to 5.0 seconds for fast failure in test environments.

    Returns
    -------
    AlphaVantageConfig
        An AlphaVantageConfig with api_key="test-key",
        polite_delay=0.0, delay_jitter=0.0, and timeout=5.0.
    """
    return AlphaVantageConfig(
        api_key="test-key",
        polite_delay=0.0,
        delay_jitter=0.0,
        timeout=5.0,
        requests_per_minute=25,
        requests_per_hour=500,
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
def sample_time_series_response() -> dict[str, object]:
    """Create an Alpha Vantage TIME_SERIES_DAILY JSON response mock.

    Simulates the response from the Alpha Vantage API with
    ``function=TIME_SERIES_DAILY``, containing 5 daily data points
    for the AAPL ticker.

    Returns
    -------
    dict[str, object]
        A dictionary matching the Alpha Vantage time series response
        structure with metadata and 5 daily OHLCV data points.
    """
    return {
        "Meta Data": {
            "1. Information": "Daily Prices (open, high, low, close) and Volumes",
            "2. Symbol": "AAPL",
            "3. Last Refreshed": "2026-03-21",
            "4. Output Size": "Compact",
            "5. Time Zone": "US/Eastern",
        },
        "Time Series (Daily)": {
            "2026-03-21": {
                "1. open": "228.5000",
                "2. high": "232.1000",
                "3. low": "227.0000",
                "4. close": "230.5000",
                "5. volume": "45123456",
            },
            "2026-03-20": {
                "1. open": "225.0000",
                "2. high": "229.5000",
                "3. low": "224.5000",
                "4. close": "228.0000",
                "5. volume": "38765432",
            },
            "2026-03-19": {
                "1. open": "222.0000",
                "2. high": "226.0000",
                "3. low": "221.5000",
                "4. close": "225.5000",
                "5. volume": "42345678",
            },
            "2026-03-18": {
                "1. open": "220.0000",
                "2. high": "223.5000",
                "3. low": "219.0000",
                "4. close": "222.0000",
                "5. volume": "35678901",
            },
            "2026-03-17": {
                "1. open": "218.5000",
                "2. high": "221.0000",
                "3. low": "217.5000",
                "4. close": "220.0000",
                "5. volume": "31234567",
            },
        },
    }


@pytest.fixture
def sample_global_quote_response() -> dict[str, object]:
    """Create an Alpha Vantage GLOBAL_QUOTE JSON response mock.

    Simulates the response from the Alpha Vantage API with
    ``function=GLOBAL_QUOTE`` for the AAPL ticker.

    Returns
    -------
    dict[str, object]
        A dictionary matching the Alpha Vantage global quote structure.
    """
    return {
        "Global Quote": {
            "01. symbol": "AAPL",
            "02. open": "228.5000",
            "03. high": "232.1000",
            "04. low": "227.0000",
            "05. price": "230.5000",
            "06. volume": "45123456",
            "07. latest trading day": "2026-03-21",
            "08. previous close": "228.0000",
            "09. change": "2.5000",
            "10. change percent": "1.0965%",
        },
    }


@pytest.fixture
def sample_overview_response() -> dict[str, object]:
    """Create an Alpha Vantage OVERVIEW JSON response mock.

    Simulates the response from the Alpha Vantage API with
    ``function=OVERVIEW`` for the AAPL ticker.

    Returns
    -------
    dict[str, object]
        A dictionary matching the Alpha Vantage company overview structure.
    """
    return {
        "Symbol": "AAPL",
        "AssetType": "Common Stock",
        "Name": "Apple Inc",
        "Description": "Apple Inc. designs, manufactures, and markets smartphones...",
        "CIK": "320193",
        "Exchange": "NASDAQ",
        "Currency": "USD",
        "Country": "USA",
        "Sector": "TECHNOLOGY",
        "Industry": "ELECTRONIC COMPUTERS",
        "MarketCapitalization": "3435123456789",
        "EBITDA": "130541000000",
        "PERatio": "33.5",
        "PEGRatio": "2.1",
        "BookValue": "4.38",
        "DividendPerShare": "1.00",
        "DividendYield": "0.0043",
        "EPS": "6.88",
        "52WeekHigh": "260.10",
        "52WeekLow": "164.08",
    }


@pytest.fixture
def sample_earnings_response() -> dict[str, object]:
    """Create an Alpha Vantage EARNINGS JSON response mock.

    Simulates the response from the Alpha Vantage API with
    ``function=EARNINGS`` for the AAPL ticker, containing both
    annual and quarterly earnings data.

    Returns
    -------
    dict[str, object]
        A dictionary matching the Alpha Vantage earnings structure
        with 2 annual and 2 quarterly entries.
    """
    return {
        "symbol": "AAPL",
        "annualEarnings": [
            {
                "fiscalDateEnding": "2025-09-30",
                "reportedEPS": "6.88",
            },
            {
                "fiscalDateEnding": "2024-09-30",
                "reportedEPS": "6.57",
            },
        ],
        "quarterlyEarnings": [
            {
                "fiscalDateEnding": "2025-12-31",
                "reportedDate": "2026-01-30",
                "reportedEPS": "2.40",
                "estimatedEPS": "2.35",
                "surprise": "0.05",
                "surprisePercentage": "2.1277",
            },
            {
                "fiscalDateEnding": "2025-09-30",
                "reportedDate": "2025-10-30",
                "reportedEPS": "1.64",
                "estimatedEPS": "1.60",
                "surprise": "0.04",
                "surprisePercentage": "2.5000",
            },
        ],
    }


@pytest.fixture
def sample_economic_indicator_response() -> dict[str, object]:
    """Create an Alpha Vantage REAL_GDP JSON response mock.

    Simulates the response from the Alpha Vantage API with
    ``function=REAL_GDP`` containing 4 quarterly data points.

    Returns
    -------
    dict[str, object]
        A dictionary matching the Alpha Vantage economic indicator
        response structure.
    """
    return {
        "name": "Real Gross Domestic Product",
        "interval": "quarterly",
        "unit": "billions of dollars",
        "data": [
            {"date": "2025-10-01", "value": "23500.0"},
            {"date": "2025-07-01", "value": "23200.0"},
            {"date": "2025-04-01", "value": "22900.0"},
            {"date": "2025-01-01", "value": "22600.0"},
        ],
    }


# =============================================================================
# Mock object fixtures
# =============================================================================


@pytest.fixture
def mock_alphavantage_session(
    sample_alphavantage_config: AlphaVantageConfig,
    sample_retry_config: RetryConfig,
    sample_time_series_response: dict[str, object],
) -> MagicMock:
    """Create a MagicMock simulating an Alpha Vantage session instance.

    The mock session's get() and get_with_retry() methods return a mock
    response with the sample_time_series_response data by default.

    Parameters
    ----------
    sample_alphavantage_config : AlphaVantageConfig
        Zero-delay Alpha Vantage configuration.
    sample_retry_config : RetryConfig
        Single-attempt retry configuration.
    sample_time_series_response : dict[str, object]
        Mock time series API response data.

    Returns
    -------
    MagicMock
        A MagicMock mimicking an Alpha Vantage session with get/
        get_with_retry/close methods and context manager support.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_time_series_response
    mock_response.text = '{"Meta Data": {...}, "Time Series (Daily)": {...}}'
    mock_response.headers = {"Content-Type": "application/json"}

    session = MagicMock()
    session._config = sample_alphavantage_config
    session._retry_config = sample_retry_config
    session.get.return_value = mock_response
    session.get_with_retry.return_value = mock_response
    session.close.return_value = None
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session
