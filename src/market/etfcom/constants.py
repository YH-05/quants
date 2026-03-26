"""Constants for ETF.com API client module.

This module defines all constants used by the ETF.com API client,
including bot-blocking countermeasure settings, REST API endpoints,
authentication settings, and query definitions.

Constants are organized into the following categories:

1. Bot-blocking countermeasures (User-Agent rotation, TLS fingerprint
   impersonation targets, polite delays)
2. Base URL constants (website and API base URLs)
3. REST API endpoint URLs (authentication, fund details, quotes, etc.)
4. API query definitions (fund-details POST query names)
5. HTTP headers and configuration
6. Default settings (cache, concurrency, retries)

Notes
-----
All constants use ``typing.Final`` type annotations to prevent reassignment.
The ``__all__`` list exports all public constants for use by other modules.

The User-Agent strings and browser impersonation targets are based on
real browser configurations to avoid bot detection by ETF.com.

See Also
--------
market.alphavantage.constants : Similar constant pattern used by the Alpha Vantage module.
market.fred.constants : Similar constant pattern used by the FRED module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. Bot-blocking countermeasure constants
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENTS: Final[list[str]] = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
]
"""Default User-Agent strings for HTTP requests.

Contains 12 real browser User-Agent strings covering Chrome, Firefox,
Safari, and Edge on Windows, macOS, and Linux platforms.
Rotated randomly to avoid bot detection.
"""

BROWSER_IMPERSONATE_TARGETS: Final[list[str]] = [
    "chrome",
    "chrome110",
    "chrome120",
    "edge99",
    "safari15_3",
]
"""Browser impersonation targets for curl_cffi TLS fingerprint.

These mimic real browser TLS fingerprints to avoid bot detection.
Aligned with ``market.yfinance.fetcher.BROWSER_IMPERSONATE_TARGETS``.
"""

DEFAULT_POLITE_DELAY: Final[float] = 2.0
"""Default polite delay between requests in seconds.

A minimum wait time between consecutive requests to avoid
overloading the ETF.com server and triggering rate limiting.
"""

DEFAULT_DELAY_JITTER: Final[float] = 1.0
"""Random jitter added to the polite delay in seconds.

Adds randomness to request timing to appear more human-like.
The actual delay is ``DEFAULT_POLITE_DELAY + random(0, DEFAULT_DELAY_JITTER)``.
"""

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds.

Maximum time to wait for a response before raising a timeout error.
"""

DEFAULT_HEADERS: Final[dict[str, str]] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
"""Default HTTP headers for requests.

Mimics standard browser headers to avoid bot detection.
The User-Agent header is set separately via ``DEFAULT_USER_AGENTS``.
"""

# ---------------------------------------------------------------------------
# 2. Base URL constants
# ---------------------------------------------------------------------------

ETFCOM_BASE_URL: Final[str] = "https://www.etf.com"
"""Base URL for ETF.com website."""

ETFCOM_API_BASE_URL: Final[str] = "https://api-prod.etf.com"
"""Base URL for ETF.com REST API.

The internal production API endpoint used for programmatic data access.
Unlike the scraping-based ``ETFCOM_BASE_URL``, this targets the REST API
server directly.
"""

# ---------------------------------------------------------------------------
# 3. REST API endpoint URL constants
# ---------------------------------------------------------------------------

AUTH_DETAILS_URL: Final[str] = "https://www.etf.com/api/v1/api-details"
"""URL for the ETF.com authentication details endpoint.

Returns API keys (fundApiKey, toolsApiKey), OAuth token (24h TTL),
and additional API base URLs (realTimeApiUrl, graphQLApiUrl).
The OAuth token is required as a Bearer token for all /v2/ API requests.

The response contains::

    {
        "apiBaseUrl": "https://api-prod.etf.com",
        "fundApiKey": "...",
        "toolsApiKey": "...",
        "oauthToken": "...",
        "realTimeApiUrl": "https://real-time-prod.etf.com/graphql",
        "graphQLApiUrl": "https://data.etf.com"
    }
"""

FUND_DETAILS_URL: Final[str] = "https://api-prod.etf.com/v2/fund/fund-details"
"""URL for the ETF.com fund details POST API endpoint.

Accepts POST requests with a ticker and query names to return detailed
fund data. Supports 18 different query types via ``FUND_DETAILS_QUERY_NAMES``.

See Also
--------
FUND_DETAILS_QUERY_NAMES : List of available query names for this endpoint.
"""

DELAYED_QUOTES_URL: Final[str] = "https://api-prod.etf.com/v2/quotes/delayedquotes"
"""URL for the ETF.com delayed quotes GET API endpoint.

Returns delayed real-time quotes (OHLC, Bid/Ask) for specified tickers.
Use with query parameter ``?tickers=SPY`` or ``?tickers=SPY,QQQ``.
"""

CHARTS_URL: Final[str] = "https://api-prod.etf.com/v2/fund/charts"
"""URL for the ETF.com fund charts GET API endpoint.

Returns price chart data for specified tickers. Use with query parameters
``?dataPoint=splitPrice&interval=MAX&ticker=SPY``.
"""

PERFORMANCE_URL: Final[str] = "https://api-prod.etf.com/v2/fund/performance"
"""URL for the ETF.com fund performance GET API endpoint.

Returns performance returns (1M/3M/YTD/1Y/3Y/5Y) for a given fund.
Use with path parameter ``/{fund_id}``.
"""

TICKERS_URL: Final[str] = "https://api-prod.etf.com/v2/fund/tickers"
"""URL for the ETF.com tickers list GET API endpoint.

Returns a JSON array of all available ETF tickers (~5,100 ETFs) with
their fund IDs, names, inception dates, asset classes, and issuers.
Used to resolve ticker symbols to fund IDs required by other endpoints.

Replaces the deprecated ``/private/apps/fundflows/tickers`` endpoint.
"""

# ---------------------------------------------------------------------------
# 4. API query definitions
# ---------------------------------------------------------------------------

FUND_DETAILS_QUERY_NAMES: Final[list[str]] = [
    "fundFlowsData",
    "topHoldings",
    "fundPortfolioData",
    "sectorIndustryBreakdown",
    "regions",
    "countries",
    "economicDevelopment",
    "fundIntraData",
    "compareTicker",
    "fundSpreadChart",
    "fundPremiumChart",
    "fundTradabilityData",
    "fundTradabilitySummary",
    "fundPortfolioManData",
    "fundTaxExposuresData",
    "fundStructureData",
    "fundRankingsData",
    "fundPerformanceStatsData",
]
"""Available query names for the ``/v2/fund/fund-details`` POST endpoint.

Each query name corresponds to a different data category:

1. ``fundFlowsData`` - Daily NAV, fund flows, AUM, premium/discount (daily)
2. ``topHoldings`` - Top holdings with weights (weekly)
3. ``fundPortfolioData`` - P/E, P/B, dividend yield (weekly)
4. ``sectorIndustryBreakdown`` - Sector allocation (weekly)
5. ``regions`` - Regional allocation (monthly)
6. ``countries`` - Country allocation (monthly)
7. ``economicDevelopment`` - Economic development classification (monthly)
8. ``fundIntraData`` - Intraday price data (daily)
9. ``compareTicker`` - Competing ETF comparison (monthly)
10. ``fundSpreadChart`` - Spread chart data (weekly)
11. ``fundPremiumChart`` - Premium/discount chart data (weekly)
12. ``fundTradabilityData`` - Volume, spread, liquidity metrics (weekly)
13. ``fundTradabilitySummary`` - Creation unit, liquidity (monthly)
14. ``fundPortfolioManData`` - Expense ratio, tracking difference (monthly)
15. ``fundTaxExposuresData`` - Tax-related data (monthly)
16. ``fundStructureData`` - Legal structure, derivatives, securities lending (monthly)
17. ``fundRankingsData`` - ETF.com rankings (efficiency/liquidity/fit) (monthly)
18. ``fundPerformanceStatsData`` - Performance statistics, R-squared, grade (monthly)
"""

# ---------------------------------------------------------------------------
# 5. HTTP headers and authentication
# ---------------------------------------------------------------------------

API_HEADERS: Final[dict[str, str]] = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Origin": "https://www.etf.com",
    "Referer": "https://www.etf.com/",
}
"""HTTP headers for REST API requests.

These headers mimic a browser making an XHR/fetch request from the
ETF.com website. The ``Origin`` and ``Referer`` headers are required
to pass the API's CORS checks. ``Content-Type`` is set to JSON for
POST request payloads.
"""

AUTH_TOKEN_TTL_SECONDS: Final[int] = 82800
"""TTL (time-to-live) for the OAuth token in seconds (23 hours).

The OAuth token obtained from ``AUTH_DETAILS_URL`` is valid for 24 hours.
A 23-hour TTL (82,800 seconds) provides a 1-hour safety margin to avoid
using an expired token near the boundary.
"""

# ---------------------------------------------------------------------------
# 6. Default settings
# ---------------------------------------------------------------------------

DEFAULT_MAX_RETRIES: Final[int] = 3
"""Default maximum number of retry attempts for failed operations."""

DEFAULT_TICKER_CACHE_TTL_HOURS: Final[int] = 24
"""Default TTL (time-to-live) for the ticker list file cache in hours.

The ticker list (~5,000 entries) is expensive to fetch. Caching locally
avoids repeated API calls. A 24-hour TTL balances freshness with
performance.
"""

DEFAULT_TICKER_CACHE_SUBDIR: Final[str] = "raw/etfcom"
"""Default subdirectory (relative to DATA_DIR) for the ticker list file cache.

Ticker list JSON files are stored here with timestamps for TTL
validation.

See Also
--------
database.db.connection.get_data_dir
"""

DEFAULT_MAX_CONCURRENCY: Final[int] = 5
"""Default maximum number of concurrent API requests.

Controls the ``asyncio.Semaphore`` limit for parallel fund detail
fetches. A conservative default to avoid triggering rate limiting
on the ETF.com API.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "API_HEADERS",
    "AUTH_DETAILS_URL",
    "AUTH_TOKEN_TTL_SECONDS",
    "BROWSER_IMPERSONATE_TARGETS",
    "CHARTS_URL",
    "DEFAULT_DELAY_JITTER",
    "DEFAULT_HEADERS",
    "DEFAULT_MAX_CONCURRENCY",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_TICKER_CACHE_SUBDIR",
    "DEFAULT_TICKER_CACHE_TTL_HOURS",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENTS",
    "DELAYED_QUOTES_URL",
    "ETFCOM_API_BASE_URL",
    "ETFCOM_BASE_URL",
    "FUND_DETAILS_QUERY_NAMES",
    "FUND_DETAILS_URL",
    "PERFORMANCE_URL",
    "TICKERS_URL",
]
