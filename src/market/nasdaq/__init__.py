"""NASDAQ Stock Screener and API client module for market data retrieval.

This package provides tools for fetching stock screening data from the
NASDAQ Stock Screener API (https://api.nasdaq.com/api/screener/stocks)
and a high-level typed API client for additional NASDAQ endpoints.

Modules
-------
collector : ScreenerCollector (DataCollector ABC) for stock screening data.
constants : API URLs, headers, and configuration defaults.
errors : Exception hierarchy for NASDAQ API operations.
parser : JSON response parser and numeric cleaning utilities.
session : NasdaqSession with bot-blocking countermeasures.
types : Filter enums, configuration dataclasses, and type aliases.
client : NasdaqClient — typed API client with caching.
client_types : Record dataclasses for NasdaqClient endpoints.
client_cache : TTL constants and cache helper for NasdaqClient.
client_parsers : Response parsing helpers for NasdaqClient.

Public API
----------
ScreenerCollector
    Collector for NASDAQ Stock Screener data (DataCollector ABC).
NasdaqClient
    High-level typed API client for NASDAQ endpoints with caching.
NasdaqSession
    curl_cffi-based HTTP session with bot-blocking countermeasures.
ScreenerFilter
    Filter conditions for the NASDAQ Stock Screener API.
NasdaqConfig
    Configuration for NASDAQ Stock Screener HTTP behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.

Enums
-----
Exchange, MarketCap, Sector, Recommendation, Region, Country
    Filter enums for the NASDAQ Screener API.
MoverSection
    Section identifier for market movers data.

Error Classes
-------------
NasdaqError
    Base exception for all NASDAQ API operations.
NasdaqAPIError
    Exception raised when the NASDAQ API returns an error response.
NasdaqRateLimitError
    Exception raised when the NASDAQ API rate limit is exceeded.
NasdaqParseError
    Exception raised when NASDAQ API response parsing fails.

Data Types
----------
StockRecord
    A single stock record from the NASDAQ Screener API response.
FilterCategory
    Type alias for filter category Enum classes.
NasdaqFetchOptions
    Per-request cache control for NasdaqClient.
EarningsRecord, DividendCalendarRecord, SplitRecord, IpoRecord
    Calendar endpoint record types.
MarketMover, EtfRecord
    Market movers and ETF screener record types.
ShortInterestRecord, DividendRecord
    Quote data endpoint record types.
InsiderTrade, InstitutionalHolding, FinancialStatement, FinancialStatementRow
    Company data endpoint record types.
EarningsForecastPeriod, EarningsForecast, RatingCount, AnalystRatings,
TargetPrice, EarningsDate, AnalystSummary
    Analyst endpoint record types.

Cache Constants
---------------
get_nasdaq_cache
    Factory function for SQLiteCache configured for NASDAQ data.

Examples
--------
>>> from market.nasdaq import ScreenerCollector, ScreenerFilter, Exchange
>>> collector = ScreenerCollector()
>>> df = collector.fetch(filter=ScreenerFilter(exchange=Exchange.NASDAQ))

>>> from market.nasdaq import NasdaqClient
>>> with NasdaqClient() as client:
...     movers = client.get_market_movers()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# ---------------------------------------------------------------------------
# Eagerly imported: modules that do NOT trigger market.cache -> market.errors
# ---------------------------------------------------------------------------
from market.nasdaq.client_types import (
    AnalystRatings,
    AnalystSummary,
    DividendCalendarRecord,
    DividendRecord,
    EarningsDate,
    EarningsForecast,
    EarningsForecastPeriod,
    EarningsRecord,
    EtfRecord,
    FinancialStatement,
    FinancialStatementRow,
    InsiderTrade,
    InstitutionalHolding,
    IpoRecord,
    MarketMover,
    MoverSection,
    NasdaqFetchOptions,
    RatingCount,
    ShortInterestRecord,
    SplitRecord,
    TargetPrice,
)
from market.nasdaq.collector import ScreenerCollector
from market.nasdaq.errors import (
    NasdaqAPIError,
    NasdaqError,
    NasdaqParseError,
    NasdaqRateLimitError,
)
from market.nasdaq.session import NasdaqSession
from market.nasdaq.types import (
    Country,
    Exchange,
    FilterCategory,
    MarketCap,
    NasdaqConfig,
    Recommendation,
    Region,
    RetryConfig,
    ScreenerFilter,
    Sector,
    StockRecord,
)

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient
    from market.nasdaq.client_cache import get_nasdaq_cache as get_nasdaq_cache

# ---------------------------------------------------------------------------
# Lazy imports to avoid circular dependency:
#   market.errors -> market.nasdaq.__init__ -> market.nasdaq.client
#   -> market.cache.cache -> market.errors
#
#   market.errors -> market.nasdaq.__init__ -> market.nasdaq.client_cache
#   -> market.cache.cache -> market.errors
# ---------------------------------------------------------------------------

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "NasdaqClient": ("market.nasdaq.client", "NasdaqClient"),
    "get_nasdaq_cache": ("market.nasdaq.client_cache", "get_nasdaq_cache"),
}


def __getattr__(name: str) -> Any:
    """Lazy import for NasdaqClient and get_nasdaq_cache to break circular dependency."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AnalystRatings",
    "AnalystSummary",
    "Country",
    "DividendCalendarRecord",
    "DividendRecord",
    "EarningsDate",
    "EarningsForecast",
    "EarningsForecastPeriod",
    "EarningsRecord",
    "EtfRecord",
    "Exchange",
    "FilterCategory",
    "FinancialStatement",
    "FinancialStatementRow",
    "InsiderTrade",
    "InstitutionalHolding",
    "IpoRecord",
    "MarketCap",
    "MarketMover",
    "MoverSection",
    "NasdaqAPIError",
    "NasdaqClient",
    "NasdaqConfig",
    "NasdaqError",
    "NasdaqFetchOptions",
    "NasdaqParseError",
    "NasdaqRateLimitError",
    "NasdaqSession",
    "RatingCount",
    "Recommendation",
    "Region",
    "RetryConfig",
    "ScreenerCollector",
    "ScreenerFilter",
    "Sector",
    "ShortInterestRecord",
    "SplitRecord",
    "StockRecord",
    "TargetPrice",
    "get_nasdaq_cache",
]
