"""Constants for Alpha Vantage API client module.

This module defines all constants used by the Alpha Vantage API client,
including the API base URL, SSRF prevention whitelist, environment
variable names, rate limit defaults, and HTTP configuration values.

See Also
--------
market.jquants.constants : Similar constant pattern used by the J-Quants module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

BASE_URL: Final[str] = "https://www.alphavantage.co/query"
"""Base URL for the Alpha Vantage API.

All API requests are constructed by appending query parameters
to this base URL (e.g., ``BASE_URL + "?function=TIME_SERIES_DAILY"``).
"""

# ---------------------------------------------------------------------------
# 2. Security constants
# ---------------------------------------------------------------------------

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({"www.alphavantage.co"})
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by the Alpha Vantage session layer.
Requests to any other host will raise ``ValueError``.
"""

MAX_RESPONSE_BODY_LOG: Final[int] = 200
"""Maximum number of characters to log from response bodies (CWE-209).

Prevents sensitive data from being exposed in log messages by truncating
response body content to this length.
"""

# ---------------------------------------------------------------------------
# 3. Environment variable names
# ---------------------------------------------------------------------------

ALPHA_VANTAGE_API_KEY_ENV: Final[str] = "ALPHA_VANTAGE_API_KEY"
"""Environment variable name for Alpha Vantage API key."""

# ---------------------------------------------------------------------------
# 4. Rate limit default values
# ---------------------------------------------------------------------------

DEFAULT_REQUESTS_PER_MINUTE: Final[int] = 25
"""Default maximum number of API requests per minute.

Alpha Vantage free tier allows 25 requests per day, but premium
plans allow higher limits. This default is suitable for premium plans.
"""

DEFAULT_REQUESTS_PER_HOUR: Final[int] = 500
"""Default maximum number of API requests per hour."""

# ---------------------------------------------------------------------------
# 5. HTTP default configuration values
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds."""

DEFAULT_POLITE_DELAY: Final[float] = 2.5
"""Default polite delay between requests in seconds.

Alpha Vantage recommends spacing requests to avoid rate limiting.
A longer delay than other APIs is appropriate for the free tier.
"""

DEFAULT_DELAY_JITTER: Final[float] = 0.5
"""Random jitter added to the polite delay in seconds."""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "ALPHA_VANTAGE_API_KEY_ENV",
    "BASE_URL",
    "DEFAULT_DELAY_JITTER",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_REQUESTS_PER_HOUR",
    "DEFAULT_REQUESTS_PER_MINUTE",
    "DEFAULT_TIMEOUT",
    "MAX_RESPONSE_BODY_LOG",
]
