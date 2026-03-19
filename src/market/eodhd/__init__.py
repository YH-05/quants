"""EODHD API client module.

This package provides a skeleton client for the EODHD API
(https://eodhd.com/financial-apis/) to retrieve global financial data.

All public API methods currently raise ``NotImplementedError`` because
the API key has not been obtained yet. This skeleton defines the
interface contract for future implementation.

Modules
-------
constants : API URL, environment variable names, default configuration.
errors : Exception hierarchy for EODHD API operations.
types : Configuration dataclass.
client : Skeleton API client (all methods raise NotImplementedError).

Public API
----------
EodhdClient
    Skeleton API client with typed method signatures.
EodhdConfig
    Configuration for API key and HTTP behaviour.

Error Classes
-------------
EodhdError
    Base exception for all EODHD API operations.
EodhdAPIError
    Exception raised when the API returns an error response.
EodhdRateLimitError
    Exception raised when the API rate limit is exceeded.
EodhdValidationError
    Exception raised when data validation fails.
EodhdAuthError
    Exception raised when authentication fails.
"""

from market.eodhd.client import EodhdClient
from market.eodhd.errors import (
    EodhdAPIError,
    EodhdAuthError,
    EodhdError,
    EodhdRateLimitError,
    EodhdValidationError,
)
from market.eodhd.types import EodhdConfig

__all__ = [
    "EodhdAPIError",
    "EodhdAuthError",
    "EodhdClient",
    "EodhdConfig",
    "EodhdError",
    "EodhdRateLimitError",
    "EodhdValidationError",
]
