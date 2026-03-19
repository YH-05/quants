"""Type definitions for the market.set_exchange module.

This module provides type definitions for SET (Stock Exchange of Thailand)
data retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.set_exchange.constants : Default values referenced by SetConfig.
market.bse.types : Similar type-definition pattern for the BSE module.
"""

from dataclasses import dataclass

from market.set_exchange.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class SetConfig:
    """Configuration for SET data retrieval.

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
    timeout: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration value ranges.

        Raises
        ------
        ValueError
            If timeout is outside its valid range.
        """
        if not (1.0 <= self.timeout <= 300.0):
            raise ValueError(
                f"timeout must be between 1.0 and 300.0, got {self.timeout}"
            )


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "SetConfig",
]
