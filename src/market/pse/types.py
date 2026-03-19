"""Type definitions for the market.pse module.

This module provides type definitions for PSE (Philippine Stock Exchange)
data retrieval including configuration dataclasses.

All dataclasses use ``frozen=True`` to ensure immutability.

Note: PSE is not supported by yfinance (``YFINANCE_SUPPORTED = False``).

See Also
--------
market.pse.constants : Default values referenced by PseConfig.
market.bse.types : Similar type-definition pattern for the BSE module.
"""

from dataclasses import dataclass

from market.pse.constants import EXCHANGE_CODE, SUFFIX


@dataclass(frozen=True)
class PseConfig:
    """Configuration for PSE data retrieval.

    Parameters
    ----------
    exchange_code : str
        Exchange code identifier (default: ``EXCHANGE_CODE`` = "PSE").
    suffix : str
        yfinance ticker suffix (default: ``SUFFIX`` = ".PS").
    timeout : float
        HTTP request timeout in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If timeout is outside its valid range.

    Examples
    --------
    >>> config = PseConfig()
    >>> config.exchange_code
    'PSE'
    >>> config.suffix
    '.PS'
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
    "PseConfig",
]
