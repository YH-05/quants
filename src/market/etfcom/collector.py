"""Orchestration layer for ETF.com data collection.

This module provides the ``ETFComCollector`` class that coordinates data
fetching from ``ETFComClient`` and persistence via ``ETFComStorage``.
It groups queries by update frequency (daily / weekly / monthly) and
provides ``collect_all()`` for full pipeline execution.

Update frequency mapping
------------------------
**Daily** (3 queries):
    ``fundFlowsData``, ``delayedquotes``, ``fundIntraData``

**Weekly** (6 queries):
    ``topHoldings``, ``fundPortfolioData``, ``sectorIndustryBreakdown``,
    ``fundSpreadChart``, ``fundPremiumChart``, ``fundTradabilityData``

**Monthly** (11 queries):
    ``regions``, ``countries``, ``economicDevelopment``, ``compareTicker``,
    ``fundTradabilitySummary``, ``fundPortfolioManData``,
    ``fundTaxExposuresData``, ``fundStructureData``, ``fundRankingsData``,
    ``fundPerformanceStatsData``, ``performance`` (GET)

Architecture
------------
Follows the ``AlphaVantageCollector`` / ``PolymarketCollector`` pattern:
DI-based constructor (client + storage), per-ticker error accumulation,
``CollectionResult`` / ``CollectionSummary`` reporting.

Examples
--------
>>> from market.etfcom.collector import ETFComCollector
>>> collector = ETFComCollector()
>>> summary = collector.collect_daily(["SPY", "QQQ"])
>>> summary.has_failures
False

See Also
--------
market.alphavantage.collector : Reference implementation (collect_daily pattern).
market.polymarket.collector : Reference implementation (error accumulation pattern).
market.etfcom.client : API client providing data fetch methods.
market.etfcom.storage : Storage layer for persisting collected data.
market.etfcom.models : CollectionResult / CollectionSummary dataclasses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from market.etfcom.models import (
    AllocationRecord,
    CollectionResult,
    CollectionSummary,
    FundFlowsRecord,
    HoldingRecord,
    PerformanceRecord,
    PortfolioRecord,
    QuoteRecord,
    StructureRecord,
    TickerRecord,
    TradabilityRecord,
)
from market.etfcom.storage_constants import (
    TABLE_ALLOCATIONS,
    TABLE_FUND_FLOWS,
    TABLE_HOLDINGS,
    TABLE_PERFORMANCE,
    TABLE_PORTFOLIO,
    TABLE_QUOTES,
    TABLE_STRUCTURE,
    TABLE_TICKERS,
    TABLE_TRADABILITY,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.etfcom.client import ETFComClient
    from market.etfcom.storage import ETFComStorage

logger = get_logger(__name__)


# =============================================================================
# dict -> Record converters
# =============================================================================


def _to_fund_flows_records(
    ticker: str,
    rows: list[dict[str, Any]],
    fetched_at: str,
) -> list[FundFlowsRecord]:
    """Convert parsed fund flow dicts to ``FundFlowsRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    rows : list[dict[str, Any]]
        Parsed fund flow data from ``ETFComClient.get_fund_flows()``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[FundFlowsRecord]
        Frozen dataclass records ready for storage upsert.
    """
    records: list[FundFlowsRecord] = []
    for row in rows:
        nav_date = row.get("nav_date")
        if not nav_date:
            continue
        records.append(
            FundFlowsRecord(
                ticker=ticker,
                nav_date=str(nav_date),
                nav=row.get("nav"),
                nav_change=row.get("nav_change"),
                nav_change_percent=row.get("nav_change_percent"),
                premium_discount=row.get("premium_discount"),
                fund_flows=row.get("fund_flows"),
                shares_outstanding=row.get("shares_outstanding"),
                aum=row.get("aum"),
                fetched_at=fetched_at,
            )
        )
    return records


def _to_quote_records(
    rows: list[dict[str, Any]],
    fetched_at: str,
) -> list[QuoteRecord]:
    """Convert parsed delayed quote dicts to ``QuoteRecord`` instances.

    Parameters
    ----------
    rows : list[dict[str, Any]]
        Parsed quote data from ``ETFComClient.get_delayed_quotes()``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[QuoteRecord]
        Frozen dataclass records ready for storage upsert.
    """
    records: list[QuoteRecord] = []
    for row in rows:
        ticker_val = row.get("ticker")
        date_val = row.get("last_trade_date") or row.get("quote_date")
        if not ticker_val or not date_val:
            continue
        records.append(
            QuoteRecord(
                ticker=str(ticker_val),
                quote_date=str(date_val),
                open=row.get("open"),
                high=row.get("high"),
                low=row.get("low"),
                close=row.get("close") or row.get("last_sale"),
                volume=row.get("volume"),
                bid=row.get("bid"),
                ask=row.get("ask"),
                bid_size=row.get("bid_size"),
                ask_size=row.get("ask_size"),
                fetched_at=fetched_at,
            )
        )
    return records


def _to_holding_records(
    ticker: str,
    rows: list[dict[str, Any]],
    fetched_at: str,
) -> list[HoldingRecord]:
    """Convert parsed holding dicts to ``HoldingRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    rows : list[dict[str, Any]]
        Parsed holding data from ``ETFComClient.get_holdings()``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[HoldingRecord]
        Frozen dataclass records ready for storage upsert.
    """
    records: list[HoldingRecord] = []
    for row in rows:
        holding_ticker = row.get("ticker") or row.get("holding_ticker") or "UNKNOWN"
        as_of_date = row.get("as_of_date") or fetched_at[:10]
        records.append(
            HoldingRecord(
                ticker=ticker,
                holding_ticker=str(holding_ticker),
                as_of_date=str(as_of_date),
                holding_name=row.get("holding_name") or row.get("name"),
                weight=row.get("weight"),
                market_value=row.get("market_value"),
                shares=row.get("shares"),
                fetched_at=fetched_at,
            )
        )
    return records


def _to_portfolio_records(
    ticker: str,
    data: dict[str, Any],
    fetched_at: str,
) -> list[PortfolioRecord]:
    """Convert parsed portfolio dict to ``PortfolioRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    data : dict[str, Any]
        Parsed portfolio data from ``ETFComClient.get_portfolio_data()``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[PortfolioRecord]
        Single-element list with the portfolio record (or empty if no data).
    """
    if not data:
        return []
    return [
        PortfolioRecord(
            ticker=ticker,
            pe_ratio=data.get("pe_ratio"),
            pb_ratio=data.get("pb_ratio"),
            dividend_yield=data.get("dividend_yield"),
            weighted_avg_market_cap=data.get("weighted_avg_market_cap"),
            number_of_holdings=data.get("number_of_holdings"),
            expense_ratio=data.get("expense_ratio"),
            tracking_difference=data.get("tracking_difference"),
            median_tracking_difference=data.get("median_tracking_difference"),
            as_of_date=data.get("as_of_date"),
            fetched_at=fetched_at,
        )
    ]


def _to_allocation_records(
    ticker: str,
    rows: list[dict[str, Any]],
    allocation_type: str,
    fetched_at: str,
) -> list[AllocationRecord]:
    """Convert parsed allocation dicts to ``AllocationRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    rows : list[dict[str, Any]]
        Parsed allocation data (sectors, regions, countries, or econ dev).
    allocation_type : str
        Type label: ``"sector"``, ``"region"``, ``"country"``, or
        ``"economic_development"``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[AllocationRecord]
        Frozen dataclass records ready for storage upsert.
    """
    records: list[AllocationRecord] = []
    for row in rows:
        name = row.get("name") or row.get("sector") or row.get("region") or "Unknown"
        as_of_date = row.get("as_of_date") or fetched_at[:10]
        records.append(
            AllocationRecord(
                ticker=ticker,
                allocation_type=allocation_type,
                name=str(name),
                as_of_date=str(as_of_date),
                weight=row.get("weight"),
                market_value=row.get("market_value"),
                count=row.get("count"),
                fetched_at=fetched_at,
            )
        )
    return records


def _to_tradability_records(
    ticker: str,
    data: dict[str, Any] | list[dict[str, Any]],
    fetched_at: str,
) -> list[TradabilityRecord]:
    """Convert parsed tradability data to ``TradabilityRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    data : dict[str, Any] | list[dict[str, Any]]
        Parsed tradability data. Can be a summary dict or time-series list.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[TradabilityRecord]
        Frozen dataclass records ready for storage upsert.
    """
    # If it's a summary dict, convert to single-element list
    if isinstance(data, dict):
        if not data:
            return []
        return [
            TradabilityRecord(
                ticker=ticker,
                avg_daily_volume=data.get("avg_daily_volume"),
                avg_daily_dollar_volume=data.get("avg_daily_dollar_volume"),
                median_bid_ask_spread=data.get("median_bid_ask_spread"),
                avg_bid_ask_spread=data.get("avg_bid_ask_spread"),
                creation_unit_size=data.get("creation_unit_size"),
                open_interest=data.get("open_interest"),
                short_interest=data.get("short_interest"),
                implied_liquidity=data.get("implied_liquidity"),
                block_liquidity=data.get("block_liquidity"),
                as_of_date=data.get("as_of_date"),
                fetched_at=fetched_at,
            )
        ]
    # Time-series: we only need the latest record for the summary table
    if not data:
        return []
    return [
        TradabilityRecord(
            ticker=ticker,
            avg_daily_volume=data[0].get("avg_daily_volume") or data[0].get("volume"),
            fetched_at=fetched_at,
        )
    ]


def _to_structure_records(
    ticker: str,
    data: dict[str, Any],
    fetched_at: str,
) -> list[StructureRecord]:
    """Convert parsed structure dict to ``StructureRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    data : dict[str, Any]
        Parsed structure data from ``ETFComClient.get_structure()``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[StructureRecord]
        Single-element list (or empty if no data).
    """
    if not data:
        return []
    return [
        StructureRecord(
            ticker=ticker,
            legal_structure=data.get("legal_structure"),
            fund_type=data.get("fund_type"),
            index_tracked=data.get("index_tracked"),
            replication_method=data.get("replication_method"),
            uses_derivatives=data.get("uses_derivatives"),
            securities_lending=data.get("securities_lending"),
            tax_form=data.get("tax_form"),
            as_of_date=data.get("as_of_date"),
            fetched_at=fetched_at,
        )
    ]


def _to_performance_records(
    ticker: str,
    data: dict[str, Any],
    fetched_at: str,
) -> list[PerformanceRecord]:
    """Convert parsed performance dict to ``PerformanceRecord`` instances.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol.
    data : dict[str, Any]
        Parsed performance data (from stats or GET endpoint).
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[PerformanceRecord]
        Single-element list (or empty if no data).
    """
    if not data:
        return []
    return [
        PerformanceRecord(
            ticker=ticker,
            return_1m=data.get("return_1m"),
            return_3m=data.get("return_3m"),
            return_ytd=data.get("return_ytd"),
            return_1y=data.get("return_1y"),
            return_3y=data.get("return_3y"),
            return_5y=data.get("return_5y"),
            return_10y=data.get("return_10y"),
            r_squared=data.get("r_squared"),
            beta=data.get("beta"),
            standard_deviation=data.get("standard_deviation"),
            as_of_date=data.get("as_of_date"),
            fetched_at=fetched_at,
        )
    ]


def _to_ticker_records(
    rows: list[dict[str, Any]],
    fetched_at: str,
) -> list[TickerRecord]:
    """Convert parsed ticker dicts to ``TickerRecord`` instances.

    Parameters
    ----------
    rows : list[dict[str, Any]]
        Parsed ticker data from ``ETFComClient.get_tickers()``.
    fetched_at : str
        ISO 8601 timestamp.

    Returns
    -------
    list[TickerRecord]
        Frozen dataclass records ready for storage upsert.
    """
    records: list[TickerRecord] = []
    for row in rows:
        ticker_val = row.get("ticker")
        fund_id_val = row.get("fund_id")
        if not ticker_val or fund_id_val is None:
            continue
        records.append(
            TickerRecord(
                ticker=str(ticker_val),
                fund_id=int(fund_id_val),
                name=row.get("name"),
                issuer=row.get("issuer"),
                asset_class=row.get("asset_class"),
                inception_date=row.get("inception_date"),
                segment=row.get("segment"),
                fetched_at=fetched_at,
            )
        )
    return records


# =============================================================================
# ETFComCollector class
# =============================================================================


class ETFComCollector:
    """Orchestration layer for ETF.com Client -> Storage data pipeline.

    Groups queries by update frequency (daily / weekly / monthly) and
    provides ``collect_all()`` for full pipeline execution.

    Parameters
    ----------
    client : ETFComClient | None
        Pre-configured client instance. If ``None``, a new client is
        created with default settings.
    storage : ETFComStorage | None
        Pre-configured storage instance. If ``None``, a new storage is
        created via ``get_etfcom_storage()``.

    Examples
    --------
    >>> collector = ETFComCollector()
    >>> summary = collector.collect_daily(["SPY"])
    >>> summary.successful
    1

    >>> collector = ETFComCollector(client=mock_client, storage=mock_storage)
    >>> summary = collector.collect_all(["SPY", "QQQ"])
    """

    def __init__(
        self,
        client: ETFComClient | None = None,
        storage: ETFComStorage | None = None,
    ) -> None:
        """Initialize collector with optional dependency injection.

        Parameters
        ----------
        client : ETFComClient | None
            Pre-configured client. If ``None``, creates a new client.
        storage : ETFComStorage | None
            Pre-configured storage. If ``None``, creates a new storage.
        """
        if client is not None:
            self._client = client
        else:
            from market.etfcom.client import ETFComClient

            self._client = ETFComClient()

        if storage is not None:
            self._storage = storage
        else:
            from market.etfcom.storage import get_etfcom_storage

            self._storage = get_etfcom_storage()

        logger.info("ETFComCollector initialized")

    # ------------------------------------------------------------------
    # Tickers
    # ------------------------------------------------------------------

    def collect_tickers(self) -> CollectionSummary:
        """Collect ticker master list and persist to storage.

        Fetches the full ETF ticker list (~5,100 tickers) via
        ``ETFComClient.get_tickers()`` and upserts into
        ``etfcom_tickers``.

        Returns
        -------
        CollectionSummary
            Summary with a single ``CollectionResult`` for the tickers table.
        """
        logger.info("Collecting tickers")
        fetched_at = datetime.now(tz=UTC).isoformat()
        results: list[CollectionResult] = []

        try:
            raw = self._client.get_tickers()
            records = _to_ticker_records(raw, fetched_at)
            count = self._storage.upsert_tickers(records)
            results.append(
                CollectionResult(
                    ticker="__ALL__",
                    table=TABLE_TICKERS,
                    rows_upserted=count,
                    success=True,
                )
            )
            logger.info("Tickers collected", count=count)
        except Exception as exc:
            logger.error("Failed to collect tickers", exc_info=True)
            results.append(
                CollectionResult(
                    ticker="__ALL__",
                    table=TABLE_TICKERS,
                    rows_upserted=0,
                    success=False,
                    error_message=str(exc),
                )
            )

        return _build_summary(results)

    # ------------------------------------------------------------------
    # Daily collection (3 queries)
    # ------------------------------------------------------------------

    def collect_daily(self, tickers: list[str]) -> CollectionSummary:
        """Collect daily-frequency data for the given tickers.

        Executes 3 queries per ticker:

        1. ``fundFlowsData`` -> ``etfcom_fund_flows``
        2. ``delayedquotes`` -> ``etfcom_quotes``
        3. ``fundIntraData`` -> (logged, not separately stored)

        Parameters
        ----------
        tickers : list[str]
            List of ETF ticker symbols to collect.

        Returns
        -------
        CollectionSummary
            Aggregated summary of all collection results.
        """
        logger.info("Collecting daily data", ticker_count=len(tickers))
        results: list[CollectionResult] = []
        fetched_at = datetime.now(tz=UTC).isoformat()

        for ticker in tickers:
            # 1. Fund flows
            results.append(self._collect_fund_flows(ticker, fetched_at))
            # 2. Delayed quotes
            results.append(self._collect_delayed_quotes(ticker, fetched_at))
            # 3. Intraday data (logged but shares table with quotes/flows)
            results.append(self._collect_intra_data(ticker, fetched_at))

        return _build_summary(results)

    # ------------------------------------------------------------------
    # Weekly collection (6 queries)
    # ------------------------------------------------------------------

    def collect_weekly(self, tickers: list[str]) -> CollectionSummary:
        """Collect weekly-frequency data for the given tickers.

        Executes 6 queries per ticker:

        1. ``topHoldings`` -> ``etfcom_holdings``
        2. ``fundPortfolioData`` -> ``etfcom_portfolio``
        3. ``sectorIndustryBreakdown`` -> ``etfcom_allocations``
        4. ``fundSpreadChart`` -> (logged, spread data)
        5. ``fundPremiumChart`` -> (logged, premium data)
        6. ``fundTradabilityData`` -> ``etfcom_tradability``

        Parameters
        ----------
        tickers : list[str]
            List of ETF ticker symbols to collect.

        Returns
        -------
        CollectionSummary
            Aggregated summary of all collection results.
        """
        logger.info("Collecting weekly data", ticker_count=len(tickers))
        results: list[CollectionResult] = []
        fetched_at = datetime.now(tz=UTC).isoformat()

        for ticker in tickers:
            results.append(self._collect_holdings(ticker, fetched_at))
            results.append(self._collect_portfolio(ticker, fetched_at))
            results.append(self._collect_sector_breakdown(ticker, fetched_at))
            results.append(self._collect_spread_chart(ticker, fetched_at))
            results.append(self._collect_premium_chart(ticker, fetched_at))
            results.append(self._collect_tradability(ticker, fetched_at))

        return _build_summary(results)

    # ------------------------------------------------------------------
    # Monthly collection (11 queries)
    # ------------------------------------------------------------------

    def collect_monthly(self, tickers: list[str]) -> CollectionSummary:
        """Collect monthly-frequency data for the given tickers.

        Executes 11 queries per ticker:

        1. ``regions`` -> ``etfcom_allocations`` (type=region)
        2. ``countries`` -> ``etfcom_allocations`` (type=country)
        3. ``economicDevelopment`` -> ``etfcom_allocations`` (type=economic_development)
        4. ``compareTicker`` -> (logged, comparison data)
        5. ``fundTradabilitySummary`` -> ``etfcom_tradability``
        6. ``fundPortfolioManData`` -> ``etfcom_portfolio`` (management overlay)
        7. ``fundTaxExposuresData`` -> (logged, tax data)
        8. ``fundStructureData`` -> ``etfcom_structure``
        9. ``fundRankingsData`` -> (logged, rankings data)
        10. ``fundPerformanceStatsData`` -> ``etfcom_performance``
        11. ``performance`` (GET) -> ``etfcom_performance``

        Parameters
        ----------
        tickers : list[str]
            List of ETF ticker symbols to collect.

        Returns
        -------
        CollectionSummary
            Aggregated summary of all collection results.
        """
        logger.info("Collecting monthly data", ticker_count=len(tickers))
        results: list[CollectionResult] = []
        fetched_at = datetime.now(tz=UTC).isoformat()

        for ticker in tickers:
            results.append(self._collect_regions(ticker, fetched_at))
            results.append(self._collect_countries(ticker, fetched_at))
            results.append(self._collect_econ_dev(ticker, fetched_at))
            results.append(self._collect_compare_ticker(ticker, fetched_at))
            results.append(self._collect_tradability_summary(ticker, fetched_at))
            results.append(self._collect_portfolio_management(ticker, fetched_at))
            results.append(self._collect_tax_exposures(ticker, fetched_at))
            results.append(self._collect_structure(ticker, fetched_at))
            results.append(self._collect_rankings(ticker, fetched_at))
            results.append(self._collect_performance_stats(ticker, fetched_at))
            results.append(self._collect_performance(ticker, fetched_at))

        return _build_summary(results)

    # ------------------------------------------------------------------
    # Full collection
    # ------------------------------------------------------------------

    def collect_all(self, tickers: list[str]) -> CollectionSummary:
        """Execute full collection pipeline: tickers -> daily -> weekly -> monthly.

        Parameters
        ----------
        tickers : list[str]
            List of ETF ticker symbols to collect.

        Returns
        -------
        CollectionSummary
            Aggregated summary of all collection results.
        """
        logger.info("Starting full ETFCom collection", ticker_count=len(tickers))

        all_results: list[CollectionResult] = []

        # 1. Tickers
        ticker_summary = self.collect_tickers()
        all_results.extend(ticker_summary.results)

        # 2. Daily
        daily_summary = self.collect_daily(tickers)
        all_results.extend(daily_summary.results)

        # 3. Weekly
        weekly_summary = self.collect_weekly(tickers)
        all_results.extend(weekly_summary.results)

        # 4. Monthly
        monthly_summary = self.collect_monthly(tickers)
        all_results.extend(monthly_summary.results)

        summary = _build_summary(all_results)

        logger.info(
            "Full ETFCom collection completed",
            total_tickers=summary.total_tickers,
            successful=summary.successful,
            failed=summary.failed,
            total_rows=summary.total_rows,
        )

        return summary

    # ==================================================================
    # Private helpers — each wraps a single client call + storage upsert
    # ==================================================================

    def _collect_fund_flows(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect fund flows for a single ticker."""
        try:
            raw = self._client.get_fund_flows(ticker)
            records = _to_fund_flows_records(ticker, raw, fetched_at)
            count = self._storage.upsert_fund_flows(records)
            logger.debug("Fund flows collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_FUND_FLOWS,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect fund flows",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_FUND_FLOWS,
                success=False,
                error_message=str(exc),
            )

    def _collect_delayed_quotes(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect delayed quotes for a single ticker."""
        try:
            raw = self._client.get_delayed_quotes(ticker)
            records = _to_quote_records(raw, fetched_at)
            count = self._storage.upsert_quotes(records)
            logger.debug("Quotes collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_QUOTES,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect delayed quotes",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_QUOTES,
                success=False,
                error_message=str(exc),
            )

    def _collect_intra_data(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect intraday data for a single ticker.

        Intraday data is fetched and logged but shares the fund_flows
        table pattern. The data is logged for monitoring but the raw
        intraday records are not persisted to a separate table.
        """
        try:
            raw = self._client.get_intra_data(ticker)
            count = len(raw) if raw else 0
            logger.debug("Intra data collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_intra_data",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect intra data",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_intra_data",
                success=False,
                error_message=str(exc),
            )

    def _collect_holdings(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect top holdings for a single ticker."""
        try:
            raw = self._client.get_holdings(ticker)
            records = _to_holding_records(ticker, raw, fetched_at)
            count = self._storage.upsert_holdings(records)
            logger.debug("Holdings collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_HOLDINGS,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect holdings",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_HOLDINGS,
                success=False,
                error_message=str(exc),
            )

    def _collect_portfolio(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect portfolio data for a single ticker."""
        try:
            raw = self._client.get_portfolio_data(ticker)
            records = _to_portfolio_records(ticker, raw, fetched_at)
            count = self._storage.upsert_portfolio(records)
            logger.debug("Portfolio collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_PORTFOLIO,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect portfolio",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_PORTFOLIO,
                success=False,
                error_message=str(exc),
            )

    def _collect_sector_breakdown(
        self, ticker: str, fetched_at: str
    ) -> CollectionResult:
        """Collect sector breakdown for a single ticker."""
        try:
            raw = self._client.get_sector_breakdown(ticker)
            records = _to_allocation_records(ticker, raw, "sector", fetched_at)
            count = self._storage.upsert_allocations(records)
            logger.debug("Sector breakdown collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect sector breakdown",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                success=False,
                error_message=str(exc),
            )

    def _collect_spread_chart(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect spread chart data for a single ticker."""
        try:
            raw = self._client.get_spread_chart(ticker)
            count = len(raw) if raw else 0
            logger.debug("Spread chart collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_spread_chart",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect spread chart",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_spread_chart",
                success=False,
                error_message=str(exc),
            )

    def _collect_premium_chart(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect premium chart data for a single ticker."""
        try:
            raw = self._client.get_premium_chart(ticker)
            count = len(raw) if raw else 0
            logger.debug("Premium chart collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_premium_chart",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect premium chart",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_premium_chart",
                success=False,
                error_message=str(exc),
            )

    def _collect_tradability(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect tradability time-series data for a single ticker."""
        try:
            raw = self._client.get_tradability(ticker)
            records = _to_tradability_records(ticker, raw, fetched_at)
            count = self._storage.upsert_tradability(records)
            logger.debug("Tradability collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_TRADABILITY,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect tradability",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_TRADABILITY,
                success=False,
                error_message=str(exc),
            )

    def _collect_regions(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect regional allocation for a single ticker."""
        try:
            raw = self._client.get_regions(ticker)
            records = _to_allocation_records(ticker, raw, "region", fetched_at)
            count = self._storage.upsert_allocations(records)
            logger.debug("Regions collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect regions",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                success=False,
                error_message=str(exc),
            )

    def _collect_countries(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect country allocation for a single ticker."""
        try:
            raw = self._client.get_countries(ticker)
            records = _to_allocation_records(ticker, raw, "country", fetched_at)
            count = self._storage.upsert_allocations(records)
            logger.debug("Countries collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect countries",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                success=False,
                error_message=str(exc),
            )

    def _collect_econ_dev(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect economic development classification for a single ticker."""
        try:
            raw = self._client.get_econ_dev(ticker)
            records = _to_allocation_records(
                ticker, raw, "economic_development", fetched_at
            )
            count = self._storage.upsert_allocations(records)
            logger.debug("Econ dev collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect econ dev",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_ALLOCATIONS,
                success=False,
                error_message=str(exc),
            )

    def _collect_compare_ticker(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect competing ETF comparison data for a single ticker."""
        try:
            raw = self._client.get_compare_ticker(ticker)
            count = len(raw) if raw else 0
            logger.debug("Compare ticker collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_compare_ticker",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect compare ticker",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_compare_ticker",
                success=False,
                error_message=str(exc),
            )

    def _collect_tradability_summary(
        self, ticker: str, fetched_at: str
    ) -> CollectionResult:
        """Collect tradability summary for a single ticker."""
        try:
            raw = self._client.get_tradability_summary(ticker)
            records = _to_tradability_records(ticker, raw, fetched_at)
            count = self._storage.upsert_tradability(records)
            logger.debug("Tradability summary collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_TRADABILITY,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect tradability summary",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_TRADABILITY,
                success=False,
                error_message=str(exc),
            )

    def _collect_portfolio_management(
        self, ticker: str, fetched_at: str
    ) -> CollectionResult:
        """Collect portfolio management data for a single ticker."""
        try:
            raw = self._client.get_portfolio_management(ticker)
            count = 1 if raw else 0
            logger.debug("Portfolio management collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_portfolio_management",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect portfolio management",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_portfolio_management",
                success=False,
                error_message=str(exc),
            )

    def _collect_tax_exposures(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect tax exposure data for a single ticker."""
        try:
            raw = self._client.get_tax_exposures(ticker)
            count = 1 if raw else 0
            logger.debug("Tax exposures collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_tax_exposures",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect tax exposures",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_tax_exposures",
                success=False,
                error_message=str(exc),
            )

    def _collect_structure(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect fund structure data for a single ticker."""
        try:
            raw = self._client.get_structure(ticker)
            records = _to_structure_records(ticker, raw, fetched_at)
            count = self._storage.upsert_structure(records)
            logger.debug("Structure collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_STRUCTURE,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect structure",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_STRUCTURE,
                success=False,
                error_message=str(exc),
            )

    def _collect_rankings(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect fund rankings for a single ticker."""
        try:
            raw = self._client.get_rankings(ticker)
            count = 1 if raw else 0
            logger.debug("Rankings collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table="etfcom_rankings",
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect rankings",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table="etfcom_rankings",
                success=False,
                error_message=str(exc),
            )

    def _collect_performance_stats(
        self, ticker: str, fetched_at: str
    ) -> CollectionResult:
        """Collect performance statistics for a single ticker."""
        try:
            raw = self._client.get_performance_stats(ticker)
            records = _to_performance_records(ticker, raw, fetched_at)
            count = self._storage.upsert_performance(records)
            logger.debug("Performance stats collected", ticker=ticker, count=count)
            return CollectionResult(
                ticker=ticker,
                table=TABLE_PERFORMANCE,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect performance stats",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_PERFORMANCE,
                success=False,
                error_message=str(exc),
            )

    def _collect_performance(self, ticker: str, fetched_at: str) -> CollectionResult:
        """Collect performance returns via the GET endpoint.

        This requires a fund_id lookup from the tickers table. If the
        fund_id cannot be resolved, the collection is skipped with a
        success result (0 rows).
        """
        try:
            # Look up fund_id from tickers table
            tickers_df = self._storage.get_tickers()
            if tickers_df.empty or "ticker" not in tickers_df.columns:
                logger.warning(
                    "No tickers data in storage, skipping performance GET",
                    ticker=ticker,
                )
                return CollectionResult(
                    ticker=ticker,
                    table=TABLE_PERFORMANCE,
                    rows_upserted=0,
                    success=True,
                )

            fund_id_row = tickers_df[tickers_df["ticker"] == ticker]
            if fund_id_row.empty:
                logger.warning(
                    "No fund_id found for ticker, skipping performance GET",
                    ticker=ticker,
                )
                return CollectionResult(
                    ticker=ticker,
                    table=TABLE_PERFORMANCE,
                    rows_upserted=0,
                    success=True,
                )

            fund_id = int(fund_id_row.iloc[0]["fund_id"])
            raw = self._client.get_performance(fund_id)
            records = _to_performance_records(ticker, raw, fetched_at)
            count = self._storage.upsert_performance(records)
            logger.debug(
                "Performance GET collected",
                ticker=ticker,
                fund_id=fund_id,
                count=count,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_PERFORMANCE,
                rows_upserted=count,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "Failed to collect performance GET",
                ticker=ticker,
                exc_info=True,
            )
            return CollectionResult(
                ticker=ticker,
                table=TABLE_PERFORMANCE,
                success=False,
                error_message=str(exc),
            )


# =============================================================================
# Summary builder
# =============================================================================


def _build_summary(results: list[CollectionResult]) -> CollectionSummary:
    """Build a ``CollectionSummary`` from a list of results.

    Parameters
    ----------
    results : list[CollectionResult]
        List of individual collection results.

    Returns
    -------
    CollectionSummary
        Aggregated summary with counts.
    """
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    total_rows = sum(r.rows_upserted for r in results)
    unique_tickers = len({r.ticker for r in results})

    return CollectionSummary(
        results=tuple(results),
        total_tickers=unique_tickers,
        successful=successful,
        failed=failed,
        total_rows=total_rows,
    )


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "ETFComCollector",
]
