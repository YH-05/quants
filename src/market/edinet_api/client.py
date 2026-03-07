"""HTTP client for the EDINET disclosure API.

This module provides the ``EdinetApiClient`` class, a synchronous HTTP client
for the EDINET disclosure API (``api.edinet-fsa.go.jp``). Features include:

- ``EdinetApiSession``-based HTTP requests with SSRF prevention
- Document search by date and optional document type filter
- Streaming document download (XBRL ZIP, PDF)
- Context manager support (``with EdinetApiClient(...) as client:``)

This module is for the **EDINET disclosure API** and is completely
separate from ``market.edinet.client`` which uses the EDINET DB API.

The design follows the ``_request + _handle_response`` pattern used by
``market.edinet.client.EdinetClient``.

Examples
--------
Basic usage:

>>> config = EdinetApiConfig(api_key="your_key")
>>> with EdinetApiClient(config=config) as client:
...     docs = client.search_documents("2025-01-15")
...     print(f"Found {len(docs)} documents")

Download document:

>>> with EdinetApiClient(config=config) as client:
...     data = client.download_document("S100ABCD", format="xbrl")

See Also
--------
market.edinet_api.session : HTTP session with retry and SSRF prevention.
market.edinet_api.types : Configuration and data record dataclasses.
market.edinet_api.errors : Custom exception classes.
market.edinet_api.constants : API URLs and settings.
"""

from __future__ import annotations

import os
from typing import Any

from market.edinet_api.constants import (
    BASE_URL,
    DOWNLOAD_BASE_URL,
    EDINET_FSA_API_KEY_ENV,
)
from market.edinet_api.errors import EdinetApiAPIError, EdinetApiValidationError
from market.edinet_api.session import EdinetApiSession
from market.edinet_api.types import (
    DisclosureDocument,
    DocumentType,
    EdinetApiConfig,
    RetryConfig,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)


class EdinetApiClient:
    """Synchronous HTTP client for the EDINET disclosure API.

    Provides methods for searching disclosure documents and downloading
    document files (XBRL ZIPs, PDFs) with automatic retry on transient
    errors.

    Parameters
    ----------
    config : EdinetApiConfig | None
        API configuration. If ``None``, a default config is created
        using the ``EDINET_FSA_API_KEY`` environment variable.
    retry_config : RetryConfig | None
        Retry behaviour configuration. If ``None``, defaults are used
        (3 attempts, 1s initial delay, 30s max delay).

    Attributes
    ----------
    _config : EdinetApiConfig
        The API configuration.
    _session : EdinetApiSession
        The underlying HTTP session.

    Examples
    --------
    >>> with EdinetApiClient(config=EdinetApiConfig(api_key="key")) as client:
    ...     docs = client.search_documents("2025-01-15")
    """

    def __init__(
        self,
        config: EdinetApiConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize EdinetApiClient with configuration.

        Parameters
        ----------
        config : EdinetApiConfig | None
            API configuration. If ``None``, reads API key from
            ``EDINET_FSA_API_KEY`` environment variable.
        retry_config : RetryConfig | None
            Retry behaviour configuration. Defaults to ``RetryConfig()``.
        """
        if config is None:
            api_key = os.environ.get(EDINET_FSA_API_KEY_ENV, "")
            config = EdinetApiConfig(api_key=api_key)
        self._config: EdinetApiConfig = config
        self._session: EdinetApiSession = EdinetApiSession(
            config=config,
            retry_config=retry_config,
        )

        logger.info(
            "EdinetApiClient initialized",
            base_url=BASE_URL,
            download_base_url=DOWNLOAD_BASE_URL,
            timeout=self._config.timeout,
        )

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> EdinetApiClient:
        """Support context manager protocol.

        Returns
        -------
        EdinetApiClient
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
        """Close the HTTP session and release resources.

        Examples
        --------
        >>> client = EdinetApiClient(config=config)
        >>> client.close()
        """
        self._session.close()
        logger.debug("EdinetApiClient closed")

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def search_documents(
        self,
        date: str,
        doc_type: DocumentType | None = None,
    ) -> list[DisclosureDocument]:
        """Search disclosure documents by date.

        Calls ``GET {BASE_URL}/documents.json?date={date}&type=2``.

        Parameters
        ----------
        date : str
            Date to search for documents (format: ``YYYY-MM-DD``).
        doc_type : DocumentType | None
            Optional document type filter. When provided, only documents
            matching this type description are returned.

        Returns
        -------
        list[DisclosureDocument]
            List of disclosure document records.

        Raises
        ------
        EdinetApiValidationError
            If the date format is invalid.
        EdinetApiAPIError
            If the API returns an error response.
        EdinetApiRateLimitError
            If the API rate limit is exceeded.

        Examples
        --------
        >>> docs = client.search_documents("2025-01-15")
        >>> len(docs)
        150

        >>> docs = client.search_documents(
        ...     "2025-01-15",
        ...     doc_type=DocumentType.ANNUAL_REPORT,
        ... )
        """
        # Validate date format
        self._validate_date(date)

        logger.debug("Searching documents", date=date, doc_type=doc_type)

        url = f"{BASE_URL}/documents.json"
        params: dict[str, str] = {
            "date": date,
            "type": "2",  # type=2 returns metadata including document descriptions
        }

        response = self._session.get_with_retry(url, params=params)
        data = self._handle_response(response, url)

        # Extract document list from response
        results: list[dict[str, Any]] = data.get("results", [])
        documents: list[DisclosureDocument] = []

        for item in results:
            doc = DisclosureDocument(
                doc_id=item.get("docID", ""),
                edinet_code=item.get("edinetCode"),
                filer_name=item.get("filerName", ""),
                doc_description=item.get("docDescription", ""),
                submit_date_time=item.get("submitDateTime", ""),
                doc_type_code=item.get("docTypeCode"),
                sec_code=item.get("secCode"),
                jcn=item.get("JCN"),
            )
            documents.append(doc)

        # Apply optional document type filter
        if doc_type is not None:
            documents = [
                doc for doc in documents if doc_type.value in doc.doc_description
            ]

        logger.info(
            "Document search completed",
            date=date,
            doc_type=doc_type,
            total_results=len(results),
            filtered_results=len(documents),
        )
        return documents

    def download_document(
        self,
        doc_id: str,
        format: str = "xbrl",
    ) -> bytes:
        """Download a disclosure document.

        Downloads the document file from the EDINET disclosure download
        server using streaming download.

        Parameters
        ----------
        doc_id : str
            EDINET document ID (e.g. ``"S100ABCD"``).
        format : str
            Download format: ``"xbrl"`` (type=1, XBRL ZIP),
            ``"pdf"`` (type=2, PDF), ``"csv"`` (type=3, CSV),
            ``"english"`` (type=4, English docs) (default: ``"xbrl"``).

        Returns
        -------
        bytes
            The raw document content.

        Raises
        ------
        EdinetApiValidationError
            If the doc_id is empty or format is invalid.
        EdinetApiAPIError
            If the API returns an error response.
        EdinetApiRateLimitError
            If the API rate limit is exceeded.

        Examples
        --------
        >>> data = client.download_document("S100ABCD", format="xbrl")
        >>> len(data) > 0
        True

        >>> pdf_data = client.download_document("S100ABCD", format="pdf")
        """
        # Validate inputs
        if not doc_id:
            raise EdinetApiValidationError(
                "doc_id must not be empty",
                field="doc_id",
                value=doc_id,
            )

        format_type_map = {
            "xbrl": "1",
            "pdf": "2",
            "csv": "3",
            "english": "4",
        }
        if format not in format_type_map:
            raise EdinetApiValidationError(
                f"Invalid format '{format}'. Must be one of: {', '.join(format_type_map)}",
                field="format",
                value=format,
            )

        type_param = format_type_map[format]
        url = f"{DOWNLOAD_BASE_URL}/documents/{doc_id}"
        params: dict[str, str] = {"type": type_param}

        logger.debug(
            "Downloading document",
            doc_id=doc_id,
            format=format,
            type_param=type_param,
        )

        content = self._session.download(url, params=params)

        logger.info(
            "Document download completed",
            doc_id=doc_id,
            format=format,
            content_length=len(content),
        )
        return content

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _handle_response(
        self,
        response: Any,
        url: str,
    ) -> dict[str, Any]:
        """Parse JSON response body.

        Parameters
        ----------
        response : httpx.Response
            The HTTP response.
        url : str
            The request URL for error context.

        Returns
        -------
        dict[str, Any]
            Parsed JSON response body.

        Raises
        ------
        EdinetApiAPIError
            If the response body is not valid JSON.
        """
        try:
            data: dict[str, Any] = response.json()
        except Exception as e:
            logger.error(
                "Failed to parse response JSON",
                url=url,
                error=str(e),
            )
            raise EdinetApiAPIError(
                message=f"Failed to parse response JSON: {e}",
                url=url,
                status_code=response.status_code,
                response_body=response.text[:_MAX_RESPONSE_BODY_LOG],
            ) from e

        return data

    @staticmethod
    def _validate_date(date: str) -> None:
        """Validate date format (YYYY-MM-DD).

        Parameters
        ----------
        date : str
            Date string to validate.

        Raises
        ------
        EdinetApiValidationError
            If the date format is invalid.
        """
        if not date:
            raise EdinetApiValidationError(
                "date must not be empty",
                field="date",
                value=date,
            )

        from datetime import date as date_cls

        try:
            parsed = date_cls.fromisoformat(date)
        except ValueError as e:
            raise EdinetApiValidationError(
                f"Invalid date format '{date}'. Expected YYYY-MM-DD",
                field="date",
                value=date,
            ) from e

        if not (2000 <= parsed.year <= 2100):
            raise EdinetApiValidationError(
                f"Year {parsed.year} out of range. Expected 2000-2100",
                field="date",
                value=date,
            )


# Maximum length of response body stored in errors (CWE-209 mitigation)
_MAX_RESPONSE_BODY_LOG = 200

__all__ = ["EdinetApiClient"]
