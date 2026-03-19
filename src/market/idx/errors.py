"""Custom exception classes for the IDX module.

This module provides exchange-specific exception classes for IDX
(Indonesia Stock Exchange) by subclassing the shared base hierarchy
in ``market.asean_common.errors``.

Exception Hierarchy
-------------------
ExchangeError (from asean_common)
    IdxError (base for IDX)
        IdxAPIError (API response error - 4xx, 5xx)
        IdxRateLimitError (rate limit exceeded)
        IdxParseError (response parse failure)
        IdxValidationError (data validation failure)

See Also
--------
market.asean_common.errors : Base exchange error hierarchy.
"""

from market.asean_common.errors import (
    ExchangeAPIError,
    ExchangeError,
    ExchangeParseError,
    ExchangeRateLimitError,
    ExchangeValidationError,
)


class IdxError(ExchangeError):
    """Base exception for all IDX operations."""


class IdxAPIError(IdxError, ExchangeAPIError):
    """Exception raised when an IDX API returns an error response."""


class IdxRateLimitError(IdxError, ExchangeRateLimitError):
    """Exception raised when the IDX API rate limit is exceeded."""


class IdxParseError(IdxError, ExchangeParseError):
    """Exception raised when IDX API response parsing fails."""


class IdxValidationError(IdxError, ExchangeValidationError):
    """Exception raised when IDX data validation fails."""


__all__ = [
    "IdxAPIError",
    "IdxError",
    "IdxParseError",
    "IdxRateLimitError",
    "IdxValidationError",
]
