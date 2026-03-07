"""ETF.com scraping module for market data retrieval.

This package provides tools for scraping ETF data from ETF.com,
including ETF profiles, fund flows, screener data, and classifications.

Classes
-------
TickerCollector
    Scrapes the ETF.com screener page for ETF ticker lists.
FundamentalsCollector
    Scrapes individual ETF profile pages for key-value fundamental data.
FundFlowsCollector
    Scrapes the fund flows page for daily flow data.
HistoricalFundFlowsCollector
    Fetches historical fund flow data via the ETF.com REST API.
ETFComSession
    curl_cffi-based HTTP session with bot-blocking countermeasures.

Error Classes
-------------
ETFComError
    Base exception for all ETF.com scraping operations.
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

Data Types
----------
ETFRecord
    Parsed ETF metadata record with normalised field types.
FundFlowRecord
    A single daily fund flow record for an ETF.
FundamentalsRecord
    A single ETF fundamentals record from an ETF.com profile page.
HistoricalFundFlowRecord
    A single daily historical fund flow record from the ETF.com REST API.
RetryConfig
    Configuration for retry behaviour with exponential backoff.
ScrapingConfig
    Configuration for ETF.com scraping behaviour.
TickerInfo
    Ticker information from the ETF.com tickers API endpoint.

Examples
--------
>>> from market.etfcom import TickerCollector
>>> collector = TickerCollector()
>>> df = collector.fetch()

>>> from market.etfcom import FundamentalsCollector
>>> collector = FundamentalsCollector()
>>> df = collector.fetch(tickers=["SPY", "VOO"])

>>> from market.etfcom import ETFComSession
>>> with ETFComSession() as session:
...     response = session.get_with_retry("https://www.etf.com/SPY")
"""

from market.etfcom.collectors import (
    FundamentalsCollector,
    FundFlowsCollector,
    HistoricalFundFlowsCollector,
    TickerCollector,
)
from market.etfcom.errors import (
    ETFComAPIError,
    ETFComBlockedError,
    ETFComError,
    ETFComHTTPError,
    ETFComNotFoundError,
    ETFComScrapingError,
    ETFComTimeoutError,
)
from market.etfcom.session import ETFComSession
from market.etfcom.types import (
    ETFRecord,
    FundamentalsRecord,
    FundFlowRecord,
    HistoricalFundFlowRecord,
    RetryConfig,
    ScrapingConfig,
    TickerInfo,
)

__all__ = [
    "ETFComAPIError",
    "ETFComBlockedError",
    "ETFComError",
    "ETFComHTTPError",
    "ETFComNotFoundError",
    "ETFComScrapingError",
    "ETFComSession",
    "ETFComTimeoutError",
    "ETFRecord",
    "FundFlowRecord",
    "FundFlowsCollector",
    "FundamentalsCollector",
    "FundamentalsRecord",
    "HistoricalFundFlowRecord",
    "HistoricalFundFlowsCollector",
    "RetryConfig",
    "ScrapingConfig",
    "TickerCollector",
    "TickerInfo",
]
