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
- ``EarningsForecastPeriod`` — A single forecast period (yearly or quarterly).
- ``EarningsForecast`` — Yearly and quarterly earnings forecast data.
- ``RatingCount`` — Buy/sell/hold counts at a point in time.
- ``AnalystRatings`` — Analyst buy/sell/hold counts with history.
- ``TargetPrice`` — Analyst target price statistics (high/low/mean/median).
- ``EarningsDate`` — Upcoming earnings announcement date info.
- ``AnalystSummary`` — Aggregated analyst data from all four endpoints.

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


# =============================================================================
# Analyst Data Types
# =============================================================================


@dataclass(frozen=True)
class EarningsForecastPeriod:
    """A single forecast period from the earnings forecast endpoint.

    Represents one row in either the yearly or quarterly forecasts table,
    containing consensus estimate, number of analysts, and actual/reported
    values when available.

    Parameters
    ----------
    fiscal_end : str | None
        Fiscal period end label (e.g. ``"Dec 2025"``, ``"Q4 2025"``).
    consensus_eps_forecast : str | None
        Consensus EPS forecast (e.g. ``"$2.35"``).
    num_of_estimates : str | None
        Number of analyst estimates (e.g. ``"28"``).
    high_eps_forecast : str | None
        Highest EPS forecast (e.g. ``"$2.60"``).
    low_eps_forecast : str | None
        Lowest EPS forecast (e.g. ``"$2.10"``).

    Examples
    --------
    >>> period = EarningsForecastPeriod(
    ...     fiscal_end="Dec 2025",
    ...     consensus_eps_forecast="$2.35",
    ...     num_of_estimates="28",
    ... )
    >>> period.fiscal_end
    'Dec 2025'
    """

    fiscal_end: str | None = None
    consensus_eps_forecast: str | None = None
    num_of_estimates: str | None = None
    high_eps_forecast: str | None = None
    low_eps_forecast: str | None = None


@dataclass(frozen=True)
class EarningsForecast:
    """Earnings forecast data from the NASDAQ analyst forecast endpoint.

    Contains yearly and quarterly forecast period lists with consensus
    EPS estimates, number of analysts, and high/low forecast ranges.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    yearly : list[EarningsForecastPeriod]
        Yearly forecast periods.
    quarterly : list[EarningsForecastPeriod]
        Quarterly forecast periods.

    Examples
    --------
    >>> forecast = EarningsForecast(symbol="AAPL", yearly=[], quarterly=[])
    >>> forecast.symbol
    'AAPL'
    """

    symbol: str
    yearly: list[EarningsForecastPeriod]
    quarterly: list[EarningsForecastPeriod]


@dataclass(frozen=True)
class RatingCount:
    """Buy/sell/hold counts at a single point in time.

    Parameters
    ----------
    date : str | None
        Date label (e.g. ``"Current Quarter"``, ``"1 Month Ago"``).
    strong_buy : int
        Strong buy count.
    buy : int
        Buy count.
    hold : int
        Hold count.
    sell : int
        Sell count.
    strong_sell : int
        Strong sell count.

    Examples
    --------
    >>> rc = RatingCount(date="Current Quarter", strong_buy=10, buy=5,
    ...                  hold=3, sell=1, strong_sell=0)
    >>> rc.strong_buy
    10
    """

    date: str | None = None
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0


@dataclass(frozen=True)
class AnalystRatings:
    """Analyst ratings data from the NASDAQ analyst ratings endpoint.

    Contains buy/sell/hold/strong-buy/strong-sell counts and historical
    rating snapshots over time.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    ratings : list[RatingCount]
        Rating counts over time (current, 1M ago, 2M ago, 3M ago).

    Examples
    --------
    >>> ratings = AnalystRatings(symbol="AAPL", ratings=[])
    >>> ratings.symbol
    'AAPL'
    """

    symbol: str
    ratings: list[RatingCount]


@dataclass(frozen=True)
class TargetPrice:
    """Analyst target price statistics from the NASDAQ target price endpoint.

    Contains high, low, mean, and median analyst price targets.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    high : str | None
        Highest analyst target price (e.g. ``"$280.00"``).
    low : str | None
        Lowest analyst target price (e.g. ``"$200.00"``).
    mean : str | None
        Mean analyst target price (e.g. ``"$250.00"``).
    median : str | None
        Median analyst target price (e.g. ``"$248.00"``).

    Examples
    --------
    >>> tp = TargetPrice(symbol="AAPL", high="$280.00", low="$200.00",
    ...                  mean="$250.00", median="$248.00")
    >>> tp.mean
    '$250.00'
    """

    symbol: str
    high: str | None = None
    low: str | None = None
    mean: str | None = None
    median: str | None = None


@dataclass(frozen=True)
class EarningsDate:
    """Upcoming earnings date information from the NASDAQ earnings date endpoint.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    date : str | None
        Earnings announcement date (e.g. ``"01/30/2026"``).
    time : str | None
        Announcement timing (e.g. ``"After Market Close"``, ``"Before Market Open"``).
    fiscal_quarter_ending : str | None
        Fiscal quarter ending period (e.g. ``"Dec/2025"``).
    eps_forecast : str | None
        Consensus EPS forecast (e.g. ``"$2.35"``).

    Examples
    --------
    >>> ed = EarningsDate(symbol="AAPL", date="01/30/2026",
    ...                   time="After Market Close")
    >>> ed.date
    '01/30/2026'
    """

    symbol: str
    date: str | None = None
    time: str | None = None
    fiscal_quarter_ending: str | None = None
    eps_forecast: str | None = None


@dataclass(frozen=True)
class AnalystSummary:
    """Aggregated analyst data from all four analyst endpoints.

    A convenience type that combines earnings forecast, analyst ratings,
    target price, and earnings date data for a single symbol.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    forecast : EarningsForecast | None
        Earnings forecast data, or ``None`` if unavailable.
    ratings : AnalystRatings | None
        Analyst ratings data, or ``None`` if unavailable.
    target_price : TargetPrice | None
        Target price data, or ``None`` if unavailable.
    earnings_date : EarningsDate | None
        Earnings date data, or ``None`` if unavailable.

    Examples
    --------
    >>> summary = AnalystSummary(symbol="AAPL")
    >>> summary.symbol
    'AAPL'
    """

    symbol: str
    forecast: EarningsForecast | None = None
    ratings: AnalystRatings | None = None
    target_price: TargetPrice | None = None
    earnings_date: EarningsDate | None = None


__all__ = [
    "AnalystRatings",
    "AnalystSummary",
    "DividendCalendarRecord",
    "EarningsDate",
    "EarningsForecast",
    "EarningsForecastPeriod",
    "EarningsRecord",
    "EtfRecord",
    "IpoRecord",
    "MarketMover",
    "MoverSection",
    "NasdaqFetchOptions",
    "RatingCount",
    "SplitRecord",
    "TargetPrice",
]
