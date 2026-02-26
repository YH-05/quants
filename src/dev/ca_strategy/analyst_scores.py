"""Analyst score loading for the CA Strategy pipeline.

Reads analyst KY/AK scores from ``list_portfolio_20151224.json`` and
maps them to CA Strategy tickers via the universe configuration file.

The function bridges the Bloomberg ticker namespace used in the portfolio
list to the internal ticker namespace used by the CA Strategy pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

from dev.ca_strategy.types import AnalystScore
from utils_core.logging import get_logger

logger = get_logger(__name__)

__all__ = ["load_analyst_scores"]


def load_analyst_scores(
    portfolio_list_path: Path | str,
    universe_path: Path | str,
) -> dict[str, AnalystScore]:
    """Load analyst KY/AK scores from the portfolio list JSON.

    Reads ``list_portfolio_20151224.json`` and ``universe.json``,
    maps Bloomberg tickers to CA Strategy tickers, and extracts
    valid analyst scores.

    Parameters
    ----------
    portfolio_list_path : Path | str
        Path to the portfolio list JSON file (e.g.
        ``data/Transcript/list_portfolio_20151224.json``).
    universe_path : Path | str
        Path to the universe JSON file (e.g.
        ``research/ca_strategy_poc/config/universe.json``).

    Returns
    -------
    dict[str, AnalystScore]
        CA Strategy ticker to ``AnalystScore`` mapping.
        Only tickers with at least one valid score (KY or AK as
        integer, not ``" "``) are included.

    Examples
    --------
    >>> scores = load_analyst_scores(
    ...     "data/Transcript/list_portfolio_20151224.json",
    ...     "research/ca_strategy_poc/config/universe.json",
    ... )
    >>> scores["AAPL"].ky
    2
    """
    portfolio_list_path = Path(portfolio_list_path)
    universe_path = Path(universe_path)

    # Build Bloomberg_Ticker -> CA Strategy ticker mapping from universe
    bloomberg_to_ticker = _build_bloomberg_mapping(universe_path)

    # Load portfolio list
    portfolio_data = json.loads(
        portfolio_list_path.read_text(encoding="utf-8"),
    )

    result: dict[str, AnalystScore] = {}

    for msci_id, entries in portfolio_data.items():
        # Skip metadata keys
        if msci_id.startswith("_"):
            continue

        if not isinstance(entries, list) or len(entries) == 0:
            continue

        entry = entries[0]

        # Get Bloomberg ticker
        bloomberg_ticker = entry.get("Bloomberg_Ticker")
        if bloomberg_ticker is None:
            logger.debug(
                "Skipping entry with null Bloomberg_Ticker",
                msci_id=msci_id,
            )
            continue

        # Map to CA Strategy ticker
        ca_ticker = bloomberg_to_ticker.get(bloomberg_ticker)
        if ca_ticker is None:
            logger.debug(
                "Bloomberg ticker not found in universe mapping",
                bloomberg_ticker=bloomberg_ticker,
                msci_id=msci_id,
            )
            continue

        # Extract KY/AK scores
        ky = _parse_score(entry.get("KY", " "))
        ak = _parse_score(entry.get("AK", " "))

        # Include only if at least one score is valid
        if ky is None and ak is None:
            continue

        result[ca_ticker] = AnalystScore(
            ticker=ca_ticker,
            ky=ky,
            ak=ak,
        )

    logger.info(
        "Analyst scores loaded",
        total_entries=len(portfolio_data),
        scores_extracted=len(result),
    )

    return result


def _build_bloomberg_mapping(universe_path: Path) -> dict[str, str]:
    """Build a Bloomberg ticker to CA Strategy ticker mapping.

    Parameters
    ----------
    universe_path : Path
        Path to universe.json.

    Returns
    -------
    dict[str, str]
        Mapping of ``bloomberg_ticker`` to ``ticker``.
    """
    data = json.loads(universe_path.read_text(encoding="utf-8"))
    tickers_list = data.get("tickers", [])

    mapping: dict[str, str] = {}
    for entry in tickers_list:
        bloomberg = entry.get("bloomberg_ticker", "")
        ticker = entry.get("ticker", "")
        if bloomberg and ticker:
            mapping[bloomberg] = ticker

    logger.debug(
        "Bloomberg ticker mapping built",
        mapping_size=len(mapping),
    )
    return mapping


def _parse_score(value: object) -> int | None:
    """Parse a KY/AK score value.

    Parameters
    ----------
    value : object
        Score value from the portfolio list. Can be an integer,
        a space string ``" "``, or None.

    Returns
    -------
    int | None
        Parsed integer score, or None if the value is a space
        string or not a valid integer.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value.strip() == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, float):
        return int(value)
    return None
