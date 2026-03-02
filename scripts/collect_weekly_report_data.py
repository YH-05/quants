#!/usr/bin/env python3
"""Weekly Report Data Collection Script.

Collect market data compatible with wr-data-aggregator for the weekly market report.
This script is the canonical data source for `/generate-market-report --weekly` Phase 2.

It uses PerformanceAnalyzer4Agent, InterestRateAnalyzer4Agent, CurrencyAnalyzer4Agent,
and UpcomingEvents4Agent to produce fixed-name output files (no timestamps), with
return values converted from percentage form to decimal form.

Output files (fixed names, no timestamps):
- indices.json       : US index performance compatible with wr-data-aggregator
- mag7.json          : MAG7 + SOX performance (sorted by weekly_return desc)
- sectors.json       : Sector ETF performance (top/bottom/all, sorted by weekly_return desc)
- interest_rates.json: US interest rate data from InterestRateAnalyzer4Agent
- currencies.json    : JPY cross currency data from CurrencyAnalyzer4Agent
- upcoming_events.json: Upcoming earnings and economic events
- metadata.json      : Period, generation info, and mode

Examples
--------
Basic usage (auto-calculates period based on today's date):

    $ uv run python scripts/collect_weekly_report_data.py

Specify output directory:

    $ uv run python scripts/collect_weekly_report_data.py --output articles/weekly_report_20260122/data

Specify custom date range (compatible with weekly_comment_data.py):

    $ uv run python scripts/collect_weekly_report_data.py --start 2026-01-14 --end 2026-01-21

Notes
-----
- Period is Tuesday-to-Tuesday by default (via calculate_weekly_comment_period).
- Return values are converted: return_pct (%) / 100 -> decimal (e.g., 2.5 -> 0.025).
- yfinance .info calls use retry (max 3) with exponential backoff and null fallback.
- SOX (^SOX) is included in both indices.json and mag7.json.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yfinance as yf

from analyze.config.loader import get_symbol_group
from analyze.reporting.currency_agent import CurrencyAnalyzer4Agent
from analyze.reporting.interest_rate_agent import InterestRateAnalyzer4Agent
from analyze.reporting.performance_agent import PerformanceAnalyzer4Agent
from analyze.reporting.upcoming_events_agent import UpcomingEvents4Agent
from database.utils import (
    calculate_weekly_comment_period,
    format_date_japanese,
    format_date_us,
    get_logger,
    parse_date,
)

logger = get_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

SOX_TICKER = "^SOX"
SOX_NAME = "Philadelphia Semiconductor"

# Number of top/bottom sectors to include
TOP_BOTTOM_COUNT = 3

# yfinance retry settings
YFINANCE_MAX_RETRIES = 3
YFINANCE_BACKOFF_BASE = 2.0  # seconds


# =============================================================================
# Symbol Name Mapping Helpers
# =============================================================================


def _build_name_map(group: str, subgroup: str | None = None) -> dict[str, str]:
    """Build a ticker -> name mapping from symbols.yaml.

    Parameters
    ----------
    group : str
        Symbol group name.
    subgroup : str | None
        Optional subgroup name.

    Returns
    -------
    dict[str, str]
        Mapping from ticker to display name.
    """
    items = get_symbol_group(group, subgroup)
    return {item["symbol"]: item["name"] for item in items}


# =============================================================================
# yfinance Helpers with Retry
# =============================================================================


def fetch_market_caps(
    tickers: list[str],
    max_retries: int = YFINANCE_MAX_RETRIES,
) -> dict[str, int | None]:
    """Fetch market cap for each ticker using yfinance .info with retry.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols to fetch market cap for.
    max_retries : int
        Maximum number of retry attempts per ticker.

    Returns
    -------
    dict[str, int | None]
        Mapping from ticker to market cap (None if unavailable).
    """
    result: dict[str, int | None] = {}

    for ticker in tickers:
        market_cap: int | None = None
        for attempt in range(max_retries):
            try:
                info = yf.Ticker(ticker).info
                market_cap = info.get("marketCap")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = YFINANCE_BACKOFF_BASE**attempt
                    logger.warning(
                        "yfinance .info failed, retrying",
                        ticker=ticker,
                        attempt=attempt + 1,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "yfinance .info failed after all retries, using null fallback",
                        ticker=ticker,
                        error=str(e),
                    )
        result[ticker] = market_cap

    return result


def fetch_sector_weights(
    tickers: list[str],
    max_retries: int = YFINANCE_MAX_RETRIES,
) -> dict[str, dict[str, Any]]:
    """Fetch weight and top holdings for sector ETFs via yfinance .info.

    Parameters
    ----------
    tickers : list[str]
        List of sector ETF ticker symbols.
    max_retries : int
        Maximum number of retry attempts per ticker.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapping from ticker to {weight: float | None, top_holdings: list[str]}.
    """
    result: dict[str, dict[str, Any]] = {}

    for ticker in tickers:
        weight: float | None = None
        top_holdings: list[str] = []

        for attempt in range(max_retries):
            try:
                info = yf.Ticker(ticker).info
                # yfinance does not expose weight directly; set to None
                weight = None
                # top holdings are not reliably available from .info
                top_holdings = []
                _ = info  # suppress unused warning
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = YFINANCE_BACKOFF_BASE**attempt
                    logger.warning(
                        "yfinance sector info failed, retrying",
                        ticker=ticker,
                        attempt=attempt + 1,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "yfinance sector info failed after all retries",
                        ticker=ticker,
                        error=str(e),
                    )

        result[ticker] = {"weight": weight, "top_holdings": top_holdings}

    return result


# =============================================================================
# Adapter Functions
# =============================================================================


def _get_weekly_return(symbol_data: dict[str, float]) -> float | None:
    """Extract weekly return in decimal form from symbol performance data.

    Tries keys in order: "WoW", "1W".

    Parameters
    ----------
    symbol_data : dict[str, float]
        Period -> return_pct (percentage form) mapping.

    Returns
    -------
    float | None
        Weekly return as decimal, or None if unavailable.
    """
    for key in ("WoW", "1W"):
        if key in symbol_data:
            return symbol_data[key] / 100.0
    return None


def _get_ytd_return(symbol_data: dict[str, float]) -> float | None:
    """Extract YTD return in decimal form from symbol performance data.

    Parameters
    ----------
    symbol_data : dict[str, float]
        Period -> return_pct (percentage form) mapping.

    Returns
    -------
    float | None
        YTD return as decimal, or None if unavailable.
    """
    if "YTD" in symbol_data:
        return symbol_data["YTD"] / 100.0
    return None


def adapt_to_indices(
    perf_result: dict[str, Any],
    start_date: date,
    end_date: date,
    name_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Convert PerformanceResult dict to wr-data-aggregator compatible indices list.

    Converts return_pct from percentage to decimal form and renames fields.

    Parameters
    ----------
    perf_result : dict[str, Any]
        Output of PerformanceResult.to_dict() for indices/us group.
    start_date : date
        Period start date (used for change calculation context).
    end_date : date
        Period end date.
    name_map : dict[str, str] | None
        Override ticker -> name mapping. If None, loaded from symbols.yaml.

    Returns
    -------
    list[dict[str, Any]]
        List of index items with ticker, name, weekly_return (decimal),
        ytd_return (decimal), price, and change fields.
    """
    if name_map is None:
        name_map = _build_name_map("indices", "us")

    symbols_data: dict[str, dict[str, float]] = perf_result.get("symbols", {})
    result: list[dict[str, Any]] = []

    for ticker, period_data in symbols_data.items():
        name = name_map.get(ticker, ticker)
        weekly_return = _get_weekly_return(period_data)
        ytd_return = _get_ytd_return(period_data)

        # price and change: not available from PerformanceResult directly
        # (PerformanceResult only provides return_pct, not raw prices)
        # Set to None; downstream scripts can supplement if needed
        price: float | None = None
        change: float | None = None

        if price is not None and weekly_return is not None:
            # change = price_start * weekly_return = price / (1 + weekly_return) * weekly_return
            # Approximation: change = price * weekly_return (since weekly_return is small)
            change = price * weekly_return

        result.append(
            {
                "ticker": ticker,
                "name": name,
                "weekly_return": weekly_return,
                "ytd_return": ytd_return,
                "price": price,
                "change": change,
            }
        )

    logger.debug(
        "Adapted indices data",
        count=len(result),
        start_date=str(start_date),
        end_date=str(end_date),
    )
    return result


def adapt_to_mag7(
    mag7_perf_result: dict[str, Any],
    sox_perf: dict[str, Any] | None = None,
    market_caps: dict[str, int | None] | None = None,
    name_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Convert PerformanceResult dict to wr-data-aggregator compatible mag7 dict.

    Parameters
    ----------
    mag7_perf_result : dict[str, Any]
        Output of PerformanceResult.to_dict() for mag7 group.
    sox_perf : dict[str, Any] | None
        Optional PerformanceResult.to_dict() for indices/us group containing SOX data.
    market_caps : dict[str, int | None] | None
        Market cap data from fetch_market_caps(). If None, market_cap set to None.
    name_map : dict[str, str] | None
        Override ticker -> name mapping. If None, loaded from symbols.yaml.

    Returns
    -------
    dict[str, Any]
        MAG7 data with 'mag7' array (sorted by weekly_return desc) and 'sox' object.
    """
    if name_map is None:
        name_map = _build_name_map("mag7")

    symbols_data: dict[str, dict[str, float]] = mag7_perf_result.get("symbols", {})
    mag7_list: list[dict[str, Any]] = []

    for ticker, period_data in symbols_data.items():
        name = name_map.get(ticker, ticker)
        weekly_return = _get_weekly_return(period_data)
        ytd_return = _get_ytd_return(period_data)
        market_cap = market_caps.get(ticker) if market_caps else None

        mag7_list.append(
            {
                "ticker": ticker,
                "name": name,
                "weekly_return": weekly_return,
                "ytd_return": ytd_return,
                "price": None,
                "market_cap": market_cap,
            }
        )

    # Sort by weekly_return descending (None values go to end)
    mag7_list.sort(
        key=lambda x: x.get("weekly_return")
        if x.get("weekly_return") is not None
        else float("-inf"),
        reverse=True,
    )

    # Extract SOX from the us-indices performance result
    sox: dict[str, Any] | None = None
    if sox_perf is not None:
        sox_symbols: dict[str, dict[str, float]] = sox_perf.get("symbols", {})
        if SOX_TICKER in sox_symbols:
            sox_data = sox_symbols[SOX_TICKER]
            sox = {
                "ticker": SOX_TICKER,
                "name": SOX_NAME,
                "weekly_return": _get_weekly_return(sox_data),
                "ytd_return": _get_ytd_return(sox_data),
                "price": None,
            }

    logger.debug(
        "Adapted MAG7 data",
        mag7_count=len(mag7_list),
        has_sox=sox is not None,
    )

    return {
        "mag7": mag7_list,
        "sox": sox,
    }


def adapt_to_sectors(
    sectors_perf_result: dict[str, Any],
    sector_weights: dict[str, dict[str, Any]] | None = None,
    name_map: dict[str, str] | None = None,
    top_bottom_count: int = TOP_BOTTOM_COUNT,
) -> dict[str, Any]:
    """Convert PerformanceResult dict to wr-data-aggregator compatible sectors dict.

    Parameters
    ----------
    sectors_perf_result : dict[str, Any]
        Output of PerformanceResult.to_dict() for sectors group.
    sector_weights : dict[str, dict[str, Any]] | None
        Optional weight and top holdings per sector from fetch_sector_weights().
    name_map : dict[str, str] | None
        Override ticker -> name mapping. If None, loaded from symbols.yaml.
    top_bottom_count : int
        Number of top and bottom sectors to include.

    Returns
    -------
    dict[str, Any]
        Sectors data with top_sectors, bottom_sectors, all_sectors (all sorted desc).
    """
    if name_map is None:
        name_map = _build_name_map("sectors")

    symbols_data: dict[str, dict[str, float]] = sectors_perf_result.get("symbols", {})
    all_sectors: list[dict[str, Any]] = []

    for ticker, period_data in symbols_data.items():
        name = name_map.get(ticker, ticker)
        weekly_return = _get_weekly_return(period_data)
        ytd_return = _get_ytd_return(period_data)

        weight_info = sector_weights.get(ticker, {}) if sector_weights else {}
        weight = weight_info.get("weight")
        top_holdings = weight_info.get("top_holdings", [])

        all_sectors.append(
            {
                "ticker": ticker,
                "name": name,
                "weekly_return": weekly_return,
                "ytd_return": ytd_return,
                "weight": weight,
                "top_holdings": top_holdings,
            }
        )

    # Sort all_sectors by weekly_return descending (None values go to end)
    all_sectors.sort(
        key=lambda x: x.get("weekly_return")
        if x.get("weekly_return") is not None
        else float("-inf"),
        reverse=True,
    )

    top_sectors = all_sectors[:top_bottom_count]
    bottom_sectors = all_sectors[-top_bottom_count:][::-1]

    logger.debug(
        "Adapted sectors data",
        total_count=len(all_sectors),
        top_count=len(top_sectors),
        bottom_count=len(bottom_sectors),
    )

    return {
        "top_sectors": top_sectors,
        "bottom_sectors": bottom_sectors,
        "all_sectors": all_sectors,
    }


# =============================================================================
# 4Agent Wrapper Functions
# =============================================================================


def collect_interest_rates(
    output_dir: Path,
) -> dict[str, Any] | None:
    """Collect interest rate data and write interest_rates.json.

    Parameters
    ----------
    output_dir : Path
        Output directory for the JSON file.

    Returns
    -------
    dict[str, Any] | None
        Collected data dict, or None on failure.
    """
    try:
        logger.info("Collecting interest rate data")
        analyzer = InterestRateAnalyzer4Agent()
        result = analyzer.get_interest_rate_data()
        result_dict = result.to_dict()

        if result.data_freshness.get("has_date_gap"):
            logger.warning(
                "Date gap detected in interest rate data",
                newest_date=result.data_freshness.get("newest_date"),
                oldest_date=result.data_freshness.get("oldest_date"),
            )

        save_json(result_dict, output_dir / "interest_rates.json")
        logger.info("Interest rate data collected and saved")
        return result_dict

    except Exception as e:
        logger.error(
            "Failed to collect interest rate data", error=str(e), exc_info=True
        )
        return None


def collect_currencies(
    output_dir: Path,
) -> dict[str, Any] | None:
    """Collect currency data and write currencies.json.

    Parameters
    ----------
    output_dir : Path
        Output directory for the JSON file.

    Returns
    -------
    dict[str, Any] | None
        Collected data dict, or None on failure.
    """
    try:
        logger.info("Collecting currency data")
        analyzer = CurrencyAnalyzer4Agent()
        result = analyzer.get_currency_performance()
        result_dict = result.to_dict()

        if result.data_freshness.get("has_date_gap"):
            logger.warning(
                "Date gap detected in currency data",
                newest_date=result.data_freshness.get("newest_date"),
                oldest_date=result.data_freshness.get("oldest_date"),
            )

        save_json(result_dict, output_dir / "currencies.json")
        logger.info("Currency data collected and saved")
        return result_dict

    except Exception as e:
        logger.error("Failed to collect currency data", error=str(e), exc_info=True)
        return None


def collect_upcoming_events(
    output_dir: Path,
) -> dict[str, Any] | None:
    """Collect upcoming events data and write upcoming_events.json.

    Parameters
    ----------
    output_dir : Path
        Output directory for the JSON file.

    Returns
    -------
    dict[str, Any] | None
        Collected data dict, or None on failure.
    """
    try:
        logger.info("Collecting upcoming events data")
        agent = UpcomingEvents4Agent()
        result = agent.get_upcoming_events()
        result_dict = result.to_dict()

        save_json(result_dict, output_dir / "upcoming_events.json")
        logger.info("Upcoming events data collected and saved")
        return result_dict

    except Exception as e:
        logger.error(
            "Failed to collect upcoming events data", error=str(e), exc_info=True
        )
        return None


# =============================================================================
# JSON Utilities
# =============================================================================


def save_json(data: dict[str, Any], file_path: Path) -> None:
    """Save data to JSON file (UTF-8, pretty printed).

    Parameters
    ----------
    data : dict[str, Any]
        Data to save.
    file_path : Path
        Output file path.
    """
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Data saved", file=str(file_path))


# =============================================================================
# Orchestration
# =============================================================================


def collect_all_data(
    output_dir: Path,
    start_date: date,
    end_date: date,
) -> dict[str, bool]:
    """Collect all weekly report data and write fixed-name output files.

    Parameters
    ----------
    output_dir : Path
        Output directory for all JSON files.
    start_date : date
        Period start date.
    end_date : date
        Period end date.

    Returns
    -------
    dict[str, bool]
        Mapping from file name to success status.
    """
    logger.info(
        "Starting weekly report data collection",
        output_dir=str(output_dir),
        start_date=str(start_date),
        end_date=str(end_date),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, bool] = {}

    analyzer = PerformanceAnalyzer4Agent()

    # --- Collect US indices performance ---
    us_perf: dict[str, Any] | None = None
    try:
        us_result = analyzer.get_group_performance("indices", "us")
        us_perf = us_result.to_dict()

        indices_list = adapt_to_indices(us_perf, start_date, end_date)
        indices_output = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "indices": indices_list,
        }
        save_json(indices_output, output_dir / "indices.json")
        results["indices.json"] = True

        if us_result.data_freshness.get("has_date_gap"):
            logger.warning(
                "Date gap detected in US indices data",
                newest_date=us_result.data_freshness.get("newest_date"),
                oldest_date=us_result.data_freshness.get("oldest_date"),
            )
    except Exception as e:
        logger.error("Failed to collect US indices data", error=str(e), exc_info=True)
        results["indices.json"] = False

    # --- Collect MAG7 performance ---
    try:
        mag7_result = analyzer.get_group_performance("mag7")
        mag7_perf = mag7_result.to_dict()

        # Fetch market caps for MAG7 tickers
        mag7_tickers = list(mag7_perf.get("symbols", {}).keys())
        try:
            market_caps = fetch_market_caps(mag7_tickers)
        except Exception as e:
            logger.warning("Failed to fetch market caps", error=str(e))
            market_caps = {}

        mag7_output = adapt_to_mag7(
            mag7_perf,
            sox_perf=us_perf,
            market_caps=market_caps,
        )
        mag7_output["period"] = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        }
        save_json(mag7_output, output_dir / "mag7.json")
        results["mag7.json"] = True

        if mag7_result.data_freshness.get("has_date_gap"):
            logger.warning(
                "Date gap detected in MAG7 data",
                newest_date=mag7_result.data_freshness.get("newest_date"),
                oldest_date=mag7_result.data_freshness.get("oldest_date"),
            )
    except Exception as e:
        logger.error("Failed to collect MAG7 data", error=str(e), exc_info=True)
        results["mag7.json"] = False

    # --- Collect Sectors performance ---
    try:
        sectors_result = analyzer.get_group_performance("sectors")
        sectors_perf = sectors_result.to_dict()

        # Fetch sector weights (best-effort, null on failure)
        sector_tickers = list(sectors_perf.get("symbols", {}).keys())
        try:
            sector_weights = fetch_sector_weights(sector_tickers)
        except Exception as e:
            logger.warning("Failed to fetch sector weights", error=str(e))
            sector_weights = {}

        sectors_output = adapt_to_sectors(sectors_perf, sector_weights=sector_weights)
        sectors_output["period"] = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        }
        save_json(sectors_output, output_dir / "sectors.json")
        results["sectors.json"] = True

        if sectors_result.data_freshness.get("has_date_gap"):
            logger.warning(
                "Date gap detected in sectors data",
                newest_date=sectors_result.data_freshness.get("newest_date"),
                oldest_date=sectors_result.data_freshness.get("oldest_date"),
            )
    except Exception as e:
        logger.error("Failed to collect sectors data", error=str(e), exc_info=True)
        results["sectors.json"] = False

    # --- Collect interest rates ---
    ir_result = collect_interest_rates(output_dir)
    results["interest_rates.json"] = ir_result is not None

    # --- Collect currencies ---
    fx_result = collect_currencies(output_dir)
    results["currencies.json"] = fx_result is not None

    # --- Collect upcoming events ---
    events_result = collect_upcoming_events(output_dir)
    results["upcoming_events.json"] = events_result is not None

    # --- Metadata ---
    try:
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "start_jp": format_date_japanese(start_date, "short"),
                "end_jp": format_date_japanese(end_date, "short"),
                "start_us": format_date_us(start_date, "short"),
                "end_us": format_date_us(end_date, "short"),
            },
            "mode": "weekly",
            "files": {k: "ok" if v else "error" for k, v in results.items()},
        }
        save_json(metadata, output_dir / "metadata.json")
        results["metadata.json"] = True
    except Exception as e:
        logger.error("Failed to save metadata", error=str(e), exc_info=True)
        results["metadata.json"] = False

    success_count = sum(results.values())
    total_count = len(results)
    logger.info(
        "Weekly report data collection completed",
        success_count=success_count,
        total_count=total_count,
    )

    return results


# =============================================================================
# CLI
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Collect market data for weekly report generation (wr-data-aggregator compatible). "
            "Produces fixed-name output files with return values in decimal form."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-calculate period based on today's date
  uv run python scripts/collect_weekly_report_data.py

  # Specify output directory
  uv run python scripts/collect_weekly_report_data.py --output articles/weekly_report_20260122/data

  # Specify custom date range
  uv run python scripts/collect_weekly_report_data.py --start 2026-01-14 --end 2026-01-21

  # Specify reference date for auto period calculation
  uv run python scripts/collect_weekly_report_data.py --date 2026-01-22
        """,
    )

    default_output = ".tmp/weekly-report-data"

    parser.add_argument(
        "--output",
        type=str,
        default=default_output,
        help=f"Output directory for JSON files (default: {default_output})",
    )

    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD). If not specified, calculates from --date.",
    )

    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD). If not specified, calculates from --date.",
    )

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Reference date for period calculation (YYYY-MM-DD). Defaults to today.",
    )

    return parser


def main() -> int:
    """Main entry point.

    Returns
    -------
    int
        Exit code: 0 on success, 1 on failure.
    """
    logger.info("Weekly report data collection started")

    parser = create_parser()
    args = parser.parse_args()

    # Determine period
    if args.start and args.end:
        start_date = parse_date(args.start)
        end_date = parse_date(args.end)
        logger.info(
            "Using explicit date range",
            start=str(start_date),
            end=str(end_date),
        )
    else:
        reference_date = parse_date(args.date) if args.date else date.today()
        period = calculate_weekly_comment_period(reference_date)
        start_date = period["start"]
        end_date = period["end"]
        logger.info(
            "Calculated period from reference date",
            reference=str(reference_date),
            start=str(start_date),
            end=str(end_date),
        )

    output_dir = Path(args.output)

    try:
        results = collect_all_data(output_dir, start_date, end_date)

        if not any(results.values()):
            logger.error("No data files were created successfully")
            return 1

        # Print summary
        print(f"\n{'=' * 60}")
        print("Weekly Report Data Collection Complete")
        print(f"{'=' * 60}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Output: {output_dir}")
        print("\nFiles created:")
        for filename, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"  [{status}] {filename}")
        print(f"{'=' * 60}\n")

        return 0

    except Exception as e:
        logger.error("Unexpected error", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
