"""Constants for EODHD API client module.

This module defines all constants used by the EODHD API client,
including the API base URL, SSRF prevention whitelist, environment
variable names, and default configuration values.

EODHD (https://eodhd.com/financial-apis/) provides global financial data
including end-of-day prices, fundamentals, dividends, splits, and more.

See Also
--------
market.jquants.constants : Similar constant pattern used by the J-Quants module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

BASE_URL: Final[str] = "https://eodhd.com/api"
"""Base URL for the EODHD API.

All API requests are constructed by appending endpoint paths
to this base URL (e.g., ``BASE_URL + "/eod/AAPL.US"``).
"""

# ---------------------------------------------------------------------------
# 2. Security constants
# ---------------------------------------------------------------------------

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({"eodhd.com"})
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by the EODHD client layer.
Requests to any other host will raise ``ValueError``.
"""

# ---------------------------------------------------------------------------
# 3. Environment variable names
# ---------------------------------------------------------------------------

EODHD_API_KEY_ENV: Final[str] = "EODHD_API_KEY"
"""Environment variable name for EODHD API key."""

# ---------------------------------------------------------------------------
# 4. Default configuration values
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds."""

DEFAULT_FORMAT: Final[str] = "json"
"""Default response format for EODHD API requests.

EODHD supports ``json`` and ``csv`` formats.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "BASE_URL",
    "DEFAULT_FORMAT",
    "DEFAULT_TIMEOUT",
    "EODHD_API_KEY_ENV",
]
