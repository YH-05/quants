"""EDINET DB API module for Japanese listed company financial data.

This package provides tools for accessing the EDINET DB REST API
(https://edinetdb.jp), which provides structured financial data
extracted from securities reports filed with the Financial Services
Agency of Japan (FSA).

Modules
-------
client : EdinetClient for all 10 API endpoints with retry and rate limiting.
constants : API URLs, environment variable names, rate limit settings,
    DB path constants, and ranking metric definitions.
errors : Exception hierarchy for EDINET DB API operations.
rate_limiter : DailyRateLimiter for daily API call counting with persistence.
storage : EdinetStorage for DuckDB-backed data persistence (8 tables).
syncer : EdinetSyncer for 6-phase sync orchestration with resume support.
types : Configuration dataclasses, data record dataclasses, and type aliases.

Public API
----------
EdinetClient
    Synchronous HTTP client for all 10 EDINET DB API endpoints.
EdinetStorage
    DuckDB storage layer managing 8 tables for EDINET data.
EdinetSyncer
    6-phase sync orchestrator with checkpoint-based resume support.

Configuration
-------------
EdinetConfig
    Configuration for EDINET DB API client behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.
DailyRateLimiter
    Daily API call limit manager with JSON file persistence.

Error Classes
-------------
EdinetError
    Base exception for all EDINET DB API operations.
EdinetAPIError
    Exception raised when the EDINET DB API returns an error response.
EdinetRateLimitError
    Exception raised when the daily API call limit is exceeded.
EdinetValidationError
    Exception raised when input validation fails.
EdinetParseError
    Exception raised when API response parsing fails.

Data Types
----------
Company
    Company master data (~3,848 rows).
FinancialRecord
    Annual financial statements (24 indicators).
RatioRecord
    Computed financial ratios (13 ratios).
AnalysisResult
    AI-generated financial health analysis.
TextBlock
    Securities report text excerpts.
RankingEntry
    Metric-based company rankings.
Industry
    Industry master data (34 classifications).
SyncProgress
    Sync state for resume support.

Examples
--------
>>> from market.edinet import EdinetClient, EdinetConfig
>>> config = EdinetConfig(api_key="your_key")
>>> with EdinetClient(config=config) as client:
...     companies = client.list_companies()
...     print(f"Found {len(companies)} companies")
"""

from market.edinet.client import EdinetClient
from market.edinet.errors import (
    EdinetAPIError,
    EdinetError,
    EdinetParseError,
    EdinetRateLimitError,
    EdinetValidationError,
)
from market.edinet.rate_limiter import DailyRateLimiter
from market.edinet.storage import EdinetStorage
from market.edinet.syncer import EdinetSyncer
from market.edinet.types import (
    AnalysisResult,
    Company,
    EdinetConfig,
    FinancialRecord,
    Industry,
    RankingEntry,
    RatioRecord,
    RetryConfig,
    SyncProgress,
    TextBlock,
)

__all__ = [
    "AnalysisResult",
    "Company",
    "DailyRateLimiter",
    "EdinetAPIError",
    "EdinetClient",
    "EdinetConfig",
    "EdinetError",
    "EdinetParseError",
    "EdinetRateLimitError",
    "EdinetStorage",
    "EdinetSyncer",
    "EdinetValidationError",
    "FinancialRecord",
    "Industry",
    "RankingEntry",
    "RatioRecord",
    "RetryConfig",
    "SyncProgress",
    "TextBlock",
]
