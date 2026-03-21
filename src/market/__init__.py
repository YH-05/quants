"""Market package for financial market data analysis.

This package provides core infrastructure for market data handling including:
- Data fetching (Yahoo Finance, FRED, NASDAQ, EDINET, EODHD, etc.)
- Data export (JSON, CSV, SQLite, Agent-optimized JSON)
- Type definitions for market data
- JSON schema definitions for validation
- Error handling
- ASEAN market data (SGX, Bursa, SET, IDX, HOSE, PSE)

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
asean_common
    ASEAN market common foundation (constants, types, storage, screener)
eodhd
    EODHD API client (global financial data)
factset
    FactSet API integration (planned)
export
    Data export utilities
polymarket
    Polymarket prediction market data (events, markets, order books, trades)
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
    EDINET_DB, BSE, JQUANTS, EDINET_API, POLYMARKET)
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
AseanMarket
    Enum for 6 ASEAN exchanges (SGX, Bursa, SET, IDX, HOSE, PSE)
TickerRecord
    Frozen dataclass representing an ASEAN ticker
AseanTickerStorage
    DuckDB storage layer for ASEAN ticker master data
EodhdClient
    Skeleton API client for EODHD financial data
EodhdConfig
    Configuration for EODHD API key and HTTP behaviour
SgxConfig
    Configuration for SGX (Singapore Exchange) data retrieval
BursaConfig
    Configuration for Bursa Malaysia data retrieval
SetConfig
    Configuration for SET (Stock Exchange of Thailand) data retrieval
IdxConfig
    Configuration for IDX (Indonesia Stock Exchange) data retrieval
HoseConfig
    Configuration for HOSE (Ho Chi Minh Stock Exchange) data retrieval
PseConfig
    Configuration for PSE (Philippine Stock Exchange) data retrieval
"""

from .asean_common import (
    AseanError,
    AseanLookupError,
    AseanMarket,
    AseanScreenerError,
    AseanStorageError,
    AseanTickerStorage,
    TickerRecord,
)
from .bse import (
    Announcement,
    BhavcopyCollector,
    BhavcopyType,
    BseAPIError,
    BseConfig,
    BseError,
    BseParseError,
    BseRateLimitError,
    BseSession,
    BseValidationError,
    CorporateAction,
    CorporateCollector,
    FinancialResult,
    IndexCollector,
    IndexName,
    QuoteCollector,
    ScripGroup,
    ScripQuote,
)
from .bse import (
    RetryConfig as BseRetryConfig,
)
from .bursa import (
    BursaAPIError,
    BursaConfig,
    BursaError,
    BursaParseError,
    BursaRateLimitError,
    BursaValidationError,
)
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
from .edinet_api import EdinetApiClient
from .eodhd import (
    EodhdAPIError,
    EodhdAuthError,
    EodhdClient,
    EodhdConfig,
    EodhdError,
    EodhdRateLimitError,
    EodhdValidationError,
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
from .hose import (
    HoseAPIError,
    HoseConfig,
    HoseError,
    HoseParseError,
    HoseRateLimitError,
    HoseValidationError,
)
from .idx import (
    IdxAPIError,
    IdxConfig,
    IdxError,
    IdxParseError,
    IdxRateLimitError,
    IdxValidationError,
)
from .jquants import JQuantsClient
from .nasdaq import (
    ScreenerCollector,
    ScreenerFilter,
)
from .polymarket import (
    PolymarketAPIError,
    PolymarketClient,
    PolymarketConfig,
    PolymarketError,
    PolymarketEvent,
    PolymarketMarket,
    PolymarketNotFoundError,
    PolymarketRateLimitError,
    PolymarketValidationError,
)
from .pse import (
    PseAPIError,
    PseConfig,
    PseError,
    PseParseError,
    PseRateLimitError,
    PseValidationError,
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
from .set_exchange import (
    SetAPIError,
    SetConfig,
    SetError,
    SetParseError,
    SetRateLimitError,
    SetValidationError,
)
from .sgx import (
    SgxAPIError,
    SgxConfig,
    SgxError,
    SgxParseError,
    SgxRateLimitError,
    SgxValidationError,
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
    # BSE
    "Announcement",
    # ASEAN common
    "AseanError",
    "AseanLookupError",
    "AseanMarket",
    "AseanScreenerError",
    "AseanStorageError",
    "AseanTickerStorage",
    "BhavcopyCollector",
    "BhavcopyType",
    # Bloomberg errors
    "BloombergConnectionError",
    "BloombergDataError",
    "BloombergError",
    "BloombergSessionError",
    "BloombergValidationError",
    "BseAPIError",
    "BseConfig",
    "BseError",
    "BseParseError",
    "BseRateLimitError",
    "BseRetryConfig",
    "BseSession",
    "BseValidationError",
    # Bursa (Malaysia)
    "BursaAPIError",
    "BursaConfig",
    "BursaError",
    "BursaParseError",
    "BursaRateLimitError",
    "BursaValidationError",
    # Core
    "CacheConfig",
    "CacheError",
    "CorporateAction",
    "CorporateCollector",
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
    # EDINET (DB API)
    "EdinetAPIError",
    # EDINET (Disclosure API)
    "EdinetApiClient",
    "EdinetClient",
    "EdinetConfig",
    "EdinetError",
    "EdinetParseError",
    "EdinetRateLimitError",
    "EdinetStorage",
    "EdinetSyncer",
    "EdinetValidationError",
    # EODHD
    "EodhdAPIError",
    "EodhdAuthError",
    "EodhdClient",
    "EodhdConfig",
    "EodhdError",
    "EodhdRateLimitError",
    "EodhdValidationError",
    "ErrorCode",
    "ExportConfig",
    "ExportError",
    # FRED errors
    "FREDError",
    "FREDFetchError",
    "FREDValidationError",
    "FinancialResult",
    "FundFlowsCollector",
    "FundamentalsCollector",
    # HOSE (Vietnam)
    "HoseAPIError",
    "HoseConfig",
    "HoseError",
    "HoseParseError",
    "HoseRateLimitError",
    "HoseValidationError",
    # IDX (Indonesia)
    "IdxAPIError",
    "IdxConfig",
    "IdxError",
    "IdxParseError",
    "IdxRateLimitError",
    "IdxValidationError",
    "IndexCollector",
    "IndexName",
    # J-Quants
    "JQuantsClient",
    "MarketConfig",
    "MarketDataResult",
    "MarketError",
    # NASDAQ
    "NasdaqAPIError",
    "NasdaqError",
    "NasdaqParseError",
    "NasdaqRateLimitError",
    # Polymarket
    "PolymarketAPIError",
    "PolymarketClient",
    "PolymarketConfig",
    "PolymarketError",
    "PolymarketEvent",
    "PolymarketMarket",
    "PolymarketNotFoundError",
    "PolymarketRateLimitError",
    "PolymarketValidationError",
    # PSE (Philippines)
    "PseAPIError",
    "PseConfig",
    "PseError",
    "PseParseError",
    "PseRateLimitError",
    "PseValidationError",
    "QuoteCollector",
    "ScreenerCollector",
    "ScreenerFilter",
    "ScripGroup",
    "ScripQuote",
    # SET (Thailand)
    "SetAPIError",
    "SetConfig",
    "SetError",
    "SetParseError",
    "SetRateLimitError",
    "SetValidationError",
    # SGX (Singapore)
    "SgxAPIError",
    "SgxConfig",
    "SgxError",
    "SgxParseError",
    "SgxRateLimitError",
    "SgxValidationError",
    "StockDataMetadata",
    "TickerCollector",
    "TickerRecord",
    "ValidationError",
    "validate_config",
    "validate_economic_metadata",
    "validate_stock_metadata",
]

__version__ = "0.1.0"
