"""JSON schema definitions for market data using Pydantic V2.

This module provides Pydantic models for validating and serializing:
- Stock data metadata
- Economic indicator metadata
- Market configuration

All models use Pydantic V2 with strict validation and JSON schema support.

Examples
--------
>>> from market.schema import StockDataMetadata
>>> metadata = StockDataMetadata(
...     symbol="AAPL",
...     source="yfinance",
...     fetched_at=datetime.now(),
... )
>>> metadata.model_dump()
{'symbol': 'AAPL', 'source': 'yfinance', ...}
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from database.db.connection import get_data_dir

# =============================================================================
# Date Range Model
# =============================================================================


class DateRange(BaseModel):
    """Date range for data queries.

    Parameters
    ----------
    start : str
        Start date in ISO format (YYYY-MM-DD)
    end : str
        End date in ISO format (YYYY-MM-DD)

    Examples
    --------
    >>> date_range = DateRange(start="2025-01-01", end="2026-01-01")
    >>> date_range.start
    '2025-01-01'
    """

    start: str = Field(..., description="Start date in ISO format (YYYY-MM-DD)")
    end: str = Field(..., description="End date in ISO format (YYYY-MM-DD)")


# =============================================================================
# Metadata Models
# =============================================================================


class StockDataMetadata(BaseModel):
    """Metadata for stock price data.

    Required fields: symbol, source, fetched_at
    Optional fields: from_cache, record_count, date_range

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g., "AAPL", "GOOGL")
    source : str
        Data source identifier (e.g., "yfinance", "bloomberg")
    fetched_at : datetime
        Timestamp when data was fetched
    from_cache : bool, default=False
        Whether data was retrieved from cache
    record_count : int | None, default=None
        Number of records in the dataset (must be >= 0)
    date_range : DateRange | None, default=None
        Date range of the data

    Examples
    --------
    >>> from datetime import datetime
    >>> metadata = StockDataMetadata(
    ...     symbol="AAPL",
    ...     source="yfinance",
    ...     fetched_at=datetime(2026, 1, 25, 10, 0, 0),
    ... )
    >>> metadata.symbol
    'AAPL'
    """

    symbol: str = Field(..., description="Ticker symbol")
    source: str = Field(..., description="Data source identifier")
    fetched_at: datetime = Field(..., description="Timestamp when data was fetched")
    from_cache: bool = Field(default=False, description="Whether from cache")
    record_count: int | None = Field(
        default=None, ge=0, description="Number of records"
    )
    date_range: DateRange | None = Field(default=None, description="Date range")


class EconomicDataMetadata(BaseModel):
    """Metadata for economic indicator data (e.g., FRED).

    Required fields: series_id, source, fetched_at
    Optional fields: from_cache, record_count, title, units, frequency

    Parameters
    ----------
    series_id : str
        Economic series identifier (e.g., "GDP", "UNRATE")
    source : str
        Data source identifier (e.g., "fred")
    fetched_at : datetime
        Timestamp when data was fetched
    from_cache : bool, default=False
        Whether data was retrieved from cache
    record_count : int | None, default=None
        Number of records in the dataset (must be >= 0)
    title : str | None, default=None
        Human-readable title of the series
    units : str | None, default=None
        Units of measurement
    frequency : str | None, default=None
        Data frequency (e.g., "Monthly", "Quarterly")

    Examples
    --------
    >>> from datetime import datetime
    >>> metadata = EconomicDataMetadata(
    ...     series_id="GDP",
    ...     source="fred",
    ...     fetched_at=datetime(2026, 1, 25, 10, 0, 0),
    ... )
    >>> metadata.series_id
    'GDP'
    """

    series_id: str = Field(..., description="Economic series identifier")
    source: str = Field(..., description="Data source identifier")
    fetched_at: datetime = Field(..., description="Timestamp when data was fetched")
    from_cache: bool = Field(default=False, description="Whether from cache")
    record_count: int | None = Field(
        default=None, ge=0, description="Number of records"
    )
    title: str | None = Field(default=None, description="Series title")
    units: str | None = Field(default=None, description="Units of measurement")
    frequency: str | None = Field(default=None, description="Data frequency")


# =============================================================================
# Configuration Models
# =============================================================================


class DataSourceConfig(BaseModel):
    """Configuration for a data source.

    All fields are optional with sensible defaults.

    Parameters
    ----------
    api_key : str | None, default=None
        API key for authenticated access
    base_url : str | None, default=None
        Base URL for the data source API
    timeout : int, default=30
        Request timeout in seconds (must be >= 0)
    rate_limit : int | None, default=None
        Maximum requests per minute (must be >= 0)

    Examples
    --------
    >>> config = DataSourceConfig(timeout=60, api_key="xxx")
    >>> config.timeout
    60
    """

    api_key: str | None = Field(default=None, description="API key")
    base_url: str | None = Field(default=None, description="Base URL")
    timeout: int = Field(default=30, ge=0, description="Timeout in seconds")
    rate_limit: int | None = Field(
        default=None, ge=0, description="Rate limit (requests/minute)"
    )


class CacheConfig(BaseModel):
    """Cache configuration.

    Parameters
    ----------
    enabled : bool, default=True
        Whether caching is enabled
    ttl_seconds : int, default=3600
        Time-to-live in seconds (must be >= 0)
    max_size_mb : int, default=100
        Maximum cache size in megabytes (must be >= 0)

    Examples
    --------
    >>> config = CacheConfig()
    >>> config.enabled
    True
    >>> config.ttl_seconds
    3600
    """

    enabled: bool = Field(default=True, description="Whether caching is enabled")
    ttl_seconds: int = Field(default=3600, ge=0, description="TTL in seconds")
    max_size_mb: int = Field(default=100, ge=0, description="Max cache size in MB")


class ExportConfig(BaseModel):
    """Export configuration.

    Parameters
    ----------
    default_format : Literal["parquet", "csv", "json"], default="parquet"
        Default export format
    output_dir : str, default="data/exports"
        Default output directory
    compression : str | None, default=None
        Compression algorithm (e.g., "gzip", "snappy")

    Examples
    --------
    >>> config = ExportConfig(default_format="csv")
    >>> config.default_format
    'csv'
    """

    default_format: Literal["parquet", "csv", "json"] = Field(
        default="parquet", description="Default export format"
    )
    output_dir: str = Field(
        default_factory=lambda: str(get_data_dir() / "exports"),
        description="Output directory",
    )
    compression: str | None = Field(default=None, description="Compression algorithm")


class MarketConfig(BaseModel):
    """Complete market data configuration.

    Parameters
    ----------
    data_sources : dict[str, DataSourceConfig], default={}
        Configuration for each data source
    cache : CacheConfig, default=CacheConfig()
        Cache configuration
    export : ExportConfig, default=ExportConfig()
        Export configuration

    Examples
    --------
    >>> config = MarketConfig()
    >>> config.data_sources
    {}
    >>> config.cache.enabled
    True
    """

    data_sources: dict[str, DataSourceConfig] = Field(
        default_factory=dict, description="Data source configurations"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig, description="Cache configuration"
    )
    export: ExportConfig = Field(
        default_factory=ExportConfig, description="Export configuration"
    )


# =============================================================================
# Validation Functions
# =============================================================================


def validate_stock_metadata(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate stock data metadata dictionary.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary containing stock metadata fields

    Returns
    -------
    tuple[bool, list[str]]
        A tuple of (is_valid, errors) where:
        - is_valid: True if validation passed
        - errors: List of error messages (empty if valid)

    Examples
    --------
    >>> data = {"symbol": "AAPL", "source": "yfinance", "fetched_at": "2026-01-25T10:00:00Z"}
    >>> is_valid, errors = validate_stock_metadata(data)
    >>> is_valid
    True
    """
    try:
        StockDataMetadata.model_validate(data)
        return True, []
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors


def validate_economic_metadata(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate economic data metadata dictionary.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary containing economic metadata fields

    Returns
    -------
    tuple[bool, list[str]]
        A tuple of (is_valid, errors) where:
        - is_valid: True if validation passed
        - errors: List of error messages (empty if valid)

    Examples
    --------
    >>> data = {"series_id": "GDP", "source": "fred", "fetched_at": "2026-01-25T10:00:00Z"}
    >>> is_valid, errors = validate_economic_metadata(data)
    >>> is_valid
    True
    """
    try:
        EconomicDataMetadata.model_validate(data)
        return True, []
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors


def validate_config(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate market configuration dictionary.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary containing market configuration

    Returns
    -------
    tuple[bool, list[str]]
        A tuple of (is_valid, errors) where:
        - is_valid: True if validation passed
        - errors: List of error messages (empty if valid)

    Examples
    --------
    >>> config = {"cache": {"enabled": True}}
    >>> is_valid, errors = validate_config(config)
    >>> is_valid
    True
    """
    try:
        MarketConfig.model_validate(data)
        return True, []
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors


__all__ = [
    "CacheConfig",
    "DataSourceConfig",
    "DateRange",
    "EconomicDataMetadata",
    "ExportConfig",
    "MarketConfig",
    "StockDataMetadata",
    "validate_config",
    "validate_economic_metadata",
    "validate_stock_metadata",
]
