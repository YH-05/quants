"""Constants for J-Quants API client module.

This module defines all constants used by the J-Quants API client,
including the API base URL, SSRF prevention whitelist, environment
variable names, token file path, and default configuration values.

See Also
--------
market.bse.constants : Similar constant pattern used by the BSE module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

BASE_URL: Final[str] = "https://api.jquants.com/v1"
"""Base URL for the J-Quants API.

All API requests are constructed by appending endpoint paths
to this base URL (e.g., ``BASE_URL + "/listed/info"``).
"""

# ---------------------------------------------------------------------------
# 2. Security constants
# ---------------------------------------------------------------------------

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset({"api.jquants.com"})
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by the J-Quants session layer.
Requests to any other host will raise ``ValueError``.
"""

# ---------------------------------------------------------------------------
# 3. Environment variable names
# ---------------------------------------------------------------------------

JQUANTS_MAIL_ADDRESS_ENV: Final[str] = "JQUANTS_MAIL_ADDRESS"
"""Environment variable name for J-Quants login email address."""

JQUANTS_PASSWORD_ENV: Final[str] = "JQUANTS_PASSWORD"
"""Environment variable name for J-Quants login password."""

# ---------------------------------------------------------------------------
# 4. Token file path
# ---------------------------------------------------------------------------

TOKEN_FILE_PATH: Final[str] = "~/.jquants/token.json"
"""Default path for the J-Quants token persistence file.

Stores refresh_token and id_token with expiry timestamps.
The ``~`` is expanded at runtime via ``pathlib.Path.expanduser()``.
"""

# ---------------------------------------------------------------------------
# 5. Default configuration values
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds."""

DEFAULT_POLITE_DELAY: Final[float] = 0.1
"""Default polite delay between requests in seconds.

J-Quants API is an official API with rate limits handled server-side,
so a shorter delay than BSE is appropriate.
"""

DEFAULT_DELAY_JITTER: Final[float] = 0.05
"""Random jitter added to the polite delay in seconds."""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "BASE_URL",
    "DEFAULT_DELAY_JITTER",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_TIMEOUT",
    "JQUANTS_MAIL_ADDRESS_ENV",
    "JQUANTS_PASSWORD_ENV",
    "TOKEN_FILE_PATH",
]
