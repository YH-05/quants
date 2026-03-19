"""Custom exception classes for the SGX module.

This module provides exchange-specific exception classes for SGX
(Singapore Exchange) by subclassing the shared base hierarchy
in ``market.asean_common.errors``.

Exception Hierarchy
-------------------
ExchangeError (from asean_common)
    SgxError (base for SGX)
        SgxAPIError (API response error - 4xx, 5xx)
        SgxRateLimitError (rate limit exceeded)
        SgxParseError (response parse failure)
        SgxValidationError (data validation failure)

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


class SgxError(ExchangeError):
    """Base exception for all SGX operations."""


class SgxAPIError(SgxError, ExchangeAPIError):
    """Exception raised when an SGX API returns an error response."""


class SgxRateLimitError(SgxError, ExchangeRateLimitError):
    """Exception raised when the SGX API rate limit is exceeded."""


class SgxParseError(SgxError, ExchangeParseError):
    """Exception raised when SGX API response parsing fails."""


class SgxValidationError(SgxError, ExchangeValidationError):
    """Exception raised when SGX data validation fails."""


__all__ = [
    "SgxAPIError",
    "SgxError",
    "SgxParseError",
    "SgxRateLimitError",
    "SgxValidationError",
]
