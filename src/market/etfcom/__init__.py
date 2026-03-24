"""ETF.com data retrieval module.

This package provides an API-based client for retrieving ETF data from
ETF.com, including ticker lists, fund flows, holdings, portfolio data,
performance, tradability, and structure information.

Modules
-------
constants : API URL, endpoint paths, default configuration.
errors : Exception hierarchy for ETF.com API operations.
types : Configuration dataclasses (AuthConfig, RetryConfig, ScrapingConfig).
session : curl_cffi-based HTTP session with OAuth authentication.
client : High-level API client with typed methods.
parser : JSON response parsing functions.
models : Frozen dataclasses for all record types.
storage : SQLite storage layer for persisting ETF.com data.
storage_constants : Table names and schema definitions.
collector : Orchestrator for collecting data via Client -> Storage flow.

Public API
----------
ETFComClient
    High-level API client with typed methods and automatic authentication.
ETFComCollector
    Orchestrator for collecting data via Client -> Storage flow.
ETFComStorage
    SQLite storage layer for persisting ETF.com data.
get_etfcom_storage
    Factory function for ``ETFComStorage`` with env-based path.
ETFComSession
    curl_cffi-based HTTP session with bot-blocking countermeasures.

Record Types
------------
TickerRecord
    ETF ticker metadata record.
FundFlowsRecord
    Daily fund flow record.
HoldingRecord
    Individual ETF holding record.
PortfolioRecord
    Portfolio composition record.
AllocationRecord
    Asset/sector allocation record.
TradabilityRecord
    Liquidity and tradability metrics record.
StructureRecord
    ETF structure and tax information record.
PerformanceRecord
    Performance metrics record.
QuoteRecord
    Delayed quote / pricing record.
CollectionResult
    Outcome of a single collect operation.
CollectionSummary
    Aggregated summary of multiple collection results.

Configuration Types
-------------------
AuthConfig
    API authentication credentials (OAuth token, API keys, URLs).
RetryConfig
    Configuration for retry behaviour with exponential backoff.
ScrapingConfig
    Configuration for ETF.com HTTP behaviour.
TickerInfo
    Ticker information from the ETF.com tickers API endpoint.

Error Classes
-------------
ETFComError
    Base exception for all ETF.com operations.
ETFComAPIError
    Exception raised when the ETF.com REST API returns an error response.
ETFComHTTPError
    Base exception for HTTP status code errors (403, 404, 429).
ETFComBlockedError
    Exception raised when bot-blocking is detected.
ETFComNotFoundError
    Exception raised when an ETF.com page returns HTTP 404 Not Found.
ETFComScrapingError
    Exception raised when HTML parsing / data extraction fails.
ETFComTimeoutError
    Exception raised when a page load or navigation times out.

Examples
--------
>>> from market.etfcom import ETFComClient
>>> client = ETFComClient()
>>> tickers = client.fetch_tickers()

>>> from market.etfcom import ETFComCollector
>>> collector = ETFComCollector(client=client, storage=storage)

>>> from market.etfcom import ETFComSession
>>> with ETFComSession() as session:
...     response = session.get_with_retry("https://api-v2.etf.com/tickers")
"""

from market.etfcom.client import ETFComClient
from market.etfcom.collector import ETFComCollector
from market.etfcom.errors import (
    ETFComAPIError,
    ETFComBlockedError,
    ETFComError,
    ETFComHTTPError,
    ETFComNotFoundError,
    ETFComScrapingError,
    ETFComTimeoutError,
)
from market.etfcom.models import (
    AllocationRecord,
    CollectionResult,
    CollectionSummary,
    FundFlowsRecord,
    HoldingRecord,
    PerformanceRecord,
    PortfolioRecord,
    QuoteRecord,
    StructureRecord,
    TickerRecord,
    TradabilityRecord,
)
from market.etfcom.session import ETFComSession
from market.etfcom.storage import ETFComStorage, get_etfcom_storage
from market.etfcom.types import (
    AuthConfig,
    RetryConfig,
    ScrapingConfig,
    TickerInfo,
)

__all__ = [
    # Client / Collector / Storage
    "ETFComClient",
    "ETFComCollector",
    "ETFComSession",
    "ETFComStorage",
    "get_etfcom_storage",
    # Record types (11 models)
    "AllocationRecord",
    "CollectionResult",
    "CollectionSummary",
    "FundFlowsRecord",
    "HoldingRecord",
    "PerformanceRecord",
    "PortfolioRecord",
    "QuoteRecord",
    "StructureRecord",
    "TickerRecord",
    "TradabilityRecord",
    # Configuration types
    "AuthConfig",
    "RetryConfig",
    "ScrapingConfig",
    "TickerInfo",
    # Error classes (7 types)
    "ETFComAPIError",
    "ETFComBlockedError",
    "ETFComError",
    "ETFComHTTPError",
    "ETFComNotFoundError",
    "ETFComScrapingError",
    "ETFComTimeoutError",
]
