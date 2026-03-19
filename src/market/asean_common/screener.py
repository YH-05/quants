"""tradingview-screener integration for ASEAN ticker fetching.

This module provides functions to fetch ASEAN exchange-listed tickers
using the ``tradingview-screener`` library. It queries the TradingView
scanner API for stock-type instruments on each ASEAN exchange and
converts the results into ``TickerRecord`` instances.

Functions
---------
fetch_tickers_from_screener(market)
    Fetch tickers for a single ASEAN market.
fetch_all_asean_tickers()
    Fetch tickers for all 6 ASEAN markets.

Notes
-----
The ``tradingview-screener`` package is an optional dependency
(installed via the ``asean`` extra). When not installed,
``fetch_tickers_from_screener`` returns an empty list instead of
raising an error.

Examples
--------
>>> from market.asean_common.screener import fetch_tickers_from_screener
>>> from market.asean_common.constants import AseanMarket
>>> tickers = fetch_tickers_from_screener(AseanMarket.SGX)
>>> len(tickers) > 0
True

See Also
--------
market.asean_common.constants : SCREENER_MARKET_MAP and YFINANCE_SUFFIX_MAP.
market.asean_common.types : TickerRecord dataclass.
market.asean_common.errors : AseanScreenerError exception.
"""

from __future__ import annotations

import math

import pandas as pd

from market.asean_common.constants import (
    SCREENER_MARKET_MAP,
    YFINANCE_SUFFIX_MAP,
    AseanMarket,
)
from market.asean_common.errors import AseanScreenerError
from market.asean_common.types import TickerRecord
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy import handled inside _query_screener to avoid top-level side effects
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Screener query columns
# ---------------------------------------------------------------------------

_SCREENER_COLUMNS: list[str] = [
    "name",
    "exchange",
    "market",
    "type",
    "sector",
    "industry",
    "market_cap_basic",
    "currency",
]

# Maximum number of tickers to fetch per query.
# tradingview-screener defaults to 50; we want all listed stocks.
_MAX_RESULTS: int = 5000


# ============================================================================
# Internal helpers
# ============================================================================


def _is_nan(value: object) -> bool:
    """Check if a value is NaN (float or numpy NaN).

    Parameters
    ----------
    value : object
        Value to check.

    Returns
    -------
    bool
        True if the value is NaN, False otherwise.
    """
    if value is None:
        return False
    try:
        if isinstance(value, float) and math.isnan(value):
            return True
        return bool(pd.isna(value))
    except (ValueError, TypeError):
        return False


def _extract_ticker_symbol(raw_ticker: str) -> str:
    """Extract the ticker symbol from tradingview-screener format.

    The tradingview-screener returns tickers in ``EXCHANGE:SYMBOL``
    format (e.g. ``SGX:D05``). This function extracts just the
    ``SYMBOL`` part.

    Parameters
    ----------
    raw_ticker : str
        Raw ticker string from tradingview-screener (e.g. ``"SGX:D05"``).

    Returns
    -------
    str
        The ticker symbol without the exchange prefix (e.g. ``"D05"``).
    """
    if ":" in raw_ticker:
        return raw_ticker.split(":", maxsplit=1)[1]
    return raw_ticker


def _query_screener(market: AseanMarket) -> tuple[int, pd.DataFrame]:
    """Execute a tradingview-screener query for a single ASEAN market.

    Parameters
    ----------
    market : AseanMarket
        The ASEAN exchange to query.

    Returns
    -------
    tuple[int, pd.DataFrame]
        A tuple of (total_count, DataFrame) from the screener API.

    Raises
    ------
    ModuleNotFoundError
        If tradingview-screener is not installed.
    Exception
        If the API query fails.
    """
    from tradingview_screener import Column, Query

    tv_market = SCREENER_MARKET_MAP[market]
    logger.debug(
        "Querying tradingview-screener", market=market.value, tv_market=tv_market
    )

    query = (
        Query()
        .set_markets(tv_market)
        .select(*_SCREENER_COLUMNS)
        .where(Column("type") == "stock")
        .limit(_MAX_RESULTS)
    )

    return query.get_scanner_data()


def _df_to_ticker_records(
    df: pd.DataFrame,
    market: AseanMarket,
) -> list[TickerRecord]:
    """Convert a tradingview-screener DataFrame to TickerRecord instances.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame from tradingview-screener with columns matching
        ``_SCREENER_COLUMNS``.
    market : AseanMarket
        The ASEAN market these tickers belong to.

    Returns
    -------
    list[TickerRecord]
        List of TickerRecord instances.
    """
    yf_suffix = YFINANCE_SUFFIX_MAP[market]
    records: list[TickerRecord] = []

    for _, row in df.iterrows():
        raw_ticker = str(row["ticker"])
        symbol = _extract_ticker_symbol(raw_ticker)

        sector_val = row.get("sector")
        industry_val = row.get("industry")
        cap_val = row.get("market_cap_basic")
        currency_val = row.get("currency")

        records.append(
            TickerRecord(
                ticker=symbol,
                name=symbol,
                market=market,
                yfinance_suffix=yf_suffix,
                sector=str(sector_val)
                if sector_val is not None and not _is_nan(sector_val)
                else None,
                industry=str(industry_val)
                if industry_val is not None and not _is_nan(industry_val)
                else None,
                market_cap=int(cap_val)
                if cap_val is not None and not _is_nan(cap_val)
                else None,
                currency=str(currency_val)
                if currency_val is not None and not _is_nan(currency_val)
                else None,
            )
        )

    return records


# ============================================================================
# Public API
# ============================================================================


def fetch_tickers_from_screener(market: AseanMarket) -> list[TickerRecord]:
    """Fetch tickers for a single ASEAN market via tradingview-screener.

    Queries the TradingView scanner API for all stock-type instruments
    listed on the specified ASEAN exchange and returns them as
    ``TickerRecord`` instances.

    Parameters
    ----------
    market : AseanMarket
        The ASEAN exchange to query (e.g. ``AseanMarket.SGX``).

    Returns
    -------
    list[TickerRecord]
        List of TickerRecord instances for the specified market.
        Returns an empty list if ``tradingview-screener`` is not installed.

    Raises
    ------
    AseanScreenerError
        If the tradingview-screener API query fails (network error,
        unexpected response, etc.).

    Examples
    --------
    >>> from market.asean_common.constants import AseanMarket
    >>> tickers = fetch_tickers_from_screener(AseanMarket.SGX)
    >>> isinstance(tickers, list)
    True
    """
    logger.info(
        "Fetching tickers from screener",
        market=market.value,
    )

    try:
        count, df = _query_screener(market)
    except ModuleNotFoundError:
        logger.warning(
            "tradingview-screener not installed, returning empty list",
            market=market.value,
        )
        return []
    except Exception as exc:
        msg = f"Failed to fetch tickers from screener for {market.value}: {exc}"
        logger.error(msg)
        raise AseanScreenerError(msg) from exc

    if df.empty:
        logger.info("No tickers found from screener", market=market.value)
        return []

    records = _df_to_ticker_records(df, market)
    logger.info(
        "Tickers fetched from screener",
        market=market.value,
        count=len(records),
        total_available=count,
    )
    return records


def fetch_all_asean_tickers() -> dict[AseanMarket, list[TickerRecord]]:
    """Fetch tickers for all 6 ASEAN markets via tradingview-screener.

    Iterates over all ``AseanMarket`` members and calls
    ``fetch_tickers_from_screener`` for each one.

    Returns
    -------
    dict[AseanMarket, list[TickerRecord]]
        Dictionary mapping each AseanMarket to its list of TickerRecords.
        Markets where fetching fails will have empty lists.

    Examples
    --------
    >>> result = fetch_all_asean_tickers()
    >>> len(result) == 6
    True
    >>> all(isinstance(k, AseanMarket) for k in result)
    True
    """
    logger.info("Fetching tickers for all ASEAN markets")
    result: dict[AseanMarket, list[TickerRecord]] = {}

    for market in AseanMarket:
        result[market] = fetch_tickers_from_screener(market)

    total = sum(len(v) for v in result.values())
    logger.info(
        "All ASEAN tickers fetched",
        total_tickers=total,
        market_counts={m.value: len(v) for m, v in result.items()},
    )
    return result


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    "fetch_all_asean_tickers",
    "fetch_tickers_from_screener",
]
