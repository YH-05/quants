"""Fetcher module for SEC EDGAR filing data.

This module provides the EdgarFetcher class for retrieving SEC EDGAR filings
using the edgartools library as the underlying data source.

Features
--------
- Fetch filings by CIK or ticker symbol
- Filter by filing type (10-K, 10-Q, 13F)
- Retrieve latest filing for a given form type
- Automatic identity configuration check
- Structured error handling with context

Notes
-----
The edgartools library installs as ``edgar`` in site-packages, which conflicts
with our ``src/edgar`` package. This module uses ``importlib.machinery.PathFinder``
to import the edgartools ``Company`` class from the correct location.
"""

from __future__ import annotations

import functools
import importlib.machinery
import importlib.util
import sys
from typing import TYPE_CHECKING, Any

from database.rate_limiter import RateLimiter
from edgar.config import DEFAULT_RATE_LIMIT_PER_SECOND, load_config
from edgar.errors import EdgarError, FilingNotFoundError
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from edgar.types import FilingType

logger = get_logger(__name__)


@functools.lru_cache(maxsize=1)
def _import_edgartools_company() -> Any:
    """Import the Company class from the edgartools site-packages module.

    Returns
    -------
    type
        The edgartools Company class

    Raises
    ------
    EdgarError
        If edgartools is not installed or Company class is not found

    Notes
    -----
    edgartools installs as ``edgar`` in site-packages, which conflicts with
    our ``src/edgar`` package. We use ``importlib.machinery.PathFinder`` to
    locate and load the correct module from site-packages.
    """
    site_packages_paths = [p for p in sys.path if "site-packages" in p]
    spec = importlib.machinery.PathFinder.find_spec("edgar", site_packages_paths)

    if spec is None or spec.origin is None:
        msg = "edgartools is not installed. Install it with: uv add edgartools"
        raise EdgarError(msg)

    mod = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        msg = "Failed to load edgartools module: loader is None"
        raise EdgarError(msg)

    spec.loader.exec_module(mod)

    company_cls = getattr(mod, "Company", None)
    if company_cls is None:
        msg = "edgartools module does not export 'Company' class"
        raise EdgarError(msg)

    return company_cls


class EdgarFetcher:
    """Fetcher for SEC EDGAR filing data.

    Wraps the edgartools ``Company.get_filings()`` method to provide
    a typed, error-handled interface for retrieving SEC filings.

    The fetcher automatically verifies that SEC EDGAR identity is configured
    before making any requests.

    Attributes
    ----------
    _company_cls : type
        The edgartools Company class, lazily loaded

    Examples
    --------
    >>> from edgar.config import set_identity
    >>> set_identity("John Doe", "john@example.com")
    >>> fetcher = EdgarFetcher()
    >>> filings = fetcher.fetch("AAPL", FilingType.FORM_10K, limit=5)
    >>> latest = fetcher.fetch_latest("AAPL", FilingType.FORM_10K)
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        rate_limit_per_second: int | None = None,
    ) -> None:
        """Initialize EdgarFetcher.

        The edgartools Company class is lazily loaded on first use.

        Parameters
        ----------
        rate_limiter : RateLimiter | None
            An existing RateLimiter instance. If None, a new instance is
            created with the default or specified rate limit.
        rate_limit_per_second : int | None
            Maximum requests per second. Only used when rate_limiter is None.
            Defaults to DEFAULT_RATE_LIMIT_PER_SECOND (10).
        """
        logger.debug("Initializing EdgarFetcher")
        self._company_cls: Any | None = None

        if rate_limiter is not None:
            self._rate_limiter = rate_limiter
        else:
            rate = rate_limit_per_second or DEFAULT_RATE_LIMIT_PER_SECOND
            self._rate_limiter = RateLimiter(max_requests_per_second=rate)

        logger.debug(
            "EdgarFetcher rate limiter configured",
            max_requests_per_second=self._rate_limiter.max_requests_per_second,
        )

    def _get_company_cls(self) -> Any:
        """Get the edgartools Company class, loading it if necessary.

        Returns
        -------
        type
            The edgartools Company class

        Raises
        ------
        EdgarError
            If edgartools is not installed
        """
        if self._company_cls is None:
            logger.debug("Loading edgartools Company class")
            self._company_cls = _import_edgartools_company()
            logger.debug("edgartools Company class loaded successfully")
        return self._company_cls

    def _ensure_identity_configured(self) -> None:
        """Verify that SEC EDGAR identity is configured.

        Raises
        ------
        EdgarError
            If identity is not configured
        """
        config = load_config()
        if not config.is_identity_configured:
            msg = (
                "SEC EDGAR identity is not configured. "
                "Call set_identity(name, email) before fetching filings."
            )
            raise EdgarError(msg)

    def fetch(
        self,
        cik_or_ticker: str,
        form: FilingType,
        limit: int = 10,
    ) -> list[Any]:
        """Fetch filings for a company by CIK or ticker symbol.

        Parameters
        ----------
        cik_or_ticker : str
            CIK number or ticker symbol (e.g., "AAPL", "0000320193")
        form : FilingType
            The filing form type to filter by
        limit : int, default=10
            Maximum number of filings to return

        Returns
        -------
        list[Any]
            List of edgartools Filing objects

        Raises
        ------
        FilingNotFoundError
            If the company or filings cannot be found
        EdgarError
            If an unexpected error occurs during fetching

        Examples
        --------
        >>> fetcher = EdgarFetcher()
        >>> filings = fetcher.fetch("AAPL", FilingType.FORM_10K, limit=5)
        >>> len(filings) <= 5
        True
        """
        self._ensure_identity_configured()

        logger.info(
            "Fetching filings",
            cik_or_ticker=cik_or_ticker,
            form=form.value,
            limit=limit,
        )

        self._rate_limiter.acquire()

        try:
            company_cls = self._get_company_cls()
            company = company_cls(cik_or_ticker)

            filings = company.get_filings(form=form.value)
            result = list(filings.latest(limit))

            logger.info(
                "Filings fetched successfully",
                cik_or_ticker=cik_or_ticker,
                form=form.value,
                requested_limit=limit,
                fetched_count=len(result),
            )
            return result

        except (FilingNotFoundError, EdgarError):
            raise

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Failed to fetch filings",
                cik_or_ticker=cik_or_ticker,
                form=form.value,
                error=str(e),
                error_type=error_type,
                exc_info=True,
            )

            # AIDEV-NOTE: edgartools raises various exceptions (e.g., ValueError
            # for invalid ticker, HTTPError for network issues). We wrap them
            # in our domain exceptions for consistent error handling.
            if "not found" in str(e).lower() or "no cik" in str(e).lower():
                raise FilingNotFoundError(
                    f"Company not found: '{cik_or_ticker}'",
                    context={
                        "cik_or_ticker": cik_or_ticker,
                        "form": form.value,
                    },
                ) from e

            raise EdgarError(
                f"Failed to fetch filings for '{cik_or_ticker}': {e}",
                context={
                    "cik_or_ticker": cik_or_ticker,
                    "form": form.value,
                    "limit": limit,
                    "original_error": error_type,
                },
            ) from e

    def fetch_latest(
        self,
        cik_or_ticker: str,
        form: FilingType,
    ) -> Any | None:
        """Fetch the latest filing for a company by CIK or ticker symbol.

        Parameters
        ----------
        cik_or_ticker : str
            CIK number or ticker symbol (e.g., "AAPL", "0000320193")
        form : FilingType
            The filing form type to filter by

        Returns
        -------
        Any | None
            The latest edgartools Filing object, or None if no filings found

        Raises
        ------
        FilingNotFoundError
            If the company cannot be found
        EdgarError
            If an unexpected error occurs during fetching

        Examples
        --------
        >>> fetcher = EdgarFetcher()
        >>> filing = fetcher.fetch_latest("AAPL", FilingType.FORM_10K)
        >>> filing is not None
        True
        """
        logger.info(
            "Fetching latest filing",
            cik_or_ticker=cik_or_ticker,
            form=form.value,
        )

        filings = self.fetch(cik_or_ticker, form, limit=1)

        if not filings:
            logger.warning(
                "No filings found",
                cik_or_ticker=cik_or_ticker,
                form=form.value,
            )
            return None

        latest = filings[0]
        logger.info(
            "Latest filing fetched successfully",
            cik_or_ticker=cik_or_ticker,
            form=form.value,
        )
        return latest


__all__ = [
    "EdgarFetcher",
]
