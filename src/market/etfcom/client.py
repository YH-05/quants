"""High-level API client for ETF.com data retrieval.

This module provides the ``ETFComClient`` class — a typed client covering
22 public methods (18 POST fund-details queries + 4 GET endpoints) with a
``_post_fund_details()`` DRY helper that keeps each method to 3-5 lines.

Features include:

- **Session DI**: ``ETFComSession`` can be injected or auto-created.
- **``_post_fund_details()``**: DRY helper for all 18 fund-details POST queries.
- **Validation helpers**: ``_validate_fund_id()``, ``_validate_ticker()``,
  ``_resolve_fund_id()``.
- **Context manager**: ``with ETFComClient() as client:``.
- **Parser delegation**: Each method delegates JSON parsing to the
  corresponding function in ``parser.py``.

Architecture
------------
Each public method follows this pattern::

    def get_<data>(self, ticker: str) -> ...:
        response = self._post_fund_details(ticker, "<queryName>")
        return parse_<data>(response)

The ``_post_fund_details()`` helper handles:

1. Calling ``session.post_fund_details(ticker, [query_name])``
2. Extracting the JSON response body

Examples
--------
>>> from market.etfcom.client import ETFComClient
>>> with ETFComClient() as client:
...     flows = client.get_fund_flows("SPY")
...     print(f"Got {len(flows)} flow records")

>>> with ETFComClient() as client:
...     tickers = client.get_tickers()
...     print(f"Got {len(tickers)} ETFs")

See Also
--------
market.alphavantage.client : Reference implementation (``_get_cached_or_fetch()`` DRY pattern).
market.polymarket.client : Reference implementation (``_request()`` + ``_handle_response()``).
market.etfcom.session : Underlying HTTP session with authentication.
market.etfcom.parser : JSON response parsers for all 22 endpoints.
market.etfcom.constants : API endpoint URLs and query name definitions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from market.etfcom.constants import (
    CHARTS_URL,
    DELAYED_QUOTES_URL,
    PERFORMANCE_URL,
    TICKERS_URL,
)
from market.etfcom.parser import (
    parse_charts,
    parse_compare_ticker,
    parse_countries,
    parse_delayed_quotes,
    parse_econ_dev,
    parse_fund_flows,
    parse_holdings,
    parse_intra_data,
    parse_performance,
    parse_performance_stats,
    parse_portfolio_data,
    parse_portfolio_management,
    parse_premium_chart,
    parse_rankings,
    parse_regions,
    parse_sector_breakdown,
    parse_spread_chart,
    parse_structure,
    parse_tax_exposures,
    parse_tickers,
    parse_tradability,
    parse_tradability_summary,
)
from market.etfcom.session import ETFComSession
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.etfcom.types import RetryConfig, ScrapingConfig

logger = get_logger(__name__)


class ETFComClient:
    """High-level typed API client for the ETF.com REST API.

    Provides 22 public methods across 2 categories:

    **18 POST fund-details queries** (via ``_post_fund_details()`` DRY helper):

    - ``get_fund_flows`` — Daily NAV, fund flows, AUM, premium/discount
    - ``get_holdings`` — Top holdings with weights
    - ``get_portfolio_data`` — P/E, P/B, dividend yield
    - ``get_sector_breakdown`` — Sector allocation
    - ``get_regions`` — Regional allocation
    - ``get_countries`` — Country allocation
    - ``get_econ_dev`` — Economic development classification
    - ``get_intra_data`` — Intraday price data
    - ``get_compare_ticker`` — Competing ETF comparison
    - ``get_spread_chart`` — Spread chart data
    - ``get_premium_chart`` — Premium/discount chart data
    - ``get_tradability`` — Volume, spread, liquidity metrics
    - ``get_tradability_summary`` — Aggregated tradability metrics
    - ``get_portfolio_management`` — Expense ratio, tracking difference
    - ``get_tax_exposures`` — Tax-related data
    - ``get_structure`` — Legal structure, derivatives, securities lending
    - ``get_rankings`` — ETF.com ratings (efficiency/liquidity/fit)
    - ``get_performance_stats`` — Performance statistics, R-squared, grade

    **4 GET endpoints**:

    - ``get_tickers`` — All available ETF tickers (~5,100)
    - ``get_delayed_quotes`` — Delayed real-time quotes (OHLC, Bid/Ask)
    - ``get_charts`` — Price chart data
    - ``get_performance`` — Performance returns (1M/3M/YTD/1Y/3Y/5Y)

    Parameters
    ----------
    session : ETFComSession | None
        Pre-configured session instance. If ``None``, a new session is
        created using ``scraping_config`` and ``retry_config``.
    scraping_config : ScrapingConfig | None
        Scraping configuration. Only used when ``session`` is ``None``.
    retry_config : RetryConfig | None
        Retry configuration. Only used when ``session`` is ``None``.

    Examples
    --------
    >>> with ETFComClient() as client:
    ...     flows = client.get_fund_flows("SPY")
    ...     tickers = client.get_tickers()

    >>> session = ETFComSession(config=ScrapingConfig(polite_delay=3.0))
    >>> client = ETFComClient(session=session)
    """

    def __init__(
        self,
        session: ETFComSession | None = None,
        scraping_config: ScrapingConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize ETFComClient with optional dependency injection.

        Parameters
        ----------
        session : ETFComSession | None
            Pre-configured session. If ``None``, creates a new session.
        scraping_config : ScrapingConfig | None
            Scraping configuration for session creation.
        retry_config : RetryConfig | None
            Retry configuration for session creation.
        """
        if session is not None:
            self._session = session
        else:
            self._session = ETFComSession(
                config=scraping_config,
                retry_config=retry_config,
            )

        logger.info("ETFComClient initialized")

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> ETFComClient:
        """Support context manager protocol.

        Returns
        -------
        ETFComClient
            Self for use in ``with`` statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close client on context exit.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type if an exception was raised.
        exc_val : BaseException | None
            Exception instance if an exception was raised.
        exc_tb : Any
            Traceback if an exception was raised.
        """
        self.close()

    def close(self) -> None:
        """Close the client and release resources.

        Closes the underlying ``ETFComSession``.
        """
        self._session.close()
        logger.debug("ETFComClient closed")

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _validate_fund_id(self, fund_id: int) -> None:
        """Validate that a fund_id is a positive integer.

        Parameters
        ----------
        fund_id : int
            The fund ID to validate.

        Raises
        ------
        ValueError
            If ``fund_id`` is 0 or negative.
        """
        if fund_id <= 0:
            raise ValueError(f"fund_id must be positive, got {fund_id}")

    def _validate_ticker(self, ticker: str) -> None:
        """Validate that a ticker string is non-empty.

        Parameters
        ----------
        ticker : str
            The ticker symbol to validate.

        Raises
        ------
        ValueError
            If ``ticker`` is empty or whitespace-only.
        """
        if not ticker or not ticker.strip():
            raise ValueError(f"ticker must not be empty, got {ticker!r}")

    def _resolve_fund_id(self, fund_id: int) -> int:
        """Resolve and validate a fund_id.

        Parameters
        ----------
        fund_id : int
            The fund ID to resolve.

        Returns
        -------
        int
            The validated fund ID.

        Raises
        ------
        ValueError
            If ``fund_id`` is 0 or negative.
        """
        self._validate_fund_id(fund_id)
        return fund_id

    # =========================================================================
    # DRY Helper
    # =========================================================================

    def _post_fund_details(
        self,
        ticker: str,
        query_name: str,
    ) -> dict[str, Any]:
        """Send a POST request to the fund-details endpoint and return JSON.

        This is the DRY helper that all 18 fund-details public methods
        delegate to. It handles:

        1. Calling ``session.post_fund_details(ticker, [query_name])``
        2. Extracting and returning the JSON response body.

        Parameters
        ----------
        ticker : str
            The ETF ticker symbol (e.g. ``"SPY"``).
        query_name : str
            The fund-details query name (from ``FUND_DETAILS_QUERY_NAMES``).

        Returns
        -------
        dict[str, Any]
            The full JSON response body.

        Raises
        ------
        ETFComBlockedError
            If the request is blocked by bot detection.
        ETFComAPIError
            If authentication fails or the API returns an error.
        """
        self._validate_ticker(ticker)

        logger.debug(
            "Fetching fund details",
            ticker=ticker,
            query_name=query_name,
        )

        response = self._session.post_fund_details(ticker, [query_name])
        result: dict[str, Any] = response.json()

        logger.debug(
            "Fund details fetched",
            ticker=ticker,
            query_name=query_name,
        )

        return result

    # =========================================================================
    # 18 POST Methods (fund-details queries)
    # =========================================================================

    def get_fund_flows(self, ticker: str) -> list[dict[str, Any]]:
        """Get daily NAV, fund flows, AUM, and premium/discount data.

        Queries ``fundFlowsData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with daily flow data.

        Raises
        ------
        ValueError
            If ``ticker`` is empty.
        ETFComBlockedError
            If the request is blocked.
        """
        response = self._post_fund_details(ticker, "fundFlowsData")
        return parse_fund_flows(response)

    def get_holdings(self, ticker: str) -> list[dict[str, Any]]:
        """Get top holdings with weights.

        Queries ``topHoldings`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with holding data.
        """
        response = self._post_fund_details(ticker, "topHoldings")
        return parse_holdings(response)

    def get_portfolio_data(self, ticker: str) -> dict[str, Any]:
        """Get portfolio characteristics (P/E, P/B, dividend yield, etc.).

        Queries ``fundPortfolioData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with portfolio metrics.
        """
        response = self._post_fund_details(ticker, "fundPortfolioData")
        return parse_portfolio_data(response)

    def get_sector_breakdown(self, ticker: str) -> list[dict[str, Any]]:
        """Get sector allocation data.

        Queries ``sectorIndustryBreakdown`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with sector allocation data.
        """
        response = self._post_fund_details(ticker, "sectorIndustryBreakdown")
        return parse_sector_breakdown(response)

    def get_regions(self, ticker: str) -> list[dict[str, Any]]:
        """Get regional allocation data.

        Queries ``regions`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with region allocation data.
        """
        response = self._post_fund_details(ticker, "regions")
        return parse_regions(response)

    def get_countries(self, ticker: str) -> list[dict[str, Any]]:
        """Get country allocation data.

        Queries ``countries`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with country allocation data.
        """
        response = self._post_fund_details(ticker, "countries")
        return parse_countries(response)

    def get_econ_dev(self, ticker: str) -> list[dict[str, Any]]:
        """Get economic development classification data.

        Queries ``economicDevelopment`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with economic development data.
        """
        response = self._post_fund_details(ticker, "economicDevelopment")
        return parse_econ_dev(response)

    def get_intra_data(self, ticker: str) -> list[dict[str, Any]]:
        """Get intraday price data.

        Queries ``fundIntraData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with intraday data.
        """
        response = self._post_fund_details(ticker, "fundIntraData")
        return parse_intra_data(response)

    def get_compare_ticker(self, ticker: str) -> list[dict[str, Any]]:
        """Get competing ETF comparison data.

        Queries ``compareTicker`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with comparison data.
        """
        response = self._post_fund_details(ticker, "compareTicker")
        return parse_compare_ticker(response)

    def get_spread_chart(self, ticker: str) -> list[dict[str, Any]]:
        """Get bid-ask spread chart data.

        Queries ``fundSpreadChart`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with spread chart data.
        """
        response = self._post_fund_details(ticker, "fundSpreadChart")
        return parse_spread_chart(response)

    def get_premium_chart(self, ticker: str) -> list[dict[str, Any]]:
        """Get premium/discount chart data.

        Queries ``fundPremiumChart`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with premium/discount chart data.
        """
        response = self._post_fund_details(ticker, "fundPremiumChart")
        return parse_premium_chart(response)

    def get_tradability(self, ticker: str) -> list[dict[str, Any]]:
        """Get volume, spread, and liquidity time-series data.

        Queries ``fundTradabilityData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case dicts with tradability data.
        """
        response = self._post_fund_details(ticker, "fundTradabilityData")
        return parse_tradability(response)

    def get_tradability_summary(self, ticker: str) -> dict[str, Any]:
        """Get aggregated tradability metrics.

        Queries ``fundTradabilitySummary`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with tradability summary metrics.
        """
        response = self._post_fund_details(ticker, "fundTradabilitySummary")
        return parse_tradability_summary(response)

    def get_portfolio_management(self, ticker: str) -> dict[str, Any]:
        """Get expense ratio, tracking difference, and management data.

        Queries ``fundPortfolioManData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with portfolio management data.
        """
        response = self._post_fund_details(ticker, "fundPortfolioManData")
        return parse_portfolio_management(response)

    def get_tax_exposures(self, ticker: str) -> dict[str, Any]:
        """Get tax-related data.

        Queries ``fundTaxExposuresData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with tax exposure data.
        """
        response = self._post_fund_details(ticker, "fundTaxExposuresData")
        return parse_tax_exposures(response)

    def get_structure(self, ticker: str) -> dict[str, Any]:
        """Get fund structure data.

        Queries ``fundStructureData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with structure data.
        """
        response = self._post_fund_details(ticker, "fundStructureData")
        return parse_structure(response)

    def get_rankings(self, ticker: str) -> dict[str, Any]:
        """Get ETF.com rating grades.

        Queries ``fundRankingsData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with rankings data.
        """
        response = self._post_fund_details(ticker, "fundRankingsData")
        return parse_rankings(response)

    def get_performance_stats(self, ticker: str) -> dict[str, Any]:
        """Get performance statistics, R-squared, beta, and grade.

        Queries ``fundPerformanceStatsData`` via the fund-details POST endpoint.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with performance statistics.
        """
        response = self._post_fund_details(ticker, "fundPerformanceStatsData")
        return parse_performance_stats(response)

    # =========================================================================
    # 4 GET Methods
    # =========================================================================

    def get_tickers(self) -> list[dict[str, Any]]:
        """Get all available ETF tickers (~5,100 ETFs).

        Sends an authenticated GET to ``/v2/fund/tickers``.

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case ticker dicts with fund_id, name, issuer,
            asset_class, and inception_date fields.
        """
        logger.debug("Fetching tickers list", url=TICKERS_URL)

        response = self._session.get_authenticated(TICKERS_URL)
        raw: list[dict[str, Any]] | dict[str, Any] = response.json()

        result = parse_tickers(raw)

        logger.info("Tickers fetched", count=len(result))
        return result

    def get_delayed_quotes(self, tickers: str) -> list[dict[str, Any]]:
        """Get delayed real-time quotes for one or more tickers.

        Sends an authenticated GET to ``/v2/quotes/delayedquotes``.

        Parameters
        ----------
        tickers : str
            Comma-separated ticker symbols (e.g. ``"SPY"`` or ``"SPY,QQQ"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case quote dicts with OHLC, bid/ask, and volume.

        Raises
        ------
        ValueError
            If ``tickers`` is empty.
        """
        self._validate_ticker(tickers)

        url = f"{DELAYED_QUOTES_URL}?{urlencode({'tickers': tickers})}"
        logger.debug("Fetching delayed quotes", url=url, tickers=tickers)

        response = self._session.get_authenticated(url)
        raw: dict[str, Any] = response.json()

        result = parse_delayed_quotes(raw)

        logger.info("Delayed quotes fetched", count=len(result))
        return result

    def get_charts(
        self,
        ticker: str,
        data_point: str = "splitPrice",
        interval: str = "MAX",
    ) -> list[dict[str, Any]]:
        """Get price chart data for a ticker.

        Sends an authenticated GET to ``/v2/fund/charts``.

        Parameters
        ----------
        ticker : str
            ETF ticker symbol (e.g. ``"SPY"``).
        data_point : str
            Data point type (default: ``"splitPrice"``).
        interval : str
            Time interval (default: ``"MAX"``).

        Returns
        -------
        list[dict[str, Any]]
            List of snake_case chart point dicts.

        Raises
        ------
        ValueError
            If ``ticker`` is empty.
        """
        self._validate_ticker(ticker)

        url = f"{CHARTS_URL}?{urlencode({'dataPoint': data_point, 'interval': interval, 'ticker': ticker})}"
        logger.debug("Fetching charts", url=url, ticker=ticker)

        response = self._session.get_authenticated(url)
        raw: dict[str, Any] = response.json()

        result = parse_charts(raw)

        logger.info("Charts fetched", count=len(result), ticker=ticker)
        return result

    def get_performance(self, fund_id: int) -> dict[str, Any]:
        """Get performance returns (1M/3M/YTD/1Y/3Y/5Y) for a fund.

        Sends an authenticated GET to ``/v2/fund/performance/{fund_id}``.

        Parameters
        ----------
        fund_id : int
            The fund ID (obtained from ``get_tickers()``).

        Returns
        -------
        dict[str, Any]
            Snake_case dict with performance return data.

        Raises
        ------
        ValueError
            If ``fund_id`` is 0 or negative.
        """
        self._resolve_fund_id(fund_id)

        url = f"{PERFORMANCE_URL}/{fund_id}"
        logger.debug("Fetching performance", url=url, fund_id=fund_id)

        response = self._session.get_authenticated(url)
        raw: dict[str, Any] = response.json()

        result = parse_performance(raw)

        logger.info("Performance fetched", fund_id=fund_id)
        return result


# =============================================================================
# Module exports
# =============================================================================

__all__ = ["ETFComClient"]
