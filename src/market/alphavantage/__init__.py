"""Alpha Vantage API client module.

This package provides a client for the Alpha Vantage API
(https://www.alphavantage.co/) to retrieve US stock market data,
fundamental data, forex rates, cryptocurrency data, and economic indicators.

Modules
-------
constants : API URL, environment variable names, default configuration.
errors : Exception hierarchy for Alpha Vantage API operations.
types : Configuration dataclasses, API parameter Enums.
session : httpx-based HTTP session with rate limiting and retry logic.
client : High-level API client with caching.
cache : Cache helper with TTL constants.
rate_limiter : Dual-window sliding rate limiter (sync and async).
parser : JSON response parsing functions.

Public API
----------
AlphaVantageClient
    High-level API client with typed methods and caching.
AlphaVantageSession
    httpx-based HTTP session with rate limiting.
AlphaVantageConfig
    Configuration for authentication and HTTP behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.
FetchOptions
    Options for controlling cache behaviour per request.

Enums
-----
OutputSize
    Output size parameter (COMPACT / FULL).
Interval
    Intraday interval parameter (1min / 5min / 15min / 30min / 60min).
TimeSeriesFunction
    Time series API function names.
FundamentalFunction
    Fundamental data API function names.
ForexFunction
    Forex API function names.
CryptoFunction
    Cryptocurrency API function names.
EconomicIndicator
    Economic indicator API function names.

Rate Limiters
-------------
DualWindowRateLimiter
    Thread-safe dual-window sliding rate limiter.
AsyncDualWindowRateLimiter
    Async-safe dual-window sliding rate limiter.

Error Classes
-------------
AlphaVantageError
    Base exception for all Alpha Vantage API operations.
AlphaVantageAPIError
    Exception raised when the API returns an error response.
AlphaVantageRateLimitError
    Exception raised when the API rate limit is exceeded.
AlphaVantageValidationError
    Exception raised when data validation fails.
AlphaVantageParseError
    Exception raised when response parsing fails.
AlphaVantageAuthError
    Exception raised when authentication fails.
"""

from market.alphavantage.cache import (
    COMPANY_OVERVIEW_TTL,
    CRYPTO_TTL,
    ECONOMIC_INDICATOR_TTL,
    FOREX_TTL,
    FUNDAMENTALS_TTL,
    GLOBAL_QUOTE_TTL,
    TIME_SERIES_DAILY_TTL,
    TIME_SERIES_INTRADAY_TTL,
    get_alphavantage_cache,
)
from market.alphavantage.client import AlphaVantageClient
from market.alphavantage.errors import (
    AlphaVantageAPIError,
    AlphaVantageAuthError,
    AlphaVantageError,
    AlphaVantageParseError,
    AlphaVantageRateLimitError,
    AlphaVantageValidationError,
)
from market.alphavantage.parser import (
    parse_company_overview,
    parse_earnings,
    parse_economic_indicator,
    parse_financial_statements,
    parse_forex_rate,
    parse_global_quote,
    parse_time_series,
)
from market.alphavantage.rate_limiter import (
    AsyncDualWindowRateLimiter,
    DualWindowRateLimiter,
)
from market.alphavantage.session import AlphaVantageSession
from market.alphavantage.types import (
    AlphaVantageConfig,
    CryptoFunction,
    EconomicIndicator,
    FetchOptions,
    ForexFunction,
    FundamentalFunction,
    Interval,
    OutputSize,
    RetryConfig,
    TimeSeriesFunction,
)

__all__ = [
    "COMPANY_OVERVIEW_TTL",
    "CRYPTO_TTL",
    "ECONOMIC_INDICATOR_TTL",
    "FOREX_TTL",
    "FUNDAMENTALS_TTL",
    "GLOBAL_QUOTE_TTL",
    "TIME_SERIES_DAILY_TTL",
    "TIME_SERIES_INTRADAY_TTL",
    "AlphaVantageAPIError",
    "AlphaVantageAuthError",
    "AlphaVantageClient",
    "AlphaVantageConfig",
    "AlphaVantageError",
    "AlphaVantageParseError",
    "AlphaVantageRateLimitError",
    "AlphaVantageSession",
    "AlphaVantageValidationError",
    "AsyncDualWindowRateLimiter",
    "CryptoFunction",
    "DualWindowRateLimiter",
    "EconomicIndicator",
    "FetchOptions",
    "ForexFunction",
    "FundamentalFunction",
    "Interval",
    "OutputSize",
    "RetryConfig",
    "TimeSeriesFunction",
    "get_alphavantage_cache",
    "parse_company_overview",
    "parse_earnings",
    "parse_economic_indicator",
    "parse_financial_statements",
    "parse_forex_rate",
    "parse_global_quote",
    "parse_time_series",
]
