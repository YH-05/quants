"""Type definitions for the market.set_exchange module.

This module provides type definitions for SET (Stock Exchange of Thailand)
data retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.set_exchange.constants : Default values referenced by SetConfig.
market.asean_common.types : ExchangeConfig base class.
"""

from dataclasses import dataclass

from market.asean_common.types import ExchangeConfig
from market.set_exchange.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class SetConfig(ExchangeConfig):
    """Configuration for SET data retrieval.

    Inherits timeout validation from ``ExchangeConfig``.

    Parameters
    ----------
    exchange_code : str
        Exchange code identifier (default: ``EXCHANGE_CODE`` = "SET").
    suffix : str
        yfinance ticker suffix (default: ``SUFFIX`` = ".BK").
    timeout : float
        HTTP request timeout in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If timeout is outside its valid range.

    Examples
    --------
    >>> config = SetConfig()
    >>> config.exchange_code
    'SET'
    >>> config.suffix
    '.BK'
    """

    exchange_code: str = EXCHANGE_CODE
    suffix: str = SUFFIX


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "SetConfig",
]
