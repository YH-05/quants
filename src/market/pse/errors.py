"""Custom exception classes for the PSE module.

This module provides exchange-specific exception classes for PSE
(Philippine Stock Exchange) by subclassing the shared base hierarchy
in ``market.asean_common.errors``.

Exception Hierarchy
-------------------
ExchangeError (from asean_common)
    PseError (base for PSE)
        PseAPIError (API response error - 4xx, 5xx)
        PseRateLimitError (rate limit exceeded)
        PseParseError (response parse failure)
        PseValidationError (data validation failure)

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


class PseError(ExchangeError):
    """Base exception for all PSE operations."""


class PseAPIError(PseError, ExchangeAPIError):
    """Exception raised when a PSE API returns an error response."""


class PseRateLimitError(PseError, ExchangeRateLimitError):
    """Exception raised when the PSE API rate limit is exceeded."""


class PseParseError(PseError, ExchangeParseError):
    """Exception raised when PSE API response parsing fails."""


class PseValidationError(PseError, ExchangeValidationError):
    """Exception raised when PSE data validation fails."""


__all__ = [
    "PseAPIError",
    "PseError",
    "PseParseError",
    "PseRateLimitError",
    "PseValidationError",
]
