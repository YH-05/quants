"""Type definitions for the market.sgx module.

This module provides type definitions for SGX (Singapore Exchange) data
retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.sgx.constants : Default values referenced by SgxConfig.
market.asean_common.types : ExchangeConfig base class.
"""

from dataclasses import dataclass

from market.asean_common.types import ExchangeConfig
from market.sgx.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class SgxConfig(ExchangeConfig):
    """Configuration for SGX data retrieval.

    Inherits timeout validation from ``ExchangeConfig``.

    Parameters
    ----------
    exchange_code : str
        Exchange code identifier (default: ``EXCHANGE_CODE`` = "SGX").
    suffix : str
        yfinance ticker suffix (default: ``SUFFIX`` = ".SI").
    timeout : float
        HTTP request timeout in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If timeout is outside its valid range.

    Examples
    --------
    >>> config = SgxConfig()
    >>> config.exchange_code
    'SGX'
    >>> config.suffix
    '.SI'
    """

    exchange_code: str = EXCHANGE_CODE
    suffix: str = SUFFIX


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "SgxConfig",
]
