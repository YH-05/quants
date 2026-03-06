"""Type definitions for the market.bse module.

This module provides type definitions for BSE data retrieval including:

- Enum types (BhavcopyType, ScripGroup, IndexName)
- Configuration dataclasses (BseConfig, RetryConfig)
- Data record dataclasses (ScripQuote, FinancialResult, Announcement,
  CorporateAction)

All Enums inherit from ``str`` and ``Enum`` so they can be used directly as
string values in API query parameters. All dataclasses use ``frozen=True``
to ensure immutability.

See Also
--------
market.bse.constants : Default values referenced by BseConfig.
market.nasdaq.types : Similar type-definition pattern for the NASDAQ module.
"""

from dataclasses import dataclass
from enum import Enum

from market.bse.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
)

# =============================================================================
# Enum Definitions
# =============================================================================


class BhavcopyType(str, Enum):
    """Bhavcopy (daily market data) type for BSE downloads.

    BSE publishes different types of bhavcopy files for equity,
    derivatives, and debt market segments.

    Parameters
    ----------
    value : str
        The identifier used in BSE API/download URLs.

    Examples
    --------
    >>> BhavcopyType.EQUITY
    <BhavcopyType.EQUITY: 'equity'>
    >>> str(BhavcopyType.EQUITY)
    'equity'
    """

    EQUITY = "equity"
    DERIVATIVES = "derivatives"
    DEBT = "debt"


class ScripGroup(str, Enum):
    """BSE scrip (security) group classification.

    BSE classifies listed securities into groups based on market
    capitalisation, trading frequency, and other criteria.

    - A: Large-cap, frequently traded
    - B: Mid/small-cap
    - T: Trade-to-trade (no intraday)
    - Z: Non-compliance
    - X: Micro-cap

    Parameters
    ----------
    value : str
        The BSE scrip group identifier.

    Examples
    --------
    >>> ScripGroup.A
    <ScripGroup.A: 'A'>
    """

    A = "A"
    B = "B"
    T = "T"
    Z = "Z"
    X = "X"


class IndexName(str, Enum):
    """BSE index names for market data retrieval.

    Contains the major BSE indices used for market tracking
    and benchmarking.

    Parameters
    ----------
    value : str
        The BSE index identifier as used in API requests.

    Examples
    --------
    >>> IndexName.SENSEX
    <IndexName.SENSEX: 'SENSEX'>
    """

    SENSEX = "SENSEX"
    SENSEX_50 = "SENSEX 50"
    BSE_100 = "BSE 100"
    BSE_200 = "BSE 200"
    BSE_500 = "BSE 500"
    BSE_MIDCAP = "BSE MIDCAP"
    BSE_SMALLCAP = "BSE SMALLCAP"
    BSE_LARGECAP = "BSE LARGECAP"
    BANKEX = "BANKEX"
    BSE_IT = "BSE IT"
    BSE_HEALTHCARE = "BSE HEALTHCARE"
    BSE_AUTO = "BSE AUTO"


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class BseConfig:
    """Configuration for BSE API HTTP behaviour.

    Controls polite delays, request timeout, and User-Agent rotation.
    Default values are sourced from ``market.bse.constants`` to keep
    a single source of truth.

    Parameters
    ----------
    polite_delay : float
        Minimum wait time between consecutive requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 0.15).
    delay_jitter : float
        Random jitter added to polite delay in seconds
        (default: ``DEFAULT_DELAY_JITTER`` = 0.05).
    user_agents : tuple[str, ...]
        User-Agent strings for HTTP request rotation. When empty the
        default list from ``constants.DEFAULT_USER_AGENTS`` is used at
        runtime (default: ``()``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = BseConfig(polite_delay=0.5, timeout=60.0)
    >>> config.polite_delay
    0.5
    """

    polite_delay: float = DEFAULT_POLITE_DELAY
    delay_jitter: float = DEFAULT_DELAY_JITTER
    user_agents: tuple[str, ...] = ()
    timeout: float = DEFAULT_TIMEOUT

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
class ScripQuote:
    """A single scrip (security) quote from BSE.

    Stores quote data for a BSE-listed security including price,
    volume, and identification information.

    Parameters
    ----------
    scrip_code : str
        BSE scrip code (e.g. ``"500325"`` for Reliance Industries).
    scrip_name : str
        Security name (e.g. ``"RELIANCE INDUSTRIES LTD"``).
    scrip_group : str
        BSE scrip group classification (e.g. ``"A"``).
    open : str
        Opening price (e.g. ``"2450.00"``).
    high : str
        Day's high price (e.g. ``"2480.50"``).
    low : str
        Day's low price (e.g. ``"2440.00"``).
    close : str
        Closing price (e.g. ``"2470.25"``).
    last : str
        Last traded price (e.g. ``"2469.90"``).
    prev_close : str
        Previous day's closing price (e.g. ``"2445.00"``).
    num_trades : str
        Number of trades (e.g. ``"125000"``).
    num_shares : str
        Number of shares traded (e.g. ``"5000000"``).
    net_turnover : str
        Net turnover in INR (e.g. ``"12345678900"``).

    Examples
    --------
    >>> quote = ScripQuote(
    ...     scrip_code="500325",
    ...     scrip_name="RELIANCE INDUSTRIES LTD",
    ...     scrip_group="A",
    ...     open="2450.00",
    ...     high="2480.50",
    ...     low="2440.00",
    ...     close="2470.25",
    ...     last="2469.90",
    ...     prev_close="2445.00",
    ...     num_trades="125000",
    ...     num_shares="5000000",
    ...     net_turnover="12345678900",
    ... )
    >>> quote.scrip_code
    '500325'
    """

    scrip_code: str
    scrip_name: str
    scrip_group: str
    open: str
    high: str
    low: str
    close: str
    last: str
    prev_close: str
    num_trades: str
    num_shares: str
    net_turnover: str


@dataclass(frozen=True)
class FinancialResult:
    """A financial result record from BSE corporate filings.

    Stores quarterly or annual financial result data for a
    BSE-listed company.

    Parameters
    ----------
    scrip_code : str
        BSE scrip code.
    scrip_name : str
        Security name.
    period_ended : str
        Financial period end date (e.g. ``"31-Mar-2025"``).
    revenue : str
        Total revenue/income (e.g. ``"250000"`` in Cr).
    net_profit : str
        Net profit after tax (e.g. ``"18500"`` in Cr).
    eps : str
        Earnings per share (e.g. ``"27.35"``).

    Examples
    --------
    >>> result = FinancialResult(
    ...     scrip_code="500325",
    ...     scrip_name="RELIANCE INDUSTRIES LTD",
    ...     period_ended="31-Mar-2025",
    ...     revenue="250000",
    ...     net_profit="18500",
    ...     eps="27.35",
    ... )
    >>> result.scrip_code
    '500325'
    """

    scrip_code: str
    scrip_name: str
    period_ended: str
    revenue: str
    net_profit: str
    eps: str


@dataclass(frozen=True)
class Announcement:
    """A corporate announcement from BSE.

    Stores announcement data published by BSE-listed companies.

    Parameters
    ----------
    scrip_code : str
        BSE scrip code.
    scrip_name : str
        Security name.
    subject : str
        Announcement subject/title.
    announcement_date : str
        Date of announcement (e.g. ``"15-Jan-2025"``).
    category : str
        Announcement category (e.g. ``"Board Meeting"``).

    Examples
    --------
    >>> ann = Announcement(
    ...     scrip_code="500325",
    ...     scrip_name="RELIANCE INDUSTRIES LTD",
    ...     subject="Board Meeting Outcome",
    ...     announcement_date="15-Jan-2025",
    ...     category="Board Meeting",
    ... )
    >>> ann.subject
    'Board Meeting Outcome'
    """

    scrip_code: str
    scrip_name: str
    subject: str
    announcement_date: str
    category: str


@dataclass(frozen=True)
class CorporateAction:
    """A corporate action record from BSE.

    Stores information about corporate actions such as dividends,
    bonuses, splits, and rights issues.

    Parameters
    ----------
    scrip_code : str
        BSE scrip code.
    scrip_name : str
        Security name.
    ex_date : str
        Ex-date for the corporate action (e.g. ``"01-Feb-2025"``).
    purpose : str
        Description of the corporate action (e.g. ``"Dividend - Rs 8 Per Share"``).
    record_date : str
        Record date for eligibility (e.g. ``"03-Feb-2025"``).

    Examples
    --------
    >>> action = CorporateAction(
    ...     scrip_code="500325",
    ...     scrip_name="RELIANCE INDUSTRIES LTD",
    ...     ex_date="01-Feb-2025",
    ...     purpose="Dividend - Rs 8 Per Share",
    ...     record_date="03-Feb-2025",
    ... )
    >>> action.purpose
    'Dividend - Rs 8 Per Share'
    """

    scrip_code: str
    scrip_name: str
    ex_date: str
    purpose: str
    record_date: str


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "Announcement",
    "BhavcopyType",
    "BseConfig",
    "CorporateAction",
    "FinancialResult",
    "IndexName",
    "RetryConfig",
    "ScripGroup",
    "ScripQuote",
]
