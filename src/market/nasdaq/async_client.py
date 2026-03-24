"""Async wrapper for the NASDAQ API client.

This module provides ``AsyncNasdaqClient``, a thin asynchronous wrapper
around :class:`~market.nasdaq.client.NasdaqClient` that uses
``asyncio.to_thread()`` to run synchronous methods in a thread-pool
executor.  This enables non-blocking access to all NASDAQ API endpoints
in an ``async`` / ``await`` context without duplicating business logic.

The wrapper preserves the full public API of ``NasdaqClient`` (15 endpoint
methods + ``fetch_for_symbols`` batch helper) and supports the async
context manager protocol (``async with``).

Design Decisions
----------------
- **asyncio.to_thread()** is preferred over ``loop.run_in_executor()``
  because it is simpler, requires Python 3.9+, and copies the current
  context automatically.
- **No business-logic duplication**: all parsing, caching, and validation
  remain in the synchronous ``NasdaqClient``.
- **Constructor DI**: an existing ``NasdaqClient`` can be injected, or
  one is created automatically from keyword arguments.

Examples
--------
>>> from market.nasdaq.async_client import AsyncNasdaqClient
>>> async with AsyncNasdaqClient() as client:
...     movers = await client.get_market_movers()
...     records = await client.get_short_interest("AAPL")

>>> from market.nasdaq.client import NasdaqClient
>>> sync_client = NasdaqClient()
>>> async_client = AsyncNasdaqClient(client=sync_client)
>>> result = await async_client.get_earnings_calendar(date="2026-01-30")
>>> await async_client.aclose()

See Also
--------
market.nasdaq.client : Synchronous NasdaqClient that this module wraps.
market.nasdaq.client_types : Record dataclasses used by both clients.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Literal

from market.nasdaq.client import NasdaqClient
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.nasdaq.client_types import (
        AnalystRatings,
        AnalystSummary,
        DividendCalendarRecord,
        DividendRecord,
        EarningsDate,
        EarningsForecast,
        EarningsRecord,
        EtfRecord,
        FinancialStatement,
        InsiderTrade,
        InstitutionalHolding,
        IpoRecord,
        MarketMover,
        NasdaqFetchOptions,
        ShortInterestRecord,
        SplitRecord,
        TargetPrice,
    )

logger = get_logger(__name__)


class AsyncNasdaqClient:
    """Async wrapper over :class:`~market.nasdaq.client.NasdaqClient`.

    Delegates every public method to the synchronous ``NasdaqClient`` via
    ``asyncio.to_thread()``, enabling non-blocking access in async contexts.

    Parameters
    ----------
    client : NasdaqClient | None
        An existing synchronous client instance.  If ``None``, a new
        ``NasdaqClient`` is created from the remaining *kwargs*.
    **kwargs : Any
        Keyword arguments forwarded to ``NasdaqClient()`` when *client*
        is ``None``.  Common options include ``session``, ``config``,
        ``retry_config``, and ``cache``.

    Examples
    --------
    >>> async with AsyncNasdaqClient() as client:
    ...     movers = await client.get_market_movers()

    >>> from market.nasdaq.client import NasdaqClient
    >>> sync = NasdaqClient()
    >>> async_cl = AsyncNasdaqClient(client=sync)
    >>> await async_cl.aclose()
    """

    def __init__(
        self,
        client: NasdaqClient | None = None,
        **kwargs: Any,
    ) -> None:
        self._client: NasdaqClient = client or NasdaqClient(**kwargs)
        logger.info("AsyncNasdaqClient initialized")

    # =========================================================================
    # Async Context Manager
    # =========================================================================

    async def __aenter__(self) -> AsyncNasdaqClient:
        """Enter the async context manager.

        Returns
        -------
        AsyncNasdaqClient
            Self for use in ``async with`` statement.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async context manager and release resources.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised.
        exc_val : BaseException | None
            Exception instance if an exception was raised.
        exc_tb : Any
            Traceback if an exception was raised.
        """
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying synchronous client and release resources."""
        self._client.close()
        logger.debug("AsyncNasdaqClient closed")

    # =========================================================================
    # Calendar Endpoints
    # =========================================================================

    async def get_earnings_calendar(
        self,
        date: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[EarningsRecord]:
        """Fetch earnings calendar data for a specific date.

        Parameters
        ----------
        date : str
            Date string (e.g. ``"2026-01-30"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[EarningsRecord]
            List of earnings records for the given date.
        """
        return await asyncio.to_thread(
            self._client.get_earnings_calendar, date=date, options=options
        )

    async def get_dividends_calendar(
        self,
        date: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[DividendCalendarRecord]:
        """Fetch dividends calendar data for a specific date.

        Parameters
        ----------
        date : str
            Date string (e.g. ``"2026-02-07"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[DividendCalendarRecord]
            List of dividend records for the given date.
        """
        return await asyncio.to_thread(
            self._client.get_dividends_calendar, date=date, options=options
        )

    async def get_splits_calendar(
        self,
        date: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[SplitRecord]:
        """Fetch stock splits calendar data for a specific date.

        Parameters
        ----------
        date : str
            Date string (e.g. ``"2024-06-10"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[SplitRecord]
            List of split records for the given date.
        """
        return await asyncio.to_thread(
            self._client.get_splits_calendar, date=date, options=options
        )

    async def get_ipo_calendar(
        self,
        year_month: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[IpoRecord]:
        """Fetch IPO calendar data for a specific year-month.

        Parameters
        ----------
        year_month : str
            Year-month string (e.g. ``"2026-03"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[IpoRecord]
            List of IPO records for the given year-month.
        """
        return await asyncio.to_thread(
            self._client.get_ipo_calendar, year_month=year_month, options=options
        )

    # =========================================================================
    # Market Movers / ETF Endpoints
    # =========================================================================

    async def get_market_movers(
        self,
        options: NasdaqFetchOptions | None = None,
    ) -> dict[str, list[MarketMover]]:
        """Fetch market movers data (gainers, losers, most active).

        Parameters
        ----------
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, list[MarketMover]]
            A dictionary keyed by section name.
        """
        return await asyncio.to_thread(self._client.get_market_movers, options=options)

    async def get_etf_screener(
        self,
        options: NasdaqFetchOptions | None = None,
    ) -> list[EtfRecord]:
        """Fetch ETF screener data.

        Parameters
        ----------
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[EtfRecord]
            List of ETF records from the screener.
        """
        return await asyncio.to_thread(self._client.get_etf_screener, options=options)

    # =========================================================================
    # Quote Data Endpoints
    # =========================================================================

    async def get_short_interest(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[ShortInterestRecord]:
        """Fetch short interest data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[ShortInterestRecord]
            List of short interest records.
        """
        return await asyncio.to_thread(
            self._client.get_short_interest, symbol, options=options
        )

    async def get_dividend_history(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[DividendRecord]:
        """Fetch dividend history data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[DividendRecord]
            List of dividend history records.
        """
        return await asyncio.to_thread(
            self._client.get_dividend_history, symbol, options=options
        )

    # =========================================================================
    # Company Data Endpoints
    # =========================================================================

    async def get_insider_trades(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[InsiderTrade]:
        """Fetch insider trades data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[InsiderTrade]
            List of insider trade records.
        """
        return await asyncio.to_thread(
            self._client.get_insider_trades, symbol, options=options
        )

    async def get_institutional_holdings(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> list[InstitutionalHolding]:
        """Fetch institutional holdings data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[InstitutionalHolding]
            List of institutional holding records.
        """
        return await asyncio.to_thread(
            self._client.get_institutional_holdings, symbol, options=options
        )

    async def get_financials(
        self,
        symbol: str,
        frequency: Literal["annual", "quarterly"] = "annual",
        options: NasdaqFetchOptions | None = None,
    ) -> FinancialStatement:
        """Fetch financial statements data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        frequency : Literal["annual", "quarterly"]
            Data frequency (``"annual"`` or ``"quarterly"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        FinancialStatement
            Financial statements with income, balance sheet, and cash flow.
        """
        return await asyncio.to_thread(
            self._client.get_financials, symbol, frequency=frequency, options=options
        )

    # =========================================================================
    # Analyst Endpoints
    # =========================================================================

    async def get_earnings_forecast(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> EarningsForecast:
        """Fetch earnings forecast data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        EarningsForecast
            Earnings forecast with yearly and quarterly periods.
        """
        return await asyncio.to_thread(
            self._client.get_earnings_forecast, symbol, options=options
        )

    async def get_analyst_ratings(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> AnalystRatings:
        """Fetch analyst ratings data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        AnalystRatings
            Analyst ratings with history.
        """
        return await asyncio.to_thread(
            self._client.get_analyst_ratings, symbol, options=options
        )

    async def get_target_price(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> TargetPrice:
        """Fetch analyst target price data for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        TargetPrice
            Target price with high/low/mean/median.
        """
        return await asyncio.to_thread(
            self._client.get_target_price, symbol, options=options
        )

    async def get_earnings_date(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> EarningsDate:
        """Fetch upcoming earnings date information for a symbol.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        EarningsDate
            Earnings date information.
        """
        return await asyncio.to_thread(
            self._client.get_earnings_date, symbol, options=options
        )

    async def get_analyst_summary(
        self,
        symbol: str,
        options: NasdaqFetchOptions | None = None,
    ) -> AnalystSummary:
        """Fetch aggregated analyst data for a symbol.

        Calls the synchronous ``get_analyst_summary()`` which internally
        fetches forecast, ratings, target price, and earnings date.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. ``"AAPL"``).
        options : NasdaqFetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        AnalystSummary
            Aggregated analyst data.
        """
        return await asyncio.to_thread(
            self._client.get_analyst_summary, symbol, options=options
        )

    # =========================================================================
    # Batch Helpers
    # =========================================================================

    async def fetch_for_symbols(
        self,
        symbols: list[str],
        method_name: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch data for multiple symbols using a specified endpoint method.

        Delegates to the synchronous ``fetch_for_symbols()`` via
        ``asyncio.to_thread()``.  The batch iteration runs in a single
        thread to honour the session's polite delay between requests.

        Parameters
        ----------
        symbols : list[str]
            Ticker symbols to fetch.
        method_name : str
            Name of a ``NasdaqClient`` method that accepts ``symbol``
            as its first positional argument.
        **kwargs : Any
            Additional keyword arguments forwarded to every call.

        Returns
        -------
        dict[str, Any]
            Mapping of symbol -> result for each successful fetch.
        """
        return await asyncio.to_thread(
            self._client.fetch_for_symbols, symbols, method_name, **kwargs
        )


__all__ = ["AsyncNasdaqClient"]
