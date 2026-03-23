"""Polymarket prediction market API client package.

This package provides a client for the Polymarket prediction market APIs
(Gamma, CLOB, Data) to retrieve market data, prices, order books, and trades.

Modules
-------
constants : API URLs, allowed hosts, default configuration values.
errors : Exception hierarchy for Polymarket API operations.
types : Configuration dataclasses and enums (PolymarketConfig, PriceInterval).
session : httpx-based HTTP session with rate limiting and SSRF prevention.
models : Pydantic V2 response models for API data.
cache : Cache helper with 6-tier TTL constants.
client : High-level API client with caching.
collector : Data collection orchestrator (Client -> Storage).

Public API
----------
PolymarketClient
    High-level API client with typed methods and caching.
PolymarketCollector
    Data collection orchestrator coordinating Client -> Storage flow.
CollectionResult
    Frozen dataclass capturing collection statistics and errors.
PolymarketConfig
    Configuration for API base URLs and HTTP behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.
FetchOptions
    Options for controlling cache behaviour per request.
PriceInterval
    Enum for historical price data query intervals.

Response Models
---------------
PolymarketEvent
    A top-level event containing one or more markets.
PolymarketMarket
    A prediction market with tokens.
OrderBook
    Full order book snapshot for a market.
OrderBookLevel
    Single price level in an order book.
TradeRecord
    A single trade execution record.
PricePoint
    Single historical price data point.

Error Classes
-------------
PolymarketError
    Base exception for all Polymarket API operations.
PolymarketAPIError
    Exception raised when the API returns an error response.
PolymarketRateLimitError
    Exception raised when the API rate limit is exceeded.
PolymarketValidationError
    Exception raised when data validation fails.
PolymarketNotFoundError
    Exception raised when a requested resource is not found.
"""

from market.polymarket.client import PolymarketClient
from market.polymarket.collector import CollectionResult, PolymarketCollector
from market.polymarket.errors import (
    PolymarketAPIError,
    PolymarketError,
    PolymarketNotFoundError,
    PolymarketRateLimitError,
    PolymarketValidationError,
)
from market.polymarket.models import (
    OrderBook,
    OrderBookLevel,
    PolymarketEvent,
    PolymarketMarket,
    PricePoint,
    TradeRecord,
)
from market.polymarket.session import PolymarketSession
from market.polymarket.types import (
    FetchOptions,
    PolymarketConfig,
    PriceInterval,
    RetryConfig,
)

__all__ = [
    "CollectionResult",
    "FetchOptions",
    "OrderBook",
    "OrderBookLevel",
    "PolymarketAPIError",
    "PolymarketClient",
    "PolymarketCollector",
    "PolymarketConfig",
    "PolymarketError",
    "PolymarketEvent",
    "PolymarketMarket",
    "PolymarketNotFoundError",
    "PolymarketRateLimitError",
    "PolymarketSession",
    "PolymarketValidationError",
    "PriceInterval",
    "PricePoint",
    "RetryConfig",
    "TradeRecord",
]
