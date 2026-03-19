"""Type definitions for the market.bursa module.

This module provides type definitions for Bursa Malaysia data
retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.bursa.constants : Default values referenced by BursaConfig.
market.asean_common.types : ExchangeConfig base class.
"""

from dataclasses import dataclass

from market.asean_common.types import ExchangeConfig
from market.bursa.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class BursaConfig(ExchangeConfig):
    """Configuration for Bursa Malaysia data retrieval.

    Inherits timeout validation from ``ExchangeConfig``.

    Parameters
    ----------
    exchange_code : str
        Exchange code identifier (default: ``EXCHANGE_CODE`` = "BURSA").
    suffix : str
        yfinance ticker suffix (default: ``SUFFIX`` = ".KL").
    timeout : float
        HTTP request timeout in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If timeout is outside its valid range.

    Examples
    --------
    >>> config = BursaConfig()
    >>> config.exchange_code
    'BURSA'
    >>> config.suffix
    '.KL'
    """

    exchange_code: str = EXCHANGE_CODE
    suffix: str = SUFFIX


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "BursaConfig",
]
