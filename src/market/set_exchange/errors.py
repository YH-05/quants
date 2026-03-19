"""Custom exception classes for the SET Exchange module.

This module provides exchange-specific exception classes for SET
(Stock Exchange of Thailand) by subclassing the shared base hierarchy
in ``market.asean_common.errors``.

The package name is ``set_exchange`` to avoid collision with the
Python built-in ``set`` type. The error class prefix is ``Set``
for brevity.

Exception Hierarchy
-------------------
ExchangeError (from asean_common)
    SetError (base for SET)
        SetAPIError (API response error - 4xx, 5xx)
        SetRateLimitError (rate limit exceeded)
        SetParseError (response parse failure)
        SetValidationError (data validation failure)

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


class SetError(ExchangeError):
    """Base exception for all SET operations."""


class SetAPIError(SetError, ExchangeAPIError):
    """Exception raised when a SET API returns an error response."""


class SetRateLimitError(SetError, ExchangeRateLimitError):
    """Exception raised when the SET API rate limit is exceeded."""


class SetParseError(SetError, ExchangeParseError):
    """Exception raised when SET API response parsing fails."""


class SetValidationError(SetError, ExchangeValidationError):
    """Exception raised when SET data validation fails."""


__all__ = [
    "SetAPIError",
    "SetError",
    "SetParseError",
    "SetRateLimitError",
    "SetValidationError",
]
