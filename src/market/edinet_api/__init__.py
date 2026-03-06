"""EDINET disclosure API client module.

This package provides a synchronous HTTP client for the EDINET disclosure
API (``api.edinet-fsa.go.jp``), enabling search and download of disclosure
documents such as annual reports, quarterly reports, and extraordinary
reports filed with Japan's Financial Services Agency (FSA).

This module is for the **EDINET disclosure API** and is completely
separate from the existing ``market.edinet`` module which uses the
**EDINET DB API** (``edinetdb.jp``).

Modules
-------
constants : API URLs, SSRF whitelist, environment variable names.
errors : Exception hierarchy for EDINET disclosure API operations.
types : Configuration dataclasses, Enums, and data record types.
session : httpx-based HTTP session with X-API-Key auth and retry.
client : High-level API client for document search and download.
parsers : ZIP/XBRL/PDF extraction utilities.

Public API
----------
EdinetApiClient
    Synchronous HTTP client for document search and download.
EdinetApiSession
    httpx-based session with X-API-Key auth, polite delay, and retry.
EdinetApiConfig
    Configuration for EDINET API HTTP behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.

Enums
-----
DocumentType
    Classification of disclosure document types.

Error Classes
-------------
EdinetApiError
    Base exception for all EDINET disclosure API operations.
EdinetApiAPIError
    Exception raised when the API returns an error response.
EdinetApiRateLimitError
    Exception raised when the API rate limit is exceeded.
EdinetApiValidationError
    Exception raised when input validation fails.

Data Types
----------
DisclosureDocument
    Frozen dataclass for disclosure document metadata.

Parser Functions
----------------
parse_xbrl_zip
    Extract XBRL files from a ZIP archive.
extract_pdf
    Extract a PDF file from a ZIP archive.
"""

from market.edinet_api.client import EdinetApiClient
from market.edinet_api.errors import (
    EdinetApiAPIError,
    EdinetApiError,
    EdinetApiRateLimitError,
    EdinetApiValidationError,
)
from market.edinet_api.parsers import extract_pdf, parse_xbrl_zip
from market.edinet_api.session import EdinetApiSession
from market.edinet_api.types import (
    DisclosureDocument,
    DocumentType,
    EdinetApiConfig,
    RetryConfig,
)

__all__ = [
    "DisclosureDocument",
    "DocumentType",
    "EdinetApiAPIError",
    "EdinetApiClient",
    "EdinetApiConfig",
    "EdinetApiError",
    "EdinetApiRateLimitError",
    "EdinetApiSession",
    "EdinetApiValidationError",
    "RetryConfig",
    "extract_pdf",
    "parse_xbrl_zip",
]
