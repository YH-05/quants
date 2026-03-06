"""Constants for BSE (Bombay Stock Exchange) data retrieval module.

This module defines all constants used by the BSE data retrieval module,
including the API base URL, SSRF prevention whitelist, default HTTP headers,
User-Agent rotation list, polite delay settings, output directory path,
and column name mapping from API response keys to snake_case.

Constants are organized into the following categories:

1. API URL (BSE India API base endpoint)
2. Security (SSRF prevention via ALLOWED_HOSTS)
3. Bot-blocking countermeasures (User-Agent rotation, polite delays)
4. Default HTTP headers
5. Output settings (data directory)
6. Column name mapping (API keys to snake_case)

Notes
-----
All constants use ``typing.Final`` type annotations to prevent reassignment.
The ``__all__`` list exports all public constants for use by other modules.

The User-Agent strings are based on real browser configurations to avoid
bot detection by BSE India.

See Also
--------
market.nasdaq.constants : Similar constant pattern used by the NASDAQ module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

BASE_URL: Final[str] = "https://api.bseindia.com/BseIndiaAPI/api"
"""Base URL for the BSE India API.

All API requests are constructed by appending endpoint paths
to this base URL (e.g., ``BASE_URL + "/getScripHeaderData"``).
"""

BHAVCOPY_DOWNLOAD_BASE_URL: Final[str] = (
    "https://www.bseindia.com/download/BhavCopy/Equity"
)
"""Base URL for BSE Bhavcopy (daily market data) CSV downloads.

Bhavcopy files are published daily after market close for equity,
derivatives, and debt segments.

Examples
--------
>>> f"{BHAVCOPY_DOWNLOAD_BASE_URL}/BhavCopy_BSE_CM_0_0_0_20260305_F_0000.CSV"
'https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_20260305_F_0000.CSV'
"""

# ---------------------------------------------------------------------------
# 2. Security constants
# ---------------------------------------------------------------------------

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {"api.bseindia.com", "www.bseindia.com"}
)
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by the BSE session layer.
Requests to any other host will raise ``ValueError``.
"""

# ---------------------------------------------------------------------------
# 3. Bot-blocking countermeasure constants
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

DEFAULT_POLITE_DELAY: Final[float] = 0.15
"""Default polite delay between requests in seconds.

A minimum wait time between consecutive requests to avoid
overloading the BSE API server and triggering rate limiting.
BSE is more tolerant than NASDAQ, so a shorter delay is used.
"""

DEFAULT_DELAY_JITTER: Final[float] = 0.05
"""Random jitter added to the polite delay in seconds.

Adds randomness to request timing to appear more human-like.
The actual delay is ``DEFAULT_POLITE_DELAY + random(0, DEFAULT_DELAY_JITTER)``.
"""

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds.

Maximum time to wait for a response before raising a timeout error.
"""

# ---------------------------------------------------------------------------
# 4. Default HTTP headers
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
    "Referer": "https://www.bseindia.com/",
}
"""Default HTTP headers for BSE API requests.

Includes a static User-Agent for simple requests, Referer set to
the BSE India website (required by BSE API), and standard Accept headers.
For session-based requests with User-Agent rotation, use
``DEFAULT_USER_AGENTS`` instead.
"""

# ---------------------------------------------------------------------------
# 5. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR: Final[str] = "data/raw/bse/"
"""Default directory for output files.

Follows the project convention of ``data/raw/<source>/``.
"""

# ---------------------------------------------------------------------------
# 6. Column name mapping
# ---------------------------------------------------------------------------

COLUMN_NAME_MAP: Final[dict[str, str]] = {
    "ScripCode": "scrip_code",
    "ScripName": "scrip_name",
    "ScripGroup": "scrip_group",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "last": "last",
    "PrevClose": "prev_close",
    "No_Trades": "num_trades",
    "No_of_Shrs": "num_shares",
    "Net_Turnov": "net_turnover",
    "TotalTradedValue": "total_traded_value",
    "TotalTradedQuantity": "total_traded_quantity",
}

BHAVCOPY_COLUMN_NAME_MAP: Final[dict[str, str]] = {
    "SC_CODE": "scrip_code",
    "SC_NAME": "scrip_name",
    "SC_GROUP": "scrip_group",
    "SC_TYPE": "scrip_type",
    "OPEN": "open",
    "HIGH": "high",
    "LOW": "low",
    "CLOSE": "close",
    "LAST": "last",
    "PREVCLOSE": "prev_close",
    "NO_TRADES": "num_trades",
    "NO_OF_SHRS": "num_shares",
    "NET_TURNOV": "net_turnover",
    "TDCLOINDI": "tdcloindi",
    "ISIN_CODE": "isin_code",
    "TRADING_DATE": "trading_date",
}
"""Mapping from BSE API response column names to snake_case.

The API returns PascalCase or mixed-case keys. This mapping normalises
them to consistent snake_case for use in pandas DataFrames.

Examples
--------
>>> COLUMN_NAME_MAP["ScripCode"]
'scrip_code'
>>> COLUMN_NAME_MAP["PrevClose"]
'prev_close'
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "BASE_URL",
    "BHAVCOPY_COLUMN_NAME_MAP",
    "BHAVCOPY_DOWNLOAD_BASE_URL",
    "COLUMN_NAME_MAP",
    "DEFAULT_DELAY_JITTER",
    "DEFAULT_HEADERS",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENTS",
]
