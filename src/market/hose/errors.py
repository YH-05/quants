"""Custom exception classes for the HOSE module.

This module provides exchange-specific exception classes for HOSE
(Ho Chi Minh Stock Exchange) by subclassing the shared base hierarchy
in ``market.asean_common.errors``.

Exception Hierarchy
-------------------
ExchangeError (from asean_common)
    HoseError (base for HOSE)
        HoseAPIError (API response error - 4xx, 5xx)
        HoseRateLimitError (rate limit exceeded)
        HoseParseError (response parse failure)
        HoseValidationError (data validation failure)

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


class HoseError(ExchangeError):
    """Base exception for all HOSE operations."""


class HoseAPIError(HoseError, ExchangeAPIError):
    """Exception raised when a HOSE API returns an error response."""


class HoseRateLimitError(HoseError, ExchangeRateLimitError):
    """Exception raised when the HOSE API rate limit is exceeded."""


class HoseParseError(HoseError, ExchangeParseError):
    """Exception raised when HOSE API response parsing fails."""


class HoseValidationError(HoseError, ExchangeValidationError):
    """Exception raised when HOSE data validation fails."""


__all__ = [
    "HoseAPIError",
    "HoseError",
    "HoseParseError",
    "HoseRateLimitError",
    "HoseValidationError",
]
