"""Common type definitions for the market package.

This module provides type definitions for market data analysis including:
- Data source configurations
- Market data results
- Analysis results
- Agent output structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd


class DataSource(str, Enum):
    """Data source types for market data fetching.

    Attributes
    ----------
    YFINANCE : str
        Yahoo Finance data source
    FRED : str
        Federal Reserve Economic Data
    LOCAL : str
        Local cache/database
    BLOOMBERG : str
        Bloomberg Terminal data source
    FACTSET : str
        FactSet data source
    ETF_COM : str
        ETF.com data source
    NASDAQ : str
        NASDAQ Stock Screener data source
    EDINET_DB : str
        EDINET DB API data source (Japanese listed company financials)
    BSE : str
        Bombay Stock Exchange data source
    JQUANTS : str
        J-Quants API data source (Japanese stock market data via JPX)
    EDINET_API : str
        EDINET disclosure API data source (FSA filings search/download)
    """

    YFINANCE = "yfinance"
    FRED = "fred"
    LOCAL = "local"
    BLOOMBERG = "bloomberg"
    FACTSET = "factset"
    ETF_COM = "etfcom"
    NASDAQ = "nasdaq"
    EDINET_DB = "edinet_db"
    BSE = "bse"
    JQUANTS = "jquants"
    EDINET_API = "edinet_api"


@dataclass
class MarketDataResult:
    """Result of a market data fetch operation.

    Parameters
    ----------
    symbol : str
        The symbol that was fetched
    data : pd.DataFrame
        The fetched OHLCV data
    source : DataSource
        Data source used
    fetched_at : datetime
        Timestamp when data was fetched
    from_cache : bool
        Whether data was retrieved from cache
    metadata : dict[str, Any]
        Additional metadata

    Examples
    --------
    >>> result = MarketDataResult(
    ...     symbol="AAPL",
    ...     data=df,
    ...     source=DataSource.YFINANCE,
    ...     fetched_at=datetime.now(),
    ...     from_cache=False,
    ... )
    """

    symbol: str
    data: pd.DataFrame
    source: DataSource
    fetched_at: datetime
    from_cache: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Check if the result contains no data."""
        return self.data.empty

    @property
    def row_count(self) -> int:
        """Get the number of rows in the data."""
        return len(self.data)


@dataclass
class AnalysisResult:
    """Result of an analysis operation.

    Parameters
    ----------
    symbol : str
        The symbol that was analyzed
    data : pd.DataFrame
        The analysis results
    indicators : dict[str, pd.Series]
        Calculated indicators
    statistics : dict[str, float]
        Summary statistics
    analyzed_at : datetime
        Timestamp of analysis

    Examples
    --------
    >>> result = AnalysisResult(
    ...     symbol="AAPL",
    ...     data=df,
    ...     indicators={"sma_20": sma_series},
    ...     statistics={"mean_return": 0.05},
    ... )
    """

    symbol: str
    data: pd.DataFrame
    indicators: dict[str, pd.Series] = field(default_factory=dict)
    statistics: dict[str, float] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentOutputMetadata:
    """Metadata for agent-consumable output.

    Parameters
    ----------
    generated_at : datetime
        Timestamp of generation
    version : str
        Output format version
    source : str
        Source module/function
    symbols : list[str]
        Symbols included
    period : str
        Data period
    """

    generated_at: datetime
    version: str = "1.0"
    source: str = ""
    symbols: list[str] = field(default_factory=list)
    period: str = ""


@dataclass
class AgentOutput:
    """Structured output for AI agents.

    Parameters
    ----------
    metadata : AgentOutputMetadata
        Output metadata
    summary : str
        Human-readable summary
    data : dict[str, Any]
        Structured data
    recommendations : list[str]
        Analysis-based recommendations
    """

    metadata: AgentOutputMetadata
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": {
                "generated_at": self.metadata.generated_at.isoformat(),
                "version": self.metadata.version,
                "source": self.metadata.source,
                "symbols": self.metadata.symbols,
                "period": self.metadata.period,
            },
            "summary": self.summary,
            "data": self.data,
            "recommendations": self.recommendations,
        }


__all__ = [
    "AgentOutput",
    "AgentOutputMetadata",
    "AnalysisResult",
    "DataSource",
    "MarketDataResult",
]
