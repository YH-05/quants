"""Data collection orchestrator for Polymarket prediction market data.

This module provides the ``PolymarketCollector`` class that coordinates
data fetching from ``PolymarketClient`` and persistence via
``PolymarketStorage``. It supports full collection (``collect_all``)
as well as individual collection methods for each data type.

The ``CollectionResult`` frozen dataclass captures collection statistics
including counts per data type, error messages, and timing information.

Examples
--------
>>> from market.polymarket.client import PolymarketClient
>>> from market.polymarket.storage import get_polymarket_storage
>>> from market.polymarket.collector import PolymarketCollector
>>> client = PolymarketClient()
>>> storage = get_polymarket_storage()
>>> collector = PolymarketCollector(client=client, storage=storage)
>>> result = collector.collect_all()
>>> print(f"Collected {result.total_collected} items")

See Also
--------
market.polymarket.client : API client providing data fetch methods.
market.polymarket.storage : Storage layer for persisting collected data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.polymarket.client import PolymarketClient
    from market.polymarket.models import PolymarketEvent
    from market.polymarket.storage import PolymarketStorage
    from market.polymarket.types import PriceInterval

logger = get_logger(__name__)


# ============================================================================
# CollectionResult dataclass
# ============================================================================


@dataclass(frozen=True)
class CollectionResult:
    """Statistics from a Polymarket data collection run.

    This frozen dataclass captures the outcome of a collection operation
    including per-type counts, error messages, and timing information.
    All count fields default to ``0`` and errors defaults to an empty tuple.

    Parameters
    ----------
    events_collected : int
        Number of events collected and persisted.
    markets_collected : int
        Number of markets collected and persisted.
    price_histories_collected : int
        Number of price history records collected and persisted.
    trades_collected : int
        Number of trades collected and persisted.
    oi_snapshots_collected : int
        Number of open interest snapshots collected and persisted.
    orderbook_snapshots_collected : int
        Number of order book snapshots collected and persisted.
    leaderboard_collected : int
        Number of leaderboard snapshots collected.
    holders_collected : int
        Number of holder records collected and persisted.
    errors : tuple[str, ...]
        Tuple of error messages encountered during collection.
    started_at : datetime
        Timestamp when collection started.
    finished_at : datetime | None
        Timestamp when collection finished. ``None`` if not yet finished.

    Examples
    --------
    >>> result = CollectionResult(events_collected=5, markets_collected=10)
    >>> result.total_collected
    15
    >>> result.has_errors
    False
    """

    events_collected: int = 0
    markets_collected: int = 0
    price_histories_collected: int = 0
    trades_collected: int = 0
    oi_snapshots_collected: int = 0
    orderbook_snapshots_collected: int = 0
    leaderboard_collected: int = 0
    holders_collected: int = 0
    errors: tuple[str, ...] = ()
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    finished_at: datetime | None = None

    @property
    def total_collected(self) -> int:
        """Return the total number of items collected across all types.

        Returns
        -------
        int
            Sum of all ``*_collected`` counts.
        """
        return (
            self.events_collected
            + self.markets_collected
            + self.price_histories_collected
            + self.trades_collected
            + self.oi_snapshots_collected
            + self.orderbook_snapshots_collected
            + self.leaderboard_collected
            + self.holders_collected
        )

    @property
    def has_errors(self) -> bool:
        """Return whether any errors occurred during collection.

        Returns
        -------
        bool
            ``True`` if the ``errors`` tuple is non-empty.
        """
        return len(self.errors) > 0


# ============================================================================
# PolymarketCollector class
# ============================================================================


class PolymarketCollector:
    """Orchestrator for collecting Polymarket data via Client -> Storage flow.

    Coordinates data fetching from ``PolymarketClient`` and persistence
    via ``PolymarketStorage``. Provides ``collect_all()`` for full
    collection and individual methods for each data type.

    Parameters
    ----------
    client : PolymarketClient
        API client for fetching Polymarket data.
    storage : PolymarketStorage
        Storage layer for persisting collected data.

    Examples
    --------
    >>> collector = PolymarketCollector(client=client, storage=storage)
    >>> result = collector.collect_all()
    >>> print(result.total_collected)
    """

    def __init__(
        self,
        client: PolymarketClient,
        storage: PolymarketStorage,
    ) -> None:
        """Initialize collector with client and storage.

        The internal ``_errors`` list is reset at the start of each
        ``collect_all()`` call.
        """
        self._client = client
        self._storage = storage
        self._errors: list[str] = []
        logger.info("PolymarketCollector initialized")

    # ------------------------------------------------------------------
    # Individual collect methods
    # ------------------------------------------------------------------

    def collect_events(
        self,
        *,
        limit: int = 100,
        active: bool | None = None,
        closed: bool | None = None,
    ) -> tuple[int, list[PolymarketEvent]]:
        """Collect events from the API and persist to storage.

        Fetches events via ``client.get_events()`` and saves them
        via ``storage.upsert_events()`` with cascading market/token saves.

        Parameters
        ----------
        limit : int
            Maximum number of events to fetch (default: 100).
        active : bool | None
            If ``True``, request only active events from the Gamma API.
            If ``None``, no active filter is applied.
        closed : bool | None
            If ``False``, request only non-closed events from the Gamma API.
            If ``None``, no closed filter is applied.

        Returns
        -------
        tuple[int, list[PolymarketEvent]]
            Tuple of (count, events_list). On failure returns ``(0, [])``.
        """
        logger.info("Collecting events", limit=limit, active=active, closed=closed)
        try:
            events = self._client.get_events(
                limit=limit,
                active=active,
                closed=closed,
            )
            if not events:
                logger.info("No events found")
                return 0, []

            fetched_at = datetime.now(tz=UTC).isoformat()
            self._storage.upsert_events(events, fetched_at=fetched_at)
            logger.info("Events collected and saved", count=len(events))
            return len(events), events
        except Exception as exc:
            logger.error("Failed to collect events", exc_info=True)
            self._errors.append("Failed to collect events")
            return 0, []

    def collect_price_history(
        self,
        token_id: str,
        *,
        interval: str | PriceInterval = "1d",
    ) -> int:
        """Collect price history for a token and persist to storage.

        Fetches price history via ``client.get_prices_history()`` and
        extracts ``PricePoint`` data from the result's DataFrame.

        Parameters
        ----------
        token_id : str
            The token identifier to collect price history for.
        interval : str | PriceInterval
            Price interval (default: ``"1d"``). Accepts both string and
            ``PriceInterval`` enum values.

        Returns
        -------
        int
            Number of price points collected, or ``0`` on failure.
        """
        from market.polymarket.models import PricePoint
        from market.polymarket.types import PriceInterval

        logger.info(
            "Collecting price history",
            token_id=token_id,
            interval=str(interval),
        )
        try:
            price_interval = (
                interval
                if isinstance(interval, PriceInterval)
                else PriceInterval(interval)
            )
            result = self._client.get_prices_history(token_id, interval=price_interval)
            df = result.data
            if df.empty:
                logger.info("No price history data", token_id=token_id)
                return 0

            # Convert DataFrame to PricePoint list (vectorized extraction)
            records = df[["timestamp", "price"]].to_dict("records")
            points: list[PricePoint] = [
                PricePoint(t=int(r["timestamp"]), p=float(r["price"])) for r in records
            ]

            fetched_at = datetime.now(tz=UTC).isoformat()
            self._storage.upsert_price_history(
                token_id,
                points,
                price_interval,
                fetched_at=fetched_at,
            )
            logger.info(
                "Price history collected and saved",
                token_id=token_id,
                count=len(points),
            )
            return len(points)
        except Exception as exc:
            logger.error(
                "Failed to collect price history", token_id=token_id, exc_info=True
            )
            self._errors.append(f"Failed to collect price history for token {token_id}")
            return 0

    def collect_trades(
        self,
        condition_id: str,
        *,
        limit: int = 100,
    ) -> int:
        """Collect trades for a market and persist to storage.

        Fetches trades via ``client.get_trades()`` and saves them
        via ``storage.upsert_trades()``.

        Parameters
        ----------
        condition_id : str
            The market condition ID to collect trades for.
        limit : int
            Maximum number of trades to fetch (default: 100).

        Returns
        -------
        int
            Number of trades collected, or ``0`` on failure.
        """
        logger.info(
            "Collecting trades",
            condition_id=condition_id,
            limit=limit,
        )
        try:
            trades = self._client.get_trades(condition_id, limit=limit)
            if not trades:
                logger.info("No trades found", condition_id=condition_id)
                return 0

            fetched_at = datetime.now(tz=UTC).isoformat()
            self._storage.upsert_trades(trades, fetched_at=fetched_at)
            logger.info(
                "Trades collected and saved",
                condition_id=condition_id,
                count=len(trades),
            )
            return len(trades)
        except Exception as exc:
            logger.error(
                "Failed to collect trades", condition_id=condition_id, exc_info=True
            )
            self._errors.append(f"Failed to collect trades for market {condition_id}")
            return 0

    def collect_open_interest(self, condition_id: str) -> int:
        """Collect open interest snapshot for a market and persist to storage.

        Fetches OI data via ``client.get_open_interest()`` and saves
        as a JSON snapshot via ``storage.insert_oi_snapshot()``.

        If the OI endpoint returns HTTP 404 (deprecated / unavailable),
        the error is logged as a warning and collection is skipped
        without recording it as a collection error.

        Parameters
        ----------
        condition_id : str
            The market condition ID to collect OI for.

        Returns
        -------
        int
            ``1`` on success, ``0`` on failure or skip.
        """
        from market.polymarket.errors import PolymarketAPIError

        logger.info("Collecting open interest", condition_id=condition_id)
        try:
            oi_data = self._client.get_open_interest(condition_id)
            if not oi_data:
                logger.info("No OI data found", condition_id=condition_id)
                return 0

            fetched_at = datetime.now(tz=UTC).isoformat()
            self._storage.insert_oi_snapshot(
                condition_id,
                oi_data,
                fetched_at=fetched_at,
            )
            logger.info("OI snapshot collected and saved", condition_id=condition_id)
            return 1
        except PolymarketAPIError as exc:
            if exc.status_code == 404:
                logger.warning(
                    "OI endpoint returned 404, skipping (endpoint may be deprecated)",
                    condition_id=condition_id,
                    url=exc.url,
                )
                return 0
            logger.error(
                "Failed to collect OI", condition_id=condition_id, exc_info=True
            )
            self._errors.append(f"Failed to collect OI for market {condition_id}")
            return 0
        except Exception as exc:
            logger.error(
                "Failed to collect OI", condition_id=condition_id, exc_info=True
            )
            self._errors.append(f"Failed to collect OI for market {condition_id}")
            return 0

    def collect_orderbooks(self, token_ids: list[str]) -> int:
        """Collect order book snapshots for multiple tokens.

        Iterates over the given token IDs, fetches each order book
        via ``client.get_orderbook()``, and saves each snapshot via
        ``storage.insert_orderbook_snapshot()``. Errors on individual
        tokens are logged as warnings and do not halt the overall process.

        For closed or inactive markets the CLOB API may return errors
        (no active orderbook). These are downgraded to warnings and
        not recorded as collection errors.

        Parameters
        ----------
        token_ids : list[str]
            List of token IDs to collect order books for.

        Returns
        -------
        int
            Number of order book snapshots successfully collected.
        """
        from market.polymarket.errors import PolymarketAPIError

        logger.info("Collecting orderbooks", token_count=len(token_ids))
        collected = 0
        for token_id in token_ids:
            try:
                orderbook = self._client.get_orderbook(token_id)
                fetched_at = datetime.now(tz=UTC).isoformat()
                self._storage.insert_orderbook_snapshot(
                    orderbook,
                    fetched_at=fetched_at,
                )
                collected += 1
                logger.debug("Orderbook snapshot saved", token_id=token_id)
            except PolymarketAPIError as exc:
                # Closed/inactive markets often have no orderbook -- skip gracefully
                logger.warning(
                    "Orderbook unavailable (API error), skipping",
                    token_id=token_id,
                    status_code=exc.status_code,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to collect orderbook, skipping",
                    token_id=token_id,
                    error=str(exc),
                )

        logger.info("Orderbooks collected", total=collected)
        return collected

    def collect_leaderboard(self, *, limit: int = 100) -> int:
        """Collect leaderboard snapshot and persist to storage.

        Fetches leaderboard data via ``client.get_leaderboard()``
        and saves it as a JSON snapshot via
        ``storage.insert_leaderboard_snapshot()``.

        If the leaderboard endpoint returns HTTP 404 (deprecated),
        the error is logged as a warning and collection is skipped
        without recording it as a collection error.

        Parameters
        ----------
        limit : int
            Maximum number of leaderboard entries (default: 100).

        Returns
        -------
        int
            ``1`` on success, ``0`` on failure or skip.
        """
        from market.polymarket.errors import PolymarketAPIError

        logger.info("Collecting leaderboard", limit=limit)
        try:
            entries = self._client.get_leaderboard(limit=limit)
            if not entries:
                logger.info("No leaderboard entries found")
                return 0

            fetched_at = datetime.now(tz=UTC).isoformat()
            self._storage.insert_leaderboard_snapshot(
                entries,
                fetched_at=fetched_at,
            )
            logger.info("Leaderboard snapshot collected and saved")
            return 1
        except PolymarketAPIError as exc:
            if exc.status_code == 404:
                logger.warning(
                    "Leaderboard endpoint returned 404, skipping "
                    "(endpoint may be deprecated)",
                    url=exc.url,
                )
                return 0
            logger.error("Failed to collect leaderboard", exc_info=True)
            self._errors.append("Failed to collect leaderboard")
            return 0
        except Exception as exc:
            logger.error("Failed to collect leaderboard", exc_info=True)
            self._errors.append("Failed to collect leaderboard")
            return 0

    def collect_holders(self, condition_ids: list[str]) -> int:
        """Collect holder data for multiple markets and persist to storage.

        Iterates over the given condition IDs, fetches holder data
        via ``client.get_holders()``, and saves via
        ``storage.upsert_holders()``. Errors on individual markets
        are logged and recorded but do not halt the overall process.

        Parameters
        ----------
        condition_ids : list[str]
            List of market condition IDs to collect holders for.

        Returns
        -------
        int
            Number of markets for which holders were successfully collected.
        """
        logger.info("Collecting holders", condition_count=len(condition_ids))
        collected = 0
        for condition_id in condition_ids:
            try:
                holders = self._client.get_holders(condition_id)
                self._storage.upsert_holders(condition_id, holders)
                collected += 1
                logger.debug("Holders saved", condition_id=condition_id)
            except Exception as exc:
                logger.error(
                    "Failed to collect holders",
                    condition_id=condition_id,
                    exc_info=True,
                )
                self._errors.append(
                    f"Failed to collect holders for market {condition_id}"
                )

        logger.info("Holders collected", total=collected)
        return collected

    # ------------------------------------------------------------------
    # Full collection
    # ------------------------------------------------------------------

    def collect_all(
        self,
        *,
        event_limit: int = 100,
        active_only: bool = True,
    ) -> CollectionResult:
        """Execute full data collection pipeline.

        Collects all data types in sequence:
        events -> price_history -> trades -> OI -> orderbooks ->
        leaderboard -> holders.

        Market-level data (trades, OI, orderbooks, holders) is collected
        for all markets discovered during event collection.

        Parameters
        ----------
        event_limit : int
            Maximum number of events to fetch (default: 100).
        active_only : bool
            If ``True`` (default), collect only active, non-closed events.
            Set to ``False`` to collect all events regardless of status.

        Returns
        -------
        CollectionResult
            Frozen dataclass with collection statistics and any errors.
        """
        started_at = datetime.now(tz=UTC)
        self._errors = []

        logger.info(
            "Starting full Polymarket data collection",
            active_only=active_only,
        )

        # Step 1: Collect events (includes cascading markets + tokens)
        active_flag = True if active_only else None
        closed_flag = False if active_only else None
        events_count, collected_events = self.collect_events(
            limit=event_limit,
            active=active_flag,
            closed=closed_flag,
        )

        # Extract condition_ids and token_ids from collected events
        condition_ids: list[str] = []
        token_ids: list[str] = []
        markets_count = 0

        for event in collected_events:
            for market in event.markets:
                if market.condition_id:
                    condition_ids.append(market.condition_id)
                markets_count += 1
                for tok in market.tokens:
                    tok_id = tok.get("token_id")
                    if tok_id:
                        token_ids.append(str(tok_id))

        logger.info(
            "Discovered markets and tokens",
            condition_ids_count=len(condition_ids),
            token_ids_count=len(token_ids),
        )

        # Step 2: Collect price history for each token
        price_histories_count = 0
        for token_id in token_ids:
            price_histories_count += self.collect_price_history(token_id)

        # Step 3: Collect trades for each market
        trades_count = 0
        for cid in condition_ids:
            trades_count += self.collect_trades(cid)

        # Step 4: Collect OI for each market
        oi_count = 0
        for cid in condition_ids:
            oi_count += self.collect_open_interest(cid)

        # Step 5: Collect orderbooks for each token
        orderbooks_count = self.collect_orderbooks(token_ids)

        # Step 6: Collect leaderboard
        leaderboard_count = self.collect_leaderboard()

        # Step 7: Collect holders for each market
        holders_count = self.collect_holders(condition_ids)

        finished_at = datetime.now(tz=UTC)

        result = CollectionResult(
            events_collected=events_count,
            markets_collected=markets_count,
            price_histories_collected=price_histories_count,
            trades_collected=trades_count,
            oi_snapshots_collected=oi_count,
            orderbook_snapshots_collected=orderbooks_count,
            leaderboard_collected=leaderboard_count,
            holders_collected=holders_count,
            errors=tuple(self._errors),
            started_at=started_at,
            finished_at=finished_at,
        )

        logger.info(
            "Full collection completed",
            total_collected=result.total_collected,
            error_count=len(result.errors),
            duration_seconds=(finished_at - started_at).total_seconds(),
        )

        return result


__all__ = [
    "CollectionResult",
    "PolymarketCollector",
]
