"""Constants for the EDINET DB API module.

This module defines all constants used by the EDINET DB API module,
including the base API URL, environment variable names for API key and
database path, rate limiting parameters, state file names, HTTP settings,
SQLite table names, and the list of available ranking metrics.

Constants are organized into the following categories:

1. API settings (base URL, authentication environment variable)
2. Database path settings (environment variable, default path components)
3. Rate limiting (daily limit, safety margin)
4. State file names (sync state, rate limit counter)
5. HTTP settings (timeout, polite delay)
6. SQLite table names
7. Ranking metrics (18 metrics available via ``/v1/rankings/{metric}``)

Notes
-----
All constants use ``typing.Final`` type annotations to prevent reassignment.
The ``__all__`` list exports all public constants for use by other modules.

The ranking metrics correspond to the EDINET DB API
``GET /v1/rankings/{metric}`` endpoint, which supports 18 financial
indicators for company ranking.

See Also
--------
market.nasdaq.constants : Similar constant pattern used by the NASDAQ module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API settings
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL: Final[str] = "https://edinetdb.jp"
"""Base URL for the EDINET DB REST API.

All API requests are constructed by appending endpoint paths to this URL.
The API requires authentication via ``X-API-Key`` header for most endpoints.

Examples
--------
>>> f"{DEFAULT_BASE_URL}/v1/companies"
'https://edinetdb.jp/v1/companies'
"""

EDINET_API_KEY_ENV: Final[str] = "EDINET_DB_API_KEY"
"""Environment variable name for the EDINET DB API key.

The API key is read from this environment variable when no explicit
key is provided to ``EdinetConfig``. The key is sent as an
``X-API-Key`` HTTP header with each authenticated request.
"""

# ---------------------------------------------------------------------------
# 2. Database path settings
# ---------------------------------------------------------------------------

EDINET_DB_PATH_ENV: Final[str] = "EDINET_DB_PATH"
"""Environment variable name for overriding the default SQLite file path.

When set, this takes precedence over the default path resolved by
``get_db_path("sqlite", "edinet")``. The CLI ``--db-path`` argument
takes highest precedence over both this variable and the default.
"""

DEFAULT_DB_SUBDIR: Final[str] = "sqlite"
"""Default subdirectory name under ``DATA_DIR`` for SQLite files.

Used as the first argument to ``get_db_path()`` when resolving the
default database path.
"""

DEFAULT_DB_NAME: Final[str] = "edinet"
"""Default database name (without extension) for the EDINET SQLite file.

Used as the second argument to ``get_db_path()`` when resolving the
default database path. The resulting file is ``edinet.db``.
"""

# ---------------------------------------------------------------------------
# 3. Rate limiting
# ---------------------------------------------------------------------------

DAILY_RATE_LIMIT: Final[int] = 100
"""Maximum number of API calls allowed per day (Free plan).

The EDINET DB API Free plan allows 100 requests per day.
Pro plan allows 1,000 requests/day, Business 10,000 requests/day.
"""

SAFE_MARGIN: Final[int] = 5
"""Safety margin subtracted from the daily rate limit.

The effective daily limit is ``DAILY_RATE_LIMIT - SAFE_MARGIN = 95``
calls per day. This margin prevents accidental overuse due to
concurrent requests or counting discrepancies.
"""

# ---------------------------------------------------------------------------
# 4. State file names
# ---------------------------------------------------------------------------

SYNC_STATE_FILENAME: Final[str] = "_sync_state.json"
"""Filename for the sync progress state file.

This file is stored in the same directory as the SQLite database file.
It tracks the current sync phase, completed EDINET codes, today's API
call count, and error history. Used for resuming interrupted syncs.
"""

RATE_LIMIT_FILENAME: Final[str] = "_rate_limit.json"
"""Filename for the daily rate limit counter file.

This file is stored in the same directory as the SQLite database file.
It tracks the number of API calls made today and the current date.
The counter resets automatically when the date changes.
"""

# ---------------------------------------------------------------------------
# 5. HTTP settings
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds.

Maximum time to wait for a response from the EDINET DB API before
raising a timeout error.
"""

DEFAULT_POLITE_DELAY: Final[float] = 0.1
"""Default polite delay between consecutive API requests in seconds.

A minimum wait time between requests to avoid overloading the
EDINET DB API server and triggering rate limiting. Set to 100ms
as a baseline; the actual delay may include additional jitter.
"""

# ---------------------------------------------------------------------------
# 6. SQLite table names
# ---------------------------------------------------------------------------

TABLE_COMPANIES: Final[str] = "companies"
"""SQLite table name for company master data.

Primary key: ``edinet_code``. Contains approximately 3,848 rows
for all listed Japanese companies.
"""

TABLE_FINANCIALS: Final[str] = "financials"
"""SQLite table name for annual financial statement data.

Primary key: ``(edinet_code, fiscal_year)``. Stores up to 6 years
of 24 financial indicators per company.
"""

TABLE_RATIOS: Final[str] = "ratios"
"""SQLite table name for computed financial ratio data.

Primary key: ``(edinet_code, fiscal_year)``. Stores up to 6 years
of 13 financial ratios per company.
"""

TABLE_TEXT_BLOCKS: Final[str] = "text_blocks"
"""SQLite table name for securities report text excerpts.

Primary key: ``(edinet_code, fiscal_year)``. Contains business
overview, risk factors, and management analysis text from annual
securities reports (yuho).
"""

TABLE_INDUSTRIES: Final[str] = "industries"
"""SQLite table name for industry master data.

Primary key: ``slug``. Contains 34 industry classifications with
average financial indicators.
"""

TABLE_INDUSTRY_DETAILS: Final[str] = "industry_details"
"""SQLite table name for detailed industry data.

Primary key: ``slug``. Contains company lists and industry-average
financial data for each of the 34 industry classifications.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "DAILY_RATE_LIMIT",
    "DEFAULT_BASE_URL",
    "DEFAULT_DB_NAME",
    "DEFAULT_DB_SUBDIR",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_TIMEOUT",
    "EDINET_API_KEY_ENV",
    "EDINET_DB_PATH_ENV",
    "RATE_LIMIT_FILENAME",
    "SAFE_MARGIN",
    "SYNC_STATE_FILENAME",
    "TABLE_COMPANIES",
    "TABLE_FINANCIALS",
    "TABLE_INDUSTRIES",
    "TABLE_INDUSTRY_DETAILS",
    "TABLE_RATIOS",
    "TABLE_TEXT_BLOCKS",
]
