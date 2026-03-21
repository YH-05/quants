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

from typing import Final

import pandas as pd

from market.asean_common._utils import (
    _coerce_optional_int,
    _coerce_optional_str,
    _is_nan,
)
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

_SCREENER_COLUMNS: Final[list[str]] = [
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
    from tradingview_screener import (  # pyright: ignore[reportMissingImports]
        Column,
        Query,
    )

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

    for row_dict in df.to_dict(orient="records"):
        raw_ticker = str(row_dict["ticker"])
        symbol = _extract_ticker_symbol(raw_ticker)
        # Use actual name from TradingView if available, fallback to symbol
        name_val = row_dict.get("name")
        name = (
            str(name_val) if name_val is not None and not _is_nan(name_val) else symbol
        )

        records.append(
            TickerRecord(
                ticker=symbol,
                name=name,
                market=market,
                yfinance_suffix=yf_suffix,
                sector=_coerce_optional_str(row_dict.get("sector")),
                industry=_coerce_optional_str(row_dict.get("industry")),
                market_cap=_coerce_optional_int(row_dict.get("market_cap_basic")),
                currency=_coerce_optional_str(row_dict.get("currency")),
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
        safe_msg = f"Failed to fetch tickers from screener for {market.value}"
        logger.error(safe_msg, error=str(exc), exc_info=True)
        raise AseanScreenerError(safe_msg) from exc

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

    Queries TradingView scanner API concurrently for all ASEAN exchanges
    using a thread pool. Each market is fetched in parallel for improved
    performance (estimated 4-6x speedup over sequential execution).

    Returns
    -------
    dict[AseanMarket, list[TickerRecord]]
        Dictionary mapping each AseanMarket to its list of TickerRecords.

    Raises
    ------
    AseanScreenerError
        If any single market fails during fetching. The exception
        propagates immediately (fail-fast); partial results are not
        returned.

    Examples
    --------
    >>> result = fetch_all_asean_tickers()
    >>> len(result) == 6
    True
    >>> all(isinstance(k, AseanMarket) for k in result)
    True
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info("Fetching tickers for all ASEAN markets")
    result: dict[AseanMarket, list[TickerRecord]] = {}

    # AIDEV-NOTE: Exception propagation policy (fail-fast)
    # future.result() re-raises any exception from the worker thread.
    # If fetch_tickers_from_screener raises AseanScreenerError for any
    # single market, the exception propagates and the entire function
    # aborts without returning partial results.  This is intentional:
    # callers should handle AseanScreenerError at the call site.
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fetch_tickers_from_screener, market): market
            for market in AseanMarket
        }
        for future in as_completed(futures):
            market = futures[future]
            result[market] = future.result()

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
