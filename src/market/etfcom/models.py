"""Storage record models for the ETF.com persistence layer.

This module defines frozen dataclass types that correspond 1:1 to the SQLite
table columns defined in ``storage_constants.py``. Each record type is used
by ``ETFComStorage`` for upsert and get operations.

Record types (table-mapped)
---------------------------
- ``TickerRecord`` (8 fields) -- ``etfcom_tickers``
- ``FundFlowsRecord`` (10 fields) -- ``etfcom_fund_flows``
- ``HoldingRecord`` (8 fields) -- ``etfcom_holdings``
- ``PortfolioRecord`` (11 fields) -- ``etfcom_portfolio``
- ``AllocationRecord`` (8 fields) -- ``etfcom_allocations``
- ``TradabilityRecord`` (12 fields) -- ``etfcom_tradability``
- ``StructureRecord`` (10 fields) -- ``etfcom_structure``
- ``PerformanceRecord`` (13 fields) -- ``etfcom_performance``
- ``QuoteRecord`` (12 fields) -- ``etfcom_quotes``

Record types (non-table)
------------------------
- ``CollectionResult`` -- Outcome of a single collect operation.
- ``CollectionSummary`` -- Aggregated summary of multiple ``CollectionResult``.

All dataclasses use ``frozen=True`` to ensure immutability. Required fields
(primary key) are listed first, followed by Optional data fields with
``None`` defaults, and finally ``fetched_at``.

See Also
--------
market.etfcom.storage_constants : Table name constants.
market.alphavantage.models : Reference pattern for frozen dataclass records.
"""

from __future__ import annotations

from dataclasses import dataclass

# =============================================================================
# Tickers
# =============================================================================


@dataclass(frozen=True)
class TickerRecord:
    """Ticker information record for ``etfcom_tickers``.

    Contains the core identification fields returned by the
    ``/v2/fund/tickers`` API endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key.
    fund_id : int
        Unique fund identifier used by the ETF.com API.
    name : str | None
        Full fund name (e.g. ``"SPDR S&P 500 ETF Trust"``).
    issuer : str | None
        Fund issuer name (e.g. ``"State Street"``).
    asset_class : str | None
        Asset class (e.g. ``"Equity"``, ``"Fixed Income"``).
    inception_date : str | None
        Fund inception date (e.g. ``"1993-01-22"``).
    segment : str | None
        ETF.com segment classification.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = TickerRecord(
    ...     ticker="SPY",
    ...     fund_id=1,
    ...     name="SPDR S&P 500 ETF Trust",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.ticker
    'SPY'
    """

    # --- Required key fields ---
    ticker: str
    fund_id: int

    # --- Data fields (all Optional) ---
    name: str | None = None
    issuer: str | None = None
    asset_class: str | None = None
    inception_date: str | None = None
    segment: str | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Fund Flows
# =============================================================================


@dataclass(frozen=True)
class FundFlowsRecord:
    """Daily fund flow record for ``etfcom_fund_flows``.

    Contains NAV, fund flows, AUM, and premium/discount data from the
    ``fundFlowsData`` query of the ``/v2/fund/fund-details`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key (part 1).
    nav_date : str
        NAV date in ISO 8601 format (e.g. ``"2026-01-15"``).
        Primary key (part 2).
    nav : float | None
        Net asset value per share.
    nav_change : float | None
        Daily NAV change.
    nav_change_percent : float | None
        Daily NAV change as percentage.
    premium_discount : float | None
        Premium/discount to NAV as percentage.
    fund_flows : float | None
        Net fund flows in dollars.
    shares_outstanding : float | None
        Total shares outstanding.
    aum : float | None
        Assets under management in dollars.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = FundFlowsRecord(
    ...     ticker="SPY",
    ...     nav_date="2026-01-15",
    ...     nav=580.25,
    ...     fund_flows=1_500_000_000.0,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.ticker
    'SPY'
    """

    # --- Required key fields ---
    ticker: str
    nav_date: str

    # --- Data fields (all Optional) ---
    nav: float | None = None
    nav_change: float | None = None
    nav_change_percent: float | None = None
    premium_discount: float | None = None
    fund_flows: float | None = None
    shares_outstanding: float | None = None
    aum: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Holdings
# =============================================================================


@dataclass(frozen=True)
class HoldingRecord:
    """Top holding record for ``etfcom_holdings``.

    Contains individual holding positions from the ``topHoldings`` query
    of the ``/v2/fund/fund-details`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key (part 1).
    holding_ticker : str
        Ticker of the held security (e.g. ``"AAPL"``).
        Primary key (part 2).
    as_of_date : str
        Holdings data as-of date in ISO 8601 format.
        Primary key (part 3).
    holding_name : str | None
        Name of the held security.
    weight : float | None
        Weight of the holding as decimal (e.g. ``0.072`` for 7.2%).
    market_value : float | None
        Market value of the holding in dollars.
    shares : float | None
        Number of shares held.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = HoldingRecord(
    ...     ticker="SPY",
    ...     holding_ticker="AAPL",
    ...     as_of_date="2026-01-10",
    ...     weight=0.072,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.weight
    0.072
    """

    # --- Required key fields ---
    ticker: str
    holding_ticker: str
    as_of_date: str

    # --- Data fields (all Optional) ---
    holding_name: str | None = None
    weight: float | None = None
    market_value: float | None = None
    shares: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Portfolio
# =============================================================================


@dataclass(frozen=True)
class PortfolioRecord:
    """Portfolio characteristics record for ``etfcom_portfolio``.

    Contains portfolio-level valuation metrics from the
    ``fundPortfolioData`` query of the ``/v2/fund/fund-details`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key.
    pe_ratio : float | None
        Price-to-earnings ratio.
    pb_ratio : float | None
        Price-to-book ratio.
    dividend_yield : float | None
        Dividend yield as decimal.
    weighted_avg_market_cap : float | None
        Weighted average market capitalization.
    number_of_holdings : int | None
        Total number of holdings.
    expense_ratio : float | None
        Fund expense ratio as decimal.
    tracking_difference : float | None
        Tracking difference vs benchmark.
    median_tracking_difference : float | None
        Median tracking difference vs benchmark.
    as_of_date : str | None
        Data as-of date in ISO 8601 format.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = PortfolioRecord(
    ...     ticker="SPY",
    ...     pe_ratio=22.5,
    ...     pb_ratio=4.1,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.pe_ratio
    22.5
    """

    # --- Required key fields ---
    ticker: str

    # --- Data fields (all Optional) ---
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    dividend_yield: float | None = None
    weighted_avg_market_cap: float | None = None
    number_of_holdings: int | None = None
    expense_ratio: float | None = None
    tracking_difference: float | None = None
    median_tracking_difference: float | None = None
    as_of_date: str | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Allocations (Sector, Region, Country, Economic Development)
# =============================================================================


@dataclass(frozen=True)
class AllocationRecord:
    """Allocation breakdown record for ``etfcom_allocations``.

    Contains sector, region, country, or economic development allocation
    data from the ``sectorIndustryBreakdown``, ``regions``, ``countries``,
    and ``economicDevelopment`` queries.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key (part 1).
    allocation_type : str
        Type of allocation: ``"sector"``, ``"region"``, ``"country"``,
        or ``"economic_development"``. Primary key (part 2).
    name : str
        Allocation category name (e.g. ``"Technology"``, ``"United States"``).
        Primary key (part 3).
    as_of_date : str
        Data as-of date in ISO 8601 format. Primary key (part 4).
    weight : float | None
        Allocation weight as decimal (e.g. ``0.32`` for 32%).
    market_value : float | None
        Market value of the allocation in dollars.
    count : int | None
        Number of holdings in this allocation category.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = AllocationRecord(
    ...     ticker="SPY",
    ...     allocation_type="sector",
    ...     name="Technology",
    ...     as_of_date="2026-01-10",
    ...     weight=0.32,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.weight
    0.32
    """

    # --- Required key fields ---
    ticker: str
    allocation_type: str
    name: str
    as_of_date: str

    # --- Data fields (all Optional) ---
    weight: float | None = None
    market_value: float | None = None
    count: int | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Tradability
# =============================================================================


@dataclass(frozen=True)
class TradabilityRecord:
    """Tradability metrics record for ``etfcom_tradability``.

    Contains volume, spread, and liquidity data from the
    ``fundTradabilityData`` and ``fundTradabilitySummary`` queries.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key.
    avg_daily_volume : float | None
        Average daily trading volume.
    avg_daily_dollar_volume : float | None
        Average daily dollar trading volume.
    median_bid_ask_spread : float | None
        Median bid-ask spread as percentage.
    avg_bid_ask_spread : float | None
        Average bid-ask spread as percentage.
    creation_unit_size : int | None
        Creation unit size (number of shares per basket).
    open_interest : float | None
        Options open interest.
    short_interest : float | None
        Short interest as percentage of shares outstanding.
    implied_liquidity : float | None
        Implied liquidity in dollars.
    block_liquidity : float | None
        Block trade liquidity in dollars.
    as_of_date : str | None
        Data as-of date in ISO 8601 format.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = TradabilityRecord(
    ...     ticker="SPY",
    ...     avg_daily_volume=75_000_000.0,
    ...     median_bid_ask_spread=0.0001,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.avg_daily_volume
    75000000.0
    """

    # --- Required key fields ---
    ticker: str

    # --- Data fields (all Optional) ---
    avg_daily_volume: float | None = None
    avg_daily_dollar_volume: float | None = None
    median_bid_ask_spread: float | None = None
    avg_bid_ask_spread: float | None = None
    creation_unit_size: int | None = None
    open_interest: float | None = None
    short_interest: float | None = None
    implied_liquidity: float | None = None
    block_liquidity: float | None = None
    as_of_date: str | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Structure
# =============================================================================


@dataclass(frozen=True)
class StructureRecord:
    """Fund structure record for ``etfcom_structure``.

    Contains legal structure, derivatives usage, and securities lending
    data from the ``fundStructureData`` query.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key.
    legal_structure : str | None
        Legal structure type (e.g. ``"UIT"``, ``"Open-End Fund"``).
    fund_type : str | None
        Fund type classification.
    index_tracked : str | None
        Name of the benchmark index tracked.
    replication_method : str | None
        Replication method (e.g. ``"Full Replication"``,
        ``"Representative Sampling"``).
    uses_derivatives : bool | None
        Whether the fund uses derivatives.
    securities_lending : bool | None
        Whether the fund engages in securities lending.
    tax_form : str | None
        Tax reporting form type (e.g. ``"1099"``).
    as_of_date : str | None
        Data as-of date in ISO 8601 format.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = StructureRecord(
    ...     ticker="SPY",
    ...     legal_structure="UIT",
    ...     index_tracked="S&P 500",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.legal_structure
    'UIT'
    """

    # --- Required key fields ---
    ticker: str

    # --- Data fields (all Optional) ---
    legal_structure: str | None = None
    fund_type: str | None = None
    index_tracked: str | None = None
    replication_method: str | None = None
    uses_derivatives: bool | None = None
    securities_lending: bool | None = None
    tax_form: str | None = None
    as_of_date: str | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Performance
# =============================================================================


@dataclass(frozen=True)
class PerformanceRecord:
    """Performance statistics record for ``etfcom_performance``.

    Contains return periods, tracking metrics, and grades from the
    ``fundPerformanceStatsData`` query and ``/v2/fund/performance`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key.
    return_1m : float | None
        1-month total return as decimal.
    return_3m : float | None
        3-month total return as decimal.
    return_ytd : float | None
        Year-to-date total return as decimal.
    return_1y : float | None
        1-year total return as decimal.
    return_3y : float | None
        3-year annualized total return as decimal.
    return_5y : float | None
        5-year annualized total return as decimal.
    return_10y : float | None
        10-year annualized total return as decimal.
    r_squared : float | None
        R-squared vs benchmark.
    beta : float | None
        Beta vs benchmark.
    standard_deviation : float | None
        Annualized standard deviation.
    as_of_date : str | None
        Data as-of date in ISO 8601 format.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = PerformanceRecord(
    ...     ticker="SPY",
    ...     return_1y=0.265,
    ...     r_squared=0.9998,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.return_1y
    0.265
    """

    # --- Required key fields ---
    ticker: str

    # --- Data fields (all Optional) ---
    return_1m: float | None = None
    return_3m: float | None = None
    return_ytd: float | None = None
    return_1y: float | None = None
    return_3y: float | None = None
    return_5y: float | None = None
    return_10y: float | None = None
    r_squared: float | None = None
    beta: float | None = None
    standard_deviation: float | None = None
    as_of_date: str | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Quotes
# =============================================================================


@dataclass(frozen=True)
class QuoteRecord:
    """Delayed quote record for ``etfcom_quotes``.

    Contains OHLC price, bid/ask, and volume data from the
    ``/v2/quotes/delayedquotes`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``). Primary key (part 1).
    quote_date : str
        Quote date in ISO 8601 format (e.g. ``"2026-01-15"``).
        Primary key (part 2).
    open : float | None
        Opening price.
    high : float | None
        Highest price.
    low : float | None
        Lowest price.
    close : float | None
        Closing price.
    volume : float | None
        Trading volume.
    bid : float | None
        Best bid price.
    ask : float | None
        Best ask price.
    bid_size : float | None
        Bid size (number of shares).
    ask_size : float | None
        Ask size (number of shares).
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = QuoteRecord(
    ...     ticker="SPY",
    ...     quote_date="2026-01-15",
    ...     close=580.25,
    ...     volume=75_000_000.0,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.close
    580.25
    """

    # --- Required key fields ---
    ticker: str
    quote_date: str

    # --- Data fields (all Optional) ---
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    bid: float | None = None
    ask: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Collection Result (non-table)
# =============================================================================


@dataclass(frozen=True)
class CollectionResult:
    """Outcome of a single ETF.com collect operation.

    Captures per-ticker collection statistics including table name,
    row count, and any error message. Used as the return type of
    individual ``ETFComCollector`` operations.

    Parameters
    ----------
    ticker : str
        The ETF ticker symbol that was collected.
    table : str
        The target table name for the collected data.
    rows_upserted : int
        Number of rows successfully upserted to storage.
    success : bool
        Whether the collection was successful.
    error_message : str | None
        Error description if collection failed. ``None`` on success.

    Examples
    --------
    >>> result = CollectionResult(
    ...     ticker="SPY",
    ...     table="etfcom_fund_flows",
    ...     rows_upserted=250,
    ...     success=True,
    ... )
    >>> result.success
    True
    """

    ticker: str
    table: str
    rows_upserted: int = 0
    success: bool = True
    error_message: str | None = None


# =============================================================================
# Collection Summary (non-table)
# =============================================================================


@dataclass(frozen=True)
class CollectionSummary:
    """Aggregated summary of multiple ``CollectionResult`` instances.

    Provides a high-level view of an entire collection run, including
    per-ticker results and aggregate counts.

    Parameters
    ----------
    results : tuple[CollectionResult, ...]
        Tuple of individual collection results.
    total_tickers : int
        Total number of tickers processed.
    successful : int
        Number of successful collections.
    failed : int
        Number of failed collections.
    total_rows : int
        Total rows upserted across all results.

    Examples
    --------
    >>> summary = CollectionSummary(
    ...     results=(
    ...         CollectionResult("SPY", "etfcom_fund_flows", 250, True),
    ...     ),
    ...     total_tickers=1, successful=1, failed=0, total_rows=250,
    ... )
    >>> summary.has_failures
    False
    """

    results: tuple[CollectionResult, ...] = ()
    total_tickers: int = 0
    successful: int = 0
    failed: int = 0
    total_rows: int = 0

    @property
    def has_failures(self) -> bool:
        """Return whether any collections failed.

        Returns
        -------
        bool
            ``True`` if ``failed > 0``.
        """
        return self.failed > 0


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "AllocationRecord",
    "CollectionResult",
    "CollectionSummary",
    "FundFlowsRecord",
    "HoldingRecord",
    "PerformanceRecord",
    "PortfolioRecord",
    "QuoteRecord",
    "StructureRecord",
    "TickerRecord",
    "TradabilityRecord",
]
