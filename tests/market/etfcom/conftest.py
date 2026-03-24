"""Pytest configuration and shared fixtures for market.etfcom test suite.

This module provides reusable fixtures for testing the ETF.com API-based
module, including zero-delay configurations, mock sessions with authentication
support, mock clients, mock storage, and sample REST API response data.
These fixtures are designed to be shared across all test files
(unit, property, integration).

Fixtures
--------
zero_delay_config : ScrapingConfig
    Test-friendly ScrapingConfig with zero delays (alias for
    ``sample_scraping_config``).
sample_scraping_config : ScrapingConfig
    Test-friendly ScrapingConfig with zero delays.
sample_retry_config : RetryConfig
    Test-friendly RetryConfig with single retry and minimal delay.
mock_curl_response : MagicMock
    MagicMock simulating a curl_cffi Response with status_code=200.
mock_session : MagicMock
    MagicMock simulating an authenticated ETFComSession instance.
mock_client : MagicMock
    MagicMock simulating an ETFComClient with all 22 public methods.
mock_storage : MagicMock
    MagicMock simulating an ETFComStorage with all upsert/get methods.
sample_tickers_response : list[dict[str, object]]
    Mock ``/v2/fund/tickers`` GET endpoint response (3 ETFs).
sample_delayed_quotes_response : dict[str, object]
    Mock ``/v2/quotes/delayedquotes`` GET endpoint response.
sample_fund_details_response : dict[str, dict[str, object]]
    Mock responses for all 18 ``/v2/fund/fund-details`` POST query names.
sample_api_error_response : dict[str, object]
    Mock API error response JSON.
tmp_cache_dir : Path
    Temporary directory for ticker cache file storage.

See Also
--------
tests.market.conftest : Parent-level market package fixtures.
market.etfcom.types : ScrapingConfig and RetryConfig definitions.
market.etfcom.session : ETFComSession class.
market.etfcom.client : ETFComClient class.
market.etfcom.storage : ETFComStorage class.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from market.etfcom.types import RetryConfig, ScrapingConfig

# =============================================================================
# Configuration fixtures
# =============================================================================


@pytest.fixture
def sample_scraping_config() -> ScrapingConfig:
    """Create a test-friendly ScrapingConfig with zero delays.

    All delay-related parameters are set to zero to avoid slow tests.
    headless is True (default) for CI compatibility.

    Returns
    -------
    ScrapingConfig
        A ScrapingConfig with zero polite_delay, zero delay_jitter,
        zero stability_wait, and minimal timeout.
    """
    return ScrapingConfig(
        polite_delay=0.0,
        delay_jitter=0.0,
        user_agents=("TestAgent/1.0",),
        impersonate="chrome",
        timeout=5.0,
        headless=True,
        stability_wait=0.0,
        max_page_retries=1,
    )


@pytest.fixture
def zero_delay_config(sample_scraping_config: ScrapingConfig) -> ScrapingConfig:
    """Alias for ``sample_scraping_config`` with zero delays.

    Provides a more descriptive name for tests focused on
    ensuring zero polite delay and jitter in test environments.

    Parameters
    ----------
    sample_scraping_config : ScrapingConfig
        Zero-delay scraping configuration.

    Returns
    -------
    ScrapingConfig
        A ScrapingConfig with zero polite_delay and zero delay_jitter.
    """
    return sample_scraping_config


@pytest.fixture
def sample_retry_config() -> RetryConfig:
    """Create a test-friendly RetryConfig with single retry and minimal delay.

    Minimizes retry overhead in tests while still testing retry logic.

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
# Mock object fixtures
# =============================================================================


@pytest.fixture
def mock_curl_response() -> MagicMock:
    """Create a MagicMock simulating a successful curl_cffi Response.

    The mock response has status_code=200 and a JSON body containing
    an empty dict (suitable for API responses).

    Returns
    -------
    MagicMock
        A MagicMock with status_code=200, json(), text, and content.
    """
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {}
    response.text = "{}"
    response.content = b"{}"
    response.headers = {"Content-Type": "application/json; charset=utf-8"}
    return response


@pytest.fixture
def mock_session(
    sample_scraping_config: ScrapingConfig,
    sample_retry_config: RetryConfig,
    mock_curl_response: MagicMock,
) -> MagicMock:
    """Create a MagicMock simulating an authenticated ETFComSession.

    The mock session includes all public methods from ``ETFComSession``:
    ``get()``, ``post()``, ``get_with_retry()``, ``post_with_retry()``,
    ``post_fund_details()``, ``get_authenticated()``,
    ``rotate_session()``, and ``close()``.

    By default, all request methods return ``mock_curl_response``.

    Parameters
    ----------
    sample_scraping_config : ScrapingConfig
        Zero-delay scraping configuration.
    sample_retry_config : RetryConfig
        Single-retry configuration.
    mock_curl_response : MagicMock
        Mock HTTP response.

    Returns
    -------
    MagicMock
        A MagicMock mimicking an authenticated ETFComSession.
    """
    session = MagicMock()
    session._config = sample_scraping_config
    session._retry_config = sample_retry_config

    # GET/POST methods
    session.get.return_value = mock_curl_response
    session.get_with_retry.return_value = mock_curl_response
    session.post.return_value = mock_curl_response
    session.post_with_retry.return_value = mock_curl_response

    # Authenticated methods
    session.post_fund_details.return_value = mock_curl_response
    session.get_authenticated.return_value = mock_curl_response

    # Session management
    session.rotate_session.return_value = None
    session.close.return_value = None

    # Context manager support
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    return session


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a MagicMock simulating an ETFComClient.

    The mock client includes all 22 public methods grouped by category:

    **18 POST fund-details methods** (return empty list or dict):
        ``get_fund_flows``, ``get_holdings``, ``get_portfolio_data``,
        ``get_sector_breakdown``, ``get_regions``, ``get_countries``,
        ``get_econ_dev``, ``get_intra_data``, ``get_compare_ticker``,
        ``get_spread_chart``, ``get_premium_chart``, ``get_tradability``,
        ``get_tradability_summary``, ``get_portfolio_management``,
        ``get_tax_exposures``, ``get_structure``, ``get_rankings``,
        ``get_performance_stats``.

    **4 GET methods** (return empty list or dict):
        ``get_tickers``, ``get_delayed_quotes``, ``get_charts``,
        ``get_performance``.

    Returns
    -------
    MagicMock
        A MagicMock mimicking ETFComClient with all 22 methods.
    """
    client = MagicMock()

    # 18 POST fund-details methods (list-returning)
    for method_name in (
        "get_fund_flows",
        "get_holdings",
        "get_sector_breakdown",
        "get_regions",
        "get_countries",
        "get_econ_dev",
        "get_intra_data",
        "get_compare_ticker",
        "get_spread_chart",
        "get_premium_chart",
        "get_tradability",
    ):
        getattr(client, method_name).return_value = []

    # POST fund-details methods (dict-returning)
    for method_name in (
        "get_portfolio_data",
        "get_tradability_summary",
        "get_portfolio_management",
        "get_tax_exposures",
        "get_structure",
        "get_rankings",
        "get_performance_stats",
    ):
        getattr(client, method_name).return_value = {}

    # 4 GET methods
    client.get_tickers.return_value = []
    client.get_delayed_quotes.return_value = []
    client.get_charts.return_value = []
    client.get_performance.return_value = {}

    # Context manager support
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.close.return_value = None

    return client


@pytest.fixture
def mock_storage(tmp_path: Path) -> MagicMock:
    """Create a MagicMock simulating an ETFComStorage.

    The mock storage includes all upsert methods (returning row counts)
    and get methods (returning empty DataFrames).

    Parameters
    ----------
    tmp_path : Path
        Pytest-provided temporary directory.

    Returns
    -------
    MagicMock
        A MagicMock mimicking ETFComStorage with all upsert/get methods.
    """
    import pandas as pd

    storage = MagicMock()

    # Upsert methods return row count
    for method_name in (
        "upsert_tickers",
        "upsert_fund_flows",
        "upsert_holdings",
        "upsert_portfolio",
        "upsert_allocations",
        "upsert_tradability",
        "upsert_structure",
        "upsert_performance",
        "upsert_quotes",
    ):
        getattr(storage, method_name).return_value = 0

    # Get methods return empty DataFrames
    for method_name in (
        "get_tickers",
        "get_fund_flows",
        "get_holdings",
        "get_portfolio",
        "get_allocations",
        "get_tradability",
        "get_structure",
        "get_performance",
        "get_quotes",
    ):
        getattr(storage, method_name).return_value = pd.DataFrame()

    # Utility methods
    storage.ensure_tables.return_value = None
    storage.get_table_names.return_value = [
        "etfcom_allocations",
        "etfcom_fund_flows",
        "etfcom_holdings",
        "etfcom_performance",
        "etfcom_portfolio",
        "etfcom_quotes",
        "etfcom_structure",
        "etfcom_tickers",
        "etfcom_tradability",
    ]
    storage.get_row_count.return_value = 0
    storage.get_stats.return_value = {
        "etfcom_allocations": 0,
        "etfcom_fund_flows": 0,
        "etfcom_holdings": 0,
        "etfcom_performance": 0,
        "etfcom_portfolio": 0,
        "etfcom_quotes": 0,
        "etfcom_structure": 0,
        "etfcom_tickers": 0,
        "etfcom_tradability": 0,
    }

    return storage


# =============================================================================
# REST API response fixtures
# =============================================================================


@pytest.fixture
def sample_tickers_response() -> list[dict[str, Any]]:
    """Create a mock ``/v2/fund/tickers`` GET endpoint response.

    Simulates the JSON array returned by the authenticated tickers
    endpoint, containing 3 ETFs (SPY, VOO, QQQ) with realistic data.

    Returns
    -------
    list[dict[str, Any]]
        A list of ticker dictionaries with camelCase keys.
    """
    return [
        {
            "fundId": 1,
            "ticker": "SPY",
            "fundName": "SPDR S&P 500 ETF Trust",
            "issuer": "State Street",
            "assetClass": "Equity",
            "inceptionDate": "1993-01-22",
        },
        {
            "fundId": 2,
            "ticker": "VOO",
            "fundName": "Vanguard S&P 500 ETF",
            "issuer": "Vanguard",
            "assetClass": "Equity",
            "inceptionDate": "2010-09-07",
        },
        {
            "fundId": 3,
            "ticker": "QQQ",
            "fundName": "Invesco QQQ Trust",
            "issuer": "Invesco",
            "assetClass": "Equity",
            "inceptionDate": "1999-03-10",
        },
    ]


@pytest.fixture
def sample_delayed_quotes_response() -> dict[str, Any]:
    """Create a mock ``/v2/quotes/delayedquotes`` GET endpoint response.

    Simulates the JSON response for delayed quotes of SPY and QQQ
    with realistic OHLC and bid/ask data.

    Returns
    -------
    dict[str, Any]
        A dictionary containing a ``data`` key with quote records.
    """
    return {
        "data": [
            {
                "ticker": "SPY",
                "quoteDate": "2026-03-21T00:00:00.000Z",
                "open": 578.50,
                "high": 582.10,
                "low": 577.30,
                "close": 580.25,
                "volume": 75000000.0,
                "bid": 580.20,
                "ask": 580.30,
                "bidSize": 500.0,
                "askSize": 300.0,
            },
            {
                "ticker": "QQQ",
                "quoteDate": "2026-03-21T00:00:00.000Z",
                "open": 485.00,
                "high": 490.50,
                "low": 483.20,
                "close": 488.75,
                "volume": 42000000.0,
                "bid": 488.70,
                "ask": 488.80,
                "bidSize": 200.0,
                "askSize": 150.0,
            },
        ],
    }


@pytest.fixture
def sample_fund_details_response() -> dict[str, dict[str, Any]]:
    """Create mock responses for all 18 ``/v2/fund/fund-details`` POST queries.

    Returns a dictionary keyed by query name, where each value is the
    full JSON response body in the ``{"data": {queryName: {"data": ...}}}``
    nesting format used by the ETF.com fund-details endpoint.

    This fixture provides realistic sample data for all 18 fund-details
    query names defined in ``FUND_DETAILS_QUERY_NAMES``.

    Returns
    -------
    dict[str, dict[str, Any]]
        A dictionary mapping query name to its full mock API response.
    """
    return {
        "fundFlowsData": {
            "data": {
                "fundFlowsData": {
                    "data": [
                        {
                            "navDate": "2026-03-21T00:00:00.000Z",
                            "nav": 580.25,
                            "navChange": 2.15,
                            "navChangePercent": 0.48,
                            "premiumDiscount": -0.02,
                            "fundFlows": 2787590000.0,
                            "sharesOutstanding": 920000000.0,
                            "aum": 414230000000.0,
                        },
                        {
                            "navDate": "2026-03-20T00:00:00.000Z",
                            "nav": 578.10,
                            "navChange": -1.30,
                            "navChangePercent": -0.29,
                            "premiumDiscount": 0.01,
                            "fundFlows": -1234560000.0,
                            "sharesOutstanding": 919500000.0,
                            "aum": 411950000000.0,
                        },
                    ],
                },
            },
        },
        "topHoldings": {
            "data": {
                "topHoldings": {
                    "data": [
                        {
                            "holdingTicker": "AAPL",
                            "holdingName": "Apple Inc.",
                            "weight": 0.072,
                            "marketValue": 29880000000.0,
                            "shares": 175000000,
                            "asOfDate": "2026-03-15T00:00:00.000Z",
                        },
                        {
                            "holdingTicker": "MSFT",
                            "holdingName": "Microsoft Corporation",
                            "weight": 0.065,
                            "marketValue": 26975000000.0,
                            "shares": 65000000,
                            "asOfDate": "2026-03-15T00:00:00.000Z",
                        },
                    ],
                },
            },
        },
        "fundPortfolioData": {
            "data": {
                "fundPortfolioData": {
                    "data": {
                        "peRatio": 22.5,
                        "pbRatio": 4.1,
                        "dividendYield": 0.013,
                        "weightedAvgMarketCap": 850000000000.0,
                        "numberOfHoldings": 503,
                        "expenseRatio": 0.0945,
                        "trackingDifference": -0.05,
                        "medianTrackingDifference": -0.04,
                        "asOfDate": "2026-03-15T00:00:00.000Z",
                    },
                },
            },
        },
        "sectorIndustryBreakdown": {
            "data": {
                "sectorIndustryBreakdown": {
                    "data": [
                        {
                            "name": "Technology",
                            "weight": 0.32,
                            "marketValue": 132736000000.0,
                            "count": 75,
                            "asOfDate": "2026-03-15T00:00:00.000Z",
                        },
                        {
                            "name": "Healthcare",
                            "weight": 0.13,
                            "marketValue": 53850000000.0,
                            "count": 65,
                            "asOfDate": "2026-03-15T00:00:00.000Z",
                        },
                    ],
                },
            },
        },
        "regions": {
            "data": {
                "regions": {
                    "data": [
                        {
                            "name": "North America",
                            "weight": 0.99,
                            "asOfDate": "2026-03-01T00:00:00.000Z",
                        },
                    ],
                },
            },
        },
        "countries": {
            "data": {
                "countries": {
                    "data": [
                        {
                            "name": "United States",
                            "weight": 0.99,
                            "asOfDate": "2026-03-01T00:00:00.000Z",
                        },
                    ],
                },
            },
        },
        "economicDevelopment": {
            "data": {
                "economicDevelopment": {
                    "data": [
                        {
                            "name": "Developed",
                            "weight": 1.0,
                            "asOfDate": "2026-03-01T00:00:00.000Z",
                        },
                    ],
                },
            },
        },
        "fundIntraData": {
            "data": {
                "fundIntraData": {
                    "data": [
                        {
                            "timestamp": "2026-03-21T14:30:00.000Z",
                            "price": 580.25,
                            "volume": 1200000,
                        },
                    ],
                },
            },
        },
        "compareTicker": {
            "data": {
                "compareTicker": {
                    "data": [
                        {
                            "ticker": "VOO",
                            "fundName": "Vanguard S&P 500 ETF",
                            "expenseRatio": 0.03,
                            "aum": 751490000000.0,
                        },
                    ],
                },
            },
        },
        "fundSpreadChart": {
            "data": {
                "fundSpreadChart": {
                    "data": [
                        {
                            "date": "2026-03-21T00:00:00.000Z",
                            "medianSpread": 0.0001,
                        },
                    ],
                },
            },
        },
        "fundPremiumChart": {
            "data": {
                "fundPremiumChart": {
                    "data": [
                        {
                            "date": "2026-03-21T00:00:00.000Z",
                            "premiumDiscount": -0.02,
                        },
                    ],
                },
            },
        },
        "fundTradabilityData": {
            "data": {
                "fundTradabilityData": {
                    "data": [
                        {
                            "date": "2026-03-21T00:00:00.000Z",
                            "avgDailyVolume": 75000000.0,
                            "avgDailyDollarVolume": 43500000000.0,
                            "medianBidAskSpread": 0.0001,
                        },
                    ],
                },
            },
        },
        "fundTradabilitySummary": {
            "data": {
                "fundTradabilitySummary": {
                    "data": {
                        "avgDailyVolume": 75000000.0,
                        "avgDailyDollarVolume": 43500000000.0,
                        "medianBidAskSpread": 0.0001,
                        "avgBidAskSpread": 0.00012,
                        "creationUnitSize": 50000,
                        "impliedLiquidity": 25000000000.0,
                    },
                },
            },
        },
        "fundPortfolioManData": {
            "data": {
                "fundPortfolioManData": {
                    "data": {
                        "expenseRatio": 0.0945,
                        "trackingDifference": -0.05,
                        "medianTrackingDifference": -0.04,
                    },
                },
            },
        },
        "fundTaxExposuresData": {
            "data": {
                "fundTaxExposuresData": {
                    "data": {
                        "taxForm": "1099",
                        "capitalGainsDistribution": 0.0,
                        "dividendDistribution": 6.32,
                    },
                },
            },
        },
        "fundStructureData": {
            "data": {
                "fundStructureData": {
                    "data": {
                        "legalStructure": "UIT",
                        "fundType": "Index",
                        "indexTracked": "S&P 500",
                        "replicationMethod": "Full Replication",
                        "usesDerivatives": False,
                        "securitiesLending": True,
                        "taxForm": "1099",
                    },
                },
            },
        },
        "fundRankingsData": {
            "data": {
                "fundRankingsData": {
                    "data": {
                        "overallRating": "A",
                        "efficiencyRating": "A",
                        "liquidityRating": "A",
                        "fitRating": "A",
                    },
                },
            },
        },
        "fundPerformanceStatsData": {
            "data": {
                "fundPerformanceStatsData": {
                    "data": {
                        "rSquared": 0.9998,
                        "beta": 1.0,
                        "standardDeviation": 0.15,
                        "returnYTD": 0.125,
                        "return1Y": 0.265,
                        "return3Y": 0.098,
                        "return5Y": 0.112,
                        "return10Y": 0.128,
                    },
                },
            },
        },
    }


@pytest.fixture
def sample_api_error_response() -> dict[str, object]:
    """Create a mock API error response JSON.

    Simulates a typical error response from the ETF.com REST API.

    Returns
    -------
    dict[str, object]
        A dictionary with error information.
    """
    return {
        "error": "Forbidden",
        "message": "Access denied",
        "statusCode": 403,
    }


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for ticker cache file storage.

    Uses pytest's ``tmp_path`` fixture to provide an isolated directory
    for file cache tests.

    Parameters
    ----------
    tmp_path : Path
        Pytest-provided temporary directory.

    Returns
    -------
    Path
        A temporary directory path for cache file testing.
    """
    return tmp_path
