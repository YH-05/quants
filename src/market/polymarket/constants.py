"""Constants for Polymarket API client module.

This module defines all constants used by the Polymarket API client,
including the base URLs for three API endpoints (Gamma, CLOB, Data),
SSRF prevention whitelist, and default configuration values.

See Also
--------
market.jquants.constants : Similar constant pattern used by the J-Quants module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

GAMMA_BASE_URL: Final[str] = "https://gamma-api.polymarket.com"
"""Base URL for the Polymarket Gamma API.

The Gamma API provides market metadata such as event details,
market descriptions, and resolution information.
"""

CLOB_BASE_URL: Final[str] = "https://clob.polymarket.com"
"""Base URL for the Polymarket CLOB (Central Limit Order Book) API.

The CLOB API provides real-time pricing, order book depth,
and order management endpoints.
"""

DATA_BASE_URL: Final[str] = "https://data-api.polymarket.com"
"""Base URL for the Polymarket Data API.

The Data API provides historical trade data, open interest,
and volume information.
"""

# ---------------------------------------------------------------------------
# 2. Security constants
# ---------------------------------------------------------------------------

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "gamma-api.polymarket.com",
        "clob.polymarket.com",
        "data-api.polymarket.com",
    }
)
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by the Polymarket session layer.
Requests to any other host will raise ``ValueError``.
"""

# ---------------------------------------------------------------------------
# 3. Default configuration values
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds."""

DEFAULT_RATE_LIMIT_PER_SECOND: Final[float] = 1.5
"""Default maximum number of requests per second.

Polymarket APIs are public but rate-limited; this conservative
default helps avoid HTTP 429 responses.
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "CLOB_BASE_URL",
    "DATA_BASE_URL",
    "DEFAULT_RATE_LIMIT_PER_SECOND",
    "DEFAULT_TIMEOUT",
    "GAMMA_BASE_URL",
]
