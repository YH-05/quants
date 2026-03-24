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
AlphaVantageStorage
    SQLite storage layer for persisting Alpha Vantage data.
get_alphavantage_storage
    Factory function for ``AlphaVantageStorage`` with env-based path.
AlphaVantageCollector
    Orchestrator for collecting data via Client -> Storage flow.
CollectionResult
    Outcome of a single collect operation.
CollectionSummary
    Aggregated summary of multiple collection results.

Record Types
------------
DailyPriceRecord
    Daily OHLCV price record.
CompanyOverviewRecord
    Company profile and fundamentals record.
IncomeStatementRecord
    Income statement record.
BalanceSheetRecord
    Balance sheet record.
CashFlowRecord
    Cash flow statement record.
AnnualEarningsRecord
    Annual earnings record.
QuarterlyEarningsRecord
    Quarterly earnings record.
EconomicIndicatorRecord
    Economic indicator time-series record.
ForexDailyRecord
    Daily forex exchange rate record.

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
from market.alphavantage.collector import (
    AlphaVantageCollector,
    CollectionResult,
    CollectionSummary,
)
from market.alphavantage.errors import (
    AlphaVantageAPIError,
    AlphaVantageAuthError,
    AlphaVantageError,
    AlphaVantageParseError,
    AlphaVantageRateLimitError,
    AlphaVantageValidationError,
)
from market.alphavantage.models import (
    AnnualEarningsRecord,
    BalanceSheetRecord,
    CashFlowRecord,
    CompanyOverviewRecord,
    DailyPriceRecord,
    EarningsRecord,
    EconomicIndicatorRecord,
    ForexDailyRecord,
    IncomeStatementRecord,
    QuarterlyEarningsRecord,
)
from market.alphavantage.parser import (
    parse_company_overview,
    parse_crypto_time_series,
    parse_earnings,
    parse_economic_indicator,
    parse_financial_statements,
    parse_forex_rate,
    parse_fx_time_series,
    parse_global_quote,
    parse_time_series,
)
from market.alphavantage.rate_limiter import (
    AsyncDualWindowRateLimiter,
    DualWindowRateLimiter,
)
from market.alphavantage.session import AlphaVantageSession
from market.alphavantage.storage import AlphaVantageStorage, get_alphavantage_storage
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
    "AlphaVantageCollector",
    "AlphaVantageConfig",
    "AlphaVantageError",
    "AlphaVantageParseError",
    "AlphaVantageRateLimitError",
    "AlphaVantageSession",
    "AlphaVantageStorage",
    "AlphaVantageValidationError",
    "AnnualEarningsRecord",
    "AsyncDualWindowRateLimiter",
    "BalanceSheetRecord",
    "CashFlowRecord",
    "CollectionResult",
    "CollectionSummary",
    "CompanyOverviewRecord",
    "CryptoFunction",
    "DailyPriceRecord",
    "DualWindowRateLimiter",
    "EarningsRecord",
    "EconomicIndicator",
    "EconomicIndicatorRecord",
    "FetchOptions",
    "ForexDailyRecord",
    "ForexFunction",
    "FundamentalFunction",
    "IncomeStatementRecord",
    "Interval",
    "OutputSize",
    "QuarterlyEarningsRecord",
    "RetryConfig",
    "TimeSeriesFunction",
    "get_alphavantage_cache",
    "get_alphavantage_storage",
    "parse_company_overview",
    "parse_crypto_time_series",
    "parse_earnings",
    "parse_economic_indicator",
    "parse_financial_statements",
    "parse_forex_rate",
    "parse_fx_time_series",
    "parse_global_quote",
    "parse_time_series",
]
