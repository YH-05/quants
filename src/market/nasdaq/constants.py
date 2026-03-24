"""Constants for NASDAQ Stock Screener module.

This module defines all constants used by the NASDAQ Stock Screener module,
including the API endpoint URL, default HTTP headers, User-Agent rotation list,
browser impersonation targets for curl_cffi, polite delay settings, request
timeout, output directory path, and column name mapping from API response
keys to snake_case.

Constants are organized into the following categories:

1. API URL (screener endpoint)
2. Bot-blocking countermeasures (User-Agent rotation, TLS fingerprint
   impersonation targets, polite delays, timeout)
3. Default HTTP headers
4. Output settings (CSV directory)
5. Column name mapping (API camelCase to snake_case)

Notes
-----
All constants use ``typing.Final`` type annotations to prevent reassignment.
The ``__all__`` list exports all public constants for use by other modules.

The User-Agent strings and browser impersonation targets are based on
real browser configurations to avoid bot detection by NASDAQ.

See Also
--------
market.etfcom.constants : Similar constant pattern used by the ETF.com module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

NASDAQ_SCREENER_URL: Final[str] = "https://api.nasdaq.com/api/screener/stocks"
"""URL for the NASDAQ Stock Screener API endpoint.

Accepts GET requests with optional query parameters for filtering stocks
by exchange, market cap, sector, recommendation, region, and country.
Use ``limit=0`` to retrieve all matching records.

Examples
--------
>>> import urllib.parse
>>> params = {"exchange": "nasdaq", "sector": "technology", "limit": "0"}
>>> f"{NASDAQ_SCREENER_URL}?{urllib.parse.urlencode(params)}"
'https://api.nasdaq.com/api/screener/stocks?exchange=nasdaq&sector=technology&limit=0'
"""

# ---------------------------------------------------------------------------
# 2. Bot-blocking countermeasure constants
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
Aligned with ``market.etfcom.constants.BROWSER_IMPERSONATE_TARGETS``.
"""

DEFAULT_POLITE_DELAY: Final[float] = 1.0
"""Default polite delay between requests in seconds.

A minimum wait time between consecutive requests to avoid
overloading the NASDAQ API server and triggering rate limiting.
"""

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds.

Maximum time to wait for a response before raising a timeout error.
"""

DEFAULT_DELAY_JITTER: Final[float] = 0.5
"""Random jitter added to the polite delay in seconds.

Adds randomness to request timing to appear more human-like.
The actual delay is ``DEFAULT_POLITE_DELAY + random(0, DEFAULT_DELAY_JITTER)``.
"""

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({"api.nasdaq.com"})
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by ``NasdaqSession.get()``.
Requests to any other host will raise ``ValueError``.
"""

# ---------------------------------------------------------------------------
# 3. Default HTTP headers
# ---------------------------------------------------------------------------

DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}
"""Default HTTP headers for NASDAQ API requests.

Includes a static User-Agent for simple requests. For session-based
requests with User-Agent rotation, use ``DEFAULT_USER_AGENTS`` instead.
The Accept header specifies JSON as the preferred response format.
"""

# ---------------------------------------------------------------------------
# 4. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR: Final[str] = "data/raw/nasdaq"
"""Default directory for CSV output files.

Follows the project convention of ``data/raw/<source>/``.
Files are named ``{category}_{value}_{YYYY-MM-DD}.csv``.
"""

# ---------------------------------------------------------------------------
# 5. Column name mapping
# ---------------------------------------------------------------------------

COLUMN_NAME_MAP: Final[dict[str, str]] = {
    "symbol": "symbol",
    "name": "name",
    "lastsale": "last_sale",
    "netchange": "net_change",
    "pctchange": "pct_change",
    "marketCap": "market_cap",
    "country": "country",
    "ipoyear": "ipo_year",
    "volume": "volume",
    "sector": "sector",
    "industry": "industry",
    "url": "url",
}
"""Mapping from NASDAQ API response column names to snake_case.

The API returns camelCase or concatenated keys (e.g., ``lastsale``,
``marketCap``, ``pctchange``). This mapping normalises them to
consistent snake_case for use in pandas DataFrames.

Examples
--------
>>> COLUMN_NAME_MAP["marketCap"]
'market_cap'
>>> COLUMN_NAME_MAP["lastsale"]
'last_sale'
"""

# ---------------------------------------------------------------------------
# 6. NasdaqClient API URL constants
# ---------------------------------------------------------------------------

NASDAQ_API_BASE: Final[str] = "https://api.nasdaq.com/api"
"""Base URL for all NASDAQ API endpoints.

All NasdaqClient endpoint URLs are constructed relative to this base.
"""

EARNINGS_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/calendar/earnings"
"""URL for the NASDAQ Earnings Calendar API endpoint."""

DIVIDENDS_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/calendar/dividends"
"""URL for the NASDAQ Dividends Calendar API endpoint."""

SPLITS_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/calendar/splits"
"""URL for the NASDAQ Stock Splits Calendar API endpoint."""

IPO_CALENDAR_URL: Final[str] = f"{NASDAQ_API_BASE}/ipo/calendar"
"""URL for the NASDAQ IPO Calendar API endpoint."""

STOCK_QUOTE_URL: Final[str] = f"{NASDAQ_API_BASE}/quote/{{symbol}}/info"
"""URL template for NASDAQ stock quote (real-time info) endpoint.

Use ``STOCK_QUOTE_URL.format(symbol="AAPL")`` to construct the URL.
"""

STOCK_SUMMARY_URL: Final[str] = f"{NASDAQ_API_BASE}/quote/{{symbol}}/summary"
"""URL template for NASDAQ stock summary endpoint.

Use ``STOCK_SUMMARY_URL.format(symbol="AAPL")`` to construct the URL.
"""

STOCK_CHART_URL: Final[str] = f"{NASDAQ_API_BASE}/quote/{{symbol}}/chart"
"""URL template for NASDAQ stock chart (historical price) endpoint.

Use ``STOCK_CHART_URL.format(symbol="AAPL")`` to construct the URL.
"""

INSTITUTIONAL_HOLDINGS_URL: Final[str] = (
    f"{NASDAQ_API_BASE}/company/{{symbol}}/institutional-holdings"
)
"""URL template for NASDAQ institutional holdings endpoint.

Use ``INSTITUTIONAL_HOLDINGS_URL.format(symbol="AAPL")`` to construct the URL.
"""

INSIDER_TRADES_URL: Final[str] = f"{NASDAQ_API_BASE}/company/{{symbol}}/insider-trades"
"""URL template for NASDAQ insider trades endpoint.

Use ``INSIDER_TRADES_URL.format(symbol="AAPL")`` to construct the URL.
"""

SEC_FILINGS_URL: Final[str] = f"{NASDAQ_API_BASE}/company/{{symbol}}/sec-filings"
"""URL template for NASDAQ SEC filings endpoint.

Use ``SEC_FILINGS_URL.format(symbol="AAPL")`` to construct the URL.
"""

ANALYST_FORECAST_URL: Final[str] = f"{NASDAQ_API_BASE}/analyst/{{symbol}}/forecast"
"""URL template for NASDAQ analyst forecast endpoint.

Use ``ANALYST_FORECAST_URL.format(symbol="AAPL")`` to construct the URL.
"""

ANALYST_RATINGS_URL: Final[str] = f"{NASDAQ_API_BASE}/analyst/{{symbol}}/ratings"
"""URL template for NASDAQ analyst ratings endpoint.

Use ``ANALYST_RATINGS_URL.format(symbol="AAPL")`` to construct the URL.
"""

ANALYST_TARGET_PRICE_URL: Final[str] = (
    f"{NASDAQ_API_BASE}/analyst/{{symbol}}/targetprice"
)
"""URL template for NASDAQ analyst target price endpoint.

Use ``ANALYST_TARGET_PRICE_URL.format(symbol="AAPL")`` to construct the URL.
"""

ANALYST_EARNINGS_DATE_URL: Final[str] = (
    f"{NASDAQ_API_BASE}/analyst/{{symbol}}/earnings-date"
)
"""URL template for NASDAQ analyst earnings date endpoint.

Use ``ANALYST_EARNINGS_DATE_URL.format(symbol="AAPL")`` to construct the URL.
"""

COMPANY_PROFILE_URL: Final[str] = (
    f"{NASDAQ_API_BASE}/company/{{symbol}}/company-profile"
)
"""URL template for NASDAQ company profile endpoint.

Use ``COMPANY_PROFILE_URL.format(symbol="AAPL")`` to construct the URL.
"""

MARKET_MOVERS_URL: Final[str] = f"{NASDAQ_API_BASE}/marketmovers"
"""URL for the NASDAQ Market Movers API endpoint.

Returns most advanced (gainers), most declined (losers), and most active
(highest volume) stocks.
"""

ETF_SCREENER_URL: Final[str] = f"{NASDAQ_API_BASE}/screener/etf"
"""URL for the NASDAQ ETF Screener API endpoint.

Accepts GET requests with optional query parameters for filtering ETFs.
Use ``limit=0`` to retrieve all matching records.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "ANALYST_EARNINGS_DATE_URL",
    "ANALYST_FORECAST_URL",
    "ANALYST_RATINGS_URL",
    "ANALYST_TARGET_PRICE_URL",
    "BROWSER_IMPERSONATE_TARGETS",
    "COLUMN_NAME_MAP",
    "COMPANY_PROFILE_URL",
    "DEFAULT_DELAY_JITTER",
    "DEFAULT_HEADERS",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENTS",
    "DIVIDENDS_CALENDAR_URL",
    "EARNINGS_CALENDAR_URL",
    "ETF_SCREENER_URL",
    "INSIDER_TRADES_URL",
    "INSTITUTIONAL_HOLDINGS_URL",
    "IPO_CALENDAR_URL",
    "MARKET_MOVERS_URL",
    "NASDAQ_API_BASE",
    "NASDAQ_SCREENER_URL",
    "SEC_FILINGS_URL",
    "SPLITS_CALENDAR_URL",
    "STOCK_CHART_URL",
    "STOCK_QUOTE_URL",
    "STOCK_SUMMARY_URL",
]
