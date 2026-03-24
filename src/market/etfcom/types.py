"""Type definitions for the market.etfcom module.

This module provides dataclass definitions for ETF.com scraping including:

- Scraping configuration (bot-blocking countermeasures)
- Retry configuration (exponential backoff)
- Data record types (fundamentals, fund flows, ETF metadata)
- REST API record types (historical fund flows, ticker info)

All configuration dataclasses use ``frozen=True`` to ensure immutability.
Field names use snake_case following project convention; raw ETF.com column
names (e.g. "Expense Ratio") are mapped to snake_case during parsing.

See Also
--------
market.etfcom.constants : Default values referenced by ScrapingConfig.
market.yfinance.types : Similar type-definition pattern for yfinance module.
market.fred.types : Similar type-definition pattern for FRED module.
"""

from dataclasses import dataclass
from datetime import date

from market.etfcom.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
)

# AIDEV-NOTE: Legacy default for Playwright-based scraping. Kept inline
# after DEFAULT_STABILITY_WAIT was removed from constants.py (Wave 1 API migration).
# Will be removed when browser.py / collectors.py are rewritten in later Waves.
_LEGACY_STABILITY_WAIT: float = 2.0

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class ScrapingConfig:
    """Configuration for ETF.com scraping behaviour.

    Controls polite delays, TLS fingerprint impersonation, Playwright
    headless mode, and page-level retry settings.  Default values are
    sourced from ``market.etfcom.constants`` to keep a single source of
    truth.

    Parameters
    ----------
    polite_delay : float
        Minimum wait time between consecutive requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 2.0).
    delay_jitter : float
        Random jitter added to polite delay in seconds
        (default: ``DEFAULT_DELAY_JITTER`` = 1.0).
    user_agents : tuple[str, ...]
        User-Agent strings for HTTP request rotation.  When empty the
        default list from ``constants.DEFAULT_USER_AGENTS`` is used at
        runtime (default: ``()``).
    impersonate : str
        curl_cffi TLS fingerprint impersonation target
        (default: ``'chrome'``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    headless : bool
        Whether to run Playwright in headless mode (default: True).
    stability_wait : float
        Wait time in seconds for page stability after navigation
        (default: ``DEFAULT_STABILITY_WAIT`` = 1.0).
    max_page_retries : int
        Maximum number of page-level retries for scraping operations
        (default: 5).

    Examples
    --------
    >>> config = ScrapingConfig(polite_delay=3.0, headless=False)
    >>> config.polite_delay
    3.0
    """

    polite_delay: float = DEFAULT_POLITE_DELAY
    delay_jitter: float = DEFAULT_DELAY_JITTER
    user_agents: tuple[str, ...] = ()
    impersonate: str = "chrome"
    timeout: float = DEFAULT_TIMEOUT
    headless: bool = True
    stability_wait: float = _LEGACY_STABILITY_WAIT
    max_page_retries: int = 5


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


# =============================================================================
# Data Record Dataclasses
# =============================================================================


@dataclass(frozen=True)
class FundamentalsRecord:
    """A single ETF fundamentals record scraped from an ETF.com profile page.

    Contains the 17 key-value fields extracted from the ``#summary-data``
    and ``#classification-index-data`` sections.  All string fields
    (except ``ticker``) are optional because ETF.com may return ``'--'``
    placeholders for delisted or incomplete ETFs, which are mapped to
    ``None`` during parsing.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"VOO"``).
    issuer : str | None
        Fund issuer name (e.g. ``"Vanguard"``).
    inception_date : str | None
        Fund inception date as displayed on ETF.com (e.g. ``"09/07/10"``).
    expense_ratio : str | None
        Expense ratio as displayed (e.g. ``"0.03%"``).
    aum : str | None
        Assets under management as displayed (e.g. ``"$751.49B"``).
    index_tracked : str | None
        Name of the tracked index (e.g. ``"S&P 500"``).
    segment : str | None
        ETF segment classification (e.g. ``"MSCI USA Large Cap"``).
    structure : str | None
        Fund structure (e.g. ``"Open-Ended Fund"``).
    asset_class : str | None
        Asset class (e.g. ``"Equity"``, ``"Fixed Income"``).
    category : str | None
        ETF category (e.g. ``"Size and Style"``).
    focus : str | None
        Investment focus (e.g. ``"Large Cap"``).
    niche : str | None
        Investment niche (e.g. ``"Broad-based"``).
    region : str | None
        Geographic region (e.g. ``"North America"``).
    geography : str | None
        Specific geography (e.g. ``"U.S."``).
    index_weighting_methodology : str | None
        Index weighting method (e.g. ``"Market Cap"``).
    index_selection_methodology : str | None
        Index selection method (e.g. ``"Committee"``).
    segment_benchmark : str | None
        Segment benchmark name (e.g. ``"MSCI USA Large Cap"``).

    Examples
    --------
    >>> record = FundamentalsRecord(
    ...     ticker="VOO",
    ...     issuer="Vanguard",
    ...     inception_date="09/07/10",
    ...     expense_ratio="0.03%",
    ...     aum="$751.49B",
    ...     index_tracked="S&P 500",
    ...     segment="MSCI USA Large Cap",
    ...     structure="Open-Ended Fund",
    ...     asset_class="Equity",
    ...     category="Size and Style",
    ...     focus="Large Cap",
    ...     niche="Broad-based",
    ...     region="North America",
    ...     geography="U.S.",
    ...     index_weighting_methodology="Market Cap",
    ...     index_selection_methodology="Committee",
    ...     segment_benchmark="MSCI USA Large Cap",
    ... )
    >>> record.ticker
    'VOO'
    """

    ticker: str
    issuer: str | None
    inception_date: str | None
    expense_ratio: str | None
    aum: str | None
    index_tracked: str | None
    segment: str | None
    structure: str | None
    asset_class: str | None
    category: str | None
    focus: str | None
    niche: str | None
    region: str | None
    geography: str | None
    index_weighting_methodology: str | None
    index_selection_methodology: str | None
    segment_benchmark: str | None


@dataclass(frozen=True)
class FundFlowRecord:
    """A single daily fund flow record for an ETF.

    Parameters
    ----------
    date : date
        Date of the fund flow observation.
    ticker : str
        ETF ticker symbol (e.g. ``"VOO"``).
    net_flows : float
        Net fund flows for the day (positive = inflows, negative = outflows).
        The unit follows ETF.com convention (typically millions USD).

    Examples
    --------
    >>> from datetime import date
    >>> record = FundFlowRecord(
    ...     date=date(2025, 9, 10),
    ...     ticker="VOO",
    ...     net_flows=2787.59,
    ... )
    >>> record.net_flows
    2787.59
    """

    date: date
    ticker: str
    net_flows: float


@dataclass
class ETFRecord:
    """Parsed ETF metadata record with normalised field types.

    Unlike ``FundamentalsRecord`` (which stores raw scraped strings),
    ``ETFRecord`` holds cleaned and type-converted values suitable for
    analysis and storage.  This dataclass is *mutable* to allow
    incremental enrichment during the data pipeline.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    name : str
        ETF full name.
    issuer : str | None
        Fund issuer name (default: None).
    category : str | None
        ETF category (default: None).
    expense_ratio : float | None
        Expense ratio as a decimal (e.g. 0.03 for 0.03%) (default: None).
    aum : float | None
        Assets under management in USD (default: None).
    inception_date : date | None
        Fund inception date (default: None).

    Examples
    --------
    >>> from datetime import date
    >>> etf = ETFRecord(
    ...     ticker="VOO",
    ...     name="Vanguard S&P 500 ETF",
    ...     issuer="Vanguard",
    ...     expense_ratio=0.03,
    ...     aum=751.49e9,
    ...     inception_date=date(2010, 9, 7),
    ... )
    >>> etf.ticker
    'VOO'
    """

    ticker: str
    name: str
    issuer: str | None = None
    category: str | None = None
    expense_ratio: float | None = None
    aum: float | None = None
    inception_date: date | None = None


# =============================================================================
# REST API Data Record Dataclasses
# =============================================================================


@dataclass(frozen=True)
class HistoricalFundFlowRecord:
    """A single daily historical fund flow record from the ETF.com REST API.

    Contains the 9 fields returned by the ``fund-flows-query`` API endpoint
    for a given fund. All numeric fields are ``float | None`` because the
    API may return ``null`` for dates where data is unavailable.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``).
    nav_date : date
        Date of the observation.
    nav : float | None
        Net asset value per share on the given date.
    nav_change : float | None
        Absolute change in NAV from the previous trading day.
    nav_change_percent : float | None
        Percentage change in NAV from the previous trading day.
    premium_discount : float | None
        Premium or discount to NAV (positive = premium, negative = discount).
    fund_flows : float | None
        Net fund flows for the day in USD (positive = inflows,
        negative = outflows).
    shares_outstanding : float | None
        Total shares outstanding on the given date.
    aum : float | None
        Assets under management in USD on the given date.

    Examples
    --------
    >>> from datetime import date
    >>> record = HistoricalFundFlowRecord(
    ...     ticker="SPY",
    ...     nav_date=date(2025, 9, 10),
    ...     nav=450.25,
    ...     nav_change=2.15,
    ...     nav_change_percent=0.48,
    ...     premium_discount=-0.02,
    ...     fund_flows=2787590000.0,
    ...     shares_outstanding=920000000.0,
    ...     aum=414230000000.0,
    ... )
    >>> record.ticker
    'SPY'
    """

    ticker: str
    nav_date: date
    nav: float | None
    nav_change: float | None
    nav_change_percent: float | None
    premium_discount: float | None
    fund_flows: float | None
    shares_outstanding: float | None
    aum: float | None


@dataclass(frozen=True)
class TickerInfo:
    """Ticker information from the ETF.com tickers API endpoint.

    Contains the 6 fields returned by the ``tickers`` API endpoint for
    each ETF. Used primarily to resolve ticker symbols to fund IDs
    required by the ``fund-flows-query`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``).
    fund_id : int
        Unique fund identifier used by the ETF.com API.
    name : str
        Full fund name (e.g. ``"SPDR S&P 500 ETF Trust"``).
    issuer : str | None
        Fund issuer name (e.g. ``"State Street"``).
    asset_class : str | None
        Asset class (e.g. ``"Equity"``, ``"Fixed Income"``).
    inception_date : str | None
        Fund inception date as returned by the API (e.g. ``"1993-01-22"``).

    Examples
    --------
    >>> info = TickerInfo(
    ...     ticker="SPY",
    ...     fund_id=1,
    ...     name="SPDR S&P 500 ETF Trust",
    ...     issuer="State Street",
    ...     asset_class="Equity",
    ...     inception_date="1993-01-22",
    ... )
    >>> info.fund_id
    1
    """

    ticker: str
    fund_id: int
    name: str
    issuer: str | None
    asset_class: str | None
    inception_date: str | None


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "ETFRecord",
    "FundFlowRecord",
    "FundamentalsRecord",
    "HistoricalFundFlowRecord",
    "RetryConfig",
    "ScrapingConfig",
    "TickerInfo",
]
