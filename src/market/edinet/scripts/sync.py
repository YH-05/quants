"""CLI script for syncing EDINET DB data to local DuckDB database.

This script provides command-line interface for managing EDINET data sync.
Supports initial 5-phase sync, daily incremental updates, resume from
checkpoint, status checking, and single company sync.

Follows the FRED ``sync_historical.py`` pattern.

Synced data
-----------
- **FinancialRecord** — 30 fields (2 required keys + 28 Optional indicators).
  All financial indicator fields are ``Optional`` because the API returns
  different field sets depending on the accounting standard
  (JP GAAP / US GAAP / IFRS).
- **RatioRecord** — 21 fields (2 required keys + 19 Optional ratios).
  Includes profitability, balance-sheet, dividend, efficiency, per-share,
  valuation, cash-flow, per-employee metrics, and adjustment factors.

Field definitions are verified against the official EDINET DB API
(see ``docs/project/project-70/step0-api-verification.json``).

Schema migration
----------------
When the DuckDB schema does not match the current dataclass definitions
(e.g. after a field rename or addition), ``EdinetStorage`` automatically
applies ``ALTER TABLE`` migrations on first access. Old column names
(``operating_cf``, ``investing_cf``, ``financing_cf``, ``employees``,
``rnd_expense``) are renamed to their new counterparts, and missing
columns are added with ``NULL`` defaults.

Examples
--------
Run initial 6-phase sync:
    $ uv run python -m market.edinet.scripts.sync --initial

Run daily incremental sync:
    $ uv run python -m market.edinet.scripts.sync --daily

Resume interrupted sync:
    $ uv run python -m market.edinet.scripts.sync --resume

Check sync status:
    $ uv run python -m market.edinet.scripts.sync --status

Sync single company:
    $ uv run python -m market.edinet.scripts.sync --company E00001

Custom DB path:
    $ uv run python -m market.edinet.scripts.sync --initial --db-path /data/edinet.duckdb

See Also
--------
market.edinet.syncer : EdinetSyncer orchestrator.
market.edinet.storage : EdinetStorage with schema migration support.
market.edinet.types : EdinetConfig configuration, FinancialRecord, RatioRecord.
market.fred.scripts.sync_historical : Reference implementation.
"""

import argparse
import os
import sys
from pathlib import Path

from utils_core.logging import get_logger

from ..syncer import EdinetSyncer
from ..types import EdinetConfig

logger = get_logger(__name__, module="edinet_sync")


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Parameters
    ----------
    args : list[str] | None
        Command line arguments. If None, uses sys.argv[1:].

    Returns
    -------
    argparse.Namespace
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Sync EDINET DB data to local DuckDB database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Initial 6-phase sync:
    %(prog)s --initial

  Daily incremental sync:
    %(prog)s --daily

  Resume interrupted sync:
    %(prog)s --resume

  Check sync status:
    %(prog)s --status

  Sync single company:
    %(prog)s --company E00001

  Run specific phase only:
    %(prog)s --initial --phase companies

  Custom DB path:
    %(prog)s --initial --db-path /data/edinet.duckdb
""",
    )

    # Sync mode options
    sync_group = parser.add_argument_group("Sync Options")
    sync_group.add_argument(
        "--initial",
        action="store_true",
        help="Run initial 5-phase sync (companies -> industries -> "
        "company_details -> financials_ratios -> text_blocks)",
    )
    sync_group.add_argument(
        "--daily",
        action="store_true",
        help="Run daily incremental sync (companies + financials_ratios + text_blocks)",
    )
    sync_group.add_argument(
        "--resume",
        action="store_true",
        help="Resume sync from last checkpoint",
    )
    sync_group.add_argument(
        "--status",
        action="store_true",
        help="Show current sync status",
    )
    sync_group.add_argument(
        "--company",
        type=str,
        metavar="CODE",
        help="Sync a single company by EDINET code (e.g. E00001)",
    )

    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--phase",
        type=str,
        metavar="NAME",
        help="Run a specific phase only (e.g. companies, industries, rankings)",
    )
    config_group.add_argument(
        "--db-path",
        type=str,
        metavar="PATH",
        help="Custom DuckDB database file path",
    )

    return parser.parse_args(args)


def run_sync(args: argparse.Namespace) -> int:
    """Execute the sync operation based on arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments

    Returns
    -------
    int
        Exit code (0 for success, 1 for failure)
    """
    # Build EdinetConfig
    api_key = os.environ.get("EDINET_DB_API_KEY", "")
    db_path = Path(args.db_path) if args.db_path else None

    config = EdinetConfig(api_key=api_key, db_path=db_path)
    syncer = EdinetSyncer(config=config)

    # Handle --status
    if args.status:
        return _show_status(syncer)

    # Handle --initial
    if args.initial:
        return _run_initial(syncer)

    # Handle --daily
    if args.daily:
        return _run_daily(syncer)

    # Handle --resume
    if args.resume:
        return _run_resume(syncer)

    # Handle --company
    if args.company:
        return _run_company(syncer, args.company)

    # No option specified
    print(
        "Error: Please specify one of --initial, --daily, --resume, --status, "
        "or --company.",
        file=sys.stderr,
    )
    return 1


def _show_status(syncer: EdinetSyncer) -> int:
    """Show current sync status.

    Parameters
    ----------
    syncer : EdinetSyncer
        Syncer instance

    Returns
    -------
    int
        Exit code
    """
    status = syncer.get_status()

    print("\nEDINET DB Sync Status")
    print("=" * 60)
    print(f"Current phase: {status['current_phase']}")
    print(f"Completed codes: {status['completed_codes_count']}")
    print(f"Today API calls: {status['today_api_calls']}")
    print(f"Remaining API calls: {status['remaining_api_calls']}")
    print(f"Errors: {status['errors_count']}")

    db_stats = status.get("db_stats", {})
    if db_stats:
        print("\nDatabase Statistics:")
        print("-" * 60)
        for table_name, count in sorted(db_stats.items()):
            print(f"  {table_name:20} | {count:>8} rows")

    print()
    return 0


def _run_initial(syncer: EdinetSyncer) -> int:
    """Run initial 6-phase sync.

    Parameters
    ----------
    syncer : EdinetSyncer
        Syncer instance

    Returns
    -------
    int
        Exit code
    """
    logger.info("Starting initial sync")
    results = syncer.run_initial()

    success_count = sum(1 for r in results if r.success)
    total_count = len(results)

    print(f"\nInitial sync completed: {success_count}/{total_count} phases successful")

    for result in results:
        status_str = "OK" if result.success else "FAIL"
        print(
            f"  [{status_str}] {result.phase}: {result.companies_processed} processed"
        )
        if result.errors:
            for error in result.errors:
                print(f"         Error: {error}")
        if result.stopped_reason:
            print(f"         Stopped: {result.stopped_reason}")

    return 0 if all(r.success for r in results) else 1


def _run_daily(syncer: EdinetSyncer) -> int:
    """Run daily incremental sync.

    Parameters
    ----------
    syncer : EdinetSyncer
        Syncer instance

    Returns
    -------
    int
        Exit code
    """
    logger.info("Starting daily sync")
    results = syncer.run_daily()

    success_count = sum(1 for r in results if r.success)
    total_count = len(results)

    print(f"\nDaily sync completed: {success_count}/{total_count} phases successful")

    for result in results:
        status_str = "OK" if result.success else "FAIL"
        print(
            f"  [{status_str}] {result.phase}: {result.companies_processed} processed"
        )

    return 0 if all(r.success for r in results) else 1


def _run_resume(syncer: EdinetSyncer) -> int:
    """Resume sync from last checkpoint.

    Parameters
    ----------
    syncer : EdinetSyncer
        Syncer instance

    Returns
    -------
    int
        Exit code
    """
    logger.info("Resuming sync from checkpoint")
    results = syncer.resume()

    success_count = sum(1 for r in results if r.success)
    total_count = len(results)

    print(f"\nResume sync completed: {success_count}/{total_count} phases successful")

    for result in results:
        status_str = "OK" if result.success else "FAIL"
        print(
            f"  [{status_str}] {result.phase}: {result.companies_processed} processed"
        )
        if result.errors:
            for error in result.errors:
                print(f"         Error: {error}")
        if result.stopped_reason:
            print(f"         Stopped: {result.stopped_reason}")

    return 0 if all(r.success for r in results) else 1


def _run_company(syncer: EdinetSyncer, code: str) -> int:
    """Sync a single company.

    Parameters
    ----------
    syncer : EdinetSyncer
        Syncer instance
    code : str
        EDINET code

    Returns
    -------
    int
        Exit code
    """
    logger.info("Syncing single company", code=code)
    result = syncer.sync_company(code)

    if result.success:
        print(f"Company '{code}' synced successfully")
        return 0
    else:
        print(f"Failed to sync company '{code}'")
        if result.stopped_reason:
            print(f"  Reason: {result.stopped_reason}")
        for error in result.errors:
            print(f"  Error: {error}")
        return 1


def main() -> int:
    """Main entry point.

    Returns
    -------
    int
        Exit code
    """
    args = parse_args()
    return run_sync(args)


if __name__ == "__main__":
    sys.exit(main())
