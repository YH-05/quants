"""Type definitions for the market.polymarket module.

This module provides type definitions for Polymarket API data retrieval including:

- Configuration dataclasses (PolymarketConfig, RetryConfig)
- Price interval enum (PriceInterval)

All dataclasses use ``frozen=True`` to ensure immutability.
Polymarket APIs are public and do not require authentication,
so there are no credential fields.

See Also
--------
market.jquants.types : Similar type-definition pattern for the J-Quants module.
market.eodhd.types : Similar type-definition pattern for the EODHD module.
market.polymarket.constants : Default values referenced by PolymarketConfig.
"""

from dataclasses import dataclass
from enum import StrEnum

from market.polymarket.constants import (
    CLOB_BASE_URL,
    DATA_BASE_URL,
    DEFAULT_RATE_LIMIT_PER_SECOND,
    DEFAULT_TIMEOUT,
    GAMMA_BASE_URL,
)

# =============================================================================
# Enums
# =============================================================================


class PriceInterval(StrEnum):
    """Time interval for historical price data queries.

    Members correspond to the ``fidelity`` parameter accepted by
    the Polymarket CLOB ``/prices-history`` endpoint.

    Examples
    --------
    >>> PriceInterval.ONE_DAY
    <PriceInterval.ONE_DAY: '1d'>
    >>> str(PriceInterval.ONE_DAY)
    '1d'
    """

    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    MAX = "max"
    ALL = "all"


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class PolymarketConfig:
    """Configuration for the Polymarket API client.

    Controls base URLs for the three API endpoints (Gamma, CLOB, Data),
    HTTP timeout, and rate-limit settings. Polymarket APIs are public
    and do not require authentication.

    Parameters
    ----------
    gamma_base_url : str
        Base URL for the Gamma API
        (default: ``GAMMA_BASE_URL``).
    clob_base_url : str
        Base URL for the CLOB API
        (default: ``CLOB_BASE_URL``).
    data_base_url : str
        Base URL for the Data API
        (default: ``DATA_BASE_URL``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    rate_limit_per_second : float
        Maximum number of requests per second
        (default: ``DEFAULT_RATE_LIMIT_PER_SECOND`` = 1.5).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = PolymarketConfig()
    >>> config.timeout
    30.0
    >>> config.gamma_base_url
    'https://gamma-api.polymarket.com'
    """

    gamma_base_url: str = GAMMA_BASE_URL
    clob_base_url: str = CLOB_BASE_URL
    data_base_url: str = DATA_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    rate_limit_per_second: float = DEFAULT_RATE_LIMIT_PER_SECOND

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
        if self.rate_limit_per_second <= 0:
            raise ValueError(
                f"rate_limit_per_second must be positive, "
                f"got {self.rate_limit_per_second}"
            )


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    base_wait : float
        Base wait time between retries in seconds (default: 1.0).
    max_wait : float
        Maximum wait time between retries in seconds (default: 30.0).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = RetryConfig(max_attempts=5, base_wait=2.0)
    >>> config.max_attempts
    5
    """

    max_attempts: int = 3
    base_wait: float = 1.0
    max_wait: float = 30.0

    def __post_init__(self) -> None:
        """Validate retry configuration value ranges.

        Raises
        ------
        ValueError
            If any configuration value is outside its valid range.
        """
        if not (1 <= self.max_attempts <= 10):
            raise ValueError(
                f"max_attempts must be between 1 and 10, got {self.max_attempts}"
            )
        if self.base_wait < 0:
            raise ValueError(f"base_wait must be non-negative, got {self.base_wait}")
        if self.max_wait < 0:
            raise ValueError(f"max_wait must be non-negative, got {self.max_wait}")


__all__ = [
    "PolymarketConfig",
    "PriceInterval",
    "RetryConfig",
]
