"""Data collection orchestrator for Alpha Vantage market data.

This module provides the ``AlphaVantageCollector`` class that coordinates
data fetching from ``AlphaVantageClient``, conversion of camelCase API
responses to snake_case dataclass records, and persistence via
``AlphaVantageStorage``. It supports ``collect_all()`` for full collection
as well as individual collect methods for each data type.

Key components:

- ``_SPECIAL_KEY_MAP`` -- Maps 18+ special camelCase/PascalCase keys to
  snake_case (e.g. ``52WeekHigh`` -> ``week_52_high``).
- ``_camel_to_snake()`` -- Regex + special-map helper for key conversion.
- ``CollectionResult`` -- Frozen dataclass for per-symbol collect outcomes.
- ``CollectionSummary`` -- Frozen dataclass aggregating multiple results.
- ``AlphaVantageCollector`` -- DI-based orchestrator (client + storage).

Examples
--------
>>> from market.alphavantage.collector import AlphaVantageCollector
>>> collector = AlphaVantageCollector()
>>> result = collector.collect_daily("AAPL")
>>> result.success
True

See Also
--------
market.polymarket.collector : Reference implementation (DI + error accumulation).
market.alphavantage.client : API client providing data fetch methods.
market.alphavantage.storage : Storage layer for persisting collected data.
market.alphavantage.parser : Response parsing functions (camelCase output).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

from market.alphavantage.models import (
    AnnualEarningsRecord,
    BalanceSheetRecord,
    CashFlowRecord,
    CompanyOverviewRecord,
    DailyPriceRecord,
    EconomicIndicatorRecord,
    ForexDailyRecord,
    IncomeStatementRecord,
    QuarterlyEarningsRecord,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.alphavantage.client import AlphaVantageClient
    from market.alphavantage.storage import AlphaVantageStorage

logger = get_logger(__name__)


# =============================================================================
# camelCase -> snake_case conversion
# =============================================================================

_SPECIAL_KEY_MAP: dict[str, str] = {
    "52WeekHigh": "week_52_high",
    "52WeekLow": "week_52_low",
    "50DayMovingAverage": "day_50_moving_average",
    "200DayMovingAverage": "day_200_moving_average",
    "MarketCapitalization": "market_capitalization",
    "EBITDA": "ebitda",
    "PERatio": "pe_ratio",
    "PEGRatio": "peg_ratio",
    "DilutedEPSTTM": "diluted_eps_ttm",
    "EPS": "eps",
    "RevenuePerShareTTM": "revenue_per_share_ttm",
    "RevenueTTM": "revenue_ttm",
    "GrossProfitTTM": "gross_profit_ttm",
    "OperatingMarginTTM": "operating_margin_ttm",
    "ReturnOnAssetsTTM": "return_on_assets_ttm",
    "ReturnOnEquityTTM": "return_on_equity_ttm",
    "PriceToSalesRatioTTM": "price_to_sales_ratio_ttm",
    "EVToRevenue": "ev_to_revenue",
    "EVToEBITDA": "ev_to_ebitda",
    "QuarterlyEarningsGrowthYOY": "quarterly_earnings_growth_yoy",
    "QuarterlyRevenueGrowthYOY": "quarterly_revenue_growth_yoy",
    "TrailingPE": "trailing_pe",
    "ForwardPE": "forward_pe",
    "PriceToBookRatio": "price_to_book_ratio",
    "SharesOutstanding": "shares_outstanding",
    "BookValue": "book_value",
    "DividendPerShare": "dividend_per_share",
    "DividendYield": "dividend_yield",
    "AnalystTargetPrice": "analyst_target_price",
    "AnalystRatingStrongBuy": "analyst_rating_strong_buy",
    "AnalystRatingBuy": "analyst_rating_buy",
    "AnalystRatingHold": "analyst_rating_hold",
    "AnalystRatingSell": "analyst_rating_sell",
    "AnalystRatingStrongSell": "analyst_rating_strong_sell",
    "ProfitMargin": "profit_margin",
    "Beta": "beta",
    "FiscalYearEnd": "fiscal_year_end",
    "LatestQuarter": "latest_quarter",
    # Financial statement fields
    "fiscalDateEnding": "fiscal_date_ending",
    "reportedCurrency": "reported_currency",
    "grossProfit": "gross_profit",
    "totalRevenue": "total_revenue",
    "costOfRevenue": "cost_of_revenue",
    "costofGoodsAndServicesSold": "cost_of_goods_and_services_sold",
    "operatingIncome": "operating_income",
    "sellingGeneralAndAdministrative": "selling_general_and_administrative",
    "researchAndDevelopment": "research_and_development",
    "operatingExpenses": "operating_expenses",
    "netIncome": "net_income",
    "interestIncome": "interest_income",
    "interestExpense": "interest_expense",
    "incomeTaxExpense": "income_tax_expense",
    "incomeBeforeTax": "income_before_tax",
    "depreciationAndAmortization": "depreciation_and_amortization",
    # Balance sheet fields
    "totalAssets": "total_assets",
    "totalCurrentAssets": "total_current_assets",
    "cashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
    "cashAndShortTermInvestments": "cash_and_short_term_investments",
    "currentNetReceivables": "current_net_receivables",
    "totalNonCurrentAssets": "total_non_current_assets",
    "propertyPlantEquipment": "property_plant_equipment",
    "intangibleAssets": "intangible_assets",
    "longTermInvestments": "long_term_investments",
    "shortTermInvestments": "short_term_investments",
    "totalLiabilities": "total_liabilities",
    "totalCurrentLiabilities": "total_current_liabilities",
    "currentLongTermDebt": "current_long_term_debt",
    "shortTermDebt": "short_term_debt",
    "currentAccountsPayable": "current_accounts_payable",
    "totalNonCurrentLiabilities": "total_non_current_liabilities",
    "longTermDebt": "long_term_debt",
    "totalShareholderEquity": "total_shareholder_equity",
    "retainedEarnings": "retained_earnings",
    "commonStock": "common_stock",
    "commonStockSharesOutstanding": "common_stock_shares_outstanding",
    # Cash flow fields
    "operatingCashflow": "operating_cashflow",
    "paymentsForOperatingActivities": "payments_for_operating_activities",
    "changeInOperatingLiabilities": "change_in_operating_liabilities",
    "changeInOperatingAssets": "change_in_operating_assets",
    "depreciationDepletionAndAmortization": "depreciation_depletion_and_amortization",
    "capitalExpenditures": "capital_expenditures",
    "changeInReceivables": "change_in_receivables",
    "changeInInventory": "change_in_inventory",
    "profitLoss": "profit_loss",
    "cashflowFromInvestment": "cashflow_from_investment",
    "cashflowFromFinancing": "cashflow_from_financing",
    "dividendPayout": "dividend_payout",
    "proceedsFromRepurchaseOfEquity": "proceeds_from_repurchase_of_equity",
    "proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet": (
        "proceeds_from_issuance_of_long_term_debt"
    ),
    "paymentsForRepurchaseOfCommonStock": "payments_for_repurchase_of_common_stock",
    "changeInCashAndCashEquivalents": "change_in_cash_and_equivalents",
    # Earnings fields
    "reportedEPS": "reported_eps",
    "reportedDate": "reported_date",
    "estimatedEPS": "estimated_eps",
    "surprisePercentage": "surprise_percentage",
}
"""Special key mappings for camelCase/PascalCase -> snake_case conversion.

Handles keys that cannot be correctly converted by regex alone:
- Numeric prefixes (52WeekHigh, 50DayMovingAverage)
- Abbreviations (EBITDA, EPS, PE, EV, TTM, YOY)
- Alpha Vantage-specific naming quirks
"""

# Regex patterns for generic camelCase -> snake_case conversion
_CAMEL_TO_SNAKE_RE1: re.Pattern[str] = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_TO_SNAKE_RE2: re.Pattern[str] = re.compile(r"([a-z\d])([A-Z])")


def _camel_to_snake(key: str) -> str:
    """Convert a camelCase or PascalCase key to snake_case.

    Uses ``_SPECIAL_KEY_MAP`` for known keys that cannot be handled by
    regex alone, then falls back to a two-pass regex approach for
    generic camelCase -> snake_case conversion.

    Parameters
    ----------
    key : str
        The camelCase or PascalCase key to convert.

    Returns
    -------
    str
        The snake_case version of the key.

    Examples
    --------
    >>> _camel_to_snake("52WeekHigh")
    'week_52_high'
    >>> _camel_to_snake("MarketCapitalization")
    'market_capitalization'
    >>> _camel_to_snake("bookValue")
    'book_value'
    """
    # Check special map first
    if key in _SPECIAL_KEY_MAP:
        return _SPECIAL_KEY_MAP[key]

    # Generic conversion: two-pass regex
    result = _CAMEL_TO_SNAKE_RE1.sub(r"\1_\2", key)
    result = _CAMEL_TO_SNAKE_RE2.sub(r"\1_\2", result)
    return result.lower()


# =============================================================================
# CollectionResult / CollectionSummary dataclasses
# =============================================================================


@dataclass(frozen=True)
class CollectionResult:
    """Outcome of a single collect operation.

    Captures per-symbol (or per-indicator) collection statistics
    including table name, row count, and any error message.

    Parameters
    ----------
    symbol : str
        The symbol or indicator name that was collected.
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
    ...     symbol="AAPL", table="av_daily_prices",
    ...     rows_upserted=100, success=True,
    ... )
    >>> result.success
    True
    """

    symbol: str
    table: str
    rows_upserted: int = 0
    success: bool = True
    error_message: str | None = None


@dataclass(frozen=True)
class CollectionSummary:
    """Aggregated summary of multiple ``CollectionResult`` instances.

    Parameters
    ----------
    results : tuple[CollectionResult, ...]
        Tuple of individual collection results.
    total_symbols : int
        Total number of symbols processed.
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
    ...         CollectionResult("AAPL", "av_daily_prices", 100, True),
    ...     ),
    ...     total_symbols=1, successful=1, failed=0, total_rows=100,
    ... )
    >>> summary.has_failures
    False
    """

    results: tuple[CollectionResult, ...] = ()
    total_symbols: int = 0
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
# AlphaVantageCollector
# =============================================================================

# Economic indicators to collect in collect_economic_indicators()
_DEFAULT_ECONOMIC_INDICATORS: tuple[str, ...] = (
    "REAL_GDP",
    "CPI",
    "INFLATION",
    "UNEMPLOYMENT",
    "TREASURY_YIELD",
    "FEDERAL_FUNDS_RATE",
)


class AlphaVantageCollector:
    """Orchestrator for collecting Alpha Vantage data via Client -> Storage flow.

    Coordinates data fetching from ``AlphaVantageClient``, transforms
    camelCase API responses into snake_case record dataclasses, and persists
    via ``AlphaVantageStorage``.

    Provides 8 individual collect methods plus ``collect_all()`` for full
    pipeline execution across multiple symbols.

    Parameters
    ----------
    client : AlphaVantageClient | None
        API client for fetching data. If ``None``, a default client is created.
    storage : AlphaVantageStorage | None
        Storage layer for persisting data. If ``None``, a default storage is
        created via ``get_alphavantage_storage()``.

    Examples
    --------
    >>> collector = AlphaVantageCollector()
    >>> result = collector.collect_daily("AAPL")
    >>> result.success
    True
    >>> summary = collector.collect_all(["AAPL", "MSFT"])
    >>> summary.total_rows > 0
    True
    """

    def __init__(
        self,
        client: AlphaVantageClient | None = None,
        storage: AlphaVantageStorage | None = None,
    ) -> None:
        if client is None:
            from market.alphavantage.client import AlphaVantageClient

            client = AlphaVantageClient()
        if storage is None:
            from market.alphavantage.storage import get_alphavantage_storage

            storage = get_alphavantage_storage()

        self._client = client
        self._storage = storage
        logger.info("AlphaVantageCollector initialized")

    # ------------------------------------------------------------------
    # collect_daily
    # ------------------------------------------------------------------

    def collect_daily(self, symbol: str) -> CollectionResult:
        """Collect daily OHLCV prices for a symbol and persist to storage.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol (e.g. ``"AAPL"``).

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        logger.info("Collecting daily prices", symbol=symbol)
        try:
            df = self._client.get_daily(symbol)
            if df.empty:
                logger.info("No daily price data returned", symbol=symbol)
                return CollectionResult(
                    symbol=symbol,
                    table="av_daily_prices",
                    rows_upserted=0,
                    success=True,
                )

            fetched_at = datetime.now(tz=UTC).isoformat()
            records = _daily_df_to_records(df, symbol, fetched_at)
            count = self._storage.upsert_daily_prices(records)
            logger.info("Daily prices collected", symbol=symbol, rows=count)
            return CollectionResult(
                symbol=symbol,
                table="av_daily_prices",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error("Failed to collect daily prices", symbol=symbol, exc_info=True)
            return CollectionResult(
                symbol=symbol,
                table="av_daily_prices",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_company_overview
    # ------------------------------------------------------------------

    def collect_company_overview(self, symbol: str) -> CollectionResult:
        """Collect company overview data and persist to storage.

        Converts PascalCase API keys to snake_case record fields.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol (e.g. ``"AAPL"``).

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        logger.info("Collecting company overview", symbol=symbol)
        try:
            overview = self._client.get_company_overview(symbol)
            if not overview:
                logger.info("No overview data returned", symbol=symbol)
                return CollectionResult(
                    symbol=symbol,
                    table="av_company_overview",
                    rows_upserted=0,
                    success=True,
                )

            fetched_at = datetime.now(tz=UTC).isoformat()
            record = _overview_dict_to_record(overview, fetched_at)
            count = self._storage.upsert_company_overview(record)
            logger.info("Company overview collected", symbol=symbol)
            return CollectionResult(
                symbol=symbol,
                table="av_company_overview",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect company overview", symbol=symbol, exc_info=True
            )
            return CollectionResult(
                symbol=symbol,
                table="av_company_overview",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_income_statement
    # ------------------------------------------------------------------

    def collect_income_statement(self, symbol: str) -> CollectionResult:
        """Collect income statement data (annual + quarterly) and persist.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        logger.info("Collecting income statement", symbol=symbol)
        try:
            fetched_at = datetime.now(tz=UTC).isoformat()
            total = 0

            for report_type in ("annualReports", "quarterlyReports"):
                df = self._client.get_income_statement(symbol, report_type=report_type)
                if df.empty:
                    continue
                period = "annual" if report_type == "annualReports" else "quarterly"
                records = _financial_df_to_income_records(
                    df, symbol, period, fetched_at
                )
                total += self._storage.upsert_income_statements(records)

            logger.info("Income statement collected", symbol=symbol, rows=total)
            return CollectionResult(
                symbol=symbol,
                table="av_income_statements",
                rows_upserted=total,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect income statement", symbol=symbol, exc_info=True
            )
            return CollectionResult(
                symbol=symbol,
                table="av_income_statements",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_balance_sheet
    # ------------------------------------------------------------------

    def collect_balance_sheet(self, symbol: str) -> CollectionResult:
        """Collect balance sheet data (annual + quarterly) and persist.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        logger.info("Collecting balance sheet", symbol=symbol)
        try:
            fetched_at = datetime.now(tz=UTC).isoformat()
            total = 0

            for report_type in ("annualReports", "quarterlyReports"):
                df = self._client.get_balance_sheet(symbol, report_type=report_type)
                if df.empty:
                    continue
                period = "annual" if report_type == "annualReports" else "quarterly"
                records = _financial_df_to_balance_records(
                    df, symbol, period, fetched_at
                )
                total += self._storage.upsert_balance_sheets(records)

            logger.info("Balance sheet collected", symbol=symbol, rows=total)
            return CollectionResult(
                symbol=symbol,
                table="av_balance_sheets",
                rows_upserted=total,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect balance sheet", symbol=symbol, exc_info=True
            )
            return CollectionResult(
                symbol=symbol,
                table="av_balance_sheets",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_cash_flow
    # ------------------------------------------------------------------

    def collect_cash_flow(self, symbol: str) -> CollectionResult:
        """Collect cash flow data (annual + quarterly) and persist.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        logger.info("Collecting cash flow", symbol=symbol)
        try:
            fetched_at = datetime.now(tz=UTC).isoformat()
            total = 0

            for report_type in ("annualReports", "quarterlyReports"):
                df = self._client.get_cash_flow(symbol, report_type=report_type)
                if df.empty:
                    continue
                period = "annual" if report_type == "annualReports" else "quarterly"
                records = _financial_df_to_cashflow_records(
                    df, symbol, period, fetched_at
                )
                total += self._storage.upsert_cash_flows(records)

            logger.info("Cash flow collected", symbol=symbol, rows=total)
            return CollectionResult(
                symbol=symbol,
                table="av_cash_flows",
                rows_upserted=total,
                success=True,
            )
        except Exception as exc:
            logger.error("Failed to collect cash flow", symbol=symbol, exc_info=True)
            return CollectionResult(
                symbol=symbol,
                table="av_cash_flows",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_earnings
    # ------------------------------------------------------------------

    def collect_earnings(self, symbol: str) -> CollectionResult:
        """Collect earnings data (annual + quarterly) and persist.

        Annual earnings are converted to ``AnnualEarningsRecord`` and
        quarterly earnings to ``QuarterlyEarningsRecord``, preserving
        type separation per the data model.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol.

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        logger.info("Collecting earnings", symbol=symbol)
        try:
            annual_df, quarterly_df = self._client.get_earnings(symbol)
            fetched_at = datetime.now(tz=UTC).isoformat()

            records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = []

            if not annual_df.empty:
                records.extend(
                    _earnings_annual_df_to_records(annual_df, symbol, fetched_at)
                )
            if not quarterly_df.empty:
                records.extend(
                    _earnings_quarterly_df_to_records(quarterly_df, symbol, fetched_at)
                )

            if not records:
                logger.info("No earnings data returned", symbol=symbol)
                return CollectionResult(
                    symbol=symbol, table="av_earnings", rows_upserted=0, success=True
                )

            count = self._storage.upsert_earnings(records)
            logger.info("Earnings collected", symbol=symbol, rows=count)
            return CollectionResult(
                symbol=symbol, table="av_earnings", rows_upserted=count, success=True
            )
        except Exception as exc:
            logger.error("Failed to collect earnings", symbol=symbol, exc_info=True)
            return CollectionResult(
                symbol=symbol,
                table="av_earnings",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_economic_indicators
    # ------------------------------------------------------------------

    def collect_economic_indicators(
        self,
        indicators: tuple[str, ...] | None = None,
    ) -> list[CollectionResult]:
        """Collect economic indicator data for multiple indicators.

        Collects each indicator independently. Failures in one indicator
        do not affect others (partial success supported).

        Parameters
        ----------
        indicators : tuple[str, ...] | None
            Indicator names to collect. Defaults to all 6 supported
            indicators.

        Returns
        -------
        list[CollectionResult]
            One ``CollectionResult`` per indicator.
        """
        indicators = indicators or _DEFAULT_ECONOMIC_INDICATORS
        results: list[CollectionResult] = []

        for indicator in indicators:
            logger.info("Collecting economic indicator", indicator=indicator)
            try:
                df = self._fetch_economic_indicator(indicator)
                if df.empty:
                    results.append(
                        CollectionResult(
                            symbol=indicator,
                            table="av_economic_indicators",
                            rows_upserted=0,
                            success=True,
                        )
                    )
                    continue

                fetched_at = datetime.now(tz=UTC).isoformat()
                records = _economic_df_to_records(df, indicator, fetched_at)
                count = self._storage.upsert_economic_indicators(records)
                logger.info(
                    "Economic indicator collected", indicator=indicator, rows=count
                )
                results.append(
                    CollectionResult(
                        symbol=indicator,
                        table="av_economic_indicators",
                        rows_upserted=count,
                        success=True,
                    )
                )
            except Exception as exc:
                logger.error(
                    "Failed to collect economic indicator",
                    indicator=indicator,
                    exc_info=True,
                )
                results.append(
                    CollectionResult(
                        symbol=indicator,
                        table="av_economic_indicators",
                        rows_upserted=0,
                        success=False,
                        error_message=str(exc),
                    )
                )

        return results

    def _fetch_economic_indicator(self, indicator: str) -> pd.DataFrame:
        """Fetch a single economic indicator from the client.

        Maps indicator name to the appropriate client method.

        Parameters
        ----------
        indicator : str
            Indicator name (e.g. ``"REAL_GDP"``).

        Returns
        -------
        pd.DataFrame
            Indicator data with ``date`` and ``value`` columns.

        Raises
        ------
        ValueError
            If the indicator name is not supported.
        """
        method_map: dict[str, Any] = {
            "REAL_GDP": self._client.get_real_gdp,
            "CPI": self._client.get_cpi,
            "INFLATION": self._client.get_inflation,
            "UNEMPLOYMENT": self._client.get_unemployment,
            "TREASURY_YIELD": self._client.get_treasury_yield,
            "FEDERAL_FUNDS_RATE": self._client.get_federal_funds_rate,
        }
        method = method_map.get(indicator)
        if method is None:
            msg = f"Unsupported economic indicator: '{indicator}'"
            raise ValueError(msg)
        return method()

    # ------------------------------------------------------------------
    # collect_forex_daily
    # ------------------------------------------------------------------

    def collect_forex_daily(
        self,
        from_currency: str,
        to_currency: str,
    ) -> CollectionResult:
        """Collect daily forex data for a currency pair and persist.

        Parameters
        ----------
        from_currency : str
            Source currency code (e.g. ``"USD"``).
        to_currency : str
            Target currency code (e.g. ``"JPY"``).

        Returns
        -------
        CollectionResult
            Result with rows_upserted count and success status.
        """
        pair = f"{from_currency}/{to_currency}"
        logger.info("Collecting forex daily", pair=pair)
        try:
            df = self._client.get_fx_daily(from_currency, to_currency)
            if df.empty:
                logger.info("No forex data returned", pair=pair)
                return CollectionResult(
                    symbol=pair, table="av_forex_daily", rows_upserted=0, success=True
                )

            fetched_at = datetime.now(tz=UTC).isoformat()
            records = _forex_df_to_records(df, from_currency, to_currency, fetched_at)
            count = self._storage.upsert_forex_daily(records)
            logger.info("Forex daily collected", pair=pair, rows=count)
            return CollectionResult(
                symbol=pair, table="av_forex_daily", rows_upserted=count, success=True
            )
        except Exception as exc:
            logger.error("Failed to collect forex daily", pair=pair, exc_info=True)
            return CollectionResult(
                symbol=pair,
                table="av_forex_daily",
                rows_upserted=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # collect_all
    # ------------------------------------------------------------------

    def collect_all(
        self,
        symbols: list[str],
        *,
        include_fundamentals: bool = True,
        include_economic: bool = True,
    ) -> CollectionSummary:
        """Collect all data types for multiple symbols.

        For each symbol, collects daily prices and optionally
        fundamentals (overview, income statement, balance sheet,
        cash flow, earnings). Economic indicators are collected once
        regardless of symbol list.

        Supports partial success: failures in one symbol/type do not
        affect other collections.

        Parameters
        ----------
        symbols : list[str]
            List of stock ticker symbols to collect data for.
        include_fundamentals : bool
            Whether to collect fundamental data (default: True).
        include_economic : bool
            Whether to collect economic indicators (default: True).

        Returns
        -------
        CollectionSummary
            Aggregated summary of all collection results.
        """
        logger.info(
            "Starting collect_all",
            symbols=symbols,
            include_fundamentals=include_fundamentals,
            include_economic=include_economic,
        )

        all_results: list[CollectionResult] = []

        for symbol in symbols:
            # Daily prices (always collected)
            all_results.append(self.collect_daily(symbol))

            if include_fundamentals:
                all_results.append(self.collect_company_overview(symbol))
                all_results.append(self.collect_income_statement(symbol))
                all_results.append(self.collect_balance_sheet(symbol))
                all_results.append(self.collect_cash_flow(symbol))
                all_results.append(self.collect_earnings(symbol))

        if include_economic:
            all_results.extend(self.collect_economic_indicators())

        successful = sum(1 for r in all_results if r.success)
        failed = sum(1 for r in all_results if not r.success)
        total_rows = sum(r.rows_upserted for r in all_results)

        summary = CollectionSummary(
            results=tuple(all_results),
            total_symbols=len(symbols),
            successful=successful,
            failed=failed,
            total_rows=total_rows,
        )

        logger.info(
            "collect_all completed",
            total_symbols=summary.total_symbols,
            successful=summary.successful,
            failed=summary.failed,
            total_rows=summary.total_rows,
        )
        return summary


# =============================================================================
# DataFrame -> Record conversion helpers
# =============================================================================


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None for NaN/None.

    Parameters
    ----------
    value : Any
        Value to convert.

    Returns
    -------
    float | None
        Float value or None if the input is NaN, None, or unparseable.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        result = float(value)
        if pd.isna(result):
            return None
        return result
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int:
    """Safely convert a value to int, returning 0 for NaN/None.

    Parameters
    ----------
    value : Any
        Value to convert.

    Returns
    -------
    int
        Integer value, defaulting to 0 on failure.
    """
    if value is None:
        return 0
    try:
        f = float(value)
        if pd.isna(f):
            return 0
        return int(f)
    except (ValueError, TypeError):
        return 0


def _safe_str(value: Any) -> str | None:
    """Safely convert a value to str, returning None for NaN/None.

    Parameters
    ----------
    value : Any
        Value to convert.

    Returns
    -------
    str | None
        String value or None if the input is NaN or None.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    s = str(value)
    return None if s in ("None", "nan", "") else s


def _daily_df_to_records(
    df: pd.DataFrame,
    symbol: str,
    fetched_at: str,
) -> list[DailyPriceRecord]:
    """Convert a daily time series DataFrame to DailyPriceRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_time_series()`` with columns:
        date, open, high, low, close, volume.
    symbol : str
        Ticker symbol.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[DailyPriceRecord]
        List of daily price records.
    """
    records: list[DailyPriceRecord] = []
    for _, row in df.iterrows():
        records.append(
            DailyPriceRecord(
                symbol=symbol,
                date=str(row.get("date", "")),
                open=_safe_float(row.get("open")) or 0.0,
                high=_safe_float(row.get("high")) or 0.0,
                low=_safe_float(row.get("low")) or 0.0,
                close=_safe_float(row.get("close")) or 0.0,
                adjusted_close=_safe_float(row.get("adjusted close")),
                volume=_safe_int(row.get("volume")),
                fetched_at=fetched_at,
            )
        )
    return records


def _overview_dict_to_record(
    data: dict[str, Any],
    fetched_at: str,
) -> CompanyOverviewRecord:
    """Convert a company overview dict to CompanyOverviewRecord.

    Applies ``_camel_to_snake()`` conversion for each key and maps
    to the record fields.

    Parameters
    ----------
    data : dict[str, Any]
        Parsed overview dict from ``client.get_company_overview()``.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    CompanyOverviewRecord
        The company overview record.
    """
    # Convert all keys to snake_case
    snake_data: dict[str, Any] = {}
    for key, value in data.items():
        snake_key = _camel_to_snake(key)
        snake_data[snake_key] = value

    return CompanyOverviewRecord(
        symbol=str(snake_data.get("symbol", "")),
        name=_safe_str(snake_data.get("name")),
        description=_safe_str(snake_data.get("description")),
        exchange=_safe_str(snake_data.get("exchange")),
        currency=_safe_str(snake_data.get("currency")),
        country=_safe_str(snake_data.get("country")),
        sector=_safe_str(snake_data.get("sector")),
        industry=_safe_str(snake_data.get("industry")),
        fiscal_year_end=_safe_str(snake_data.get("fiscal_year_end")),
        latest_quarter=_safe_str(snake_data.get("latest_quarter")),
        market_capitalization=_safe_float(snake_data.get("market_capitalization")),
        ebitda=_safe_float(snake_data.get("ebitda")),
        pe_ratio=_safe_float(snake_data.get("pe_ratio")),
        peg_ratio=_safe_float(snake_data.get("peg_ratio")),
        book_value=_safe_float(snake_data.get("book_value")),
        dividend_per_share=_safe_float(snake_data.get("dividend_per_share")),
        dividend_yield=_safe_float(snake_data.get("dividend_yield")),
        eps=_safe_float(snake_data.get("eps")),
        diluted_eps_ttm=_safe_float(snake_data.get("diluted_eps_ttm")),
        week_52_high=_safe_float(snake_data.get("week_52_high")),
        week_52_low=_safe_float(snake_data.get("week_52_low")),
        day_50_moving_average=_safe_float(snake_data.get("day_50_moving_average")),
        day_200_moving_average=_safe_float(snake_data.get("day_200_moving_average")),
        shares_outstanding=_safe_float(snake_data.get("shares_outstanding")),
        revenue_per_share_ttm=_safe_float(snake_data.get("revenue_per_share_ttm")),
        profit_margin=_safe_float(snake_data.get("profit_margin")),
        operating_margin_ttm=_safe_float(snake_data.get("operating_margin_ttm")),
        return_on_assets_ttm=_safe_float(snake_data.get("return_on_assets_ttm")),
        return_on_equity_ttm=_safe_float(snake_data.get("return_on_equity_ttm")),
        revenue_ttm=_safe_float(snake_data.get("revenue_ttm")),
        gross_profit_ttm=_safe_float(snake_data.get("gross_profit_ttm")),
        quarterly_earnings_growth_yoy=_safe_float(
            snake_data.get("quarterly_earnings_growth_yoy")
        ),
        quarterly_revenue_growth_yoy=_safe_float(
            snake_data.get("quarterly_revenue_growth_yoy")
        ),
        analyst_target_price=_safe_float(snake_data.get("analyst_target_price")),
        analyst_rating_strong_buy=_safe_float(
            snake_data.get("analyst_rating_strong_buy")
        ),
        analyst_rating_buy=_safe_float(snake_data.get("analyst_rating_buy")),
        analyst_rating_hold=_safe_float(snake_data.get("analyst_rating_hold")),
        analyst_rating_sell=_safe_float(snake_data.get("analyst_rating_sell")),
        analyst_rating_strong_sell=_safe_float(
            snake_data.get("analyst_rating_strong_sell")
        ),
        trailing_pe=_safe_float(snake_data.get("trailing_pe")),
        forward_pe=_safe_float(snake_data.get("forward_pe")),
        price_to_sales_ratio_ttm=_safe_float(
            snake_data.get("price_to_sales_ratio_ttm")
        ),
        price_to_book_ratio=_safe_float(snake_data.get("price_to_book_ratio")),
        ev_to_revenue=_safe_float(snake_data.get("ev_to_revenue")),
        ev_to_ebitda=_safe_float(snake_data.get("ev_to_ebitda")),
        beta=_safe_float(snake_data.get("beta")),
        fetched_at=fetched_at,
    )


def _financial_df_to_income_records(
    df: pd.DataFrame,
    symbol: str,
    report_type: str,
    fetched_at: str,
) -> list[IncomeStatementRecord]:
    """Convert an income statement DataFrame to IncomeStatementRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_financial_statements()`` with camelCase columns.
    symbol : str
        Ticker symbol.
    report_type : str
        ``"annual"`` or ``"quarterly"``.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[IncomeStatementRecord]
        List of income statement records.
    """
    records: list[IncomeStatementRecord] = []
    for _, row in df.iterrows():
        snake_row = {_camel_to_snake(str(k)): v for k, v in row.items()}
        records.append(
            IncomeStatementRecord(
                symbol=symbol,
                fiscal_date_ending=str(snake_row.get("fiscal_date_ending", "")),
                report_type=report_type,
                reported_currency=_safe_str(snake_row.get("reported_currency")),
                gross_profit=_safe_float(snake_row.get("gross_profit")),
                total_revenue=_safe_float(snake_row.get("total_revenue")),
                cost_of_revenue=_safe_float(snake_row.get("cost_of_revenue")),
                cost_of_goods_and_services_sold=_safe_float(
                    snake_row.get("cost_of_goods_and_services_sold")
                ),
                operating_income=_safe_float(snake_row.get("operating_income")),
                selling_general_and_administrative=_safe_float(
                    snake_row.get("selling_general_and_administrative")
                ),
                research_and_development=_safe_float(
                    snake_row.get("research_and_development")
                ),
                operating_expenses=_safe_float(snake_row.get("operating_expenses")),
                net_income=_safe_float(snake_row.get("net_income")),
                interest_income=_safe_float(snake_row.get("interest_income")),
                interest_expense=_safe_float(snake_row.get("interest_expense")),
                income_before_tax=_safe_float(snake_row.get("income_before_tax")),
                income_tax_expense=_safe_float(snake_row.get("income_tax_expense")),
                ebit=_safe_float(snake_row.get("ebit")),
                ebitda=_safe_float(snake_row.get("ebitda")),
                depreciation_and_amortization=_safe_float(
                    snake_row.get("depreciation_and_amortization")
                ),
                fetched_at=fetched_at,
            )
        )
    return records


def _financial_df_to_balance_records(
    df: pd.DataFrame,
    symbol: str,
    report_type: str,
    fetched_at: str,
) -> list[BalanceSheetRecord]:
    """Convert a balance sheet DataFrame to BalanceSheetRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_financial_statements()`` with camelCase columns.
    symbol : str
        Ticker symbol.
    report_type : str
        ``"annual"`` or ``"quarterly"``.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[BalanceSheetRecord]
        List of balance sheet records.
    """
    records: list[BalanceSheetRecord] = []
    for _, row in df.iterrows():
        snake_row = {_camel_to_snake(str(k)): v for k, v in row.items()}
        records.append(
            BalanceSheetRecord(
                symbol=symbol,
                fiscal_date_ending=str(snake_row.get("fiscal_date_ending", "")),
                report_type=report_type,
                reported_currency=_safe_str(snake_row.get("reported_currency")),
                total_assets=_safe_float(snake_row.get("total_assets")),
                total_current_assets=_safe_float(snake_row.get("total_current_assets")),
                cash_and_equivalents=_safe_float(snake_row.get("cash_and_equivalents")),
                cash_and_short_term_investments=_safe_float(
                    snake_row.get("cash_and_short_term_investments")
                ),
                inventory=_safe_float(snake_row.get("inventory")),
                current_net_receivables=_safe_float(
                    snake_row.get("current_net_receivables")
                ),
                total_non_current_assets=_safe_float(
                    snake_row.get("total_non_current_assets")
                ),
                property_plant_equipment=_safe_float(
                    snake_row.get("property_plant_equipment")
                ),
                intangible_assets=_safe_float(snake_row.get("intangible_assets")),
                goodwill=_safe_float(snake_row.get("goodwill")),
                investments=_safe_float(snake_row.get("investments")),
                long_term_investments=_safe_float(
                    snake_row.get("long_term_investments")
                ),
                short_term_investments=_safe_float(
                    snake_row.get("short_term_investments")
                ),
                total_liabilities=_safe_float(snake_row.get("total_liabilities")),
                total_current_liabilities=_safe_float(
                    snake_row.get("total_current_liabilities")
                ),
                current_long_term_debt=_safe_float(
                    snake_row.get("current_long_term_debt")
                ),
                short_term_debt=_safe_float(snake_row.get("short_term_debt")),
                current_accounts_payable=_safe_float(
                    snake_row.get("current_accounts_payable")
                ),
                total_non_current_liabilities=_safe_float(
                    snake_row.get("total_non_current_liabilities")
                ),
                long_term_debt=_safe_float(snake_row.get("long_term_debt")),
                total_shareholder_equity=_safe_float(
                    snake_row.get("total_shareholder_equity")
                ),
                retained_earnings=_safe_float(snake_row.get("retained_earnings")),
                common_stock=_safe_float(snake_row.get("common_stock")),
                common_stock_shares_outstanding=_safe_float(
                    snake_row.get("common_stock_shares_outstanding")
                ),
                fetched_at=fetched_at,
            )
        )
    return records


def _financial_df_to_cashflow_records(
    df: pd.DataFrame,
    symbol: str,
    report_type: str,
    fetched_at: str,
) -> list[CashFlowRecord]:
    """Convert a cash flow DataFrame to CashFlowRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_financial_statements()`` with camelCase columns.
    symbol : str
        Ticker symbol.
    report_type : str
        ``"annual"`` or ``"quarterly"``.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[CashFlowRecord]
        List of cash flow records.
    """
    records: list[CashFlowRecord] = []
    for _, row in df.iterrows():
        snake_row = {_camel_to_snake(str(k)): v for k, v in row.items()}
        records.append(
            CashFlowRecord(
                symbol=symbol,
                fiscal_date_ending=str(snake_row.get("fiscal_date_ending", "")),
                report_type=report_type,
                reported_currency=_safe_str(snake_row.get("reported_currency")),
                operating_cashflow=_safe_float(snake_row.get("operating_cashflow")),
                payments_for_operating_activities=_safe_float(
                    snake_row.get("payments_for_operating_activities")
                ),
                change_in_operating_liabilities=_safe_float(
                    snake_row.get("change_in_operating_liabilities")
                ),
                change_in_operating_assets=_safe_float(
                    snake_row.get("change_in_operating_assets")
                ),
                depreciation_depletion_and_amortization=_safe_float(
                    snake_row.get("depreciation_depletion_and_amortization")
                ),
                capital_expenditures=_safe_float(snake_row.get("capital_expenditures")),
                change_in_receivables=_safe_float(
                    snake_row.get("change_in_receivables")
                ),
                change_in_inventory=_safe_float(snake_row.get("change_in_inventory")),
                profit_loss=_safe_float(snake_row.get("profit_loss")),
                cashflow_from_investment=_safe_float(
                    snake_row.get("cashflow_from_investment")
                ),
                cashflow_from_financing=_safe_float(
                    snake_row.get("cashflow_from_financing")
                ),
                dividend_payout=_safe_float(snake_row.get("dividend_payout")),
                proceeds_from_repurchase_of_equity=_safe_float(
                    snake_row.get("proceeds_from_repurchase_of_equity")
                ),
                proceeds_from_issuance_of_long_term_debt=_safe_float(
                    snake_row.get("proceeds_from_issuance_of_long_term_debt")
                ),
                payments_for_repurchase_of_common_stock=_safe_float(
                    snake_row.get("payments_for_repurchase_of_common_stock")
                ),
                change_in_cash_and_equivalents=_safe_float(
                    snake_row.get("change_in_cash_and_equivalents")
                ),
                net_income=_safe_float(snake_row.get("net_income")),
                fetched_at=fetched_at,
            )
        )
    return records


def _earnings_annual_df_to_records(
    df: pd.DataFrame,
    symbol: str,
    fetched_at: str,
) -> list[AnnualEarningsRecord]:
    """Convert annual earnings DataFrame to AnnualEarningsRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_earnings()`` (annual) with camelCase columns.
    symbol : str
        Ticker symbol.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[AnnualEarningsRecord]
        List of annual earnings records.
    """
    records: list[AnnualEarningsRecord] = []
    for _, row in df.iterrows():
        snake_row = {_camel_to_snake(str(k)): v for k, v in row.items()}
        records.append(
            AnnualEarningsRecord(
                symbol=symbol,
                fiscal_date_ending=str(snake_row.get("fiscal_date_ending", "")),
                period_type="annual",
                reported_eps=_safe_float(snake_row.get("reported_eps")),
                fetched_at=fetched_at,
            )
        )
    return records


def _earnings_quarterly_df_to_records(
    df: pd.DataFrame,
    symbol: str,
    fetched_at: str,
) -> list[QuarterlyEarningsRecord]:
    """Convert quarterly earnings DataFrame to QuarterlyEarningsRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_earnings()`` (quarterly) with camelCase columns.
    symbol : str
        Ticker symbol.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[QuarterlyEarningsRecord]
        List of quarterly earnings records.
    """
    records: list[QuarterlyEarningsRecord] = []
    for _, row in df.iterrows():
        snake_row = {_camel_to_snake(str(k)): v for k, v in row.items()}
        records.append(
            QuarterlyEarningsRecord(
                symbol=symbol,
                fiscal_date_ending=str(snake_row.get("fiscal_date_ending", "")),
                period_type="quarterly",
                reported_date=_safe_str(snake_row.get("reported_date")),
                reported_eps=_safe_float(snake_row.get("reported_eps")),
                estimated_eps=_safe_float(snake_row.get("estimated_eps")),
                surprise=_safe_float(snake_row.get("surprise")),
                surprise_percentage=_safe_float(snake_row.get("surprise_percentage")),
                fetched_at=fetched_at,
            )
        )
    return records


def _economic_df_to_records(
    df: pd.DataFrame,
    indicator: str,
    fetched_at: str,
    *,
    interval: str = "",
    maturity: str = "",
) -> list[EconomicIndicatorRecord]:
    """Convert an economic indicator DataFrame to EconomicIndicatorRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_economic_indicator()`` with date, value columns.
    indicator : str
        Indicator name (e.g. ``"REAL_GDP"``).
    fetched_at : str
        ISO 8601 fetch timestamp.
    interval : str
        Data interval (default: ``""``).
    maturity : str
        Bond maturity (default: ``""``).

    Returns
    -------
    list[EconomicIndicatorRecord]
        List of economic indicator records.
    """
    records: list[EconomicIndicatorRecord] = []
    for _, row in df.iterrows():
        records.append(
            EconomicIndicatorRecord(
                indicator=indicator,
                date=str(row.get("date", "")),
                value=_safe_float(row.get("value")),
                interval=interval,
                maturity=maturity,
                fetched_at=fetched_at,
            )
        )
    return records


def _forex_df_to_records(
    df: pd.DataFrame,
    from_currency: str,
    to_currency: str,
    fetched_at: str,
) -> list[ForexDailyRecord]:
    """Convert a forex daily DataFrame to ForexDailyRecord list.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from ``parse_fx_time_series()`` with date, open, high,
        low, close columns.
    from_currency : str
        Source currency code.
    to_currency : str
        Target currency code.
    fetched_at : str
        ISO 8601 fetch timestamp.

    Returns
    -------
    list[ForexDailyRecord]
        List of forex daily records.
    """
    records: list[ForexDailyRecord] = []
    for _, row in df.iterrows():
        records.append(
            ForexDailyRecord(
                from_currency=from_currency,
                to_currency=to_currency,
                date=str(row.get("date", "")),
                open=_safe_float(row.get("open")) or 0.0,
                high=_safe_float(row.get("high")) or 0.0,
                low=_safe_float(row.get("low")) or 0.0,
                close=_safe_float(row.get("close")) or 0.0,
                fetched_at=fetched_at,
            )
        )
    return records


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "AlphaVantageCollector",
    "CollectionResult",
    "CollectionSummary",
    "_camel_to_snake",
]
