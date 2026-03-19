"""Type definitions for the market.bursa module.

This module provides type definitions for Bursa Malaysia data
retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

See Also
--------
market.bursa.constants : Default values referenced by BursaConfig.
market.bse.types : Similar type-definition pattern for the BSE module.
"""

from dataclasses import dataclass

from market.bursa.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class BursaConfig:
    """Configuration for Bursa Malaysia data retrieval.

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
    "BursaConfig",
]
