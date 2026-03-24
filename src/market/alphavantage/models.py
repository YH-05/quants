"""Storage record models for the Alpha Vantage persistence layer.

This module defines frozen dataclass types that correspond 1:1 to the SQLite
table columns defined in ``storage_constants.py``. Each record type is used
by ``AlphaVantageStorage`` for upsert and get operations.

Record types
------------
- ``DailyPriceRecord`` (9 fields) -- ``av_daily_prices``
- ``CompanyOverviewRecord`` (42 fields) -- ``av_company_overview``
- ``IncomeStatementRecord`` (21 fields) -- ``av_income_statements``
- ``BalanceSheetRecord`` (28 fields) -- ``av_balance_sheets``
- ``CashFlowRecord`` (21 fields) -- ``av_cash_flows``
- ``AnnualEarningsRecord`` (5 fields) -- ``av_earnings`` (annual rows)
- ``QuarterlyEarningsRecord`` (9 fields) -- ``av_earnings`` (quarterly rows)
- ``EconomicIndicatorRecord`` (6 fields) -- ``av_economic_indicators``
- ``ForexDailyRecord`` (8 fields) -- ``av_forex_daily``

The ``EarningsRecord`` type alias is a union of ``AnnualEarningsRecord``
and ``QuarterlyEarningsRecord`` for use in generic earnings operations.

All dataclasses use ``frozen=True`` to ensure immutability. Required fields
are listed first, followed by Optional fields with ``None`` defaults.

See Also
--------
market.alphavantage.storage_constants : Table name constants.
market.edinet.types : Reference pattern for frozen dataclass records.
docs/superpowers/specs/2026-03-24-alphavantage-storage-design.md : Design spec.
"""

from __future__ import annotations

from dataclasses import dataclass

# =============================================================================
# Daily Prices
# =============================================================================


@dataclass(frozen=True)
class DailyPriceRecord:
    """Daily OHLCV price record for ``av_daily_prices``.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``).
    date : str
        Trading date in ISO 8601 format (e.g. ``"2026-01-15"``).
    open : float
        Opening price.
    high : float
        Highest price during the session.
    low : float
        Lowest price during the session.
    close : float
        Closing price.
    adjusted_close : float | None
        Split/dividend-adjusted closing price.
        ``None`` when using ``TIME_SERIES_DAILY`` (non-adjusted).
    volume : int
        Trading volume (number of shares).
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = DailyPriceRecord(
    ...     symbol="AAPL",
    ...     date="2026-01-15",
    ...     open=150.0,
    ...     high=155.0,
    ...     low=149.0,
    ...     close=153.0,
    ...     adjusted_close=153.0,
    ...     volume=1_000_000,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.symbol
    'AAPL'
    """

    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None
    volume: int
    fetched_at: str


# =============================================================================
# Company Overview
# =============================================================================


@dataclass(frozen=True)
class CompanyOverviewRecord:
    """Company profile and fundamentals record for ``av_company_overview``.

    Contains 9 text fields + 32 numeric fields from ``parser.py``'s
    ``_OVERVIEW_NUMERIC_FIELDS`` + ``fetched_at``. All fields except
    ``symbol`` and ``fetched_at`` are Optional.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``"AAPL"``). Primary key.
    name : str | None
        Company name.
    description : str | None
        Company description / business summary.
    exchange : str | None
        Exchange name (e.g. ``"NYSE"``).
    currency : str | None
        Reporting currency (e.g. ``"USD"``).
    country : str | None
        Country of incorporation (e.g. ``"USA"``).
    sector : str | None
        GICS sector (e.g. ``"Technology"``).
    industry : str | None
        GICS industry (e.g. ``"Consumer Electronics"``).
    fiscal_year_end : str | None
        Fiscal year end month (e.g. ``"September"``).
    latest_quarter : str | None
        Latest reported quarter date (e.g. ``"2025-12-31"``).
    market_capitalization : float | None
        Market cap in reporting currency.
    ebitda : float | None
        EBITDA in reporting currency.
    pe_ratio : float | None
        Price-to-earnings ratio.
    peg_ratio : float | None
        Price/earnings-to-growth ratio.
    book_value : float | None
        Book value per share.
    dividend_per_share : float | None
        Annual dividend per share.
    dividend_yield : float | None
        Dividend yield as decimal.
    eps : float | None
        Earnings per share.
    diluted_eps_ttm : float | None
        Diluted EPS trailing twelve months.
    week_52_high : float | None
        52-week high price.
    week_52_low : float | None
        52-week low price.
    day_50_moving_average : float | None
        50-day simple moving average.
    day_200_moving_average : float | None
        200-day simple moving average.
    shares_outstanding : float | None
        Total shares outstanding.
    revenue_per_share_ttm : float | None
        Revenue per share TTM.
    profit_margin : float | None
        Net profit margin as decimal.
    operating_margin_ttm : float | None
        Operating margin TTM as decimal.
    return_on_assets_ttm : float | None
        Return on assets TTM as decimal.
    return_on_equity_ttm : float | None
        Return on equity TTM as decimal.
    revenue_ttm : float | None
        Revenue TTM in reporting currency.
    gross_profit_ttm : float | None
        Gross profit TTM in reporting currency.
    quarterly_earnings_growth_yoy : float | None
        Quarterly earnings growth year-over-year as decimal.
    quarterly_revenue_growth_yoy : float | None
        Quarterly revenue growth year-over-year as decimal.
    analyst_target_price : float | None
        Analyst consensus target price.
    analyst_rating_strong_buy : float | None
        Number of strong buy ratings.
    analyst_rating_buy : float | None
        Number of buy ratings.
    analyst_rating_hold : float | None
        Number of hold ratings.
    analyst_rating_sell : float | None
        Number of sell ratings.
    analyst_rating_strong_sell : float | None
        Number of strong sell ratings.
    trailing_pe : float | None
        Trailing price-to-earnings ratio.
    forward_pe : float | None
        Forward price-to-earnings ratio.
    price_to_sales_ratio_ttm : float | None
        Price-to-sales ratio TTM.
    price_to_book_ratio : float | None
        Price-to-book ratio.
    ev_to_revenue : float | None
        Enterprise value to revenue.
    ev_to_ebitda : float | None
        Enterprise value to EBITDA.
    beta : float | None
        Beta (5-year monthly).
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = CompanyOverviewRecord(
    ...     symbol="AAPL",
    ...     name="Apple Inc",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.symbol
    'AAPL'
    """

    # --- Required key fields ---
    symbol: str

    # --- Text fields (all Optional) ---
    name: str | None = None
    description: str | None = None
    exchange: str | None = None
    currency: str | None = None
    country: str | None = None
    sector: str | None = None
    industry: str | None = None
    fiscal_year_end: str | None = None
    latest_quarter: str | None = None

    # --- Numeric fields from _OVERVIEW_NUMERIC_FIELDS (all Optional) ---
    market_capitalization: float | None = None
    ebitda: float | None = None
    pe_ratio: float | None = None
    peg_ratio: float | None = None
    book_value: float | None = None
    dividend_per_share: float | None = None
    dividend_yield: float | None = None
    eps: float | None = None
    diluted_eps_ttm: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    day_50_moving_average: float | None = None
    day_200_moving_average: float | None = None
    shares_outstanding: float | None = None
    revenue_per_share_ttm: float | None = None
    profit_margin: float | None = None
    operating_margin_ttm: float | None = None
    return_on_assets_ttm: float | None = None
    return_on_equity_ttm: float | None = None
    revenue_ttm: float | None = None
    gross_profit_ttm: float | None = None
    quarterly_earnings_growth_yoy: float | None = None
    quarterly_revenue_growth_yoy: float | None = None
    analyst_target_price: float | None = None
    analyst_rating_strong_buy: float | None = None
    analyst_rating_buy: float | None = None
    analyst_rating_hold: float | None = None
    analyst_rating_sell: float | None = None
    analyst_rating_strong_sell: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_sales_ratio_ttm: float | None = None
    price_to_book_ratio: float | None = None
    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    beta: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Income Statement
# =============================================================================


@dataclass(frozen=True)
class IncomeStatementRecord:
    """Income statement record for ``av_income_statements``.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    fiscal_date_ending : str
        Fiscal period end date (e.g. ``"2025-12-31"``).
    report_type : str
        ``"annual"`` or ``"quarterly"``.
    reported_currency : str | None
        Reporting currency code (e.g. ``"USD"``).
    gross_profit : float | None
        Gross profit.
    total_revenue : float | None
        Total revenue.
    cost_of_revenue : float | None
        Cost of revenue.
    cost_of_goods_and_services_sold : float | None
        Cost of goods and services sold.
    operating_income : float | None
        Operating income.
    selling_general_and_administrative : float | None
        SG&A expenses.
    research_and_development : float | None
        R&D expenses.
    operating_expenses : float | None
        Total operating expenses.
    net_income : float | None
        Net income.
    interest_income : float | None
        Interest income.
    interest_expense : float | None
        Interest expense.
    income_before_tax : float | None
        Income before tax.
    income_tax_expense : float | None
        Income tax expense.
    ebit : float | None
        Earnings before interest and taxes.
    ebitda : float | None
        Earnings before interest, taxes, depreciation and amortization.
    depreciation_and_amortization : float | None
        Depreciation and amortization.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = IncomeStatementRecord(
    ...     symbol="AAPL",
    ...     fiscal_date_ending="2025-12-31",
    ...     report_type="annual",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.report_type
    'annual'
    """

    # --- Required key fields ---
    symbol: str
    fiscal_date_ending: str
    report_type: str

    # --- Financial fields (all Optional) ---
    reported_currency: str | None = None
    gross_profit: float | None = None
    total_revenue: float | None = None
    cost_of_revenue: float | None = None
    cost_of_goods_and_services_sold: float | None = None
    operating_income: float | None = None
    selling_general_and_administrative: float | None = None
    research_and_development: float | None = None
    operating_expenses: float | None = None
    net_income: float | None = None
    interest_income: float | None = None
    interest_expense: float | None = None
    income_before_tax: float | None = None
    income_tax_expense: float | None = None
    ebit: float | None = None
    ebitda: float | None = None
    depreciation_and_amortization: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Balance Sheet
# =============================================================================


@dataclass(frozen=True)
class BalanceSheetRecord:
    """Balance sheet record for ``av_balance_sheets``.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    fiscal_date_ending : str
        Fiscal period end date.
    report_type : str
        ``"annual"`` or ``"quarterly"``.
    reported_currency : str | None
        Reporting currency code.
    total_assets : float | None
        Total assets.
    total_current_assets : float | None
        Total current assets.
    cash_and_equivalents : float | None
        Cash and cash equivalents.
    cash_and_short_term_investments : float | None
        Cash and short-term investments.
    inventory : float | None
        Inventory.
    current_net_receivables : float | None
        Current net receivables.
    total_non_current_assets : float | None
        Total non-current assets.
    property_plant_equipment : float | None
        Property, plant and equipment (net).
    intangible_assets : float | None
        Intangible assets.
    goodwill : float | None
        Goodwill.
    investments : float | None
        Total investments.
    long_term_investments : float | None
        Long-term investments.
    short_term_investments : float | None
        Short-term investments.
    total_liabilities : float | None
        Total liabilities.
    total_current_liabilities : float | None
        Total current liabilities.
    current_long_term_debt : float | None
        Current portion of long-term debt.
    short_term_debt : float | None
        Short-term debt.
    current_accounts_payable : float | None
        Current accounts payable.
    total_non_current_liabilities : float | None
        Total non-current liabilities.
    long_term_debt : float | None
        Long-term debt.
    total_shareholder_equity : float | None
        Total shareholder equity.
    retained_earnings : float | None
        Retained earnings.
    common_stock : float | None
        Common stock value.
    common_stock_shares_outstanding : float | None
        Common stock shares outstanding.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = BalanceSheetRecord(
    ...     symbol="AAPL",
    ...     fiscal_date_ending="2025-12-31",
    ...     report_type="annual",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.fiscal_date_ending
    '2025-12-31'
    """

    # --- Required key fields ---
    symbol: str
    fiscal_date_ending: str
    report_type: str

    # --- Financial fields (all Optional) ---
    reported_currency: str | None = None
    total_assets: float | None = None
    total_current_assets: float | None = None
    cash_and_equivalents: float | None = None
    cash_and_short_term_investments: float | None = None
    inventory: float | None = None
    current_net_receivables: float | None = None
    total_non_current_assets: float | None = None
    property_plant_equipment: float | None = None
    intangible_assets: float | None = None
    goodwill: float | None = None
    investments: float | None = None
    long_term_investments: float | None = None
    short_term_investments: float | None = None
    total_liabilities: float | None = None
    total_current_liabilities: float | None = None
    current_long_term_debt: float | None = None
    short_term_debt: float | None = None
    current_accounts_payable: float | None = None
    total_non_current_liabilities: float | None = None
    long_term_debt: float | None = None
    total_shareholder_equity: float | None = None
    retained_earnings: float | None = None
    common_stock: float | None = None
    common_stock_shares_outstanding: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Cash Flow
# =============================================================================


@dataclass(frozen=True)
class CashFlowRecord:
    """Cash flow statement record for ``av_cash_flows``.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    fiscal_date_ending : str
        Fiscal period end date.
    report_type : str
        ``"annual"`` or ``"quarterly"``.
    reported_currency : str | None
        Reporting currency code.
    operating_cashflow : float | None
        Operating cash flow.
    payments_for_operating_activities : float | None
        Payments for operating activities.
    change_in_operating_liabilities : float | None
        Change in operating liabilities.
    change_in_operating_assets : float | None
        Change in operating assets.
    depreciation_depletion_and_amortization : float | None
        Depreciation, depletion and amortization.
    capital_expenditures : float | None
        Capital expenditures.
    change_in_receivables : float | None
        Change in receivables.
    change_in_inventory : float | None
        Change in inventory.
    profit_loss : float | None
        Profit/loss.
    cashflow_from_investment : float | None
        Cash flow from investing activities.
    cashflow_from_financing : float | None
        Cash flow from financing activities.
    dividend_payout : float | None
        Dividend payout.
    proceeds_from_repurchase_of_equity : float | None
        Proceeds from repurchase of equity.
    proceeds_from_issuance_of_long_term_debt : float | None
        Proceeds from issuance of long-term debt.
    payments_for_repurchase_of_common_stock : float | None
        Payments for repurchase of common stock.
    change_in_cash_and_equivalents : float | None
        Change in cash and cash equivalents.
    net_income : float | None
        Net income.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = CashFlowRecord(
    ...     symbol="AAPL",
    ...     fiscal_date_ending="2025-12-31",
    ...     report_type="annual",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.report_type
    'annual'
    """

    # --- Required key fields ---
    symbol: str
    fiscal_date_ending: str
    report_type: str

    # --- Financial fields (all Optional) ---
    reported_currency: str | None = None
    operating_cashflow: float | None = None
    payments_for_operating_activities: float | None = None
    change_in_operating_liabilities: float | None = None
    change_in_operating_assets: float | None = None
    depreciation_depletion_and_amortization: float | None = None
    capital_expenditures: float | None = None
    change_in_receivables: float | None = None
    change_in_inventory: float | None = None
    profit_loss: float | None = None
    cashflow_from_investment: float | None = None
    cashflow_from_financing: float | None = None
    dividend_payout: float | None = None
    proceeds_from_repurchase_of_equity: float | None = None
    proceeds_from_issuance_of_long_term_debt: float | None = None
    payments_for_repurchase_of_common_stock: float | None = None
    change_in_cash_and_equivalents: float | None = None
    net_income: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


# =============================================================================
# Earnings — Split into Annual / Quarterly
# =============================================================================


@dataclass(frozen=True)
class AnnualEarningsRecord:
    """Annual earnings record for ``av_earnings`` (period_type="annual").

    Annual earnings data from Alpha Vantage does not include
    ``reported_date``, ``estimated_eps``, ``surprise``, or
    ``surprise_percentage`` fields.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    fiscal_date_ending : str
        Fiscal period end date.
    period_type : str
        Always ``"annual"`` for this record type.
    reported_eps : float | None
        Reported earnings per share.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = AnnualEarningsRecord(
    ...     symbol="AAPL",
    ...     fiscal_date_ending="2025-09-30",
    ...     period_type="annual",
    ...     reported_eps=6.42,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.reported_eps
    6.42
    """

    # --- Required key fields ---
    symbol: str
    fiscal_date_ending: str
    period_type: str

    # --- Data fields ---
    reported_eps: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


@dataclass(frozen=True)
class QuarterlyEarningsRecord:
    """Quarterly earnings record for ``av_earnings`` (period_type="quarterly").

    Quarterly earnings data includes additional fields not present in
    annual earnings: ``reported_date``, ``estimated_eps``, ``surprise``,
    and ``surprise_percentage``.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    fiscal_date_ending : str
        Fiscal period end date.
    period_type : str
        Always ``"quarterly"`` for this record type.
    reported_date : str | None
        Actual earnings report date.
    reported_eps : float | None
        Reported earnings per share.
    estimated_eps : float | None
        Consensus estimated earnings per share.
    surprise : float | None
        Earnings surprise (reported - estimated).
    surprise_percentage : float | None
        Earnings surprise as percentage.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = QuarterlyEarningsRecord(
    ...     symbol="AAPL",
    ...     fiscal_date_ending="2025-12-31",
    ...     period_type="quarterly",
    ...     reported_date="2026-01-28",
    ...     reported_eps=2.18,
    ...     estimated_eps=2.10,
    ...     surprise=0.08,
    ...     surprise_percentage=3.81,
    ...     fetched_at="2026-01-29T00:00:00",
    ... )
    >>> record.surprise
    0.08
    """

    # --- Required key fields ---
    symbol: str
    fiscal_date_ending: str
    period_type: str

    # --- Data fields ---
    reported_date: str | None = None
    reported_eps: float | None = None
    estimated_eps: float | None = None
    surprise: float | None = None
    surprise_percentage: float | None = None

    # --- Metadata ---
    fetched_at: str = ""


EarningsRecord = AnnualEarningsRecord | QuarterlyEarningsRecord
"""Type alias for earnings records (annual or quarterly)."""


# =============================================================================
# Economic Indicators
# =============================================================================


@dataclass(frozen=True)
class EconomicIndicatorRecord:
    """Economic indicator time-series record for ``av_economic_indicators``.

    Parameters
    ----------
    indicator : str
        Indicator name (e.g. ``"REAL_GDP"``, ``"CPI"``).
    date : str
        Observation date in ISO 8601 format.
    value : float | None
        Indicator value. ``None`` for missing observations.
    interval : str
        Data interval (e.g. ``"quarterly"``, ``"monthly"``).
        Empty string for indicators without an interval parameter.
    maturity : str
        Bond maturity for Treasury Yield (e.g. ``"10year"``).
        Empty string for non-yield indicators.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = EconomicIndicatorRecord(
    ...     indicator="REAL_GDP",
    ...     date="2025-10-01",
    ...     value=23_000.0,
    ...     interval="quarterly",
    ...     maturity="",
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.indicator
    'REAL_GDP'
    """

    indicator: str
    date: str
    value: float | None = None
    interval: str = ""
    maturity: str = ""
    fetched_at: str = ""


# =============================================================================
# Forex Daily
# =============================================================================


@dataclass(frozen=True)
class ForexDailyRecord:
    """Daily forex exchange rate record for ``av_forex_daily``.

    Parameters
    ----------
    from_currency : str
        Source currency code (e.g. ``"USD"``).
    to_currency : str
        Target currency code (e.g. ``"JPY"``).
    date : str
        Trading date in ISO 8601 format.
    open : float
        Opening exchange rate.
    high : float
        Highest exchange rate during the session.
    low : float
        Lowest exchange rate during the session.
    close : float
        Closing exchange rate.
    fetched_at : str
        ISO 8601 timestamp of when the data was fetched.

    Examples
    --------
    >>> record = ForexDailyRecord(
    ...     from_currency="USD",
    ...     to_currency="JPY",
    ...     date="2026-01-15",
    ...     open=150.0,
    ...     high=151.0,
    ...     low=149.0,
    ...     close=150.5,
    ...     fetched_at="2026-01-15T20:00:00",
    ... )
    >>> record.close
    150.5
    """

    from_currency: str
    to_currency: str
    date: str
    open: float
    high: float
    low: float
    close: float
    fetched_at: str


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "AnnualEarningsRecord",
    "BalanceSheetRecord",
    "CashFlowRecord",
    "CompanyOverviewRecord",
    "DailyPriceRecord",
    "EarningsRecord",
    "EconomicIndicatorRecord",
    "ForexDailyRecord",
    "IncomeStatementRecord",
    "QuarterlyEarningsRecord",
]
