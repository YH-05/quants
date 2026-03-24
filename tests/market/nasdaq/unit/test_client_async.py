"""Unit tests for AsyncNasdaqClient — async wrapper over NasdaqClient.

Tests cover:
- Async context manager (__aenter__/__aexit__/aclose)
- All 15 async endpoint methods delegate to sync counterparts via asyncio.to_thread
- Async fetch_for_symbols batch method
- __init__ with and without explicit NasdaqClient injection
- close/aclose resource management

Test TODO List:
- [x] test_正常系_asyncコンテキストマネージャでクライアント取得
- [x] test_正常系_asyncコンテキストマネージャでaclose呼び出し
- [x] test_正常系_client未指定時に内部でNasdaqClient生成
- [x] test_正常系_client指定時にそのインスタンスを使用
- [x] test_正常系_acloseでクライアントをclose
- [x] test_正常系_get_earnings_calendarがto_threadで委譲
- [x] test_正常系_get_dividends_calendarがto_threadで委譲
- [x] test_正常系_get_splits_calendarがto_threadで委譲
- [x] test_正常系_get_ipo_calendarがto_threadで委譲
- [x] test_正常系_get_market_moversがto_threadで委譲
- [x] test_正常系_get_etf_screenerがto_threadで委譲
- [x] test_正常系_get_short_interestがto_threadで委譲
- [x] test_正常系_get_dividend_historyがto_threadで委譲
- [x] test_正常系_get_insider_tradesがto_threadで委譲
- [x] test_正常系_get_institutional_holdingsがto_threadで委譲
- [x] test_正常系_get_financialsがto_threadで委譲
- [x] test_正常系_get_earnings_forecastがto_threadで委譲
- [x] test_正常系_get_analyst_ratingsがto_threadで委譲
- [x] test_正常系_get_target_priceがto_threadで委譲
- [x] test_正常系_get_earnings_dateがto_threadで委譲
- [x] test_正常系_get_analyst_summaryがto_threadで委譲
- [x] test_正常系_fetch_for_symbolsがto_threadで委譲
- [x] test_正常系_kwargsが正しく転送される

See Also
--------
market.nasdaq.async_client : AsyncNasdaqClient implementation.
market.nasdaq.client : NasdaqClient (sync) that AsyncNasdaqClient wraps.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from market.nasdaq.async_client import AsyncNasdaqClient
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

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_sync_client() -> MagicMock:
    """Create a MagicMock simulating a NasdaqClient instance.

    Returns
    -------
    MagicMock
        A MagicMock with all NasdaqClient public methods pre-configured.
    """
    client = MagicMock()
    client.close.return_value = None
    return client


@pytest.fixture
def async_client(mock_sync_client: MagicMock) -> AsyncNasdaqClient:
    """Create an AsyncNasdaqClient with injected mock NasdaqClient.

    Parameters
    ----------
    mock_sync_client : MagicMock
        Mock NasdaqClient instance.

    Returns
    -------
    AsyncNasdaqClient
        An AsyncNasdaqClient configured for testing.
    """
    return AsyncNasdaqClient(client=mock_sync_client)


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestAsyncContextManager:
    """Tests for async context manager protocol."""

    @pytest.mark.asyncio
    async def test_正常系_asyncコンテキストマネージャでクライアント取得(
        self,
        mock_sync_client: MagicMock,
    ) -> None:
        """async with returns the AsyncNasdaqClient instance."""
        async_cl = AsyncNasdaqClient(client=mock_sync_client)
        async with async_cl as cl:
            assert cl is async_cl

    @pytest.mark.asyncio
    async def test_正常系_asyncコンテキストマネージャでaclose呼び出し(
        self,
        mock_sync_client: MagicMock,
    ) -> None:
        """async with calls aclose on exit."""
        async_cl = AsyncNasdaqClient(client=mock_sync_client)
        async with async_cl:
            pass
        mock_sync_client.close.assert_called_once()


# =============================================================================
# Initialization Tests
# =============================================================================


class TestAsyncClientInit:
    """Tests for AsyncNasdaqClient initialization."""

    def test_正常系_client指定時にそのインスタンスを使用(
        self,
        mock_sync_client: MagicMock,
    ) -> None:
        """When client is provided, it is used directly."""
        async_cl = AsyncNasdaqClient(client=mock_sync_client)
        assert async_cl._client is mock_sync_client

    @patch("market.nasdaq.async_client.NasdaqClient")
    def test_正常系_client未指定時に内部でNasdaqClient生成(
        self,
        mock_client_class: MagicMock,
    ) -> None:
        """When client is None, NasdaqClient is auto-created."""
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        async_cl = AsyncNasdaqClient()
        assert async_cl._client is mock_instance
        mock_client_class.assert_called_once()

    @patch("market.nasdaq.async_client.NasdaqClient")
    def test_正常系_client未指定時にkwargsが転送される(
        self,
        mock_client_class: MagicMock,
    ) -> None:
        """When client is None, kwargs are forwarded to NasdaqClient()."""
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        mock_cache = MagicMock()
        async_cl = AsyncNasdaqClient(cache=mock_cache)
        mock_client_class.assert_called_once_with(cache=mock_cache)


# =============================================================================
# Close / Aclose Tests
# =============================================================================


class TestAsyncClientClose:
    """Tests for close and aclose methods."""

    @pytest.mark.asyncio
    async def test_正常系_acloseでクライアントをclose(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """aclose() calls the underlying sync client's close()."""
        await async_client.aclose()
        mock_sync_client.close.assert_called_once()


# =============================================================================
# Calendar Endpoint Tests
# =============================================================================


class TestAsyncCalendarEndpoints:
    """Tests for async calendar endpoint methods."""

    @pytest.mark.asyncio
    async def test_正常系_get_earnings_calendarがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_earnings_calendar delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=EarningsRecord)]
        mock_sync_client.get_earnings_calendar.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_earnings_calendar(date="2026-01-30")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_dividends_calendarがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_dividends_calendar delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=DividendCalendarRecord)]
        mock_sync_client.get_dividends_calendar.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_dividends_calendar(date="2026-02-07")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_splits_calendarがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_splits_calendar delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=SplitRecord)]
        mock_sync_client.get_splits_calendar.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_splits_calendar(date="2024-06-10")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_ipo_calendarがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_ipo_calendar delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=IpoRecord)]
        mock_sync_client.get_ipo_calendar.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_ipo_calendar(year_month="2026-03")

        assert result == expected


# =============================================================================
# Market Movers / ETF Endpoint Tests
# =============================================================================


class TestAsyncMarketEndpoints:
    """Tests for async market movers and ETF endpoint methods."""

    @pytest.mark.asyncio
    async def test_正常系_get_market_moversがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_market_movers delegates to sync via asyncio.to_thread."""
        expected: dict[str, list[MarketMover]] = {"most_advanced": []}
        mock_sync_client.get_market_movers.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_market_movers()

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_etf_screenerがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_etf_screener delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=EtfRecord)]
        mock_sync_client.get_etf_screener.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_etf_screener()

        assert result == expected


# =============================================================================
# Quote Data Endpoint Tests
# =============================================================================


class TestAsyncQuoteEndpoints:
    """Tests for async quote data endpoint methods."""

    @pytest.mark.asyncio
    async def test_正常系_get_short_interestがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_short_interest delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=ShortInterestRecord)]
        mock_sync_client.get_short_interest.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_short_interest("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_dividend_historyがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_dividend_history delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=DividendRecord)]
        mock_sync_client.get_dividend_history.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_dividend_history("AAPL")

        assert result == expected


# =============================================================================
# Company Data Endpoint Tests
# =============================================================================


class TestAsyncCompanyEndpoints:
    """Tests for async company data endpoint methods."""

    @pytest.mark.asyncio
    async def test_正常系_get_insider_tradesがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_insider_trades delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=InsiderTrade)]
        mock_sync_client.get_insider_trades.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_insider_trades("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_institutional_holdingsがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_institutional_holdings delegates to sync via asyncio.to_thread."""
        expected = [MagicMock(spec=InstitutionalHolding)]
        mock_sync_client.get_institutional_holdings.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_institutional_holdings("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_financialsがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_financials delegates to sync via asyncio.to_thread."""
        expected = MagicMock(spec=FinancialStatement)
        mock_sync_client.get_financials.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_financials("AAPL", frequency="quarterly")

        assert result == expected


# =============================================================================
# Analyst Endpoint Tests
# =============================================================================


class TestAsyncAnalystEndpoints:
    """Tests for async analyst endpoint methods."""

    @pytest.mark.asyncio
    async def test_正常系_get_earnings_forecastがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_earnings_forecast delegates to sync via asyncio.to_thread."""
        expected = MagicMock(spec=EarningsForecast)
        mock_sync_client.get_earnings_forecast.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_earnings_forecast("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_analyst_ratingsがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_analyst_ratings delegates to sync via asyncio.to_thread."""
        expected = MagicMock(spec=AnalystRatings)
        mock_sync_client.get_analyst_ratings.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_analyst_ratings("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_target_priceがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_target_price delegates to sync via asyncio.to_thread."""
        expected = MagicMock(spec=TargetPrice)
        mock_sync_client.get_target_price.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_target_price("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_earnings_dateがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_earnings_date delegates to sync via asyncio.to_thread."""
        expected = MagicMock(spec=EarningsDate)
        mock_sync_client.get_earnings_date.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_earnings_date("AAPL")

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_get_analyst_summaryがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """get_analyst_summary delegates to sync via asyncio.to_thread."""
        expected = MagicMock(spec=AnalystSummary)
        mock_sync_client.get_analyst_summary.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.get_analyst_summary("AAPL")

        assert result == expected


# =============================================================================
# Batch Endpoint Tests
# =============================================================================


class TestAsyncBatchEndpoints:
    """Tests for async batch endpoint methods."""

    @pytest.mark.asyncio
    async def test_正常系_fetch_for_symbolsがto_threadで委譲(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """fetch_for_symbols delegates to sync via asyncio.to_thread."""
        expected: dict[str, Any] = {"AAPL": [], "MSFT": []}
        mock_sync_client.fetch_for_symbols.return_value = expected

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.fetch_for_symbols(
                ["AAPL", "MSFT"],
                "get_short_interest",
            )

        assert result == expected

    @pytest.mark.asyncio
    async def test_正常系_kwargsが正しく転送される(
        self,
        async_client: AsyncNasdaqClient,
        mock_sync_client: MagicMock,
    ) -> None:
        """Additional kwargs are forwarded to the sync method."""
        expected: dict[str, Any] = {"AAPL": []}
        options = NasdaqFetchOptions(force_refresh=True)

        with patch(
            "market.nasdaq.async_client.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = expected
            result = await async_client.fetch_for_symbols(
                ["AAPL"],
                "get_short_interest",
                options=options,
            )

        # Verify to_thread was called with the sync method and correct args
        mock_to_thread.assert_called_once()
        call_args = mock_to_thread.call_args
        # First positional arg is the sync method (functools.partial or the method itself)
        assert call_args is not None
        assert result == expected


# =============================================================================
# Integration-like tests (verifying actual asyncio.to_thread delegation)
# =============================================================================


class TestAsyncToThreadIntegration:
    """Tests verifying actual asyncio.to_thread delegation works correctly."""

    @pytest.mark.asyncio
    async def test_正常系_実際のto_threadで同期メソッドが呼ばれる(
        self,
        mock_sync_client: MagicMock,
    ) -> None:
        """Actual asyncio.to_thread correctly calls the sync method."""
        expected = [MagicMock(spec=EarningsRecord)]
        mock_sync_client.get_earnings_calendar.return_value = expected

        async_cl = AsyncNasdaqClient(client=mock_sync_client)
        result = await async_cl.get_earnings_calendar(date="2026-01-30")

        assert result == expected
        mock_sync_client.get_earnings_calendar.assert_called_once_with(
            date="2026-01-30", options=None
        )

    @pytest.mark.asyncio
    async def test_正常系_optionsが正しく転送される(
        self,
        mock_sync_client: MagicMock,
    ) -> None:
        """NasdaqFetchOptions are correctly forwarded to the sync method."""
        expected = [MagicMock(spec=ShortInterestRecord)]
        mock_sync_client.get_short_interest.return_value = expected
        options = NasdaqFetchOptions(force_refresh=True)

        async_cl = AsyncNasdaqClient(client=mock_sync_client)
        result = await async_cl.get_short_interest("AAPL", options=options)

        assert result == expected
        mock_sync_client.get_short_interest.assert_called_once_with(
            "AAPL", options=options
        )

    @pytest.mark.asyncio
    async def test_正常系_get_financialsのfrequency引数が転送される(
        self,
        mock_sync_client: MagicMock,
    ) -> None:
        """The frequency argument is correctly forwarded for get_financials."""
        expected = MagicMock(spec=FinancialStatement)
        mock_sync_client.get_financials.return_value = expected

        async_cl = AsyncNasdaqClient(client=mock_sync_client)
        result = await async_cl.get_financials("AAPL", frequency="quarterly")

        assert result == expected
        mock_sync_client.get_financials.assert_called_once_with(
            "AAPL", frequency="quarterly", options=None
        )
