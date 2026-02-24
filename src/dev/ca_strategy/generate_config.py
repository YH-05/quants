"""Configuration file generator for the CA Strategy pipeline.

Reads ``list_portfolio_YYYYMMDD.json`` (MSCI portfolio export) and generates:

- ``universe.json`` — investment universe in ``ConfigRepository`` format
- ``benchmark_weights.json`` — approximate sector weights derived from
  MSCI_Mkt_Cap_USD_MM aggregation

Usage (CLI)::

    python -m dev.ca_strategy.generate_config \\
        --source data/Transcript/list_portfolio_20151224.json \\
        --output-dir data/config

Usage (library)::

    from pathlib import Path
    from dev.ca_strategy.generate_config import generate_all

    generate_all(
        source=Path("data/Transcript/list_portfolio_20151224.json"),
        output_dir=Path("data/config"),
    )
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dev.ca_strategy.ticker_converter import TickerConverter
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 10 GICS sectors (as of MSCI World circa 2015)
# ---------------------------------------------------------------------------
_GICS_SECTORS: frozenset[str] = frozenset(
    {
        "Consumer Discretionary",
        "Consumer Staples",
        "Energy",
        "Financials",
        "Health Care",
        "Industrials",
        "Information Technology",
        "Materials",
        "Telecommunication Services",
        "Utilities",
    }
)

# ---------------------------------------------------------------------------
# Bloomberg ticker overrides for ambiguous exchange codes (NR, NQ, GK, LI)
# ---------------------------------------------------------------------------
_BLOOMBERG_OVERRIDES: dict[str, str] = {
    # NR — mixed exchange code (US and non-US)
    "GSK NR Equity": "GSK.L",  # GlaxoSmithKline (UK)
    "GE NR Equity": "GE",  # General Electric (US)
    "NOV NR Equity": "NOV",  # National Oilwell Varco (US)
    "UTX NR Equity": "UTX",  # United Technologies (US)
    "NOVOB NR Equity": "NOVO-B.CO",  # Novo Nordisk Class B (Denmark)
    # NQ — mixed exchange code
    "CRDA NQ Equity": "CRDA.L",  # Croda International (UK)
    "SGSN NQ Equity": "SGSN.SW",  # SGS SA (Switzerland)
    "ULVR NQ Equity": "ULVR.L",  # Unilever PLC (UK)
    # GK — mixed (France/UK)
    "ML GK Equity": "ML.PA",  # Michelin (France)
    "JMT GK Equity": "JMAT.L",  # Johnson Matthey (UK)
    # LI — mixed (France/Russia)
    "2273854Q LI Equity": "DSY.PA",  # Dassault Systemes (France)
    "MGNT LI Equity": "MGNT.ME",  # Magnit (Russia)
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _load_portfolio(source: Path) -> dict[str, list[dict]]:
    """Load portfolio JSON from *source*.

    Parameters
    ----------
    source : Path
        Path to the portfolio JSON file.

    Returns
    -------
    dict[str, list[dict]]
        Raw portfolio data keyed by MSCI identifier.

    Raises
    ------
    FileNotFoundError
        If *source* does not exist.
    """
    if not source.exists():
        msg = f"Portfolio source file not found: {source}"
        raise FileNotFoundError(msg)

    raw: dict[str, list[dict]] = json.loads(source.read_text(encoding="utf-8"))
    logger.debug("Portfolio loaded", source=str(source), entry_count=len(raw))
    return raw


def _flatten_entries(raw: dict[str, list[dict]]) -> list[dict]:
    """Flatten nested list structure into a single list of entries."""
    entries: list[dict] = []
    for entries_list in raw.values():
        entries.extend(entries_list)
    return entries


# ---------------------------------------------------------------------------
# Private helpers (accept pre-loaded entries, avoid repeated file reads)
# ---------------------------------------------------------------------------
def _write_universe(
    entries: list[dict],
    source_name: str,
    output_dir: Path,
    overrides: dict[str, str] | None,
    ticker_mapping: dict[str, dict] | None = None,
) -> dict[str, int]:
    """Write universe.json from pre-loaded *entries*.

    The ``ticker`` field stores the **base Bloomberg ticker** (first token
    of the Bloomberg format, e.g. ``"AAPL"`` from ``"AAPL US Equity"``),
    with digit-starting tickers resolved via *ticker_mapping*.  This
    matches the transcript directory naming used by
    :class:`~dev.ca_strategy.transcript.TranscriptLoader`.

    The ``bloomberg_ticker`` field preserves the **full Bloomberg identifier**
    (e.g. ``"AAPL US Equity"``) from the source data, stripped of leading
    and trailing whitespace.  This is required by Phase 6 data fetching.

    Parameters
    ----------
    entries : list[dict]
        Flattened list of portfolio entries.
    source_name : str
        Original source file name (stored in output metadata).
    output_dir : Path
        Directory where ``universe.json`` will be written.
    overrides : dict[str, str] | None
        Custom Bloomberg→yfinance overrides (kept for future use).
    ticker_mapping : dict[str, dict] | None, optional
        Digit-starting ticker resolution map (from ``ticker_mapping.json``).
        Keys are raw Bloomberg base tickers; values must contain a
        ``"ticker"`` key with the resolved ticker symbol.

    Returns
    -------
    dict[str, int]
        Conversion statistics with keys ``total``, ``skipped``.
    """
    mapping = ticker_mapping or {}

    tickers: list[dict[str, str]] = []
    skipped = 0
    sector_counts: dict[str, int] = {}

    for entry in entries:
        bloomberg_ticker: str = entry.get("Bloomberg_Ticker", "") or ""
        gics_sector: str = entry.get("GICS_Sector", "")
        company_name: str = entry.get("Name", "")
        country: str = entry.get("Country", "")

        if not bloomberg_ticker.strip():
            logger.warning(
                "Missing Bloomberg ticker, skipping entry",
                entry_name=company_name or "<unknown>",
            )
            skipped += 1
            continue

        # Extract base ticker (first token of Bloomberg format)
        base_ticker = bloomberg_ticker.strip().split()[0]

        # Apply ticker_mapping for digit-starting or historical tickers
        if base_ticker in mapping:
            resolved = mapping[base_ticker].get("ticker", base_ticker)
            logger.debug(
                "Ticker mapping applied",
                raw=base_ticker,
                resolved=resolved,
            )
            base_ticker = resolved

        tickers.append(
            {
                "ticker": base_ticker,
                "bloomberg_ticker": bloomberg_ticker.strip(),
                "company_name": company_name,
                "gics_sector": gics_sector,
                "country": country,
            }
        )
        sector_counts[gics_sector] = sector_counts.get(gics_sector, 0) + 1

    universe_data: dict[str, Any] = {
        "_metadata": {
            "description": "投資ユニバース（list_portfolio_20151224.json準拠）",
            "as_of_date": "2015-12-24",
            "source_file": source_name,
            "total_count": len(tickers),
            "skipped_entries": skipped,
            "sector_counts": dict(sorted(sector_counts.items())),
        },
        "tickers": tickers,
    }
    output_path = output_dir / "universe.json"
    output_path.write_text(
        json.dumps(universe_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "universe.json generated",
        output=str(output_path),
        total=len(tickers),
        skipped=skipped,
    )

    return {"total": len(tickers), "skipped": skipped}


def _write_benchmark_weights(
    entries: list[dict],
    source_name: str,
    output_dir: Path,
) -> dict[str, float]:
    """Write benchmark_weights.json from pre-loaded *entries*.

    Parameters
    ----------
    entries : list[dict]
        Flattened list of portfolio entries.
    source_name : str
        Original source file name (stored in output metadata).
    output_dir : Path
        Directory where ``benchmark_weights.json`` will be written.

    Returns
    -------
    dict[str, float]
        Mapping of sector name to weight (sums to 1.0).
    """
    # Aggregate market cap by GICS sector
    sector_cap: dict[str, float] = {}
    skipped = 0

    for entry in entries:
        gics_sector: str = entry.get("GICS_Sector", "")
        mkt_cap = entry.get("MSCI_Mkt_Cap_USD_MM")

        # Skip entries with zero or None market cap
        if not mkt_cap:
            logger.debug(
                "Skipping entry with zero/None market cap",
                name=entry.get("Name", "<unknown>"),
                sector=gics_sector,
            )
            skipped += 1
            continue

        sector_cap[gics_sector] = sector_cap.get(gics_sector, 0.0) + mkt_cap

    total_cap: float = sum(sector_cap.values())

    if total_cap == 0.0:
        logger.error("Total market cap is zero; cannot compute sector weights")
        weights: dict[str, float] = {}
    else:
        weights = {
            sector: cap / total_cap for sector, cap in sorted(sector_cap.items())
        }

    benchmark_data: dict[str, Any] = {
        "weights": weights,
        "metadata": {
            "note": (
                "Approximate sector weights derived from MSCI_Mkt_Cap_USD_MM "
                "aggregation.  These are not official benchmark weights."
            ),
            "is_approximate": True,
            "approximation": "market_cap_weighted",
            "source_file": source_name,
            "total_market_cap_usd_mm": total_cap,
            "skipped_entries": skipped,
        },
    }

    output_path = output_dir / "benchmark_weights.json"
    output_path.write_text(
        json.dumps(benchmark_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "benchmark_weights.json generated",
        output=str(output_path),
        sector_count=len(weights),
        skipped=skipped,
    )

    return weights


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_universe(
    *,
    source: Path,
    output_dir: Path,
    overrides: dict[str, str] | None = None,
    ticker_mapping: dict[str, dict] | None = None,
) -> dict[str, int]:
    """Generate ``universe.json`` from *source* portfolio file.

    Extracts base Bloomberg tickers (first token, e.g. ``"AAPL"`` from
    ``"AAPL US Equity"``) and resolves digit-starting tickers via
    *ticker_mapping*.

    Parameters
    ----------
    source : Path
        Path to the MSCI portfolio JSON file.
    output_dir : Path
        Directory where ``universe.json`` will be written.
    overrides : dict[str, str] | None, optional
        Custom Bloomberg→yfinance overrides (reserved for future use).
    ticker_mapping : dict[str, dict] | None, optional
        Digit-starting ticker resolution map.

    Returns
    -------
    dict[str, int]
        Statistics with keys ``total``, ``skipped``.

    Raises
    ------
    FileNotFoundError
        If *source* does not exist.
    """
    entries = _flatten_entries(_load_portfolio(source))
    return _write_universe(entries, source.name, output_dir, overrides, ticker_mapping)


def generate_benchmark_weights(
    *,
    source: Path,
    output_dir: Path,
) -> dict[str, float]:
    """Generate ``benchmark_weights.json`` from *source* portfolio file.

    Aggregates ``MSCI_Mkt_Cap_USD_MM`` by GICS sector to compute approximate
    market-cap-weighted sector weights.  Entries with zero or ``None``
    market-cap are silently skipped.

    Parameters
    ----------
    source : Path
        Path to the MSCI portfolio JSON file.
    output_dir : Path
        Directory where ``benchmark_weights.json`` will be written.

    Returns
    -------
    dict[str, float]
        Mapping of sector name to weight (sums to 1.0).

    Raises
    ------
    FileNotFoundError
        If *source* does not exist.
    """
    entries = _flatten_entries(_load_portfolio(source))
    return _write_benchmark_weights(entries, source.name, output_dir)


def generate_all(
    *,
    source: Path,
    output_dir: Path,
    overrides: dict[str, str] | None = None,
    ticker_mapping: dict[str, dict] | None = None,
) -> None:
    """Generate both ``universe.json`` and ``benchmark_weights.json``.

    Loads the portfolio file once and writes both output files,
    avoiding redundant I/O.

    Parameters
    ----------
    source : Path
        Path to the MSCI portfolio JSON file.
    output_dir : Path
        Directory where both config files will be written.
    overrides : dict[str, str] | None, optional
        Custom Bloomberg→yfinance ticker overrides (reserved for future use).
    ticker_mapping : dict[str, dict] | None, optional
        Digit-starting ticker resolution map.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting config generation", source=str(source), output_dir=str(output_dir)
    )

    # Load portfolio once to avoid reading the same file twice
    entries = _flatten_entries(_load_portfolio(source))

    stats = _write_universe(entries, source.name, output_dir, overrides, ticker_mapping)
    _write_benchmark_weights(entries, source.name, output_dir)

    logger.info(
        "Config generation complete",
        total=stats["total"],
        skipped=stats["skipped"],
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main(args: list[str] | None = None) -> None:
    """CLI entry point for generate_config.

    Parameters
    ----------
    args : list[str] | None, optional
        Argument list for testing.  If ``None``, reads from ``sys.argv``.

    Examples
    --------
    ::

        python -m dev.ca_strategy.generate_config \\
            --source data/Transcript/list_portfolio_20151224.json \\
            --output-dir data/config
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generate universe.json and benchmark_weights.json from an MSCI "
            "portfolio export JSON file."
        ),
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the MSCI portfolio JSON file (e.g. list_portfolio_20151224.json).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory to write universe.json and benchmark_weights.json.",
    )

    parsed = parser.parse_args(args)

    generate_all(source=parsed.source, output_dir=parsed.output_dir)


if __name__ == "__main__":
    main()
