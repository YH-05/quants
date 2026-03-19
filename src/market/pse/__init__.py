"""PSE (Philippine Stock Exchange) data retrieval module.

This package provides tools for fetching market data from
the Philippine Stock Exchange.

Note: PSE is **not** supported by yfinance. Philippine equities
can only be accessed via ADR tickers or alternative data providers.

Modules
-------
constants : Exchange identification, yfinance config, output settings.
errors : Exception hierarchy for PSE operations.
types : Configuration dataclasses.
"""

from market.pse.errors import (
    PseAPIError,
    PseError,
    PseParseError,
    PseRateLimitError,
    PseValidationError,
)
from market.pse.types import PseConfig

__all__ = [
    "PseAPIError",
    "PseConfig",
    "PseError",
    "PseParseError",
    "PseRateLimitError",
    "PseValidationError",
]
