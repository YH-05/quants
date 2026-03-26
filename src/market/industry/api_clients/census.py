"""Census Bureau API client for international trade data.

This module provides an async client for the US Census Bureau's
International Trade API, which offers:

- Monthly and annual trade statistics
- Exports and imports by various classification systems (HS, NAICS, End-Use)
- No strict rate limit, but an API key is recommended for reliability

The client includes JSON file caching with configurable TTL (default: 7 days)
to reduce API calls.

Supported endpoints:

- International Trade Exports (HS, NAICS, End-Use)
- International Trade Imports (HS, NAICS, End-Use)

Examples
--------
>>> async with CensusClient(api_key="your-key") as client:
...     result = await client.get_trade_data(
...         flow="exports",
...         classification="hs",
...         year=2025,
...         month=1,
...     )
...     for record in result.data[:5]:
...         print(f"{record.commodity_code}: ${record.value:,.0f}")

See Also
--------
market.fred.fetcher : FRED API client (similar government data API pattern).
market.industry.api_clients.bls : BLS API client.
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

CENSUS_API_BASE_URL: str = "https://api.census.gov/data/timeseries/intltrade"
"""Base URL for the Census Bureau International Trade API."""

CENSUS_API_KEY_ENV: str = "CENSUS_API_KEY"
"""Environment variable name for the Census Bureau API key."""

DEFAULT_CACHE_DIR: Path = get_data_dir() / "raw" / "industry_reports" / "census"
"""Default directory for Census API response cache files."""

DEFAULT_CACHE_TTL_SECONDS: int = 7 * 24 * 60 * 60  # 7 days
"""Default cache time-to-live in seconds (7 days)."""

VALID_FLOWS: frozenset[str] = frozenset({"exports", "imports"})
"""Valid trade flow types."""

VALID_CLASSIFICATIONS: frozenset[str] = frozenset({"hs", "naics", "enduse"})
"""Valid trade classification systems."""


# =============================================================================
# Data Models (Pydantic)
# =============================================================================


class CensusTradeRecord(BaseModel, frozen=True):
    """A single Census trade data record.

    Parameters
    ----------
    commodity_code : str
        Commodity classification code (HS, NAICS, or End-Use code).
    commodity_description : str
        Human-readable description of the commodity.
    value : float
        Trade value in US dollars.
    year : int
        Four-digit year.
    month : int | None
        Month number (1-12), or ``None`` for annual data.
    flow : str
        Trade flow direction (``"exports"`` or ``"imports"``).
    classification : str
        Classification system used (``"hs"``, ``"naics"``, or ``"enduse"``).

    Examples
    --------
    >>> record = CensusTradeRecord(
    ...     commodity_code="27",
    ...     commodity_description="Mineral fuels, oils",
    ...     value=5_000_000_000,
    ...     year=2025,
    ...     month=1,
    ...     flow="exports",
    ...     classification="hs",
    ... )
    """

    commodity_code: str
    commodity_description: str = ""
    value: float = 0.0
    year: int = 0
    month: int | None = None
    flow: str = ""
    classification: str = ""

    @property
    def date(self) -> datetime:
        """Convert year+month to a UTC datetime.

        Returns ``January 1`` for annual data (when month is ``None``).

        Returns
        -------
        datetime
            UTC datetime for the first day of the period.
        """
        month = self.month or 1
        return datetime(self.year, month, 1, tzinfo=timezone.utc)


class CensusTradeResponse(BaseModel, frozen=True):
    """Parsed response from the Census Trade API.

    Parameters
    ----------
    data : list[CensusTradeRecord]
        List of trade data records.
    flow : str
        Trade flow direction (``"exports"`` or ``"imports"``).
    classification : str
        Classification system (``"hs"``, ``"naics"``, or ``"enduse"``).
    year : int
        Query year.
    month : int | None
        Query month, or ``None`` for annual.

    Examples
    --------
    >>> response = CensusTradeResponse(
    ...     data=[],
    ...     flow="exports",
    ...     classification="hs",
    ...     year=2025,
    ...     month=1,
    ... )
    """

    data: list[CensusTradeRecord] = Field(default_factory=list)
    flow: str = ""
    classification: str = ""
    year: int = 0
    month: int | None = None

    @property
    def total_value(self) -> float:
        """Sum of all trade values in the response.

        Returns
        -------
        float
            Total trade value in USD.
        """
        return sum(r.value for r in self.data)


# =============================================================================
# Cache Utilities
# =============================================================================


def _build_cache_key(
    flow: str,
    classification: str,
    year: int,
    month: int | None,
) -> str:
    """Build a deterministic cache key from request parameters.

    Parameters
    ----------
    flow : str
        Trade flow direction.
    classification : str
        Classification system.
    year : int
        Year.
    month : int | None
        Month or None.

    Returns
    -------
    str
        SHA-256 hex digest (first 16 characters) as cache key.
    """
    key_str = f"census:{flow}:{classification}:{year}:{month}"
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def _read_cache(
    cache_dir: Path,
    cache_key: str,
    ttl_seconds: int,
) -> list[list[str]] | None:
    """Read cached Census API response if not expired.

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
    list[list[str]] | None
        Cached response data (list of rows), or ``None``.
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
    response_data: list[list[str]],
) -> None:
    """Write Census API response to the cache.

    Parameters
    ----------
    cache_dir : Path
        Cache directory.
    cache_key : str
        Cache key.
    response_data : list[list[str]]
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
# Census Client
# =============================================================================


class CensusClient:
    """Async client for the Census Bureau International Trade API.

    Fetches trade statistics from the Census Bureau, including exports
    and imports classified by HS code, NAICS code, or End-Use code.
    Includes JSON file caching with configurable TTL.

    Parameters
    ----------
    api_key : str | None
        Census Bureau API key. If ``None``, reads from the
        ``CENSUS_API_KEY`` environment variable.
    cache_dir : Path | None
        Directory for JSON cache files. If ``None``, uses
        ``data/raw/industry_reports/census``.
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
    >>> async with CensusClient() as client:
    ...     response = await client.get_trade_data(
    ...         flow="exports", classification="hs",
    ...         year=2025, month=6,
    ...     )
    ...     print(f"Total value: ${response.total_value:,.0f}")
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get(CENSUS_API_KEY_ENV)

        if not self._api_key:
            logger.error(
                "Census API key not found",
                env_var=CENSUS_API_KEY_ENV,
            )
            raise ValueError(
                f"Census API key not provided. Set the {CENSUS_API_KEY_ENV} "
                "environment variable or pass api_key parameter."
            )

        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._cache_ttl_seconds = cache_ttl_seconds
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

        logger.info(
            "CensusClient initialized",
            cache_dir=str(self._cache_dir),
            cache_ttl_seconds=cache_ttl_seconds,
            timeout=timeout,
        )

    # =========================================================================
    # Async Context Manager
    # =========================================================================

    async def __aenter__(self) -> CensusClient:
        """Start async context manager and create HTTP client.

        Returns
        -------
        CensusClient
            Self.
        """
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={
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
            logger.debug("CensusClient HTTP client closed")

    # =========================================================================
    # Public API
    # =========================================================================

    async def get_trade_data(
        self,
        flow: str,
        classification: str,
        year: int,
        month: int | None = None,
        *,
        use_cache: bool = True,
    ) -> CensusTradeResponse:
        """Fetch international trade data from the Census Bureau API.

        Parameters
        ----------
        flow : str
            Trade flow direction: ``"exports"`` or ``"imports"``.
        classification : str
            Classification system: ``"hs"``, ``"naics"``, or ``"enduse"``.
        year : int
            Four-digit year.
        month : int | None
            Month number (1-12) for monthly data. If ``None``, fetches
            annual data.
        use_cache : bool
            Whether to use the JSON file cache. Defaults to ``True``.

        Returns
        -------
        CensusTradeResponse
            Parsed response containing trade data records.

        Raises
        ------
        ValueError
            If ``flow`` or ``classification`` is not a valid value.
        httpx.HTTPError
            If the HTTP request fails.
        """
        # Validate inputs
        if flow not in VALID_FLOWS:
            raise ValueError(
                f"Invalid flow: {flow!r}. Must be one of: {sorted(VALID_FLOWS)}"
            )
        if classification not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"Invalid classification: {classification!r}. "
                f"Must be one of: {sorted(VALID_CLASSIFICATIONS)}"
            )
        if month is not None and not (1 <= month <= 12):
            raise ValueError(f"Month must be 1-12, got {month}")

        logger.info(
            "Fetching Census trade data",
            flow=flow,
            classification=classification,
            year=year,
            month=month,
        )

        # Check cache
        if use_cache:
            cache_key = _build_cache_key(flow, classification, year, month)
            cached = _read_cache(self._cache_dir, cache_key, self._cache_ttl_seconds)
            if cached is not None:
                logger.info("Returning cached Census data")
                return _parse_census_response(cached, flow, classification, year, month)

        # Build URL and parameters
        url = self._build_url(flow, classification)
        params = self._build_params(year, month)

        # Make API request
        raw_data = await self._get(url, params)

        # Cache the raw response
        if use_cache:
            cache_key = _build_cache_key(flow, classification, year, month)
            _write_cache(self._cache_dir, cache_key, raw_data)

        # Parse response
        response = _parse_census_response(raw_data, flow, classification, year, month)

        logger.info(
            "Census data fetched successfully",
            record_count=len(response.data),
            total_value=response.total_value,
        )

        return response

    async def get_trade_as_reports(
        self,
        flow: str,
        classification: str,
        year: int,
        month: int | None = None,
        sector: str = "all",
    ) -> list[IndustryReport]:
        """Fetch Census trade data and convert to IndustryReport format.

        Convenience method that fetches trade data and wraps the results
        into ``IndustryReport`` records compatible with the industry
        module's standard data model.

        Parameters
        ----------
        flow : str
            Trade flow direction.
        classification : str
            Classification system.
        year : int
            Year.
        month : int | None
            Month (optional).
        sector : str
            Sector classification for the reports. Defaults to ``"all"``.

        Returns
        -------
        list[IndustryReport]
            List of industry reports (one aggregate report).
        """
        response = await self.get_trade_data(
            flow=flow,
            classification=classification,
            year=year,
            month=month,
        )

        if not response.data:
            return []

        period_str = f"{year}-{month:02d}" if month else str(year)
        published_at = datetime(year, month or 1, 1, tzinfo=timezone.utc)

        return [
            IndustryReport(
                source="Census Bureau",
                title=(f"US {flow.title()} by {classification.upper()} ({period_str})"),
                url=(f"https://www.census.gov/foreign-trade/data/index.html#{flow}"),
                published_at=published_at,
                sector=sector,
                summary=(
                    f"Records: {len(response.data)}; "
                    f"Total value: ${response.total_value:,.0f}"
                ),
                tier=SourceTier.API,
            )
        ]

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _build_url(self, flow: str, classification: str) -> str:
        """Build the Census API URL for the given flow and classification.

        Parameters
        ----------
        flow : str
            Trade flow direction.
        classification : str
            Classification system.

        Returns
        -------
        str
            Full API endpoint URL.
        """
        return f"{CENSUS_API_BASE_URL}/{flow}/{classification}"

    def _build_params(
        self,
        year: int,
        month: int | None,
    ) -> dict[str, str]:
        """Build query parameters for the Census API request.

        Parameters
        ----------
        year : int
            Year.
        month : int | None
            Month or None for annual.

        Returns
        -------
        dict[str, str]
            Query parameters dictionary.
        """
        params: dict[str, str] = {
            "get": "CTY_CODE,CTY_NAME,ALL_VAL_MO,ALL_VAL_YR",
            "key": self._api_key or "",
        }

        if month is not None:
            params["time"] = f"{year}-{month:02d}"
        else:
            params["YEAR"] = str(year)

        return params

    async def _get(
        self,
        url: str,
        params: dict[str, str],
    ) -> list[list[str]]:
        """Send a GET request to the Census API.

        Parameters
        ----------
        url : str
            API endpoint URL.
        params : dict[str, str]
            Query parameters.

        Returns
        -------
        list[list[str]]
            Parsed JSON response (list of rows; first row is headers).

        Raises
        ------
        httpx.HTTPError
            If the request fails.
        RuntimeError
            If the client is not initialized.
        """
        if self._client is None:
            raise RuntimeError(
                "CensusClient must be used as an async context manager: "
                "async with CensusClient() as client: ..."
            )

        logger.debug(
            "Sending Census API request",
            url=url,
            params={k: v for k, v in params.items() if k != "key"},
        )

        response = await self._client.get(url, params=params)
        response.raise_for_status()

        data: list[list[str]] = response.json()
        return data


# =============================================================================
# Response Parser
# =============================================================================


def _parse_census_response(
    raw: list[list[str]],
    flow: str,
    classification: str,
    year: int,
    month: int | None,
) -> CensusTradeResponse:
    """Parse a raw Census API JSON response into typed models.

    The Census API returns a list of lists where the first row contains
    column headers and subsequent rows contain data.

    Parameters
    ----------
    raw : list[list[str]]
        Raw JSON response from the Census API.
    flow : str
        Trade flow direction.
    classification : str
        Classification system.
    year : int
        Query year.
    month : int | None
        Query month.

    Returns
    -------
    CensusTradeResponse
        Parsed and validated response.
    """
    if not raw or len(raw) < 2:
        return CensusTradeResponse(
            data=[],
            flow=flow,
            classification=classification,
            year=year,
            month=month,
        )

    headers = raw[0]
    records: list[CensusTradeRecord] = []

    # Find column indices
    code_idx = _find_column_index(headers, ["CTY_CODE", "E_COMMODITY", "I_COMMODITY"])
    name_idx = _find_column_index(
        headers, ["CTY_NAME", "E_COMMODITY_LDESC", "I_COMMODITY_LDESC"]
    )
    value_idx = _find_column_index(headers, ["ALL_VAL_MO", "GEN_VAL_MO"])

    for row in raw[1:]:
        try:
            code = row[code_idx] if code_idx is not None else ""
            name = row[name_idx] if name_idx is not None else ""

            raw_value = row[value_idx] if value_idx is not None else "0"
            try:
                value = float(raw_value) if raw_value else 0.0
            except (ValueError, TypeError):
                value = 0.0

            records.append(
                CensusTradeRecord(
                    commodity_code=code,
                    commodity_description=name,
                    value=value,
                    year=year,
                    month=month,
                    flow=flow,
                    classification=classification,
                )
            )

        except (IndexError, ValueError) as e:
            logger.debug(
                "Skipped unparseable Census row",
                error=str(e),
            )
            continue

    return CensusTradeResponse(
        data=records,
        flow=flow,
        classification=classification,
        year=year,
        month=month,
    )


def _find_column_index(
    headers: list[str],
    candidates: list[str],
) -> int | None:
    """Find the index of the first matching column header.

    Parameters
    ----------
    headers : list[str]
        List of column header names.
    candidates : list[str]
        Candidate header names to search for (in priority order).

    Returns
    -------
    int | None
        Index of the first matching header, or ``None`` if no match.
    """
    for candidate in candidates:
        if candidate in headers:
            return headers.index(candidate)
    return None


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "CENSUS_API_BASE_URL",
    "CENSUS_API_KEY_ENV",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CACHE_TTL_SECONDS",
    "VALID_CLASSIFICATIONS",
    "VALID_FLOWS",
    "CensusClient",
    "CensusTradeRecord",
    "CensusTradeResponse",
]
