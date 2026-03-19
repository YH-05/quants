"""Custom exception classes for the Bursa module.

This module provides exchange-specific exception classes for Bursa
Malaysia by subclassing the shared base hierarchy in
``market.asean_common.errors``.

Exception Hierarchy
-------------------
ExchangeError (from asean_common)
    BursaError (base for Bursa)
        BursaAPIError (API response error - 4xx, 5xx)
        BursaRateLimitError (rate limit exceeded)
        BursaParseError (response parse failure)
        BursaValidationError (data validation failure)

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


class BursaError(ExchangeError):
    """Base exception for all Bursa Malaysia operations."""


class BursaAPIError(BursaError, ExchangeAPIError):
    """Exception raised when a Bursa API returns an error response."""


class BursaRateLimitError(BursaError, ExchangeRateLimitError):
    """Exception raised when the Bursa API rate limit is exceeded."""


class BursaParseError(BursaError, ExchangeParseError):
    """Exception raised when Bursa API response parsing fails."""


class BursaValidationError(BursaError, ExchangeValidationError):
    """Exception raised when Bursa data validation fails."""


__all__ = [
    "BursaAPIError",
    "BursaError",
    "BursaParseError",
    "BursaRateLimitError",
    "BursaValidationError",
]
