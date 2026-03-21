"""Type definitions for the market.edinet module.

This module provides type definitions for the EDINET DB API client,
including:

- Configuration dataclasses (EdinetConfig, RetryConfig)
- Data record dataclasses for API responses:
  - Company: company master data (~3,848 rows)
  - FinancialRecord: annual financial statements (API-verified fields)
  - RatioRecord: computed financial ratios (API-verified fields)
  - AnalysisResult: AI-generated financial health analysis
  - TextBlock: securities report text excerpts
  - RankingEntry: metric-based company rankings
  - Industry: industry master data (34 classifications)
  - SyncProgress: sync state for resume support

All dataclasses use ``frozen=True`` to ensure immutability.
Field definitions are based on the Step 0 API verification
(``docs/project/project-70/step0-api-verification.json``).

See Also
--------
market.nasdaq.types : Similar type-definition pattern for the NASDAQ module.
market.edinet.constants : Default values referenced by EdinetConfig.
database.db.connection : ``get_db_path()`` used for default DB path resolution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from database.db.connection import get_db_path
from market.edinet.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_DB_NAME,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    EDINET_DB_PATH_ENV,
    SYNC_STATE_FILENAME,
)

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class EdinetConfig:
    """Configuration for EDINET DB API client behaviour.

    Controls API authentication, HTTP settings, and database path
    resolution. Default values are sourced from
    ``market.edinet.constants`` to keep a single source of truth.

    Parameters
    ----------
    api_key : str
        API key for EDINET DB authentication
        (sent as ``X-API-Key`` HTTP header).
    base_url : str
        Base URL for the EDINET DB REST API
        (default: ``DEFAULT_BASE_URL``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    polite_delay : float
        Minimum wait time between consecutive API requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 0.1).
    db_path : Path | None
        Explicit SQLite file path. When ``None``, the path is resolved
        via the ``EDINET_DB_PATH`` environment variable or
        ``get_db_path("sqlite", "edinet")`` fallback.

    Examples
    --------
    >>> config = EdinetConfig(api_key="my_key", timeout=60.0)
    >>> config.api_key
    'my_key'
    >>> config.timeout
    60.0
    """

    api_key: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    polite_delay: float = DEFAULT_POLITE_DELAY
    db_path: Path | None = None

    def __post_init__(self) -> None:
        """Validate configuration value ranges.

        Raises
        ------
        ValueError
            If any configuration value is outside its valid range,
            or if ``api_key`` is empty.
        """
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "api_key must not be empty. "
                "Set EDINET_DB_API_KEY environment variable or pass api_key explicitly."
            )
        if not (1.0 <= self.timeout <= 300.0):
            raise ValueError(
                f"timeout must be between 1.0 and 300.0, got {self.timeout}"
            )
        if not (0.0 <= self.polite_delay <= 60.0):
            raise ValueError(
                f"polite_delay must be between 0.0 and 60.0, got {self.polite_delay}"
            )

    @property
    def resolved_db_path(self) -> Path:
        """Resolve the SQLite file path using priority order.

        Priority:
        1. Explicit ``db_path`` field
        2. ``EDINET_DB_PATH`` environment variable
        3. ``get_db_path("sqlite", "edinet")`` fallback

        Returns
        -------
        Path
            Resolved path to the SQLite database file.

        Examples
        --------
        >>> config = EdinetConfig(
        ...     api_key="k",
        ...     db_path=Path("/data/edinet.db"),
        ... )
        >>> config.resolved_db_path
        PosixPath('/data/edinet.db')
        """
        if self.db_path is not None:
            return self.db_path

        env_path = os.environ.get(EDINET_DB_PATH_ENV, "")
        if env_path:
            return Path(env_path)

        return get_db_path("sqlite", DEFAULT_DB_NAME)

    @property
    def sync_state_path(self) -> Path:
        """Get the sync state file path.

        The sync state file is stored in the same directory as the
        SQLite database file.

        Returns
        -------
        Path
            Path to the sync state JSON file.

        Examples
        --------
        >>> config = EdinetConfig(
        ...     api_key="k",
        ...     db_path=Path("/data/sqlite/edinet.db"),
        ... )
        >>> config.sync_state_path
        PosixPath('/data/sqlite/_sync_state.json')
        """
        return self.resolved_db_path.parent / SYNC_STATE_FILENAME


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
            If any configuration value is outside its valid range.
        """
        if not (1 <= self.max_attempts <= 10):
            raise ValueError(
                f"max_attempts must be between 1 and 10, got {self.max_attempts}"
            )
        if self.initial_delay < 0:
            raise ValueError(
                f"initial_delay must be positive, got {self.initial_delay}"
            )
        if self.max_delay < self.initial_delay:
            raise ValueError(
                f"max_delay must be >= initial_delay, "
                f"got max_delay={self.max_delay}, initial_delay={self.initial_delay}"
            )


# =============================================================================
# Data Record Dataclasses
# =============================================================================


@dataclass(frozen=True)
class Company:
    """Company master data from the EDINET DB API.

    Represents a single company record as returned by the
    ``GET /v1/companies`` endpoint. Approximately 3,848 listed
    Japanese companies are available.

    Parameters
    ----------
    edinet_code : str
        EDINET code (e.g. ``"E03006"``). Primary key.
    sec_code : str
        Securities code (e.g. ``"30760"``).
    name : str
        Company name (e.g. ``"あいホールディングス株式会社"``).
    industry : str
        Industry name in Japanese (e.g. ``"卸売業"``).
    name_en : str | None
        Company name in English (e.g. ``None``).
    name_ja : str | None
        Company name in Japanese (e.g. ``"あいホールディングス株式会社"``).
    accounting_standard : str | None
        Accounting standard code (e.g. ``"JP"``).
    credit_rating : str | None
        Credit rating (e.g. ``"S"``).
    credit_score : int | None
        Credit score (e.g. ``93``).

    Examples
    --------
    >>> company = Company(
    ...     edinet_code="E03006",
    ...     sec_code="30760",
    ...     name="あいホールディングス株式会社",
    ...     industry="卸売業",
    ... )
    >>> company.edinet_code
    'E03006'
    """

    edinet_code: str
    sec_code: str
    name: str
    industry: str
    name_en: str | None = None
    name_ja: str | None = None
    accounting_standard: str | None = None
    credit_rating: str | None = None
    credit_score: int | None = None


@dataclass(frozen=True)
class FinancialRecord:
    """Annual financial statement data from the EDINET DB API.

    Represents a single fiscal year's financial data for a company.
    Fields are based on the actual API response verified in Step 0
    (``docs/project/project-70/step0-api-verification.json``).

    Required fields are ``edinet_code`` and ``fiscal_year`` only.
    All financial indicator fields are ``Optional`` (``None`` by default)
    because the API returns different field sets depending on the
    company's accounting standard (JP GAAP / US GAAP / IFRS).

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company (e.g. ``"E02144"``).
    fiscal_year : int
        Fiscal year as integer (e.g. ``2025``).
    revenue : float | None
        Revenue (売上高) in JPY.
    operating_income : float | None
        Operating income (営業利益) in JPY. JP GAAP only.
    ordinary_income : float | None
        Ordinary income (経常利益) in JPY.
    net_income : float | None
        Net income (当期純利益) in JPY.
    total_assets : float | None
        Total assets (総資産) in JPY.
    net_assets : float | None
        Net assets (純資産) in JPY.
    shareholders_equity : float | None
        Shareholders' equity (自己資本) in JPY.
    cf_operating : float | None
        Operating cash flow (営業CF) in JPY.
    cf_investing : float | None
        Investing cash flow (投資CF) in JPY.
    cf_financing : float | None
        Financing cash flow (財務CF) in JPY.
    eps : float | None
        Earnings per share (1株当たり利益).
    bps : float | None
        Book value per share (1株当たり純資産).
    diluted_eps : float | None
        Diluted earnings per share (希薄化後EPS).
    dividend_per_share : float | None
        Dividend per share (1株当たり配当).
    num_employees : int | None
        Number of employees (従業員数).
    capex : float | None
        Capital expenditure (設備投資) in JPY. JP GAAP only.
    depreciation : float | None
        Depreciation (減価償却費) in JPY. JP GAAP only.
    rnd_expenses : float | None
        R&D expenses (研究開発費) in JPY. JP GAAP only.
    goodwill : float | None
        Goodwill (のれん) in JPY. JP GAAP only.
    cash : float | None
        Cash and cash equivalents (現金及び現金同等物) in JPY.
    comprehensive_income : float | None
        Comprehensive income (包括利益) in JPY.
    equity_ratio_official : float | None
        Official equity ratio (自己資本比率) in percent.
    payout_ratio : float | None
        Payout ratio (配当性向) in percent.
    per : float | None
        Price-to-earnings ratio (株価収益率).
    profit_before_tax : float | None
        Profit before tax (税引前利益) in JPY.
    roe_official : float | None
        Official return on equity (自己資本利益率) in percent.
    accounting_standard : str | None
        Accounting standard (e.g. ``"JP GAAP"``, ``"US GAAP"``, ``"IFRS"``).
    submit_date : str | None
        Report submission date (e.g. ``"2025-06-15"``).

    Examples
    --------
    >>> record = FinancialRecord(
    ...     edinet_code="E00001",
    ...     fiscal_year=2025,
    ...     revenue=1_000_000_000.0,
    ...     net_income=70_000_000.0,
    ... )
    >>> record.revenue
    1000000000.0
    """

    # --- Required key fields ---
    edinet_code: str
    fiscal_year: int

    # --- API-verified financial fields (all Optional) ---
    # P/L fields
    revenue: float | None = None
    operating_income: float | None = None
    ordinary_income: float | None = None
    net_income: float | None = None
    profit_before_tax: float | None = None
    comprehensive_income: float | None = None

    # B/S fields
    total_assets: float | None = None
    net_assets: float | None = None
    shareholders_equity: float | None = None
    cash: float | None = None
    goodwill: float | None = None

    # Cash flow fields
    cf_operating: float | None = None
    cf_investing: float | None = None
    cf_financing: float | None = None

    # Per-share fields
    eps: float | None = None
    diluted_eps: float | None = None
    bps: float | None = None
    dividend_per_share: float | None = None

    # Ratio fields
    equity_ratio_official: float | None = None
    payout_ratio: float | None = None
    per: float | None = None
    roe_official: float | None = None

    # Other fields
    num_employees: int | None = None
    capex: float | None = None
    depreciation: float | None = None
    rnd_expenses: float | None = None
    accounting_standard: str | None = None
    submit_date: str | None = None


@dataclass(frozen=True)
class RatioRecord:
    """Computed financial ratio data from the EDINET DB API.

    Represents a single fiscal year's computed financial ratios for a
    company. Fields are based on the actual API response verified in
    Step 0 (``docs/project/project-70/step0-api-verification.json``).

    Required fields are ``edinet_code`` and ``fiscal_year`` only.
    All ratio fields are ``Optional`` (``None`` by default) because
    not all ratios are available for every company/year combination.

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company.
    fiscal_year : int
        Fiscal year as integer (e.g. ``2025``).
    roe : float | None
        Return on equity (自己資本利益率) in percent.
    roa : float | None
        Return on assets (総資産利益率) in percent.
    roe_official : float | None
        Official ROE as reported by the company.
    net_margin : float | None
        Net margin (純利益率) in percent.
    equity_ratio : float | None
        Equity ratio (自己資本比率) in percent.
    equity_ratio_official : float | None
        Official equity ratio as reported by the company.
    payout_ratio : float | None
        Payout ratio (配当性向) in percent.
    asset_turnover : float | None
        Asset turnover (総資産回転率).
    eps : float | None
        Earnings per share (1株当たり利益).
    diluted_eps : float | None
        Diluted earnings per share (希薄化後EPS).
    bps : float | None
        Book value per share (1株当たり純資産).
    dividend_per_share : float | None
        Dividend per share (1株当たり配当).
    adjusted_dividend_per_share : float | None
        Split-adjusted dividend per share (調整後1株配当).
    dividend_yield : float | None
        Dividend yield (配当利回り) in percent.
    per : float | None
        Price-to-earnings ratio (株価収益率).
    fcf : float | None
        Free cash flow (フリーキャッシュフロー) in JPY.
    net_income_per_employee : float | None
        Net income per employee (従業員1人当たり純利益).
    revenue_per_employee : float | None
        Revenue per employee (従業員1人当たり売上高).
    split_adjustment_factor : float | None
        Stock split adjustment factor (株式分割調整係数).

    Examples
    --------
    >>> record = RatioRecord(
    ...     edinet_code="E00001",
    ...     fiscal_year=2025,
    ...     roe=3.89,
    ...     roa=1.40,
    ... )
    >>> record.roe
    3.89
    """

    # --- Required key fields ---
    edinet_code: str
    fiscal_year: int

    # --- API-verified ratio fields (all Optional) ---
    # Profitability ratios
    roe: float | None = None
    roa: float | None = None
    roe_official: float | None = None
    net_margin: float | None = None

    # Balance sheet ratios
    equity_ratio: float | None = None
    equity_ratio_official: float | None = None

    # Dividend ratios
    payout_ratio: float | None = None
    dividend_per_share: float | None = None
    adjusted_dividend_per_share: float | None = None
    dividend_yield: float | None = None

    # Efficiency ratios
    asset_turnover: float | None = None

    # Per-share metrics
    eps: float | None = None
    diluted_eps: float | None = None
    bps: float | None = None

    # Valuation ratios
    per: float | None = None

    # Cash flow
    fcf: float | None = None

    # Per-employee metrics
    net_income_per_employee: float | None = None
    revenue_per_employee: float | None = None

    # Leverage / capital
    financial_leverage: float | None = None
    invested_capital: float | None = None

    # Adjustment factors
    split_adjustment_factor: float | None = None


@dataclass(frozen=True)
class TextBlock:
    """Securities report text excerpt from the EDINET DB API.

    Represents a single section of text from an annual securities
    report (yuho). Data is returned by the
    ``GET /v1/companies/{edinet_code}/text-blocks`` endpoint.

    The actual API response is a list of ``{section, text}`` dicts.
    Each item becomes one ``TextBlock`` instance with the
    ``edinet_code`` and ``fiscal_year`` injected by the client.

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company.
    fiscal_year : int
        Fiscal year as integer (e.g. ``2025``).
    section : str
        Section name (e.g. ``"事業の内容"``, ``"経営者による分析"``).
    text : str
        Section text content.

    Examples
    --------
    >>> block = TextBlock(
    ...     edinet_code="E00001",
    ...     fiscal_year=2025,
    ...     section="事業の内容",
    ...     text="事業概要テキスト",
    ... )
    >>> block.section
    '事業の内容'
    """

    edinet_code: str
    fiscal_year: int
    section: str
    text: str


@dataclass(frozen=True)
class Industry:
    """Industry master data from the EDINET DB API.

    Represents a single industry classification. Data is returned by
    the ``GET /v1/industries`` endpoint. There are 34 industry
    classifications available.

    Parameters
    ----------
    slug : str
        URL-friendly industry identifier (e.g. ``"information-communication"``).
    name : str
        Industry name in Japanese (e.g. ``"情報・通信業"``).
    company_count : int
        Number of companies in this industry.

    Examples
    --------
    >>> industry = Industry(
    ...     slug="information-communication",
    ...     name="情報・通信業",
    ...     company_count=500,
    ... )
    >>> industry.slug
    'information-communication'
    """

    slug: str
    name: str
    company_count: int


@dataclass(frozen=True)
class SyncProgress:
    """Sync progress state for resumable EDINET data synchronization.

    Tracks the current sync phase, completed EDINET codes, today's
    API call count, and error history. Stored as a JSON file next to
    the DuckDB database file for resume support.

    Parameters
    ----------
    current_phase : str
        Current sync phase name (e.g. ``"companies"``,
        ``"financials"``, ``"ratios"``).
    completed_codes : tuple[str, ...]
        Tuple of EDINET codes that have been successfully synced
        in the current phase (default: ``()``).
    today_api_calls : int
        Number of API calls made today (default: 0).
    errors : tuple[str, ...]
        Tuple of error messages encountered during sync
        (default: ``()``).

    Examples
    --------
    >>> progress = SyncProgress(current_phase="companies")
    >>> progress.today_api_calls
    0
    >>> progress.completed_codes
    ()
    """

    current_phase: str
    completed_codes: tuple[str, ...] = field(default_factory=tuple)
    today_api_calls: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "Company",
    "EdinetConfig",
    "FinancialRecord",
    "Industry",
    "RatioRecord",
    "RetryConfig",
    "SyncProgress",
    "TextBlock",
]
