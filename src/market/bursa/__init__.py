"""Bursa (Bursa Malaysia) data retrieval module.

This package provides tools for fetching market data from
Bursa Malaysia. Bursa uses numeric ticker codes (e.g. 1155 for Maybank).

Modules
-------
constants : Exchange identification, yfinance config, output settings.
errors : Exception hierarchy for Bursa operations.
types : Configuration dataclasses.
"""

from market.bursa.errors import (
    BursaAPIError,
    BursaError,
    BursaParseError,
    BursaRateLimitError,
    BursaValidationError,
)
from market.bursa.types import BursaConfig

__all__ = [
    "BursaAPIError",
    "BursaConfig",
    "BursaError",
    "BursaParseError",
    "BursaRateLimitError",
    "BursaValidationError",
]
