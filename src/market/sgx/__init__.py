"""SGX (Singapore Exchange) data retrieval module.

This package provides tools for fetching market data from
the Singapore Exchange.

Modules
-------
constants : Exchange identification, yfinance config, output settings.
errors : Exception hierarchy for SGX operations.
types : Configuration dataclasses.
"""

from market.sgx.errors import (
    SgxAPIError,
    SgxError,
    SgxParseError,
    SgxRateLimitError,
    SgxValidationError,
)
from market.sgx.types import SgxConfig

__all__ = [
    "SgxAPIError",
    "SgxConfig",
    "SgxError",
    "SgxParseError",
    "SgxRateLimitError",
    "SgxValidationError",
]
