"""Market package for financial market data analysis.

This package provides core infrastructure for market data handling including:
- Data fetching (Yahoo Finance, FRED, NASDAQ, EDINET, etc.)
- Data export (JSON, CSV, SQLite, Agent-optimized JSON)
- Type definitions for market data
- JSON schema definitions for validation
- Error handling

Submodules
----------
yfinance
    Yahoo Finance data fetcher
fred
    Federal Reserve Economic Data (FRED) API integration
etfcom
    ETF.com scraper (ticker, fundamentals, fund flows)
nasdaq
    NASDAQ Stock Screener API (stock screening data)
edinet
    EDINET DB API (Japanese listed company financial data)
factset
    FactSet API integration (planned)
export
    Data export utilities
alternative
    Alternative data sources (planned)
schema
    JSON schema definitions (Pydantic V2 models)

Public API
----------
DataExporter
    Export market data to various formats
DataSource
    Data source enum (YFINANCE, FRED, LOCAL, BLOOMBERG, FACTSET, ETF_COM, NASDAQ,
    EDINET_DB)
MarketDataResult
    Result of market data fetch operation
AnalysisResult
    Result of analysis operation
AgentOutput
    Structured output for AI agents
ExportError
    Exception for export operations
StockDataMetadata
    Metadata for stock price data
EconomicDataMetadata
    Metadata for economic indicator data
MarketConfig
    Complete market data configuration
ScreenerCollector
    NASDAQ Stock Screener data collector
ScreenerFilter
    Filter conditions for the NASDAQ Stock Screener API
EdinetClient
    Synchronous HTTP client for all 10 EDINET DB API endpoints
EdinetStorage
    DuckDB storage layer managing 8 tables for EDINET data
EdinetSyncer
    6-phase sync orchestrator with checkpoint-based resume support
"""

from .edinet import (
    DailyRateLimiter,
    EdinetAPIError,
    EdinetClient,
    EdinetConfig,
    EdinetError,
    EdinetParseError,
    EdinetRateLimitError,
    EdinetStorage,
    EdinetSyncer,
    EdinetValidationError,
)
from .errors import (
    BloombergConnectionError,
    BloombergDataError,
    BloombergError,
    BloombergSessionError,
    BloombergValidationError,
    CacheError,
    DataFetchError,
    ErrorCode,
    ExportError,
    FREDError,
    FREDFetchError,
    FREDValidationError,
    MarketError,
    NasdaqAPIError,
    NasdaqError,
    NasdaqParseError,
    NasdaqRateLimitError,
    ValidationError,
)
from .etfcom import (
    ETFComBlockedError,
    ETFComError,
    ETFComScrapingError,
    ETFComTimeoutError,
    FundamentalsCollector,
    FundFlowsCollector,
    TickerCollector,
)
from .export import DataExporter
from .nasdaq import (
    ScreenerCollector,
    ScreenerFilter,
)
from .schema import (
    CacheConfig,
    DataSourceConfig,
    DateRange,
    EconomicDataMetadata,
    ExportConfig,
    MarketConfig,
    StockDataMetadata,
    validate_config,
    validate_economic_metadata,
    validate_stock_metadata,
)
from .types import (
    AgentOutput,
    AgentOutputMetadata,
    AnalysisResult,
    DataSource,
    MarketDataResult,
)

__all__ = [
    "AgentOutput",
    "AgentOutputMetadata",
    "AnalysisResult",
    # Bloomberg errors
    "BloombergConnectionError",
    "BloombergDataError",
    "BloombergError",
    "BloombergSessionError",
    "BloombergValidationError",
    # Core
    "CacheConfig",
    "CacheError",
    "DailyRateLimiter",
    "DataExporter",
    "DataFetchError",
    "DataSource",
    "DataSourceConfig",
    "DateRange",
    # ETF.com
    "ETFComBlockedError",
    "ETFComError",
    "ETFComScrapingError",
    "ETFComTimeoutError",
    "EconomicDataMetadata",
    # EDINET
    "EdinetAPIError",
    "EdinetClient",
    "EdinetConfig",
    "EdinetError",
    "EdinetParseError",
    "EdinetRateLimitError",
    "EdinetStorage",
    "EdinetSyncer",
    "EdinetValidationError",
    "ErrorCode",
    "ExportConfig",
    "ExportError",
    # FRED errors
    "FREDError",
    "FREDFetchError",
    "FREDValidationError",
    "FundFlowsCollector",
    "FundamentalsCollector",
    "MarketConfig",
    "MarketDataResult",
    "MarketError",
    # NASDAQ
    "NasdaqAPIError",
    "NasdaqError",
    "NasdaqParseError",
    "NasdaqRateLimitError",
    "ScreenerCollector",
    "ScreenerFilter",
    "StockDataMetadata",
    "TickerCollector",
    "ValidationError",
    "validate_config",
    "validate_economic_metadata",
    "validate_stock_metadata",
]

__version__ = "0.1.0"
