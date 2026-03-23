"""Type definitions for the market.alphavantage module.

This module provides type definitions for Alpha Vantage API data retrieval
including:

- Configuration dataclasses (AlphaVantageConfig, RetryConfig, FetchOptions)
- API parameter Enums (OutputSize, Interval, TimeSeriesFunction,
  FundamentalFunction, ForexFunction, CryptoFunction, EconomicIndicator)

All dataclasses use ``frozen=True`` to ensure immutability.
All Enums inherit from ``str`` and ``Enum`` so they can be used directly
as string values in API query parameters.

See Also
--------
market.jquants.types : Similar type-definition pattern for the J-Quants module.
market.nasdaq.types : Similar ``str, Enum`` pattern for the NASDAQ module.
market.alphavantage.constants : Default values referenced by AlphaVantageConfig.
"""

from dataclasses import dataclass, field
from enum import Enum

from market.alphavantage.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_REQUESTS_PER_HOUR,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_TIMEOUT,
)

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class AlphaVantageConfig:
    """Configuration for Alpha Vantage API client.

    Controls authentication credentials, HTTP behaviour, polite delays,
    and rate limiting parameters.

    Parameters
    ----------
    api_key : str
        Alpha Vantage API key. If empty, read from
        ``ALPHA_VANTAGE_API_KEY`` environment variable at runtime.
        Excluded from ``repr`` output for security (CWE-532).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    polite_delay : float
        Minimum wait time between consecutive requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 2.5).
    delay_jitter : float
        Random jitter added to polite delay in seconds
        (default: ``DEFAULT_DELAY_JITTER`` = 0.5).
    requests_per_minute : int
        Maximum number of API requests per minute
        (default: ``DEFAULT_REQUESTS_PER_MINUTE`` = 25).
    requests_per_hour : int
        Maximum number of API requests per hour
        (default: ``DEFAULT_REQUESTS_PER_HOUR`` = 500).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = AlphaVantageConfig(api_key="demo")
    >>> config.timeout
    30.0
    >>> "demo" not in repr(config)  # api_key is hidden
    True
    """

    api_key: str = field(default="", repr=False)
    timeout: float = DEFAULT_TIMEOUT
    polite_delay: float = DEFAULT_POLITE_DELAY
    delay_jitter: float = DEFAULT_DELAY_JITTER
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE
    requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR

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
        if not (0.0 <= self.polite_delay <= 60.0):
            raise ValueError(
                f"polite_delay must be between 0.0 and 60.0, got {self.polite_delay}"
            )
        if not (0.0 <= self.delay_jitter <= 30.0):
            raise ValueError(
                f"delay_jitter must be between 0.0 and 30.0, got {self.delay_jitter}"
            )
        if not (1 <= self.requests_per_minute <= 1000):
            raise ValueError(
                f"requests_per_minute must be between 1 and 1000, "
                f"got {self.requests_per_minute}"
            )
        if not (1 <= self.requests_per_hour <= 10000):
            raise ValueError(
                f"requests_per_hour must be between 1 and 10000, "
                f"got {self.requests_per_hour}"
            )


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    exponential_base : float
        Base for exponential backoff calculation (default: 2.0).
    max_delay : float
        Maximum delay between retries in seconds (default: 30.0).
    initial_delay : float
        Initial delay between retries in seconds (default: 1.0).
    jitter : bool
        Whether to add random jitter to delays (default: True).

    Raises
    ------
    ValueError
        If max_attempts is outside its valid range.

    Examples
    --------
    >>> config = RetryConfig(max_attempts=5, exponential_base=3.0)
    >>> config.max_attempts
    5
    """

    max_attempts: int = 3
    exponential_base: float = 2.0
    max_delay: float = 30.0
    initial_delay: float = 1.0
    jitter: bool = True

    def __post_init__(self) -> None:
        """Validate retry configuration value ranges.

        Raises
        ------
        ValueError
            If max_attempts is outside its valid range.
        """
        if not (1 <= self.max_attempts <= 10):
            raise ValueError(
                f"max_attempts must be between 1 and 10, got {self.max_attempts}"
            )


@dataclass(frozen=True)
class FetchOptions:
    """Options for API data fetch requests.

    Parameters
    ----------
    use_cache : bool
        Whether to use cached data if available (default: True).
    force_refresh : bool
        Whether to force a fresh fetch, ignoring cache (default: False).

    Examples
    --------
    >>> options = FetchOptions(use_cache=False)
    >>> options.use_cache
    False
    """

    use_cache: bool = True
    force_refresh: bool = False


# =============================================================================
# API Parameter Enums
# =============================================================================


class OutputSize(str, Enum):
    """Output size parameter for Alpha Vantage time series endpoints.

    Controls the amount of data returned by time series API calls.

    Parameters
    ----------
    value : str
        The API query parameter value.

    Examples
    --------
    >>> OutputSize.COMPACT
    <OutputSize.COMPACT: 'compact'>
    >>> str(OutputSize.FULL)
    'full'
    """

    COMPACT = "compact"
    FULL = "full"


class Interval(str, Enum):
    """Intraday interval parameter for Alpha Vantage intraday endpoints.

    Specifies the time interval between two consecutive data points
    in the intraday time series.

    Parameters
    ----------
    value : str
        The API query parameter value (e.g., ``"1min"``, ``"60min"``).

    Examples
    --------
    >>> Interval.ONE_MIN
    <Interval.ONE_MIN: '1min'>
    >>> str(Interval.SIXTY_MIN)
    '60min'
    """

    ONE_MIN = "1min"
    FIVE_MIN = "5min"
    FIFTEEN_MIN = "15min"
    THIRTY_MIN = "30min"
    SIXTY_MIN = "60min"


class TimeSeriesFunction(str, Enum):
    """Function parameter for Alpha Vantage time series endpoints.

    Maps to the ``function`` query parameter in the Alpha Vantage API.

    Parameters
    ----------
    value : str
        The API ``function`` parameter value.

    Examples
    --------
    >>> TimeSeriesFunction.DAILY
    <TimeSeriesFunction.DAILY: 'TIME_SERIES_DAILY'>
    """

    DAILY = "TIME_SERIES_DAILY"
    DAILY_ADJUSTED = "TIME_SERIES_DAILY_ADJUSTED"
    WEEKLY = "TIME_SERIES_WEEKLY"
    MONTHLY = "TIME_SERIES_MONTHLY"
    INTRADAY = "TIME_SERIES_INTRADAY"


class FundamentalFunction(str, Enum):
    """Function parameter for Alpha Vantage fundamental data endpoints.

    Maps to the ``function`` query parameter for company fundamental data.

    Parameters
    ----------
    value : str
        The API ``function`` parameter value.

    Examples
    --------
    >>> FundamentalFunction.OVERVIEW
    <FundamentalFunction.OVERVIEW: 'OVERVIEW'>
    """

    OVERVIEW = "OVERVIEW"
    INCOME_STATEMENT = "INCOME_STATEMENT"
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW = "CASH_FLOW"
    EARNINGS = "EARNINGS"


class ForexFunction(str, Enum):
    """Function parameter for Alpha Vantage forex endpoints.

    Maps to the ``function`` query parameter for foreign exchange data.

    Parameters
    ----------
    value : str
        The API ``function`` parameter value.

    Examples
    --------
    >>> ForexFunction.EXCHANGE_RATE
    <ForexFunction.EXCHANGE_RATE: 'CURRENCY_EXCHANGE_RATE'>
    """

    EXCHANGE_RATE = "CURRENCY_EXCHANGE_RATE"
    FX_DAILY = "FX_DAILY"
    FX_WEEKLY = "FX_WEEKLY"
    FX_MONTHLY = "FX_MONTHLY"


class CryptoFunction(str, Enum):
    """Function parameter for Alpha Vantage cryptocurrency endpoints.

    Maps to the ``function`` query parameter for digital currency data.

    Parameters
    ----------
    value : str
        The API ``function`` parameter value.

    Examples
    --------
    >>> CryptoFunction.DAILY
    <CryptoFunction.DAILY: 'DIGITAL_CURRENCY_DAILY'>
    """

    DAILY = "DIGITAL_CURRENCY_DAILY"
    WEEKLY = "DIGITAL_CURRENCY_WEEKLY"
    MONTHLY = "DIGITAL_CURRENCY_MONTHLY"


class EconomicIndicator(str, Enum):
    """Function parameter for Alpha Vantage economic indicator endpoints.

    Maps to the ``function`` query parameter for macroeconomic data.

    Parameters
    ----------
    value : str
        The API ``function`` parameter value.

    Examples
    --------
    >>> EconomicIndicator.REAL_GDP
    <EconomicIndicator.REAL_GDP: 'REAL_GDP'>
    """

    REAL_GDP = "REAL_GDP"
    CPI = "CPI"
    INFLATION = "INFLATION"
    UNEMPLOYMENT = "UNEMPLOYMENT"
    TREASURY_YIELD = "TREASURY_YIELD"
    FEDERAL_FUNDS_RATE = "FEDERAL_FUNDS_RATE"


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "AlphaVantageConfig",
    "CryptoFunction",
    "EconomicIndicator",
    "FetchOptions",
    "ForexFunction",
    "FundamentalFunction",
    "Interval",
    "OutputSize",
    "RetryConfig",
    "TimeSeriesFunction",
]
