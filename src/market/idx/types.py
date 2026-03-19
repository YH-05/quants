"""Type definitions for the market.idx module.

This module provides type definitions for IDX (Indonesia Stock Exchange)
data retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.idx.constants : Default values referenced by IdxConfig.
market.asean_common.types : ExchangeConfig base class.
"""

from dataclasses import dataclass

from market.asean_common.types import ExchangeConfig
from market.idx.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class IdxConfig(ExchangeConfig):
    """Configuration for IDX data retrieval.

    Inherits timeout validation from ``ExchangeConfig``.

    Parameters
    ----------
    exchange_code : str
        Exchange code identifier (default: ``EXCHANGE_CODE`` = "IDX").
    suffix : str
        yfinance ticker suffix (default: ``SUFFIX`` = ".JK").
    timeout : float
        HTTP request timeout in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If timeout is outside its valid range.

    Examples
    --------
    >>> config = IdxConfig()
    >>> config.exchange_code
    'IDX'
    >>> config.suffix
    '.JK'
    """

    exchange_code: str = EXCHANGE_CODE
    suffix: str = SUFFIX


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "IdxConfig",
]
