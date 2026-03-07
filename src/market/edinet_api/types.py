"""Type definitions for the market.edinet_api module.

This module provides type definitions for EDINET disclosure API
(``api.edinet-fsa.go.jp``) data retrieval including:

- Enum types (DocumentType)
- Configuration dataclasses (EdinetApiConfig, RetryConfig)
- Data record dataclasses (DisclosureDocument)

This module is for the **EDINET disclosure API** and is completely
separate from ``market.edinet.types`` which covers the EDINET DB API.

All Enums inherit from ``str`` and ``Enum`` so they can be used directly as
string values in API query parameters. All dataclasses use ``frozen=True``
to ensure immutability.

See Also
--------
market.edinet_api.constants : Default values referenced by EdinetApiConfig.
market.edinet.types : EDINET DB API type definitions (separate module).
market.bse.types : Similar type-definition pattern for the BSE module.
"""

from dataclasses import dataclass, field
from enum import Enum

from market.edinet_api.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
)

# =============================================================================
# Enum Definitions
# =============================================================================


class DocumentType(str, Enum):
    """EDINET disclosure document type classification.

    The EDINET disclosure API classifies documents into types
    based on the kind of regulatory filing.

    Parameters
    ----------
    value : str
        The document type code used in API requests.

    Examples
    --------
    >>> DocumentType.ANNUAL_REPORT
    <DocumentType.ANNUAL_REPORT: '有価証券報告書'>
    >>> str(DocumentType.ANNUAL_REPORT)
    '有価証券報告書'
    """

    ANNUAL_REPORT = "有価証券報告書"
    QUARTERLY_REPORT = "四半期報告書"
    EXTRAORDINARY_REPORT = "臨時報告書"
    SECURITIES_REGISTRATION = "有価証券届出書"
    AMENDMENT = "訂正報告書"
    SHELF_REGISTRATION = "発行登録書"
    LARGE_HOLDING_REPORT = "大量保有報告書"
    PROXY_STATEMENT = "委任状勧誘書類"


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class EdinetApiConfig:
    """Configuration for EDINET disclosure API HTTP behaviour.

    Controls API key, polite delays, request timeout, and delay jitter.
    Default values are sourced from ``market.edinet_api.constants`` to keep
    a single source of truth.

    Parameters
    ----------
    api_key : str
        EDINET FSA API key for authentication. Sent as
        ``Subscription-Key`` query parameter (default: ``""``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    polite_delay : float
        Minimum wait time between consecutive requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 0.5).
    delay_jitter : float
        Random jitter added to polite delay in seconds
        (default: ``DEFAULT_DELAY_JITTER`` = 0.1).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = EdinetApiConfig(api_key="your-api-key", timeout=60.0)
    >>> config.timeout
    60.0
    """

    api_key: str = field(default="", repr=False)
    timeout: float = DEFAULT_TIMEOUT
    polite_delay: float = DEFAULT_POLITE_DELAY
    delay_jitter: float = DEFAULT_DELAY_JITTER

    def __post_init__(self) -> None:
        """Validate configuration value ranges.

        Raises
        ------
        ValueError
            If any configuration value is outside its valid range.
        """
        if not (1.0 <= self.timeout <= 300.0):
            raise ValueError(
                f"timeout must be between 1.0 and 300.0, got {self.timeout}"
            )
        if not (0.0 <= self.polite_delay <= 60.0):
            raise ValueError(
                f"polite_delay must be between 0.0 and 60.0, got {self.polite_delay}"
            )
        if not (0.0 <= self.delay_jitter <= 30.0):
            raise ValueError(
                f"delay_jitter must be between 0.0 and 30.0, got {self.delay_jitter}"
            )


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    initial_delay : float
        Initial delay between retries in seconds (default: 1.0).
    max_delay : float
        Maximum delay between retries in seconds (default: 30.0).
    exponential_base : float
        Base for exponential backoff calculation (default: 2.0).
    jitter : bool
        Whether to add random jitter to delays (default: True).

    Raises
    ------
    ValueError
        If max_attempts is outside its valid range.

    Examples
    --------
    >>> config = RetryConfig(max_attempts=5, initial_delay=0.5)
    >>> config.max_attempts
    5
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        """Validate retry configuration value ranges.

        Raises
        ------
        ValueError
            If max_attempts is outside its valid range.
        """
        if not (1 <= self.max_attempts <= 10):
            raise ValueError(
                f"max_attempts must be between 1 and 10, got {self.max_attempts}"
            )


# =============================================================================
# Data Record Dataclasses
# =============================================================================


@dataclass(frozen=True)
class DisclosureDocument:
    """A single disclosure document record from the EDINET disclosure API.

    Stores metadata for a disclosure document retrieved from the
    EDINET disclosure API document list endpoint.

    Parameters
    ----------
    doc_id : str
        EDINET document ID (e.g. ``"S100ABCD"``).
    edinet_code : str | None
        EDINET code of the filing company (e.g. ``"E00001"``).
    filer_name : str
        Name of the filing company (e.g. ``"テスト株式会社"``).
    doc_description : str
        Description of the document (e.g. ``"有価証券報告書"``).
    submit_date_time : str
        Document submission date/time (e.g. ``"2025-01-15 09:30"``).
    doc_type_code : str | None
        Document type code (e.g. ``"120"`` for annual report).
    sec_code : str | None
        Securities code (e.g. ``"72010"``).
    jcn : str | None
        Corporate number (法人番号).

    Examples
    --------
    >>> doc = DisclosureDocument(
    ...     doc_id="S100ABCD",
    ...     edinet_code="E00001",
    ...     filer_name="テスト株式会社",
    ...     doc_description="有価証券報告書",
    ...     submit_date_time="2025-01-15 09:30",
    ...     doc_type_code="120",
    ...     sec_code="72010",
    ...     jcn="1234567890123",
    ... )
    >>> doc.doc_id
    'S100ABCD'
    """

    doc_id: str
    edinet_code: str | None
    filer_name: str
    doc_description: str
    submit_date_time: str
    doc_type_code: str | None = None
    sec_code: str | None = None
    jcn: str | None = None


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "DisclosureDocument",
    "DocumentType",
    "EdinetApiConfig",
    "RetryConfig",
]
