"""HTTP client for the EDINET DB API.

This module provides the ``EdinetClient`` class, a synchronous HTTP client
for all 10 EDINET DB API endpoints. Features include:

- Synchronous ``httpx.Client`` with connection pooling
- Exponential backoff retry for 5xx and network errors
- No retry on 4xx client errors
- Polite delay between consecutive requests (default: 100ms)
- Optional ``DailyRateLimiter`` integration for daily call counting
- ``X-API-Key`` header authentication
- Context manager support (``with EdinetClient(...) as client:``)

The client maps each API endpoint to a typed method that returns
the appropriate dataclass from ``market.edinet.types``.

Examples
--------
Basic usage:

>>> config = EdinetConfig(api_key="your_key")
>>> with EdinetClient(config=config) as client:
...     companies = client.list_companies()
...     print(f"Found {len(companies)} companies")

With rate limiter:

>>> from market.edinet.rate_limiter import DailyRateLimiter
>>> limiter = DailyRateLimiter(state_path=config.sync_state_path.parent / "_rate_limit.json")
>>> with EdinetClient(config=config, rate_limiter=limiter) as client:
...     remaining = client.get_remaining_calls()
...     print(f"Remaining calls: {remaining}")

See Also
--------
market.edinet.types : Configuration and data record dataclasses.
market.edinet.errors : Custom exception classes.
market.edinet.rate_limiter : Daily rate limit management.
market.edinet.constants : API URL, ranking metrics, and HTTP settings.
"""

from __future__ import annotations

import dataclasses
import os
import random
import time
from typing import TYPE_CHECKING, Any

import httpx

from market.edinet.constants import DEFAULT_BASE_URL, RANKING_METRICS
from market.edinet.errors import (
    EdinetAPIError,
    EdinetRateLimitError,
)
from market.edinet.types import (
    AnalysisResult,
    Company,
    EdinetConfig,
    FinancialRecord,
    Industry,
    RankingEntry,
    RatioRecord,
    RetryConfig,
    TextBlock,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.edinet.rate_limiter import DailyRateLimiter

logger = get_logger(__name__)

# HTTP status codes that indicate rate limiting
_RATE_LIMIT_STATUS_CODE = 429


class EdinetClient:
    """Synchronous HTTP client for the EDINET DB API.

    Provides typed methods for all 10 API endpoints with automatic
    retry on transient errors and optional daily rate limiting.

    Parameters
    ----------
    config : EdinetConfig | None
        API configuration. If ``None``, a default config is created
        (requires ``EDINET_DB_API_KEY`` environment variable).
    retry_config : RetryConfig | None
        Retry behaviour configuration. If ``None``, defaults are used
        (3 attempts, 1s initial delay, 30s max delay).
    rate_limiter : DailyRateLimiter | None
        Optional daily rate limiter. When provided, each API call
        checks remaining quota and records usage.

    Attributes
    ----------
    _config : EdinetConfig
        The API configuration.
    _retry_config : RetryConfig
        The retry configuration.
    _rate_limiter : DailyRateLimiter | None
        The optional rate limiter.
    _client : httpx.Client
        The underlying HTTP client.
    _last_request_time : float
        Monotonic timestamp of the last request (for polite delay).

    Examples
    --------
    >>> with EdinetClient(config=EdinetConfig(api_key="key")) as client:
    ...     company = client.get_company("E00001")
    """

    def __init__(
        self,
        config: EdinetConfig | None = None,
        retry_config: RetryConfig | None = None,
        rate_limiter: DailyRateLimiter | None = None,
    ) -> None:
        if config is None:
            api_key = os.environ.get("EDINET_DB_API_KEY", "")
            config = EdinetConfig(api_key=api_key)
        self._config: EdinetConfig = config
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._rate_limiter: DailyRateLimiter | None = rate_limiter
        self._last_request_time: float = 0.0

        self._client: httpx.Client = httpx.Client(
            base_url=self._config.base_url,
            timeout=httpx.Timeout(self._config.timeout),
            headers={"X-API-Key": self._config.api_key},
        )

        logger.info(
            "EdinetClient initialized",
            base_url=self._config.base_url,
            timeout=self._config.timeout,
            polite_delay=self._config.polite_delay,
            has_rate_limiter=self._rate_limiter is not None,
            max_retry_attempts=self._retry_config.max_attempts,
        )

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> EdinetClient:
        """Support context manager protocol.

        Returns
        -------
        EdinetClient
            Self for use in ``with`` statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close client on context exit.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised.
        exc_val : BaseException | None
            Exception instance if an exception was raised.
        exc_tb : Any
            Traceback if an exception was raised.
        """
        self.close()

    def close(self) -> None:
        """Close the HTTP client and release resources.

        Examples
        --------
        >>> client = EdinetClient(config=config)
        >>> client.close()
        """
        self._client.close()
        logger.debug("EdinetClient closed")

    # =========================================================================
    # Public API Methods (10 endpoints)
    # =========================================================================

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search companies by name or keyword.

        Calls ``GET /v1/search?q={query}``.

        Parameters
        ----------
        query : str
            Search query string (company name, keyword, etc.).

        Returns
        -------
        list[dict[str, Any]]
            List of matching company records as dictionaries.

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> results = client.search("トヨタ")
        >>> len(results)
        1
        """
        logger.debug("Searching companies", query=query)
        raw = self._request("GET", "/v1/search", params={"q": query})
        results: list[dict[str, Any]] = self._unwrap_response(raw)
        if not isinstance(results, list):
            results = []
        logger.info("Search completed", query=query, result_count=len(results))
        return results

    def list_companies(self, per_page: int = 5000) -> list[Company]:
        """List all companies.

        Calls ``GET /v1/companies?per_page={per_page}``.

        Parameters
        ----------
        per_page : int
            Maximum number of companies to return (default: 5000).

        Returns
        -------
        list[Company]
            List of company records.

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> companies = client.list_companies()
        >>> len(companies)
        3848
        """
        logger.debug("Listing companies", per_page=per_page)
        raw = self._request(
            "GET",
            "/v1/companies",
            params={"per_page": str(per_page)},
        )
        data = self._unwrap_response(raw)
        companies = [self._parse_record(Company, item) for item in data]
        logger.info("Companies listed", count=len(companies))
        return companies

    def get_company(self, code: str) -> Company:
        """Get company details.

        Calls ``GET /v1/companies/{code}``.

        Parameters
        ----------
        code : str
            EDINET code (e.g. ``"E00001"``).

        Returns
        -------
        Company
            Company record.

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> company = client.get_company("E00001")
        >>> company.corp_name
        'テスト株式会社'
        """
        logger.debug("Getting company", code=code)
        raw = self._request("GET", f"/v1/companies/{code}")
        data = self._unwrap_response(raw)
        company = self._parse_record(Company, data)
        logger.info("Company retrieved", code=code, name=company.corp_name)
        return company

    def get_financials(self, code: str) -> list[FinancialRecord]:
        """Get financial statement time series.

        Calls ``GET /v1/companies/{code}/financials``.

        Parameters
        ----------
        code : str
            EDINET code (e.g. ``"E00001"``).

        Returns
        -------
        list[FinancialRecord]
            Financial records (up to 6 years, 30 fields each).

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> records = client.get_financials("E00001")
        >>> len(records)
        6
        """
        logger.debug("Getting financials", code=code)
        raw = self._request("GET", f"/v1/companies/{code}/financials")
        data = self._unwrap_response(raw)
        records = [self._parse_record(FinancialRecord, item) for item in data]
        logger.info("Financials retrieved", code=code, years=len(records))
        return records

    def get_ratios(self, code: str) -> list[RatioRecord]:
        """Get financial ratio time series.

        Calls ``GET /v1/companies/{code}/ratios``.

        Parameters
        ----------
        code : str
            EDINET code (e.g. ``"E00001"``).

        Returns
        -------
        list[RatioRecord]
            Ratio records (up to 6 years, 21 fields each).

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> records = client.get_ratios("E00001")
        >>> records[0].roe
        3.89
        """
        logger.debug("Getting ratios", code=code)
        raw = self._request("GET", f"/v1/companies/{code}/ratios")
        data = self._unwrap_response(raw)
        records = [self._parse_record(RatioRecord, item) for item in data]
        logger.info("Ratios retrieved", code=code, years=len(records))
        return records

    def get_analysis(self, code: str) -> AnalysisResult:
        """Get financial health analysis.

        Calls ``GET /v1/companies/{code}/analysis``.

        Parameters
        ----------
        code : str
            EDINET code (e.g. ``"E00001"``).

        Returns
        -------
        AnalysisResult
            Analysis result with health score and commentary.

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> result = client.get_analysis("E00001")
        >>> result.health_score
        75.0
        """
        logger.debug("Getting analysis", code=code)
        raw = self._request("GET", f"/v1/companies/{code}/analysis")
        data = self._unwrap_response(raw)
        result = self._parse_record(AnalysisResult, data)
        logger.info(
            "Analysis retrieved",
            code=code,
            health_score=result.health_score,
        )
        return result

    def get_text_blocks(self, code: str, year: str | None = None) -> list[TextBlock]:
        """Get securities report text excerpts.

        Calls ``GET /v1/companies/{code}/text-blocks``.

        Parameters
        ----------
        code : str
            EDINET code (e.g. ``"E00001"``).
        year : str | None
            Optional fiscal year filter (e.g. ``"2025"``).

        Returns
        -------
        list[TextBlock]
            Text block records (business overview, risk factors,
            management analysis).

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> blocks = client.get_text_blocks("E00001")
        >>> blocks[0].business_overview
        '事業概要テキスト'
        """
        logger.debug("Getting text blocks", code=code, year=year)
        params: dict[str, str] = {}
        if year is not None:
            params["year"] = year
        raw = self._request(
            "GET",
            f"/v1/companies/{code}/text-blocks",
            params=params if params else None,
        )
        data = self._unwrap_response(raw)
        blocks = [self._parse_record(TextBlock, item) for item in data]
        logger.info("Text blocks retrieved", code=code, count=len(blocks))
        return blocks

    def get_ranking(self, metric: str) -> list[RankingEntry]:
        """Get company rankings by financial metric.

        Calls ``GET /v1/rankings/{metric}``.

        Parameters
        ----------
        metric : str
            Ranking metric name (e.g. ``"roe"``, ``"eps"``).
            Must be one of the 18 valid metrics defined in
            ``RANKING_METRICS``.

        Returns
        -------
        list[RankingEntry]
            Ranking entries sorted by rank.

        Raises
        ------
        ValueError
            If the metric is not a valid ranking metric.
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> entries = client.get_ranking("roe")
        >>> entries[0].rank
        1
        """
        if metric not in RANKING_METRICS:
            raise ValueError(
                f"Invalid ranking metric '{metric}'. "
                f"Must be one of: {', '.join(RANKING_METRICS)}"
            )
        logger.debug("Getting ranking", metric=metric)
        raw = self._request("GET", f"/v1/rankings/{metric}")
        data = self._unwrap_response(raw)
        entries = [self._parse_record(RankingEntry, item) for item in data]
        logger.info("Ranking retrieved", metric=metric, count=len(entries))
        return entries

    def list_industries(self) -> list[Industry]:
        """List all industry classifications.

        Calls ``GET /v1/industries``.

        Returns
        -------
        list[Industry]
            List of industry records (34 classifications).

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> industries = client.list_industries()
        >>> len(industries)
        34
        """
        logger.debug("Listing industries")
        raw = self._request("GET", "/v1/industries")
        data = self._unwrap_response(raw)
        industries = [self._parse_record(Industry, item) for item in data]
        logger.info("Industries listed", count=len(industries))
        return industries

    def get_industry(self, slug: str) -> dict[str, Any]:
        """Get industry details.

        Calls ``GET /v1/industries/{slug}``.

        Parameters
        ----------
        slug : str
            URL-friendly industry identifier
            (e.g. ``"information-communication"``).

        Returns
        -------
        dict[str, Any]
            Industry details including company list and averages.

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.
        EdinetRateLimitError
            If the daily rate limit is exceeded.

        Examples
        --------
        >>> details = client.get_industry("information-communication")
        >>> details["name"]
        '情報・通信業'
        """
        logger.debug("Getting industry", slug=slug)
        raw = self._request("GET", f"/v1/industries/{slug}")
        data = self._unwrap_response(raw)
        logger.info("Industry retrieved", slug=slug)
        return data

    def get_status(self) -> dict[str, Any]:
        """Get API status information.

        Calls ``GET /v1/status``. This endpoint does not require
        authentication and can be used to verify API availability.

        Returns
        -------
        dict[str, Any]
            Status information including available industries and
            total company count.

        Raises
        ------
        EdinetAPIError
            If the API returns an error response.

        Examples
        --------
        >>> status = client.get_status()
        >>> status["total_companies"]
        3848
        """
        logger.debug("Getting API status")
        raw = self._request("GET", "/v1/status")
        data = self._unwrap_response(raw)
        logger.info("API status retrieved")
        return data

    # =========================================================================
    # Rate Limiter
    # =========================================================================

    def get_remaining_calls(self) -> int | None:
        """Get the number of remaining API calls for today.

        Returns
        -------
        int | None
            Remaining calls if a rate limiter is configured,
            ``None`` otherwise.

        Examples
        --------
        >>> client.get_remaining_calls()
        900
        """
        if self._rate_limiter is None:
            return None
        return self._rate_limiter.get_remaining()

    # =========================================================================
    # Internal Parsing Helpers
    # =========================================================================

    def _parse_record[T](self, cls: type[T], data: dict[str, Any]) -> T:
        """Create a dataclass instance from a dict, ignoring unknown fields.

        Extracts only the fields defined on ``cls`` from ``data``,
        silently discarding any keys that do not match a dataclass field.
        This provides resilience against API response changes that add
        new fields.

        Parameters
        ----------
        cls : type[T]
            The frozen dataclass type to instantiate.
        data : dict[str, Any]
            Raw API response dictionary (may contain unknown keys).

        Returns
        -------
        T
            An instance of ``cls`` with only known fields populated.

        Examples
        --------
        >>> client._parse_record(Company, {"edinet_code": "E00001", "unknown": 1})
        Company(edinet_code='E00001', ...)
        """
        field_names = {f.name for f in dataclasses.fields(cls)}  # type: ignore[arg-type]
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)

    def _unwrap_response(self, body: Any) -> Any:
        """Unwrap the API response envelope if present.

        The EDINET DB API wraps all responses in a ``{"data": ...}``
        envelope. This method extracts the inner payload. If the
        response is not wrapped (e.g. already a list or a dict without
        a ``"data"`` key), it is returned as-is.

        Parameters
        ----------
        body : Any
            Parsed JSON response body from the API.

        Returns
        -------
        Any
            The unwrapped payload (``body["data"]`` if present,
            otherwise ``body`` itself).

        Examples
        --------
        >>> client._unwrap_response({"data": [{"id": 1}], "meta": {}})
        [{'id': 1}]
        >>> client._unwrap_response([{"id": 1}])
        [{'id': 1}]
        """
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    # =========================================================================
    # Internal HTTP Logic
    # =========================================================================

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Execute an HTTP request with retry, polite delay, and rate limiting.

        Parameters
        ----------
        method : str
            HTTP method (e.g. ``"GET"``).
        path : str
            API endpoint path (e.g. ``"/v1/companies"``).
        params : dict[str, str] | None
            Optional query parameters.

        Returns
        -------
        Any
            Parsed JSON response body.

        Raises
        ------
        EdinetAPIError
            If the API returns a non-retryable error.
        EdinetRateLimitError
            If the daily rate limit is exceeded or API returns 429.
        """
        # Check rate limiter before making request
        self._check_rate_limit()

        last_error: Exception | None = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                # Apply polite delay
                self._apply_polite_delay()

                # Execute request
                url = path
                response = self._client.get(url, params=params)

                # Handle response
                return self._handle_response(response, path, attempt)

            except (EdinetAPIError, EdinetRateLimitError):
                raise
            except _RetryableError as e:
                last_error = e.cause
                if attempt < self._retry_config.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(
                        "Request failed, retrying",
                        path=path,
                        attempt=attempt + 1,
                        max_attempts=self._retry_config.max_attempts,
                        delay_seconds=delay,
                        error=str(e.cause),
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "All retry attempts exhausted",
                        path=path,
                        attempts=self._retry_config.max_attempts,
                        error=str(e.cause),
                    )
            except (
                httpx.ConnectError,
                httpx.TimeoutException,
            ) as e:
                last_error = e
                if attempt < self._retry_config.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(
                        "Network error, retrying",
                        path=path,
                        attempt=attempt + 1,
                        max_attempts=self._retry_config.max_attempts,
                        delay_seconds=delay,
                        error_type=type(e).__name__,
                        error=str(e),
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "All retry attempts exhausted (network error)",
                        path=path,
                        attempts=self._retry_config.max_attempts,
                        error_type=type(e).__name__,
                        error=str(e),
                    )

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        raise EdinetAPIError(
            message=f"Request failed after {self._retry_config.max_attempts} attempts: {error_msg}",
            url=f"{self._config.base_url}{path}",
            status_code=500,
            response_body="",
        )

    def _handle_response(
        self, response: httpx.Response, path: str, attempt: int
    ) -> Any:
        """Handle HTTP response, raising appropriate exceptions.

        Parameters
        ----------
        response : httpx.Response
            The HTTP response.
        path : str
            The request path for error context.
        attempt : int
            Current retry attempt number (0-indexed).

        Returns
        -------
        Any
            Parsed JSON response body.

        Raises
        ------
        _RetryableError
            If the response is a retryable 5xx error.
        EdinetRateLimitError
            If HTTP 429 is returned.
        EdinetAPIError
            If a non-retryable 4xx error is returned.
        """
        status = response.status_code

        # Record API call on successful communication
        if self._rate_limiter is not None:
            self._rate_limiter.record_call()

        # 5xx: retryable server error
        if status >= 500:
            logger.warning(
                "Server error",
                path=path,
                status_code=status,
                attempt=attempt + 1,
            )
            raise _RetryableError(
                cause=EdinetAPIError(
                    message=f"Server error: HTTP {status}",
                    url=f"{self._config.base_url}{path}",
                    status_code=status,
                    response_body=response.text,
                )
            )

        # 429: rate limit error (not retried)
        if status == _RATE_LIMIT_STATUS_CODE:
            logger.warning(
                "Rate limit response from API",
                path=path,
                status_code=status,
            )
            raise EdinetRateLimitError(
                message=f"API rate limit exceeded: HTTP {status}",
                calls_used=0,
                calls_limit=0,
            )

        # Other 4xx: client error (not retried)
        if 400 <= status < 500:
            logger.error(
                "Client error",
                path=path,
                status_code=status,
            )
            raise EdinetAPIError(
                message=f"Client error: HTTP {status}",
                url=f"{self._config.base_url}{path}",
                status_code=status,
                response_body=response.text,
            )

        # 2xx: success
        logger.debug(
            "Request succeeded",
            path=path,
            status_code=status,
        )
        return response.json()

    def _check_rate_limit(self) -> None:
        """Check the daily rate limiter and raise if limit is exceeded.

        Raises
        ------
        EdinetRateLimitError
            If the daily rate limit has been reached.
        """
        if self._rate_limiter is None:
            return

        self._rate_limiter.reset_if_new_day()

        if not self._rate_limiter.is_allowed():
            remaining = self._rate_limiter.get_remaining()
            logger.warning(
                "Daily rate limit exceeded",
                remaining=remaining,
            )
            raise EdinetRateLimitError(
                message="Daily API call limit exceeded",
                calls_used=self._rate_limiter.daily_limit
                - self._rate_limiter.safe_margin
                - remaining,
                calls_limit=self._rate_limiter.daily_limit
                - self._rate_limiter.safe_margin,
            )

    def _apply_polite_delay(self) -> None:
        """Apply polite delay between consecutive requests.

        Ensures at least ``config.polite_delay`` seconds have elapsed
        since the last request. Does nothing if this is the first
        request or enough time has already passed.
        """
        if self._last_request_time > 0:
            elapsed = time.monotonic() - self._last_request_time
            remaining = self._config.polite_delay - elapsed
            if remaining > 0:
                time.sleep(remaining)

        self._last_request_time = time.monotonic()

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Parameters
        ----------
        attempt : int
            Current attempt number (0-indexed).

        Returns
        -------
        float
            Delay in seconds.
        """
        delay = min(
            self._retry_config.initial_delay
            * (self._retry_config.exponential_base**attempt),
            self._retry_config.max_delay,
        )
        if self._retry_config.jitter:
            delay *= 0.5 + random.random()  # nosec B311 (cryptographic randomness not required for retry jitter)
        return delay


class _RetryableError(Exception):
    """Internal exception to signal a retryable error.

    This is not part of the public API. It wraps a cause exception
    so the retry loop can distinguish retryable from non-retryable
    errors.

    Parameters
    ----------
    cause : Exception
        The underlying exception that triggered the retry.
    """

    def __init__(self, cause: Exception) -> None:
        super().__init__(str(cause))
        self.cause = cause


__all__ = ["EdinetClient"]
