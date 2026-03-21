"""High-level client for Polymarket API access.

This module provides the ``PolymarketClient`` class, which integrates
the Gamma, CLOB, and Data APIs through a single interface with
SQLiteCache support and typed return values.

Features include:

- **Gamma API** (4 methods): ``get_events``, ``get_event``, ``get_markets``,
  ``get_market`` -- returning Pydantic models.
- **CLOB API single** (4 methods): ``get_prices_history``, ``get_midpoint``,
  ``get_spread``, ``get_orderbook`` -- single-market queries.
- **CLOB API bulk** (4 methods): ``get_midpoints``, ``get_spreads``,
  ``get_orderbooks``, ``get_prices`` -- multi-market queries.
- **Data API** (4 methods): ``get_open_interest``, ``get_trades``,
  ``get_leaderboard``, ``get_holders`` -- analytics data.
- ``_request()`` + ``_handle_response()`` pattern (JQuants-style).
- Context manager support.

Examples
--------
>>> from market.polymarket import PolymarketClient
>>> with PolymarketClient() as client:
...     events = client.get_events(limit=5)
...     print(f"Found {len(events)} events")

See Also
--------
market.jquants.client : Reference implementation with ``_request()`` pattern.
market.polymarket.session : Underlying HTTP session.
market.polymarket.cache : TTL constants and cache helper.
"""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from market.cache.cache import SQLiteCache, generate_cache_key
from market.polymarket.cache import (
    ACTIVE_PRICES_TTL,
    LEADERBOARD_TTL,
    METADATA_TTL,
    OI_TRADES_TTL,
    ORDERBOOK_TTL,
    get_polymarket_cache,
)
from market.polymarket.constants import (
    CLOB_BASE_URL,
    DATA_BASE_URL,
    GAMMA_BASE_URL,
    MAX_LIMIT,
)
from market.polymarket.errors import PolymarketValidationError
from market.polymarket.models import (
    OrderBook,
    OrderBookLevel,
    PolymarketEvent,
    PolymarketMarket,
    PricePoint,
    TradeRecord,
)
from market.polymarket.session import PolymarketSession
from market.polymarket.types import (
    FetchOptions,
    PolymarketConfig,
    PriceInterval,
    RetryConfig,
)
from market.types import DataSource, MarketDataResult
from utils_core.logging import get_logger

logger = get_logger(__name__)


class PolymarketClient:
    """High-level client for the Polymarket API.

    Provides typed methods for each API endpoint, integrating the three
    Polymarket APIs (Gamma, CLOB, Data) with SQLiteCache support.

    Parameters
    ----------
    config : PolymarketConfig | None
        Polymarket configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.
    cache : SQLiteCache | None
        Cache instance. If ``None``, a default persistent cache is created.

    Examples
    --------
    >>> with PolymarketClient() as client:
    ...     events = client.get_events(limit=5)
    ...     print(len(events))
    """

    _SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,256}$")

    def __init__(
        self,
        config: PolymarketConfig | None = None,
        retry_config: RetryConfig | None = None,
        cache: SQLiteCache | None = None,
    ) -> None:
        self._config: PolymarketConfig = config or PolymarketConfig()
        self._session: PolymarketSession = PolymarketSession(
            config=self._config, retry_config=retry_config
        )
        self._cache: SQLiteCache = cache or get_polymarket_cache()

        logger.info("PolymarketClient initialized")

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> "PolymarketClient":
        """Support context manager protocol.

        Returns
        -------
        PolymarketClient
            The client instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close client on context exit."""
        self.close()

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()
        logger.debug("PolymarketClient closed")

    # =========================================================================
    # Gamma API (4 methods)
    # =========================================================================

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        options: FetchOptions | None = None,
    ) -> list[PolymarketEvent]:
        """Get a list of events from the Gamma API.

        Calls ``GET /events`` on the Gamma API.

        Parameters
        ----------
        limit : int
            Maximum number of events to return (default: 100).
        offset : int
            Pagination offset (default: 0).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[PolymarketEvent]
            List of events with nested markets.

        Raises
        ------
        PolymarketValidationError
            If limit or offset is invalid.

        Examples
        --------
        >>> events = client.get_events(limit=5)
        >>> len(events) <= 5
        True
        """
        self._validate_pagination(limit, offset)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
        }

        cache_key = generate_cache_key(
            symbol=f"events_limit{limit}_offset{offset}",
            source="polymarket_gamma",
        )

        def _fetch() -> list[PolymarketEvent]:
            data = self._gamma_request("/events", params=params)
            return [
                PolymarketEvent.model_validate(item)
                for item in (data if isinstance(data, list) else [])
            ]

        events = self._fetch_cached(
            cache_key=cache_key,
            ttl=METADATA_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda evts: [e.model_dump(mode="json") for e in evts],
            deserialize_fn=lambda cached: [
                PolymarketEvent.model_validate(item) for item in cached
            ],
            log_label="events",
            limit=limit,
            offset=offset,
        )
        logger.info("Events retrieved", count=len(events))
        return events

    def get_event(
        self,
        event_id: str,
        options: FetchOptions | None = None,
    ) -> PolymarketEvent:
        """Get a single event by ID from the Gamma API.

        Calls ``GET /events/{event_id}`` on the Gamma API.

        Parameters
        ----------
        event_id : str
            The event identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        PolymarketEvent
            The event with nested markets.

        Raises
        ------
        PolymarketValidationError
            If event_id is empty.

        Examples
        --------
        >>> event = client.get_event("event-001")
        >>> event.id
        'event-001'
        """
        self._validate_id(event_id, "event_id")
        options = options or FetchOptions()

        cache_key = generate_cache_key(
            symbol=event_id,
            source="polymarket_gamma_event",
        )

        def _fetch() -> PolymarketEvent:
            data = self._gamma_request(f"/events/{event_id}")
            return PolymarketEvent.model_validate(data)

        event = self._fetch_cached(
            cache_key=cache_key,
            ttl=METADATA_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda e: e.model_dump(mode="json"),
            deserialize_fn=lambda cached: PolymarketEvent.model_validate(cached),
            log_label="event",
            event_id=event_id,
        )
        logger.info("Event retrieved", event_id=event_id, title=event.title)
        return event

    def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        options: FetchOptions | None = None,
    ) -> list[PolymarketMarket]:
        """Get a list of markets from the Gamma API.

        Calls ``GET /markets`` on the Gamma API.

        Parameters
        ----------
        limit : int
            Maximum number of markets to return (default: 100).
        offset : int
            Pagination offset (default: 0).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[PolymarketMarket]
            List of prediction markets.

        Raises
        ------
        PolymarketValidationError
            If limit or offset is invalid.

        Examples
        --------
        >>> markets = client.get_markets(limit=10)
        >>> len(markets) <= 10
        True
        """
        self._validate_pagination(limit, offset)
        options = options or FetchOptions()

        params: dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
        }

        cache_key = generate_cache_key(
            symbol=f"markets_limit{limit}_offset{offset}",
            source="polymarket_gamma",
        )

        def _fetch() -> list[PolymarketMarket]:
            data = self._gamma_request("/markets", params=params)
            return [
                PolymarketMarket.model_validate(item)
                for item in (data if isinstance(data, list) else [])
            ]

        markets = self._fetch_cached(
            cache_key=cache_key,
            ttl=METADATA_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda mkts: [m.model_dump(mode="json") for m in mkts],
            deserialize_fn=lambda cached: [
                PolymarketMarket.model_validate(item) for item in cached
            ],
            log_label="markets",
            limit=limit,
            offset=offset,
        )
        logger.info("Markets retrieved", count=len(markets))
        return markets

    def get_market(
        self,
        condition_id: str,
        options: FetchOptions | None = None,
    ) -> PolymarketMarket:
        """Get a single market by condition ID from the Gamma API.

        Calls ``GET /markets/{condition_id}`` on the Gamma API.

        Parameters
        ----------
        condition_id : str
            The market condition identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        PolymarketMarket
            The prediction market.

        Raises
        ------
        PolymarketValidationError
            If condition_id is empty.

        Examples
        --------
        >>> market = client.get_market("0xabc123")
        >>> market.condition_id
        '0xabc123'
        """
        self._validate_id(condition_id, "condition_id")
        options = options or FetchOptions()

        cache_key = generate_cache_key(
            symbol=condition_id,
            source="polymarket_gamma_market",
        )

        def _fetch() -> PolymarketMarket:
            data = self._gamma_request(f"/markets/{condition_id}")
            return PolymarketMarket.model_validate(data)

        market = self._fetch_cached(
            cache_key=cache_key,
            ttl=METADATA_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda m: m.model_dump(mode="json"),
            deserialize_fn=lambda cached: PolymarketMarket.model_validate(cached),
            log_label="market",
            condition_id=condition_id,
        )
        logger.info(
            "Market retrieved",
            condition_id=condition_id,
            question=market.question,
        )
        return market

    # =========================================================================
    # CLOB API - Single (4 methods)
    # =========================================================================

    def get_prices_history(
        self,
        token_id: str,
        interval: PriceInterval = PriceInterval.ONE_DAY,
        options: FetchOptions | None = None,
    ) -> MarketDataResult:
        """Get historical price data for a token from the CLOB API.

        Calls ``GET /prices-history`` on the CLOB API. Returns a
        ``MarketDataResult`` wrapping a DataFrame with ``timestamp``
        and ``price`` columns.

        Parameters
        ----------
        token_id : str
            The token identifier.
        interval : PriceInterval
            Price data interval/fidelity (default: ONE_DAY).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        MarketDataResult
            Result containing a DataFrame with ``timestamp`` and ``price``
            columns.

        Raises
        ------
        PolymarketValidationError
            If token_id is empty.

        Examples
        --------
        >>> result = client.get_prices_history("token123")
        >>> "price" in result.data.columns
        True
        """
        self._validate_id(token_id, "token_id")
        options = options or FetchOptions()

        # CLOB API accepts both "interval" (current) and "fidelity" (legacy)
        # params for backward compatibility
        params: dict[str, str] = {
            "market": token_id,
            "interval": str(interval),
            "fidelity": str(interval),
        }

        cache_key = generate_cache_key(
            symbol=token_id,
            interval=str(interval),
            source="polymarket_clob_prices",
        )

        def _fetch() -> MarketDataResult:
            data = self._clob_request("/prices-history", params=params)

            points: list[PricePoint] = []
            history = data.get("history", []) if isinstance(data, dict) else data
            if isinstance(history, list):
                for item in history:
                    points.append(PricePoint.model_validate(item))

            df = pd.DataFrame(
                [{"timestamp": p.t, "price": p.p} for p in points]
                if points
                else {"timestamp": [], "price": []}
            )

            return MarketDataResult(
                symbol=token_id,
                data=df,
                source=DataSource.POLYMARKET,
                fetched_at=datetime.now(tz=UTC),
                from_cache=False,
                metadata={"interval": str(interval), "point_count": len(points)},
            )

        result = self._fetch_cached(
            cache_key=cache_key,
            ttl=ACTIVE_PRICES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="prices history",
            token_id=token_id,
        )
        logger.info(
            "Prices history retrieved",
            token_id=token_id,
            points=len(result.data),
        )
        return result

    def get_midpoint(
        self,
        token_id: str,
        options: FetchOptions | None = None,
    ) -> float:
        """Get the midpoint price for a token from the CLOB API.

        Calls ``GET /midpoint`` on the CLOB API.

        Parameters
        ----------
        token_id : str
            The token identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        float
            The midpoint price (0.0 to 1.0).

        Raises
        ------
        PolymarketValidationError
            If token_id is empty.

        Examples
        --------
        >>> price = client.get_midpoint("token123")
        >>> 0.0 <= price <= 1.0
        True
        """
        self._validate_id(token_id, "token_id")
        options = options or FetchOptions()

        params: dict[str, str] = {"token_id": token_id}

        cache_key = generate_cache_key(
            symbol=token_id,
            source="polymarket_clob_midpoint",
        )

        def _fetch() -> float:
            data = self._clob_request("/midpoint", params=params)
            return float(data.get("mid", 0.0)) if isinstance(data, dict) else 0.0

        mid = self._fetch_cached(
            cache_key=cache_key,
            ttl=ACTIVE_PRICES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="midpoint",
            token_id=token_id,
        )
        logger.info("Midpoint retrieved", token_id=token_id, midpoint=mid)
        return mid

    def get_spread(
        self,
        token_id: str,
        options: FetchOptions | None = None,
    ) -> dict[str, float]:
        """Get the bid-ask spread for a token from the CLOB API.

        Calls ``GET /spread`` on the CLOB API.

        Parameters
        ----------
        token_id : str
            The token identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, float]
            Dictionary with ``bid``, ``ask``, and ``spread`` keys.

        Raises
        ------
        PolymarketValidationError
            If token_id is empty.

        Examples
        --------
        >>> spread = client.get_spread("token123")
        >>> "spread" in spread
        True
        """
        self._validate_id(token_id, "token_id")
        options = options or FetchOptions()

        params: dict[str, str] = {"token_id": token_id}

        cache_key = generate_cache_key(
            symbol=token_id,
            source="polymarket_clob_spread",
        )

        def _fetch() -> dict[str, float]:
            data = self._clob_request("/spread", params=params)
            if isinstance(data, dict):
                return {
                    "bid": float(data.get("bid", 0.0)),
                    "ask": float(data.get("ask", 0.0)),
                    "spread": float(data.get("spread", 0.0)),
                }
            return {}

        spread_data = self._fetch_cached(
            cache_key=cache_key,
            ttl=ACTIVE_PRICES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="spread",
            token_id=token_id,
        )
        logger.info("Spread retrieved", token_id=token_id, spread=spread_data)
        return spread_data

    def get_orderbook(
        self,
        token_id: str,
        options: FetchOptions | None = None,
    ) -> OrderBook:
        """Get the order book for a token from the CLOB API.

        Calls ``GET /book`` on the CLOB API.

        Parameters
        ----------
        token_id : str
            The token identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        OrderBook
            The order book snapshot with bids and asks.

        Raises
        ------
        PolymarketValidationError
            If token_id is empty.

        Examples
        --------
        >>> book = client.get_orderbook("token123")
        >>> isinstance(book, OrderBook)
        True
        """
        self._validate_id(token_id, "token_id")
        options = options or FetchOptions()

        params: dict[str, str] = {"token_id": token_id}

        cache_key = generate_cache_key(
            symbol=token_id,
            source="polymarket_clob_orderbook",
        )

        def _fetch() -> OrderBook:
            data = self._clob_request("/book", params=params)
            return self._parse_orderbook(data, token_id)

        book = self._fetch_cached(
            cache_key=cache_key,
            ttl=ORDERBOOK_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda b: b.model_dump(mode="json"),
            deserialize_fn=lambda cached: OrderBook.model_validate(cached),
            log_label="orderbook",
            token_id=token_id,
        )
        logger.info(
            "Orderbook retrieved",
            token_id=token_id,
            bids=len(book.bids),
            asks=len(book.asks),
        )
        return book

    # =========================================================================
    # CLOB API - Bulk (4 methods)
    # =========================================================================

    def get_midpoints(
        self,
        token_ids: list[str],
        options: FetchOptions | None = None,
    ) -> dict[str, float]:
        """Get midpoint prices for multiple tokens from the CLOB API.

        Calls ``GET /midpoints`` on the CLOB API.

        Parameters
        ----------
        token_ids : list[str]
            List of token identifiers.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, float]
            Mapping of token_id to midpoint price.

        Raises
        ------
        PolymarketValidationError
            If token_ids is empty.

        Examples
        --------
        >>> mids = client.get_midpoints(["token1", "token2"])
        >>> isinstance(mids, dict)
        True
        """
        self._validate_token_ids(token_ids)
        options = options or FetchOptions()

        ids_str = ",".join(token_ids)
        params: dict[str, str] = {"token_ids": ids_str}

        cache_key = generate_cache_key(
            symbol=f"midpoints_{ids_str}",
            source="polymarket_clob_midpoints",
        )

        def _fetch() -> dict[str, float]:
            data = self._clob_request("/midpoints", params=params)
            result: dict[str, float] = {}
            if isinstance(data, dict):
                for tid, val in data.items():
                    result[tid] = float(val)
            return result

        midpoints = self._fetch_cached(
            cache_key=cache_key,
            ttl=ACTIVE_PRICES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="midpoints",
            count=len(token_ids),
        )
        logger.info("Midpoints retrieved", count=len(midpoints))
        return midpoints

    def get_spreads(
        self,
        token_ids: list[str],
        options: FetchOptions | None = None,
    ) -> dict[str, dict[str, float]]:
        """Get bid-ask spreads for multiple tokens from the CLOB API.

        Calls ``GET /spreads`` on the CLOB API.

        Parameters
        ----------
        token_ids : list[str]
            List of token identifiers.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, dict[str, float]]
            Mapping of token_id to spread data (bid, ask, spread).

        Raises
        ------
        PolymarketValidationError
            If token_ids is empty.

        Examples
        --------
        >>> spreads = client.get_spreads(["token1", "token2"])
        >>> isinstance(spreads, dict)
        True
        """
        self._validate_token_ids(token_ids)
        options = options or FetchOptions()

        ids_str = ",".join(token_ids)
        params: dict[str, str] = {"token_ids": ids_str}

        cache_key = generate_cache_key(
            symbol=f"spreads_{ids_str}",
            source="polymarket_clob_spreads",
        )

        def _fetch() -> dict[str, dict[str, float]]:
            data = self._clob_request("/spreads", params=params)
            result: dict[str, dict[str, float]] = {}
            if isinstance(data, dict):
                for tid, val in data.items():
                    if isinstance(val, dict):
                        result[tid] = {
                            "bid": float(val.get("bid", 0.0)),
                            "ask": float(val.get("ask", 0.0)),
                            "spread": float(val.get("spread", 0.0)),
                        }
            return result

        spreads = self._fetch_cached(
            cache_key=cache_key,
            ttl=ACTIVE_PRICES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="spreads",
            count=len(token_ids),
        )
        logger.info("Spreads retrieved", count=len(spreads))
        return spreads

    def get_orderbooks(
        self,
        token_ids: list[str],
        options: FetchOptions | None = None,
    ) -> dict[str, OrderBook]:
        """Get order books for multiple tokens from the CLOB API.

        Calls ``GET /books`` on the CLOB API.

        Parameters
        ----------
        token_ids : list[str]
            List of token identifiers.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, OrderBook]
            Mapping of token_id to OrderBook.

        Raises
        ------
        PolymarketValidationError
            If token_ids is empty.

        Examples
        --------
        >>> books = client.get_orderbooks(["token1", "token2"])
        >>> isinstance(books, dict)
        True
        """
        self._validate_token_ids(token_ids)
        options = options or FetchOptions()

        ids_str = ",".join(token_ids)
        params: dict[str, str] = {"token_ids": ids_str}

        cache_key = generate_cache_key(
            symbol=f"orderbooks_{ids_str}",
            source="polymarket_clob_orderbooks",
        )

        def _fetch() -> dict[str, OrderBook]:
            data = self._clob_request("/books", params=params)
            result: dict[str, OrderBook] = {}
            if isinstance(data, dict):
                for tid, val in data.items():
                    if isinstance(val, dict):
                        result[tid] = self._parse_orderbook(val, tid)
            return result

        books = self._fetch_cached(
            cache_key=cache_key,
            ttl=ORDERBOOK_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda bks: {
                tid: book.model_dump(mode="json") for tid, book in bks.items()
            },
            deserialize_fn=lambda cached: {
                tid: OrderBook.model_validate(val) for tid, val in cached.items()
            },
            log_label="orderbooks",
            count=len(token_ids),
        )
        logger.info("Orderbooks retrieved", count=len(books))
        return books

    def get_prices(
        self,
        token_ids: list[str],
        options: FetchOptions | None = None,
    ) -> dict[str, float]:
        """Get latest prices for multiple tokens from the CLOB API.

        Calls ``GET /prices`` on the CLOB API.

        Parameters
        ----------
        token_ids : list[str]
            List of token identifiers.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, float]
            Mapping of token_id to latest price.

        Raises
        ------
        PolymarketValidationError
            If token_ids is empty.

        Examples
        --------
        >>> prices = client.get_prices(["token1", "token2"])
        >>> isinstance(prices, dict)
        True
        """
        self._validate_token_ids(token_ids)
        options = options or FetchOptions()

        ids_str = ",".join(token_ids)
        params: dict[str, str] = {"token_ids": ids_str}

        cache_key = generate_cache_key(
            symbol=f"prices_{ids_str}",
            source="polymarket_clob_prices_bulk",
        )

        def _fetch() -> dict[str, float]:
            data = self._clob_request("/prices", params=params)
            result: dict[str, float] = {}
            if isinstance(data, dict):
                for tid, val in data.items():
                    result[tid] = float(val)
            return result

        prices = self._fetch_cached(
            cache_key=cache_key,
            ttl=ACTIVE_PRICES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="prices",
            count=len(token_ids),
        )
        logger.info("Prices retrieved", count=len(prices))
        return prices

    # =========================================================================
    # Data API (4 methods)
    # =========================================================================

    def get_open_interest(
        self,
        condition_id: str,
        options: FetchOptions | None = None,
    ) -> dict[str, Any]:
        """Get open interest data for a market from the Data API.

        Calls ``GET /open-interest`` on the Data API.

        Parameters
        ----------
        condition_id : str
            The market condition identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        dict[str, Any]
            Open interest data including total OI and per-outcome breakdown.

        Raises
        ------
        PolymarketValidationError
            If condition_id is empty.

        Examples
        --------
        >>> oi = client.get_open_interest("0xabc123")
        >>> isinstance(oi, dict)
        True
        """
        self._validate_id(condition_id, "condition_id")
        options = options or FetchOptions()

        params: dict[str, str] = {"condition_id": condition_id}

        cache_key = generate_cache_key(
            symbol=condition_id,
            source="polymarket_data_oi",
        )

        def _fetch() -> dict[str, Any]:
            data = self._data_request("/open-interest", params=params)
            return data if isinstance(data, dict) else {}

        oi = self._fetch_cached(
            cache_key=cache_key,
            ttl=OI_TRADES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="open interest",
            condition_id=condition_id,
        )
        logger.info("Open interest retrieved", condition_id=condition_id)
        return oi

    def get_trades(
        self,
        condition_id: str,
        limit: int = 100,
        options: FetchOptions | None = None,
    ) -> list[TradeRecord]:
        """Get recent trades for a market from the Data API.

        Calls ``GET /trades`` on the Data API.

        Parameters
        ----------
        condition_id : str
            The market condition identifier.
        limit : int
            Maximum number of trades to return (default: 100).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[TradeRecord]
            List of trade records.

        Raises
        ------
        PolymarketValidationError
            If condition_id is empty or limit is invalid.

        Examples
        --------
        >>> trades = client.get_trades("0xabc123", limit=10)
        >>> all(isinstance(t, TradeRecord) for t in trades)
        True
        """
        self._validate_id(condition_id, "condition_id")
        if limit < 1:
            raise PolymarketValidationError(
                message=f"limit must be positive, got {limit}",
                field="limit",
                value=limit,
            )
        options = options or FetchOptions()

        params: dict[str, str] = {
            "condition_id": condition_id,
            "limit": str(limit),
        }

        cache_key = generate_cache_key(
            symbol=f"{condition_id}_trades_limit{limit}",
            source="polymarket_data_trades",
        )

        def _fetch() -> list[TradeRecord]:
            data = self._data_request("/trades", params=params)
            items = data if isinstance(data, list) else []
            return [TradeRecord.model_validate(item) for item in items]

        trades = self._fetch_cached(
            cache_key=cache_key,
            ttl=OI_TRADES_TTL,
            options=options,
            fetch_fn=_fetch,
            serialize_fn=lambda tds: [t.model_dump(mode="json") for t in tds],
            deserialize_fn=lambda cached: [
                TradeRecord.model_validate(item) for item in cached
            ],
            log_label="trades",
            condition_id=condition_id,
        )
        logger.info(
            "Trades retrieved",
            condition_id=condition_id,
            count=len(trades),
        )
        return trades

    def get_leaderboard(
        self,
        limit: int = 100,
        options: FetchOptions | None = None,
    ) -> list[dict[str, Any]]:
        """Get the trading leaderboard from the Data API.

        Calls ``GET /leaderboard`` on the Data API.

        Parameters
        ----------
        limit : int
            Maximum number of entries to return (default: 100).
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[dict[str, Any]]
            List of leaderboard entries.

        Raises
        ------
        PolymarketValidationError
            If limit is invalid.

        Examples
        --------
        >>> board = client.get_leaderboard(limit=10)
        >>> isinstance(board, list)
        True
        """
        if limit < 1:
            raise PolymarketValidationError(
                message=f"limit must be positive, got {limit}",
                field="limit",
                value=limit,
            )
        options = options or FetchOptions()

        params: dict[str, str] = {"limit": str(limit)}

        cache_key = generate_cache_key(
            symbol=f"leaderboard_limit{limit}",
            source="polymarket_data_leaderboard",
        )

        def _fetch() -> list[dict[str, Any]]:
            data = self._data_request("/leaderboard", params=params)
            return data if isinstance(data, list) else []

        board = self._fetch_cached(
            cache_key=cache_key,
            ttl=LEADERBOARD_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="leaderboard",
            limit=limit,
        )
        logger.info("Leaderboard retrieved", count=len(board))
        return board

    def get_holders(
        self,
        condition_id: str,
        options: FetchOptions | None = None,
    ) -> list[dict[str, Any]]:
        """Get token holders for a market from the Data API.

        Calls ``GET /holders`` on the Data API.

        Parameters
        ----------
        condition_id : str
            The market condition identifier.
        options : FetchOptions | None
            Fetch options (cache control).

        Returns
        -------
        list[dict[str, Any]]
            List of holder records.

        Raises
        ------
        PolymarketValidationError
            If condition_id is empty.

        Examples
        --------
        >>> holders = client.get_holders("0xabc123")
        >>> isinstance(holders, list)
        True
        """
        self._validate_id(condition_id, "condition_id")
        options = options or FetchOptions()

        params: dict[str, str] = {"condition_id": condition_id}

        cache_key = generate_cache_key(
            symbol=condition_id,
            source="polymarket_data_holders",
        )

        def _fetch() -> list[dict[str, Any]]:
            data = self._data_request("/holders", params=params)
            return data if isinstance(data, list) else []

        holders = self._fetch_cached(
            cache_key=cache_key,
            ttl=OI_TRADES_TTL,
            options=options,
            fetch_fn=_fetch,
            log_label="holders",
            condition_id=condition_id,
        )
        logger.info(
            "Holders retrieved",
            condition_id=condition_id,
            count=len(holders),
        )
        return holders

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _fetch_cached[T](
        self,
        cache_key: str,
        ttl: int,
        options: FetchOptions,
        fetch_fn: Callable[[], T],
        serialize_fn: Callable[[T], Any] | None = None,
        deserialize_fn: Callable[[Any], T] | None = None,
        log_label: str = "",
        **log_kwargs: Any,
    ) -> T:
        """Cache-aside helper: read from cache or fetch and store.

        Parameters
        ----------
        cache_key : str
            The cache key.
        ttl : int
            Cache time-to-live in seconds.
        options : FetchOptions
            Cache control options.
        fetch_fn : Callable[[], T]
            Function that fetches the data from the API.
        serialize_fn : Callable[[T], Any] | None
            Optional function to serialize data before caching.
            If None, data is cached as-is.
        deserialize_fn : Callable[[Any], T] | None
            Optional function to deserialize cached data.
            If None, cached data is returned as-is.
        log_label : str
            Label for log messages (e.g. "events", "midpoint").
        **log_kwargs : Any
            Additional keyword args for log messages.

        Returns
        -------
        T
            The fetched or cached data.
        """
        if options.use_cache and not options.force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {log_label}", **log_kwargs)
                return deserialize_fn(cached) if deserialize_fn else cached

        logger.debug(f"Fetching {log_label}", **log_kwargs)
        result = fetch_fn()

        cache_value = serialize_fn(result) if serialize_fn else result
        self._cache.set(cache_key, cache_value, ttl=ttl)
        return result

    def _gamma_request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Execute a request against the Gamma API.

        Parameters
        ----------
        path : str
            API endpoint path (e.g. ``"/events"``).
        params : dict[str, str] | None
            Optional query parameters.

        Returns
        -------
        Any
            Parsed JSON response (dict or list).
        """
        url = f"{self._config.gamma_base_url}{path}"
        return self._request(url, params=params)

    def _clob_request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Execute a request against the CLOB API.

        Parameters
        ----------
        path : str
            API endpoint path (e.g. ``"/midpoint"``).
        params : dict[str, str] | None
            Optional query parameters.

        Returns
        -------
        Any
            Parsed JSON response (dict or list).
        """
        url = f"{self._config.clob_base_url}{path}"
        return self._request(url, params=params)

    def _data_request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Execute a request against the Data API.

        Parameters
        ----------
        path : str
            API endpoint path (e.g. ``"/trades"``).
        params : dict[str, str] | None
            Optional query parameters.

        Returns
        -------
        Any
            Parsed JSON response (dict or list).
        """
        url = f"{self._config.data_base_url}{path}"
        return self._request(url, params=params)

    def _request(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Execute an API request via the session.

        Parameters
        ----------
        url : str
            Full API endpoint URL.
        params : dict[str, str] | None
            Optional query parameters.

        Returns
        -------
        Any
            Parsed JSON response body.

        Raises
        ------
        PolymarketAPIError
            If the API returns an error.
        """
        response = self._session.get_with_retry(url, params=params)
        result: Any = response.json()
        return result

    def _validate_id(self, value: str, field_name: str) -> None:
        """Validate a non-empty string identifier.

        Parameters
        ----------
        value : str
            The identifier value to validate.
        field_name : str
            The field name for error context.

        Raises
        ------
        PolymarketValidationError
            If the value is empty, whitespace-only, or contains
            invalid characters (path traversal prevention).

        Notes
        -----
        Allowed pattern: ``^[a-zA-Z0-9_\\-]{1,256}$``
        (alphanumerics, underscores, and hyphens; max 256 characters).
        This prevents path traversal attacks (CWE-20).
        """
        if not value or not value.strip():
            raise PolymarketValidationError(
                message=f"{field_name} must not be empty",
                field=field_name,
                value=value,
            )
        if not self._SAFE_ID_RE.match(value):
            raise PolymarketValidationError(
                message=f"{field_name} contains invalid characters: '{value}'",
                field=field_name,
                value=value,
            )

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Validate pagination parameters.

        Parameters
        ----------
        limit : int
            Maximum number of results.
        offset : int
            Pagination offset.

        Raises
        ------
        PolymarketValidationError
            If limit or offset is invalid.
        """
        if limit < 1 or limit > MAX_LIMIT:
            raise PolymarketValidationError(
                message=f"limit must be between 1 and {MAX_LIMIT}, got {limit}",
                field="limit",
                value=limit,
            )
        if offset < 0:
            raise PolymarketValidationError(
                message=f"offset must be non-negative, got {offset}",
                field="offset",
                value=offset,
            )

    def _validate_token_ids(self, token_ids: list[str]) -> None:
        """Validate a list of token IDs.

        Parameters
        ----------
        token_ids : list[str]
            List of token identifiers.

        Raises
        ------
        PolymarketValidationError
            If the list is empty or contains empty strings.
        """
        if not token_ids:
            raise PolymarketValidationError(
                message="token_ids must not be empty",
                field="token_ids",
                value=token_ids,
            )
        for tid in token_ids:
            self._validate_id(tid, "token_ids[n]")

    def _parse_orderbook(self, data: Any, token_id: str) -> OrderBook:
        """Parse raw API response into an OrderBook model.

        Parameters
        ----------
        data : Any
            Raw order book data from the API.
        token_id : str
            Token identifier for the order book.

        Returns
        -------
        OrderBook
            Parsed order book with bids and asks.
        """
        if not isinstance(data, dict):
            return OrderBook(
                market="",
                asset_id=token_id,
                bids=[],
                asks=[],
            )

        bids: list[OrderBookLevel] = []
        for bid in data.get("bids", []):
            if isinstance(bid, dict):
                bids.append(OrderBookLevel.model_validate(bid))

        asks: list[OrderBookLevel] = []
        for ask in data.get("asks", []):
            if isinstance(ask, dict):
                asks.append(OrderBookLevel.model_validate(ask))

        return OrderBook(
            market=str(data.get("market", "")),
            asset_id=str(data.get("asset_id", token_id)),
            bids=bids,
            asks=asks,
        )


__all__ = ["PolymarketClient"]
