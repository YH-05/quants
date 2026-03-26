"""BLS (Bureau of Labor Statistics) API v2.0 client.

This module provides an async client for the BLS Public Data API v2.0,
which requires a free registration key and supports:

- Up to 50 series per request
- Up to 20 years of data per request
- 500 queries per day

The client includes JSON file caching with configurable TTL (default: 7 days)
to reduce API calls and respect rate limits.

Supported data categories include:

- CES (Current Employment Statistics): Industry employment, hours, earnings
- CPI (Consumer Price Index): Inflation indicators
- PPI (Producer Price Index): Producer costs
- LNS (Labor Force Statistics): Unemployment, participation rates

Examples
--------
>>> async with BLSClient(api_key="your-key") as client:
...     result = await client.get_series(
...         series_ids=["CES3133440001"],
...         start_year=2020,
...         end_year=2025,
...     )
...     for series in result.series:
...         print(f"{series.series_id}: {len(series.data)} observations")

See Also
--------
market.fred.fetcher : FRED API client (similar government data API pattern).
market.industry.api_clients.census : Census Bureau API client.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from pathlib import Path
from pydantic import BaseModel, Field

from database.db.connection import get_data_dir
from market.industry.types import IndustryReport, SourceTier
from utils_core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

BLS_API_BASE_URL: str = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
"""Base URL for the BLS Public Data API v2.0."""

BLS_API_KEY_ENV: str = "BLS_API_KEY"
"""Environment variable name for the BLS API registration key."""

DEFAULT_CACHE_DIR: Path = get_data_dir() / "raw" / "industry_reports" / "bls"
"""Default directory for BLS API response cache files."""

DEFAULT_CACHE_TTL_SECONDS: int = 7 * 24 * 60 * 60  # 7 days
"""Default cache time-to-live in seconds (7 days)."""

MAX_SERIES_PER_REQUEST: int = 50
"""Maximum number of series IDs allowed per BLS API request."""

MAX_YEARS_PER_REQUEST: int = 20
"""Maximum year range allowed per BLS API request."""


# =============================================================================
# Data Models (Pydantic)
# =============================================================================


class BLSObservation(BaseModel, frozen=True):
    """A single BLS data observation (one time period).

    Parameters
    ----------
    year : str
        Four-digit year (e.g. ``"2025"``).
    period : str
        Period code (e.g. ``"M01"`` for January, ``"M13"`` for annual average).
    period_name : str
        Human-readable period name (e.g. ``"January"``).
    value : str
        Observation value as string (BLS returns numeric values as strings).
    footnotes : list[dict[str, str]]
        Footnote codes and texts associated with this observation.

    Examples
    --------
    >>> obs = BLSObservation(
    ...     year="2025", period="M01", period_name="January",
    ...     value="152300", footnotes=[],
    ... )
    >>> obs.value
    '152300'
    """

    year: str
    period: str
    period_name: str
    value: str
    footnotes: list[dict[str, str]] = Field(default_factory=list)

    @property
    def numeric_value(self) -> float | None:
        """Parse the value as a float, returning None if unparseable.

        Returns
        -------
        float | None
            Numeric value, or ``None`` if the value cannot be parsed.
        """
        try:
            return float(self.value)
        except (ValueError, TypeError):
            return None

    @property
    def date(self) -> datetime | None:
        """Convert year+period to a datetime.

        Only monthly periods (``M01``..``M12``) are converted.
        Annual averages (``M13``) and other periods return ``None``.

        Returns
        -------
        datetime | None
            UTC datetime for the first day of the month, or ``None``.
        """
        if not self.period.startswith("M"):
            return None
        try:
            month = int(self.period[1:])
            if 1 <= month <= 12:
                return datetime(int(self.year), month, 1, tzinfo=timezone.utc)
        except (ValueError, IndexError):
            pass
        return None


class BLSSeriesResult(BaseModel, frozen=True):
    """Result data for a single BLS series.

    Parameters
    ----------
    series_id : str
        The BLS series identifier (e.g. ``"CES3133440001"``).
    data : list[BLSObservation]
        List of observations in reverse chronological order.

    Examples
    --------
    >>> result = BLSSeriesResult(series_id="CES3133440001", data=[])
    >>> result.series_id
    'CES3133440001'
    """

    series_id: str
    data: list[BLSObservation] = Field(default_factory=list)


class BLSResponse(BaseModel, frozen=True):
    """Parsed response from the BLS API.

    Parameters
    ----------
    status : str
        API response status (e.g. ``"REQUEST_SUCCEEDED"``).
    message : list[str]
        Status messages from the API.
    series : list[BLSSeriesResult]
        List of series results.

    Examples
    --------
    >>> response = BLSResponse(
    ...     status="REQUEST_SUCCEEDED",
    ...     message=[],
    ...     series=[],
    ... )
    >>> response.status
    'REQUEST_SUCCEEDED'
    """

    status: str
    message: list[str] = Field(default_factory=list)
    series: list[BLSSeriesResult] = Field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """Check whether the response indicates success.

        Returns
        -------
        bool
            ``True`` if the status is ``"REQUEST_SUCCEEDED"``.
        """
        return self.status == "REQUEST_SUCCEEDED"


# =============================================================================
# Cache Utilities
# =============================================================================


def _build_cache_key(
    series_ids: list[str],
    start_year: int,
    end_year: int,
) -> str:
    """Build a deterministic cache key from request parameters.

    Parameters
    ----------
    series_ids : list[str]
        Sorted list of series IDs.
    start_year : int
        Start year.
    end_year : int
        End year.

    Returns
    -------
    str
        SHA-256 hex digest (first 16 characters) as cache key.
    """
    key_str = f"bls:{','.join(sorted(series_ids))}:{start_year}:{end_year}"
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def _read_cache(
    cache_dir: Path,
    cache_key: str,
    ttl_seconds: int,
) -> dict | None:
    """Read a cached API response if it exists and is not expired.

    Parameters
    ----------
    cache_dir : Path
        Cache directory.
    cache_key : str
        Cache key.
    ttl_seconds : int
        Maximum age in seconds.

    Returns
    -------
    dict | None
        Cached response data, or ``None`` if not found or expired.
    """
    cache_file = cache_dir / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at = data.get("cached_at", 0)

        if time.time() - cached_at > ttl_seconds:
            logger.debug(
                "Cache expired",
                cache_key=cache_key,
                age_seconds=time.time() - cached_at,
                ttl_seconds=ttl_seconds,
            )
            return None

        logger.debug("Cache hit", cache_key=cache_key)
        return data.get("response")

    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Failed to read cache",
            cache_key=cache_key,
            error=str(e),
        )
        return None


def _write_cache(
    cache_dir: Path,
    cache_key: str,
    response_data: dict,
) -> None:
    """Write an API response to the cache.

    Parameters
    ----------
    cache_dir : Path
        Cache directory.
    cache_key : str
        Cache key.
    response_data : dict
        API response data to cache.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{cache_key}.json"

    try:
        cache_payload = {
            "cached_at": time.time(),
            "response": response_data,
        }
        cache_file.write_text(
            json.dumps(cache_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Cache written", cache_key=cache_key, path=str(cache_file))

    except OSError as e:
        logger.warning(
            "Failed to write cache",
            cache_key=cache_key,
            error=str(e),
        )


# =============================================================================
# BLS Client
# =============================================================================


class BLSClient:
    """Async client for the BLS Public Data API v2.0.

    Fetches time series data from the Bureau of Labor Statistics, including
    employment statistics, wages, and productivity indicators. Includes
    JSON file caching with configurable TTL.

    Parameters
    ----------
    api_key : str | None
        BLS API registration key. If ``None``, reads from the
        ``BLS_API_KEY`` environment variable.
    cache_dir : Path | None
        Directory for JSON cache files. If ``None``, uses
        ``data/raw/industry_reports/bls``.
    cache_ttl_seconds : int
        Cache time-to-live in seconds. Defaults to 7 days (604800).
    timeout : float
        HTTP request timeout in seconds. Defaults to 30.0.

    Raises
    ------
    ValueError
        If no API key is provided and the environment variable is not set.

    Examples
    --------
    >>> async with BLSClient() as client:
    ...     response = await client.get_series(["CES3133440001"])
    ...     for s in response.series:
    ...         print(f"{s.series_id}: {len(s.data)} observations")
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get(BLS_API_KEY_ENV)

        if not self._api_key:
            logger.error(
                "BLS API key not found",
                env_var=BLS_API_KEY_ENV,
            )
            raise ValueError(
                f"BLS API key not provided. Set the {BLS_API_KEY_ENV} "
                "environment variable or pass api_key parameter."
            )

        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._cache_ttl_seconds = cache_ttl_seconds
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

        logger.info(
            "BLSClient initialized",
            cache_dir=str(self._cache_dir),
            cache_ttl_seconds=cache_ttl_seconds,
            timeout=timeout,
        )

    # =========================================================================
    # Async Context Manager
    # =========================================================================

    async def __aenter__(self) -> BLSClient:
        """Start async context manager and create HTTP client.

        Returns
        -------
        BLSClient
            Self.
        """
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "finance-industry-research/1.0",
            },
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Close the HTTP client on exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client. Safe to call multiple times."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("BLSClient HTTP client closed")

    # =========================================================================
    # Public API
    # =========================================================================

    async def get_series(
        self,
        series_ids: list[str],
        start_year: int | None = None,
        end_year: int | None = None,
        *,
        use_cache: bool = True,
    ) -> BLSResponse:
        """Fetch time series data from the BLS API.

        Parameters
        ----------
        series_ids : list[str]
            BLS series IDs to fetch (max 50).
        start_year : int | None
            Start year for the data range. If ``None``, uses the
            current year minus 10.
        end_year : int | None
            End year for the data range. If ``None``, uses the
            current year.
        use_cache : bool
            Whether to use the JSON file cache. Defaults to ``True``.

        Returns
        -------
        BLSResponse
            Parsed API response containing series data.

        Raises
        ------
        ValueError
            If ``series_ids`` is empty or exceeds 50 items, or if
            the year range exceeds 20 years.
        httpx.HTTPError
            If the HTTP request fails.
        RuntimeError
            If the API returns an error status.
        """
        # Validate inputs
        if not series_ids:
            raise ValueError("series_ids must not be empty")

        if len(series_ids) > MAX_SERIES_PER_REQUEST:
            raise ValueError(
                f"Maximum {MAX_SERIES_PER_REQUEST} series per request, "
                f"got {len(series_ids)}"
            )

        now_year = datetime.now(tz=timezone.utc).year
        start_year = start_year or (now_year - 10)
        end_year = end_year or now_year

        if end_year - start_year + 1 > MAX_YEARS_PER_REQUEST:
            raise ValueError(
                f"Maximum {MAX_YEARS_PER_REQUEST} year range, "
                f"got {end_year - start_year + 1}"
            )

        logger.info(
            "Fetching BLS series",
            series_count=len(series_ids),
            start_year=start_year,
            end_year=end_year,
        )

        # Check cache
        if use_cache:
            cache_key = _build_cache_key(series_ids, start_year, end_year)
            cached = _read_cache(self._cache_dir, cache_key, self._cache_ttl_seconds)
            if cached is not None:
                logger.info(
                    "Returning cached BLS data",
                    series_count=len(series_ids),
                )
                return _parse_bls_response(cached)

        # Build request payload
        payload: dict = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
            "registrationkey": self._api_key,
        }

        # Make API request
        raw_response = await self._post(payload)

        # Cache the raw response
        if use_cache:
            cache_key = _build_cache_key(series_ids, start_year, end_year)
            _write_cache(self._cache_dir, cache_key, raw_response)

        # Parse response
        response = _parse_bls_response(raw_response)

        if not response.is_success:
            logger.error(
                "BLS API returned error",
                status=response.status,
                messages=response.message,
            )
            raise RuntimeError(
                f"BLS API error: {response.status} - {'; '.join(response.message)}"
            )

        logger.info(
            "BLS data fetched successfully",
            series_count=len(response.series),
            total_observations=sum(len(s.data) for s in response.series),
        )

        return response

    async def get_series_as_reports(
        self,
        series_ids: list[str],
        sector: str = "all",
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[IndustryReport]:
        """Fetch BLS series and convert to IndustryReport format.

        Convenience method that fetches BLS data and wraps each series
        into an ``IndustryReport`` record compatible with the industry
        module's standard data model.

        Parameters
        ----------
        series_ids : list[str]
            BLS series IDs to fetch.
        sector : str
            Sector classification for the reports. Defaults to ``"all"``.
        start_year : int | None
            Start year for the data range.
        end_year : int | None
            End year for the data range.

        Returns
        -------
        list[IndustryReport]
            List of industry reports, one per series.
        """
        response = await self.get_series(
            series_ids=series_ids,
            start_year=start_year,
            end_year=end_year,
        )

        reports: list[IndustryReport] = []
        for series in response.series:
            latest_obs = series.data[0] if series.data else None
            published_at = (
                latest_obs.date
                if latest_obs and latest_obs.date
                else datetime.now(tz=timezone.utc)
            )

            summary_parts: list[str] = []
            if latest_obs:
                summary_parts.append(
                    f"Latest value: {latest_obs.value} "
                    f"({latest_obs.period_name} {latest_obs.year})"
                )
            summary_parts.append(f"Total observations: {len(series.data)}")

            reports.append(
                IndustryReport(
                    source="BLS",
                    title=f"BLS Series {series.series_id}",
                    url=f"https://data.bls.gov/timeseries/{series.series_id}",
                    published_at=published_at,
                    sector=sector,
                    summary="; ".join(summary_parts),
                    tier=SourceTier.API,
                )
            )

        return reports

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _post(self, payload: dict) -> dict:
        """Send a POST request to the BLS API.

        Parameters
        ----------
        payload : dict
            JSON payload for the request.

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        httpx.HTTPError
            If the request fails.
        RuntimeError
            If the client is not initialized (use async context manager).
        """
        if self._client is None:
            raise RuntimeError(
                "BLSClient must be used as an async context manager: "
                "async with BLSClient() as client: ..."
            )

        logger.debug(
            "Sending BLS API request",
            url=BLS_API_BASE_URL,
            series_count=len(payload.get("seriesid", [])),
        )

        response = await self._client.post(BLS_API_BASE_URL, json=payload)
        response.raise_for_status()

        data: dict = response.json()
        return data


# =============================================================================
# Response Parser
# =============================================================================


def _parse_bls_response(raw: dict) -> BLSResponse:
    """Parse a raw BLS API JSON response into typed models.

    Parameters
    ----------
    raw : dict
        Raw JSON response from the BLS API.

    Returns
    -------
    BLSResponse
        Parsed and validated response.
    """
    status = raw.get("status", "UNKNOWN")
    message = raw.get("message", [])

    series_list: list[BLSSeriesResult] = []
    results = raw.get("Results", {})
    raw_series = results.get("series", [])

    for raw_s in raw_series:
        observations: list[BLSObservation] = []

        for raw_obs in raw_s.get("data", []):
            observations.append(
                BLSObservation(
                    year=raw_obs.get("year", ""),
                    period=raw_obs.get("period", ""),
                    period_name=raw_obs.get("periodName", ""),
                    value=raw_obs.get("value", ""),
                    footnotes=raw_obs.get("footnotes", []),
                )
            )

        series_list.append(
            BLSSeriesResult(
                series_id=raw_s.get("seriesID", ""),
                data=observations,
            )
        )

    return BLSResponse(
        status=status,
        message=message,
        series=series_list,
    )


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "BLS_API_BASE_URL",
    "BLS_API_KEY_ENV",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CACHE_TTL_SECONDS",
    "MAX_SERIES_PER_REQUEST",
    "MAX_YEARS_PER_REQUEST",
    "BLSClient",
    "BLSObservation",
    "BLSResponse",
    "BLSSeriesResult",
]
