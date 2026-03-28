"""CLI entry point for Polymarket data collection.

Provides periodic and on-demand data collection from Polymarket APIs
(Gamma, CLOB, Data) into the local SQLite database.

Examples
--------
Full collection (active events only):
    $ uv run python -m market.polymarket

Show database status:
    $ uv run python -m market.polymarket --status

Collect with custom event limit:
    $ uv run python -m market.polymarket --event-limit 50

Include closed events:
    $ uv run python -m market.polymarket --all-events

See Also
--------
market.polymarket.collector : Collection orchestrator.
market.polymarket.storage : SQLite persistence layer.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from utils_core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger(__name__)


# ============================================================================
# Sub-commands
# ============================================================================


def _show_status() -> int:
    """Show current database statistics.

    Returns
    -------
    int
        Exit code (0 on success, 1 on failure).
    """
    from market.polymarket.storage import get_polymarket_storage

    logger.info("Showing Polymarket DB status")
    try:
        storage = get_polymarket_storage()
        stats = storage.get_stats()
        summary = storage.get_collection_summary()

        print("=== Polymarket DB Status ===")
        print(f"Total records: {summary['total_records']}")
        print(f"Events:        {stats.get('pm_events', 0)}")
        print(f"Markets:       {stats.get('pm_markets', 0)}")
        print(f"Tokens:        {stats.get('pm_tokens', 0)}")
        print(f"Price history: {stats.get('pm_price_history', 0)}")
        print(f"Trades:        {stats.get('pm_trades', 0)}")
        print(f"OI snapshots:  {stats.get('pm_oi_snapshots', 0)}")
        print(f"Orderbooks:    {stats.get('pm_orderbook_snapshots', 0)}")
        print(f"Leaderboard:   {stats.get('pm_leaderboard_snapshots', 0)}")
        return 0
    except Exception as exc:
        logger.error("Failed to show status", exc_info=True)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_collect(*, event_limit: int, active_only: bool) -> int:
    """Run full data collection pipeline.

    Parameters
    ----------
    event_limit : int
        Maximum number of events to fetch.
    active_only : bool
        If True, collect only active (non-closed) events.

    Returns
    -------
    int
        Exit code (0 on success, 1 on failure).
    """
    from market.polymarket.client import PolymarketClient
    from market.polymarket.collector import PolymarketCollector
    from market.polymarket.storage import get_polymarket_storage

    logger.info(
        "Starting Polymarket collection",
        event_limit=event_limit,
        active_only=active_only,
    )

    try:
        client = PolymarketClient()
        storage = get_polymarket_storage()
        collector = PolymarketCollector(client=client, storage=storage)

        result = collector.collect_all(
            event_limit=event_limit,
            active_only=active_only,
        )

        duration = (
            (result.finished_at - result.started_at).total_seconds()
            if result.finished_at
            else 0
        )

        print("=== Collection Result ===")
        print(f"Events:        {result.events_collected}")
        print(f"Markets:       {result.markets_collected}")
        print(f"Price history: {result.price_histories_collected}")
        print(f"Trades:        {result.trades_collected}")
        print(f"OI snapshots:  {result.oi_snapshots_collected}")
        print(f"Orderbooks:    {result.orderbook_snapshots_collected}")
        print(f"Leaderboard:   {result.leaderboard_collected}")
        print(f"Holders:       {result.holders_collected}")
        print(f"Total:         {result.total_collected}")
        print(f"Duration:      {duration:.1f}s")

        if result.has_errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")
            logger.warning(
                "Collection completed with errors",
                error_count=len(result.errors),
            )
            return 1

        logger.info(
            "Collection completed successfully",
            total=result.total_collected,
            duration_seconds=duration,
        )
        return 0

    except Exception as exc:
        logger.error("Collection failed", exc_info=True)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


# ============================================================================
# Argument parsing
# ============================================================================


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    argv : Sequence[str] | None
        Argument list. Uses ``sys.argv`` when ``None``.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m market.polymarket",
        description="Polymarket prediction market data collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full collection (active events, default 100)
  uv run python -m market.polymarket

  # Show DB status
  uv run python -m market.polymarket --status

  # Collect top 50 events
  uv run python -m market.polymarket --event-limit 50

  # Include closed/resolved events
  uv run python -m market.polymarket --all-events
        """,
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show database statistics and exit",
    )
    parser.add_argument(
        "--event-limit",
        type=int,
        default=100,
        help="Maximum number of events to collect (default: 100)",
    )
    parser.add_argument(
        "--all-events",
        action="store_true",
        help="Include closed/resolved events (default: active only)",
    )

    return parser.parse_args(argv)


# ============================================================================
# Main
# ============================================================================


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Parameters
    ----------
    argv : Sequence[str] | None
        Argument list for testing. Uses ``sys.argv`` when ``None``.

    Returns
    -------
    int
        Exit code (0: success, 1: failure).
    """
    args = parse_args(argv)

    if args.status:
        return _show_status()

    return _run_collect(
        event_limit=args.event_limit,
        active_only=not args.all_events,
    )


if __name__ == "__main__":
    sys.exit(main())
