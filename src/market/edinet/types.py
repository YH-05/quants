"""Type definitions for the market.edinet module.

This module provides type definitions for the EDINET DB API client,
including:

- Configuration dataclasses (EdinetConfig, RetryConfig)
- Data record dataclasses for API responses:
  - Company: company master data (~3,848 rows)
  - FinancialRecord: annual financial statements (24 indicators)
  - RatioRecord: computed financial ratios (13 ratios)
  - AnalysisResult: AI-generated financial health analysis
  - TextBlock: securities report text excerpts
  - RankingEntry: metric-based company rankings
  - Industry: industry master data (34 classifications)
  - SyncProgress: sync state for resume support

All dataclasses use ``frozen=True`` to ensure immutability.

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
        Explicit DuckDB file path. When ``None``, the path is resolved
        via the ``EDINET_DB_PATH`` environment variable or
        ``get_db_path("duckdb", "edinet")`` fallback.

    Examples
    --------
    >>> config = EdinetConfig(api_key="my_key", timeout=60.0)
    >>> config.api_key
    'my_key'
    >>> config.timeout
    60.0
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    polite_delay: float = DEFAULT_POLITE_DELAY
    db_path: Path | None = None

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

    @property
    def resolved_db_path(self) -> Path:
        """Resolve the DuckDB file path using priority order.

        Priority:
        1. Explicit ``db_path`` field
        2. ``EDINET_DB_PATH`` environment variable
        3. ``get_db_path("duckdb", "edinet")`` fallback

        Returns
        -------
        Path
            Resolved path to the DuckDB database file.

        Examples
        --------
        >>> config = EdinetConfig(
        ...     api_key="k",
        ...     db_path=Path("/data/edinet.duckdb"),
        ... )
        >>> config.resolved_db_path
        PosixPath('/data/edinet.duckdb')
        """
        if self.db_path is not None:
            return self.db_path

        env_path = os.environ.get(EDINET_DB_PATH_ENV, "")
        if env_path:
            return Path(env_path)

        return get_db_path("duckdb", DEFAULT_DB_NAME)

    @property
    def sync_state_path(self) -> Path:
        """Get the sync state file path.

        The sync state file is stored in the same directory as the
        DuckDB database file.

        Returns
        -------
        Path
            Path to the sync state JSON file.

        Examples
        --------
        >>> config = EdinetConfig(
        ...     api_key="k",
        ...     db_path=Path("/data/duckdb/edinet.duckdb"),
        ... )
        >>> config.sync_state_path
        PosixPath('/data/duckdb/_sync_state.json')
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
        EDINET code (e.g. ``"E00001"``). Primary key.
    sec_code : str
        Securities code (e.g. ``"10000"``).
    corp_name : str
        Company name in Japanese (e.g. ``"トヨタ自動車株式会社"``).
    industry_code : str
        Industry classification code (e.g. ``"3050"``).
    industry_name : str
        Industry name in Japanese (e.g. ``"情報・通信業"``).
    listing_status : str
        Listing status (e.g. ``"上場"`` or ``"非上場"``).

    Examples
    --------
    >>> company = Company(
    ...     edinet_code="E00001",
    ...     sec_code="10000",
    ...     corp_name="テスト株式会社",
    ...     industry_code="3050",
    ...     industry_name="情報・通信業",
    ...     listing_status="上場",
    ... )
    >>> company.edinet_code
    'E00001'
    """

    edinet_code: str
    sec_code: str
    corp_name: str
    industry_code: str
    industry_name: str
    listing_status: str


@dataclass(frozen=True)
class FinancialRecord:
    """Annual financial statement data from the EDINET DB API.

    Represents a single fiscal year's financial data for a company,
    containing 24 financial indicators. Data is returned by the
    ``GET /v1/companies/{edinet_code}/financials`` endpoint.

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company.
    fiscal_year : str
        Fiscal year (e.g. ``"2025"``).
    period_type : str
        Period type (e.g. ``"annual"``).
    revenue : int
        Revenue (売上高) in JPY.
    operating_income : int
        Operating income (営業利益) in JPY.
    ordinary_income : int
        Ordinary income (経常利益) in JPY.
    net_income : int
        Net income (当期純利益) in JPY.
    total_assets : int
        Total assets (総資産) in JPY.
    net_assets : int
        Net assets (純資産) in JPY.
    equity : int
        Shareholders' equity (自己資本) in JPY.
    interest_bearing_debt : int
        Interest-bearing debt (有利子負債) in JPY.
    operating_cf : int
        Operating cash flow (営業CF) in JPY.
    investing_cf : int
        Investing cash flow (投資CF) in JPY.
    financing_cf : int
        Financing cash flow (財務CF) in JPY.
    free_cf : int
        Free cash flow (フリーCF) in JPY.
    eps : float
        Earnings per share (1株当たり利益).
    bps : float
        Book value per share (1株当たり純資産).
    dividend_per_share : float
        Dividend per share (1株当たり配当).
    shares_outstanding : int
        Shares outstanding (発行済株式数).
    employees : int
        Number of employees (従業員数).
    capex : int
        Capital expenditure (設備投資) in JPY.
    depreciation : int
        Depreciation (減価償却費) in JPY.
    rnd_expense : int
        R&D expense (研究開発費) in JPY.
    goodwill : int
        Goodwill (のれん) in JPY.

    Examples
    --------
    >>> record = FinancialRecord(
    ...     edinet_code="E00001",
    ...     fiscal_year="2025",
    ...     period_type="annual",
    ...     revenue=1_000_000_000,
    ...     operating_income=100_000_000,
    ...     ordinary_income=110_000_000,
    ...     net_income=70_000_000,
    ...     total_assets=5_000_000_000,
    ...     net_assets=2_000_000_000,
    ...     equity=1_800_000_000,
    ...     interest_bearing_debt=1_000_000_000,
    ...     operating_cf=150_000_000,
    ...     investing_cf=-80_000_000,
    ...     financing_cf=-50_000_000,
    ...     free_cf=70_000_000,
    ...     eps=350.0,
    ...     bps=9_000.0,
    ...     dividend_per_share=100.0,
    ...     shares_outstanding=200_000,
    ...     employees=5_000,
    ...     capex=80_000_000,
    ...     depreciation=60_000_000,
    ...     rnd_expense=30_000_000,
    ...     goodwill=10_000_000,
    ... )
    >>> record.revenue
    1000000000
    """

    edinet_code: str
    fiscal_year: str
    period_type: str
    revenue: int
    operating_income: int
    ordinary_income: int
    net_income: int
    total_assets: int
    net_assets: int
    equity: int
    interest_bearing_debt: int
    operating_cf: int
    investing_cf: int
    financing_cf: int
    free_cf: int
    eps: float
    bps: float
    dividend_per_share: float
    shares_outstanding: int
    employees: int
    capex: int
    depreciation: int
    rnd_expense: int
    goodwill: int


@dataclass(frozen=True)
class RatioRecord:
    """Computed financial ratio data from the EDINET DB API.

    Represents a single fiscal year's computed financial ratios for a
    company, containing 13 ratio indicators. Data is returned by the
    ``GET /v1/companies/{edinet_code}/ratios`` endpoint.

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company.
    fiscal_year : str
        Fiscal year (e.g. ``"2025"``).
    period_type : str
        Period type (e.g. ``"annual"``).
    roe : float
        Return on equity (自己資本利益率) in percent.
    roa : float
        Return on assets (総資産利益率) in percent.
    operating_margin : float
        Operating margin (営業利益率) in percent.
    net_margin : float
        Net margin (純利益率) in percent.
    equity_ratio : float
        Equity ratio (自己資本比率) in percent.
    debt_equity_ratio : float
        Debt-to-equity ratio (負債資本比率).
    current_ratio : float
        Current ratio (流動比率).
    interest_coverage_ratio : float
        Interest coverage ratio (インタレスト・カバレッジ・レシオ).
    payout_ratio : float
        Payout ratio (配当性向) in percent.
    asset_turnover : float
        Asset turnover (総資産回転率).
    revenue_growth : float
        Revenue growth (売上高成長率) in percent.
    operating_income_growth : float
        Operating income growth (営業利益成長率) in percent.
    net_income_growth : float
        Net income growth (純利益成長率) in percent.

    Examples
    --------
    >>> record = RatioRecord(
    ...     edinet_code="E00001",
    ...     fiscal_year="2025",
    ...     period_type="annual",
    ...     roe=3.89,
    ...     roa=1.40,
    ...     operating_margin=10.0,
    ...     net_margin=7.0,
    ...     equity_ratio=36.0,
    ...     debt_equity_ratio=0.56,
    ...     current_ratio=1.50,
    ...     interest_coverage_ratio=5.0,
    ...     payout_ratio=28.57,
    ...     asset_turnover=0.20,
    ...     revenue_growth=5.0,
    ...     operating_income_growth=8.0,
    ...     net_income_growth=6.0,
    ... )
    >>> record.roe
    3.89
    """

    edinet_code: str
    fiscal_year: str
    period_type: str
    roe: float
    roa: float
    operating_margin: float
    net_margin: float
    equity_ratio: float
    debt_equity_ratio: float
    current_ratio: float
    interest_coverage_ratio: float
    payout_ratio: float
    asset_turnover: float
    revenue_growth: float
    operating_income_growth: float
    net_income_growth: float


@dataclass(frozen=True)
class AnalysisResult:
    """Financial health analysis result from the EDINET DB API.

    Represents the latest AI-generated financial health analysis for
    a company. Data is returned by the
    ``GET /v1/companies/{edinet_code}/analysis`` endpoint.

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company.
    health_score : float
        Financial health score (0-100).
    benchmark_comparison : str
        Comparison to benchmark (e.g. ``"above_average"``).
    commentary : str
        AI-generated commentary on financial health.

    Examples
    --------
    >>> result = AnalysisResult(
    ...     edinet_code="E00001",
    ...     health_score=75.0,
    ...     benchmark_comparison="above_average",
    ...     commentary="The company is financially healthy.",
    ... )
    >>> result.health_score
    75.0
    """

    edinet_code: str
    health_score: float
    benchmark_comparison: str
    commentary: str


@dataclass(frozen=True)
class TextBlock:
    """Securities report text excerpt from the EDINET DB API.

    Represents text excerpts from an annual securities report (yuho)
    for a company and fiscal year. Data is returned by the
    ``GET /v1/companies/{edinet_code}/text`` endpoint.

    Parameters
    ----------
    edinet_code : str
        EDINET code of the company.
    fiscal_year : str
        Fiscal year (e.g. ``"2025"``).
    business_overview : str
        Business overview text (事業の内容).
    risk_factors : str
        Risk factors text (事業等のリスク).
    management_analysis : str
        Management analysis text (経営者による分析).

    Examples
    --------
    >>> block = TextBlock(
    ...     edinet_code="E00001",
    ...     fiscal_year="2025",
    ...     business_overview="事業概要テキスト",
    ...     risk_factors="リスクファクターテキスト",
    ...     management_analysis="経営分析テキスト",
    ... )
    >>> block.business_overview
    '事業概要テキスト'
    """

    edinet_code: str
    fiscal_year: str
    business_overview: str
    risk_factors: str
    management_analysis: str


@dataclass(frozen=True)
class RankingEntry:
    """Metric-based company ranking entry from the EDINET DB API.

    Represents a single ranking entry for a specific financial metric.
    Data is returned by the ``GET /v1/rankings/{metric}`` endpoint.

    Parameters
    ----------
    metric : str
        Ranking metric name (e.g. ``"roe"``, ``"eps"``).
    rank : int
        Rank position (1-based).
    edinet_code : str
        EDINET code of the company.
    corp_name : str
        Company name in Japanese.
    value : float
        Metric value for this company.

    Examples
    --------
    >>> entry = RankingEntry(
    ...     metric="roe",
    ...     rank=1,
    ...     edinet_code="E00001",
    ...     corp_name="テスト株式会社",
    ...     value=25.5,
    ... )
    >>> entry.rank
    1
    """

    metric: str
    rank: int
    edinet_code: str
    corp_name: str
    value: float


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
    "AnalysisResult",
    "Company",
    "EdinetConfig",
    "FinancialRecord",
    "Industry",
    "RankingEntry",
    "RatioRecord",
    "RetryConfig",
    "SyncProgress",
    "TextBlock",
]
