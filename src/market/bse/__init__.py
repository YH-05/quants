"""BSE (Bombay Stock Exchange) data retrieval module.

This package provides tools for fetching market data from the
BSE India API (https://api.bseindia.com/BseIndiaAPI/api).

Modules
-------
constants : API URLs, headers, and configuration defaults.
errors : Exception hierarchy for BSE API operations.
session : httpx-based HTTP session with bot-blocking countermeasures.
types : Configuration dataclasses, Enums, and data record types.
collectors : Data collector implementations (placeholder for Wave 2+).

Public API
----------
BseSession
    httpx-based HTTP session with UA rotation, polite delay, and retry.
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

from market.bse.collectors.bhavcopy import BhavcopyCollector
from market.bse.collectors.quote import QuoteCollector
from market.bse.errors import (
    BseAPIError,
    BseError,
    BseParseError,
    BseRateLimitError,
    BseValidationError,
)
from market.bse.parsers import (
    clean_indian_number,
    clean_price,
    clean_volume,
    parse_bhavcopy_csv,
    parse_historical_csv,
    parse_quote_response,
)
from market.bse.session import BseSession
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
    "BhavcopyCollector",
    "BhavcopyType",
    "BseAPIError",
    "BseConfig",
    "BseError",
    "BseParseError",
    "BseRateLimitError",
    "BseSession",
    "BseValidationError",
    "CorporateAction",
    "FinancialResult",
    "IndexName",
    "QuoteCollector",
    "RetryConfig",
    "ScripGroup",
    "ScripQuote",
    "clean_indian_number",
    "clean_price",
    "clean_volume",
    "parse_bhavcopy_csv",
    "parse_historical_csv",
    "parse_quote_response",
]
