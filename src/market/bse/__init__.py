"""BSE (Bombay Stock Exchange) data retrieval module.

This package provides tools for fetching market data from the
BSE India API (https://api.bseindia.com/BseIndiaAPI/api).

Modules
-------
constants : API URLs, headers, and configuration defaults.
errors : Exception hierarchy for BSE API operations.
types : Configuration dataclasses, Enums, and data record types.
collectors : Data collector implementations (placeholder for Wave 2+).

Public API
----------
BseConfig
    Configuration for BSE API HTTP behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.

Enums
-----
BhavcopyType, ScripGroup, IndexName
    Filter and classification enums for BSE data.

Error Classes
-------------
BseError
    Base exception for all BSE API operations.
BseAPIError
    Exception raised when the BSE API returns an error response.
BseRateLimitError
    Exception raised when the BSE API rate limit is exceeded.
BseParseError
    Exception raised when BSE API response parsing fails.
BseValidationError
    Exception raised when BSE data validation fails.

Data Types
----------
ScripQuote, FinancialResult, Announcement, CorporateAction
    Frozen dataclasses for BSE data records.
"""

from market.bse.errors import (
    BseAPIError,
    BseError,
    BseParseError,
    BseRateLimitError,
    BseValidationError,
)
from market.bse.types import (
    Announcement,
    BhavcopyType,
    BseConfig,
    CorporateAction,
    FinancialResult,
    IndexName,
    RetryConfig,
    ScripGroup,
    ScripQuote,
)

__all__ = [
    "Announcement",
    "BhavcopyType",
    "BseAPIError",
    "BseConfig",
    "BseError",
    "BseParseError",
    "BseRateLimitError",
    "BseValidationError",
    "CorporateAction",
    "FinancialResult",
    "IndexName",
    "RetryConfig",
    "ScripGroup",
    "ScripQuote",
]
