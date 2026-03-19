"""SET (Stock Exchange of Thailand) data retrieval module.

This package provides tools for fetching market data from
the Stock Exchange of Thailand.

The package name is ``set_exchange`` instead of ``set`` to avoid
collision with the Python built-in ``set`` type.

Modules
-------
constants : Exchange identification, yfinance config, output settings.
errors : Exception hierarchy for SET operations.
types : Configuration dataclasses.
"""

from market.set_exchange.errors import (
    SetAPIError,
    SetError,
    SetParseError,
    SetRateLimitError,
    SetValidationError,
)
from market.set_exchange.types import SetConfig

__all__ = [
    "SetAPIError",
    "SetConfig",
    "SetError",
    "SetParseError",
    "SetRateLimitError",
    "SetValidationError",
]
