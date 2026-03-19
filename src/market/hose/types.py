"""Type definitions for the market.hose module.

This module provides type definitions for HOSE (Ho Chi Minh Stock Exchange)
data retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.hose.constants : Default values referenced by HoseConfig.
market.asean_common.types : ExchangeConfig base class.
"""

from dataclasses import dataclass

from market.asean_common.types import ExchangeConfig
from market.hose.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class HoseConfig(ExchangeConfig):
    """Configuration for HOSE data retrieval.

    Inherits timeout validation from ``ExchangeConfig``.

    Parameters
    ----------
    exchange_code : str
        Exchange code identifier (default: ``EXCHANGE_CODE`` = "HOSE").
    suffix : str
        yfinance ticker suffix (default: ``SUFFIX`` = ".VN").
    timeout : float
        HTTP request timeout in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If timeout is outside its valid range.

    Examples
    --------
    >>> config = HoseConfig()
    >>> config.exchange_code
    'HOSE'
    >>> config.suffix
    '.VN'
    """

    exchange_code: str = EXCHANGE_CODE
    suffix: str = SUFFIX


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "HoseConfig",
]
