"""Constants for the EDINET disclosure API module.

This module defines all constants used by the EDINET disclosure API module
(``api.edinet-fsa.go.jp``), including the base API URLs, download URL,
SSRF prevention whitelist, environment variable names, HTTP settings,
and output directory.

This module is for the **EDINET disclosure API** (金融庁の開示書類取得)
and is completely separate from the existing ``market.edinet`` module
which uses the **EDINET DB API** (``edinetdb.jp``).

Constants are organized into the following categories:

1. API URL (EDINET disclosure API base endpoints)
2. Security (SSRF prevention via ALLOWED_HOSTS)
3. Authentication (environment variable name for API key)
4. HTTP settings (timeout, polite delay, delay jitter)
5. Output settings (data directory)

Notes
-----
All constants use ``typing.Final`` type annotations to prevent reassignment.
The ``__all__`` list exports all public constants for use by other modules.

See Also
--------
market.edinet.constants : EDINET DB API constants (``edinetdb.jp``).
market.bse.constants : Similar constant pattern used by the BSE module.
"""

from typing import Final

# ---------------------------------------------------------------------------
# 1. API URL constants
# ---------------------------------------------------------------------------

BASE_URL: Final[str] = "https://api.edinet-fsa.go.jp/api/v2"
"""Base URL for the EDINET disclosure API.

All API requests are constructed by appending endpoint paths
to this base URL (e.g., ``BASE_URL + "/documents.json"``).

Examples
--------
>>> f"{BASE_URL}/documents.json?date=2025-01-15&type=2"
'https://api.edinet-fsa.go.jp/api/v2/documents.json?date=2025-01-15&type=2'
"""

DOWNLOAD_BASE_URL: Final[str] = "https://disclosure2dl.edinet-fsa.go.jp/api/v2"
"""Base URL for EDINET disclosure document downloads.

Document files (XBRL ZIPs, PDFs) are served from this separate host.

Examples
--------
>>> f"{DOWNLOAD_BASE_URL}/documents/S100ABCD?type=1"
'https://disclosure2dl.edinet-fsa.go.jp/api/v2/documents/S100ABCD?type=1'
"""

# ---------------------------------------------------------------------------
# 2. Security constants
# ---------------------------------------------------------------------------

ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {"api.edinet-fsa.go.jp", "disclosure2dl.edinet-fsa.go.jp"}
)
"""Whitelist of allowed hostnames for SSRF prevention (CWE-918).

Only requests to these hosts are permitted by the EDINET API session layer.
Requests to any other host will raise ``ValueError``.
"""

# ---------------------------------------------------------------------------
# 3. Authentication constants
# ---------------------------------------------------------------------------

EDINET_FSA_API_KEY_ENV: Final[str] = "EDINET_FSA_API_KEY"
"""Environment variable name for the EDINET disclosure API key.

The API key is read from this environment variable when no explicit
key is provided to ``EdinetApiConfig``. The key is sent as a
``Subscription-Key`` query parameter with each request.
"""

# ---------------------------------------------------------------------------
# 4. HTTP settings
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: Final[float] = 30.0
"""Default HTTP request timeout in seconds.

Maximum time to wait for a response from the EDINET disclosure API
before raising a timeout error.
"""

DEFAULT_POLITE_DELAY: Final[float] = 0.5
"""Default polite delay between consecutive API requests in seconds.

A minimum wait time between requests to avoid overloading the
EDINET disclosure API server and triggering rate limiting.
Set to 500ms as a conservative baseline for a government API.
"""

DEFAULT_DELAY_JITTER: Final[float] = 0.1
"""Random jitter added to the polite delay in seconds.

Adds randomness to request timing to appear more human-like.
The actual delay is ``DEFAULT_POLITE_DELAY + random(0, DEFAULT_DELAY_JITTER)``.
"""

# ---------------------------------------------------------------------------
# 5. Output settings
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_SUBDIR: Final[str] = "raw/edinet_api"
"""Default subdirectory (relative to DATA_DIR) for output files.

See Also
--------
database.db.connection.get_data_dir
"""

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_HOSTS",
    "BASE_URL",
    "DEFAULT_DELAY_JITTER",
    "DEFAULT_OUTPUT_SUBDIR",
    "DEFAULT_POLITE_DELAY",
    "DEFAULT_TIMEOUT",
    "DOWNLOAD_BASE_URL",
    "EDINET_FSA_API_KEY_ENV",
]
