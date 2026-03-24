"""Type definitions for the NasdaqClient module.

This module provides fetch option types and record dataclasses for the
NasdaqClient, controlling cache behaviour on a per-request basis and
defining the structure of API response records.

The ``NasdaqFetchOptions`` dataclass mirrors
``market.alphavantage.types.FetchOptions`` for API consistency.

Record dataclasses:

- ``EarningsRecord`` — A single record from the earnings calendar endpoint.
- ``DividendCalendarRecord`` — A single record from the dividends calendar.
- ``SplitRecord`` — A single record from the stock splits calendar.
- ``IpoRecord`` — A single record from the IPO calendar.

See Also
--------
market.alphavantage.types.FetchOptions : Reference implementation.
market.nasdaq.client : NasdaqClient that consumes these options.
market.nasdaq.client_parsers : Parsers that produce these record types.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class NasdaqFetchOptions:
    """Options for NasdaqClient fetch requests.

    Controls whether cached data is used and whether to force a fresh
    fetch from the NASDAQ API, ignoring any cached response.

    Parameters
    ----------
    use_cache : bool
        Whether to use cached data if available (default: True).
    force_refresh : bool
        Whether to force a fresh fetch, ignoring cache (default: False).

    Examples
    --------
    >>> options = NasdaqFetchOptions()
    >>> options.use_cache
    True
    >>> options.force_refresh
    False

    >>> NasdaqFetchOptions(use_cache=False)
    NasdaqFetchOptions(use_cache=False, force_refresh=False)
    """

    use_cache: bool = True
    force_refresh: bool = False


# =============================================================================
# Calendar Record Types
# =============================================================================


@dataclass(frozen=True)
class EarningsRecord:
    """A single record from the NASDAQ earnings calendar endpoint.

    All fields are stored as raw strings from the API response.
    Numeric conversion is deferred to downstream consumers.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    name : str | None
        Company name.
    date : str | None
        Earnings date (e.g. ``"01/30/2026"``).
    eps_estimate : str | None
        EPS estimate (e.g. ``"$2.35"``).
    eps_actual : str | None
        Actual EPS (e.g. ``"$2.40"``).
    surprise : str | None
        Earnings surprise percentage (e.g. ``"2.13%"``).
    fiscal_quarter_ending : str | None
        Fiscal quarter ending period (e.g. ``"Dec/2025"``).
    market_cap : str | None
        Market capitalisation string (e.g. ``"3,435,123,456,789"``).

    Examples
    --------
    >>> record = EarningsRecord(symbol="AAPL", name="Apple Inc.")
    >>> record.symbol
    'AAPL'
    """

    symbol: str
    name: str | None = None
    date: str | None = None
    eps_estimate: str | None = None
    eps_actual: str | None = None
    surprise: str | None = None
    fiscal_quarter_ending: str | None = None
    market_cap: str | None = None


@dataclass(frozen=True)
class DividendCalendarRecord:
    """A single record from the NASDAQ dividends calendar endpoint.

    All fields are stored as raw strings from the API response.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    company_name : str | None
        Company name.
    ex_date : str | None
        Ex-dividend date (e.g. ``"02/07/2026"``).
    payment_date : str | None
        Payment date (e.g. ``"02/13/2026"``).
    record_date : str | None
        Record date (e.g. ``"02/10/2026"``).
    dividend_rate : str | None
        Dividend rate per share (e.g. ``"$0.25"``).
    annual_dividend : str | None
        Indicated annual dividend (e.g. ``"$1.00"``).

    Examples
    --------
    >>> record = DividendCalendarRecord(symbol="AAPL", company_name="Apple Inc.")
    >>> record.symbol
    'AAPL'
    """

    symbol: str
    company_name: str | None = None
    ex_date: str | None = None
    payment_date: str | None = None
    record_date: str | None = None
    dividend_rate: str | None = None
    annual_dividend: str | None = None


@dataclass(frozen=True)
class SplitRecord:
    """A single record from the NASDAQ stock splits calendar endpoint.

    All fields are stored as raw strings from the API response.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"NVDA"``).
    name : str | None
        Company name.
    execution_date : str | None
        Split execution date (e.g. ``"06/10/2024"``).
    ratio : str | None
        Split ratio (e.g. ``"10:1"``).
    optionable : str | None
        Whether the stock is optionable (``"Y"`` or ``"N"``).

    Examples
    --------
    >>> record = SplitRecord(symbol="NVDA", name="NVIDIA Corporation")
    >>> record.symbol
    'NVDA'
    """

    symbol: str
    name: str | None = None
    execution_date: str | None = None
    ratio: str | None = None
    optionable: str | None = None


@dataclass(frozen=True)
class IpoRecord:
    """A single record from the NASDAQ IPO calendar endpoint.

    All fields are stored as raw strings from the API response.

    Parameters
    ----------
    deal_id : str | None
        Unique deal identifier.
    symbol : str | None
        Proposed ticker symbol (e.g. ``"NEWCO"``).
    company_name : str | None
        Company name.
    exchange : str | None
        Proposed exchange (e.g. ``"NASDAQ"``, ``"NYSE"``).
    share_price : str | None
        Proposed share price or range (e.g. ``"$15.00-$17.00"``).
    shares_offered : str | None
        Number of shares offered (e.g. ``"10,000,000"``).

    Examples
    --------
    >>> record = IpoRecord(symbol="NEWCO", company_name="NewCo Inc.")
    >>> record.symbol
    'NEWCO'
    """

    deal_id: str | None = None
    symbol: str | None = None
    company_name: str | None = None
    exchange: str | None = None
    share_price: str | None = None
    shares_offered: str | None = None


# =============================================================================
# Market Movers Types
# =============================================================================


class MoverSection(str, Enum):
    """Section identifier for market movers data.

    The NASDAQ Market Movers endpoint returns three sections:
    most advanced (gainers), most declined (losers), and most active
    (highest volume).

    Attributes
    ----------
    MOST_ADVANCED : str
        Stocks with the largest price increases.
    MOST_DECLINED : str
        Stocks with the largest price decreases.
    MOST_ACTIVE : str
        Stocks with the highest trading volume.

    Examples
    --------
    >>> MoverSection.MOST_ADVANCED.value
    'most_advanced'
    >>> MoverSection("most_declined")
    <MoverSection.MOST_DECLINED: 'most_declined'>
    """

    MOST_ADVANCED = "most_advanced"
    MOST_DECLINED = "most_declined"
    MOST_ACTIVE = "most_active"


@dataclass(frozen=True)
class MarketMover:
    """A single record from the NASDAQ Market Movers endpoint.

    All fields are stored as raw strings from the API response.
    Numeric conversion is deferred to downstream consumers.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    name : str | None
        Company name.
    price : str | None
        Last sale price (e.g. ``"$227.63"``).
    change : str | None
        Price change (e.g. ``"2.50"`` or ``"-1.95"``).
    change_percent : str | None
        Percentage change (e.g. ``"1.11%"`` or ``"-0.85%"``).
    volume : str | None
        Trading volume (e.g. ``"48,123,456"``).

    Examples
    --------
    >>> record = MarketMover(symbol="AAPL", name="Apple Inc.")
    >>> record.symbol
    'AAPL'
    """

    symbol: str
    name: str | None = None
    price: str | None = None
    change: str | None = None
    change_percent: str | None = None
    volume: str | None = None


# =============================================================================
# ETF Screener Types
# =============================================================================


@dataclass(frozen=True)
class EtfRecord:
    """A single record from the NASDAQ ETF Screener endpoint.

    All fields are stored as raw strings from the API response.
    Numeric conversion is deferred to downstream consumers.

    Parameters
    ----------
    symbol : str
        ETF ticker symbol (e.g. ``"SPY"``).
    name : str | None
        ETF name (e.g. ``"SPDR S&P 500 ETF Trust"``).
    last_sale : str | None
        Last sale price (e.g. ``"$590.50"``).
    net_change : str | None
        Net price change (e.g. ``"-2.30"``).
    pct_change : str | None
        Percentage change (e.g. ``"-0.39%"``).
    volume : str | None
        Trading volume (e.g. ``"48,123,456"``).
    country : str | None
        Country of domicile (e.g. ``"United States"``).
    sector : str | None
        Sector classification.
    industry : str | None
        Industry classification.
    url : str | None
        NASDAQ URL path for the ETF.

    Examples
    --------
    >>> record = EtfRecord(symbol="SPY", name="SPDR S&P 500 ETF Trust")
    >>> record.symbol
    'SPY'
    """

    symbol: str
    name: str | None = None
    last_sale: str | None = None
    net_change: str | None = None
    pct_change: str | None = None
    volume: str | None = None
    country: str | None = None
    sector: str | None = None
    industry: str | None = None
    url: str | None = None


__all__ = [
    "DividendCalendarRecord",
    "EarningsRecord",
    "EtfRecord",
    "IpoRecord",
    "MarketMover",
    "MoverSection",
    "NasdaqFetchOptions",
    "SplitRecord",
]
