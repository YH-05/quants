"""Type definitions for the market.eodhd module.

This module provides type definitions for EODHD API data retrieval including:

- Configuration dataclass (EodhdConfig)

All dataclasses use ``frozen=True`` to ensure immutability where appropriate.

See Also
--------
market.jquants.types : Similar type-definition pattern for the J-Quants module.
market.eodhd.constants : Default values referenced by EodhdConfig.
"""

from dataclasses import dataclass, field

from market.eodhd.constants import (
    BASE_URL,
    DEFAULT_FORMAT,
    DEFAULT_TIMEOUT,
)

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class EodhdConfig:
    """Configuration for EODHD API client.

    Controls API key, base URL, HTTP timeout, and response format.

    Parameters
    ----------
    api_key : str
        EODHD API key. If empty, read from ``EODHD_API_KEY``
        environment variable at runtime.
    base_url : str
        Base URL for the EODHD API
        (default: ``BASE_URL`` = ``https://eodhd.com/api``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    fmt : str
        Response format (``json`` or ``csv``)
        (default: ``DEFAULT_FORMAT`` = ``json``).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = EodhdConfig(api_key="demo")
    >>> config.timeout
    30.0
    >>> config.base_url
    'https://eodhd.com/api'
    """

    api_key: str = field(default="", repr=False)
    base_url: str = BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    fmt: str = DEFAULT_FORMAT

    def __post_init__(self) -> None:
        """Validate configuration value ranges.

        Raises
        ------
        ValueError
            If any configuration value is outside its valid range.
        """
        if not (1.0 <= self.timeout <= 300.0):
            raise ValueError(
                f"timeout must be between 1.0 and 300.0, got {self.timeout}"
            )
        if self.fmt not in ("json", "csv"):
            raise ValueError(
                f"fmt must be 'json' or 'csv', got '{self.fmt}'"
            )


__all__ = [
    "EodhdConfig",
]
