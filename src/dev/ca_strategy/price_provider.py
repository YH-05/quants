"""Price data provider abstraction for the CA Strategy package.

Defines the ``PriceDataProvider`` Protocol for fetching daily close price
data, a ``NullPriceDataProvider`` null-object implementation for testing,
and a ``FilePriceProvider`` that reads from Parquet/CSV files on disk.

The Protocol allows swapping concrete data sources (yfinance, Bloomberg,
FactSet, local files) without changing downstream code.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pandas as pd

from utils_core.logging import get_logger

if TYPE_CHECKING:
    from datetime import date

logger = get_logger(__name__)

__all__ = ["FilePriceProvider", "NullPriceDataProvider", "PriceDataProvider"]


@runtime_checkable
class PriceDataProvider(Protocol):
    """Protocol for fetching daily close price data.

    Implementations must provide a ``fetch`` method that returns a mapping
    of ticker symbol to daily close price ``pd.Series`` with a
    ``DatetimeIndex``.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols to fetch.
    start : date
        Start date (inclusive).
    end : date
        End date (inclusive).

    Returns
    -------
    dict[str, pd.Series]
        Mapping of ticker to daily close price Series with DatetimeIndex.
        Missing tickers should be omitted from the result.
    """

    def fetch(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.Series]:
        """Fetch daily close prices for the given tickers.

        Parameters
        ----------
        tickers : list[str]
            List of ticker symbols to fetch.
        start : date
            Start date (inclusive).
        end : date
            End date (inclusive).

        Returns
        -------
        dict[str, pd.Series]
            Mapping of ticker to daily close price Series with DatetimeIndex.
            Missing tickers should be omitted from the result.
        """
        ...  # pragma: no cover


class NullPriceDataProvider:
    """Null implementation for testing (returns empty dict).

    Always returns an empty dictionary regardless of input parameters.
    Useful as a default or placeholder when no real data source is
    available.
    """

    def fetch(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.Series]:
        """Return an empty dictionary.

        Parameters
        ----------
        tickers : list[str]
            List of ticker symbols (ignored).
        start : date
            Start date (ignored).
        end : date
            End date (ignored).

        Returns
        -------
        dict[str, pd.Series]
            Always an empty dictionary.
        """
        return {}


class FilePriceProvider:
    """File-based price data provider.

    Supports two modes depending on whether ``data_path`` points to a
    file or a directory:

    **Per-ticker mode** (directory):
        Reads daily close prices from individual Parquet or CSV files.
        File naming convention: ``{TICKER}.parquet`` or ``{TICKER}.csv``.
        Each file must have a ``DatetimeIndex`` and a ``close`` column.
        Parquet files take precedence when both formats exist for the
        same ticker.

    **Single-file mode** (file):
        Reads a single Parquet or CSV file where columns are ticker
        symbols and the index is a ``DatetimeIndex``. Values are daily
        close prices. The entire file is loaded into memory on
        initialization and cached for subsequent ``fetch()`` calls.

    Parameters
    ----------
    data_path : Path | str
        Path to a directory (per-ticker mode) or to a single
        ``.parquet`` / ``.csv`` file (single-file mode).

    Raises
    ------
    FileNotFoundError
        If ``data_path`` does not exist.

    Examples
    --------
    Per-ticker mode (directory with ``AAPL.parquet``, ``MSFT.csv``, ...):

    >>> provider = FilePriceProvider("data/prices/")
    >>> result = provider.fetch(["AAPL"], start=date(2024, 1, 2), end=date(2024, 1, 5))

    Single-file mode (one file with tickers as columns):

    >>> provider = FilePriceProvider("data/all_prices.parquet")
    >>> result = provider.fetch(["AAPL", "MSFT"], start=date(2024, 1, 2), end=date(2024, 1, 5))
    """

    def __init__(self, data_path: Path | str) -> None:
        self._data_path = Path(data_path)
        if not self._data_path.exists():
            msg = f"Price data path not found: {self._data_path}"
            raise FileNotFoundError(msg)

        # Determine mode based on whether data_path is a file or directory
        self._single_file_mode = self._data_path.is_file()
        self._df_cache: pd.DataFrame | None = None

        if self._single_file_mode:
            self._df_cache = self._load_single_file(self._data_path)
            logger.debug(
                "FilePriceProvider initialized (single-file mode)",
                data_path=str(self._data_path),
                columns=list(self._df_cache.columns),
                rows=len(self._df_cache),
            )
        else:
            logger.debug(
                "FilePriceProvider initialized (per-ticker mode)",
                data_path=str(self._data_path),
            )

    @staticmethod
    def _load_single_file(file_path: Path) -> pd.DataFrame:
        """Load a single price file into a DataFrame.

        Parameters
        ----------
        file_path : Path
            Path to a ``.parquet`` or ``.csv`` file.

        Returns
        -------
        pd.DataFrame
            DataFrame with ``DatetimeIndex`` and ticker columns.
        """
        if file_path.suffix == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.DatetimeIndex(df.index)

        return df

    def fetch(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.Series]:
        """Fetch daily close prices from local files.

        In **per-ticker mode**, looks for ``{TICKER}.parquet`` first,
        then ``{TICKER}.csv`` for each ticker. Reads the ``close``
        column, filters by date range ``[start, end]``, and returns a
        Series with ``DatetimeIndex``.

        In **single-file mode**, filters the cached DataFrame by the
        requested tickers (columns) and date range. Tickers not present
        as columns are silently skipped.

        Parameters
        ----------
        tickers : list[str]
            List of ticker symbols to fetch.
        start : date
            Start date (inclusive).
        end : date
            End date (inclusive).

        Returns
        -------
        dict[str, pd.Series]
            Mapping of ticker to daily close price Series.
            Tickers without matching data are omitted.
        """
        if not tickers:
            return {}

        start_ts: pd.Timestamp = pd.Timestamp(start)  # type: ignore[assignment]
        end_ts: pd.Timestamp = pd.Timestamp(end)  # type: ignore[assignment]

        if self._single_file_mode:
            result = self._fetch_single_file(tickers, start_ts, end_ts)
        else:
            result = self._fetch_per_ticker(tickers, start_ts, end_ts)

        logger.info(
            "FilePriceProvider fetch completed",
            requested=len(tickers),
            returned=len(result),
            start=start.isoformat(),
            end=end.isoformat(),
            mode="single-file" if self._single_file_mode else "per-ticker",
        )
        return result

    def _fetch_single_file(
        self,
        tickers: list[str],
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
    ) -> dict[str, pd.Series]:
        """Fetch prices from the cached single-file DataFrame.

        Parameters
        ----------
        tickers : list[str]
            List of ticker symbols to fetch.
        start_ts : pd.Timestamp
            Start timestamp (inclusive).
        end_ts : pd.Timestamp
            End timestamp (inclusive).

        Returns
        -------
        dict[str, pd.Series]
            Mapping of ticker to daily close price Series.
        """
        assert self._df_cache is not None

        result: dict[str, pd.Series] = {}
        available_columns = set(self._df_cache.columns)

        # Filter by date range
        mask = (self._df_cache.index >= start_ts) & (self._df_cache.index <= end_ts)
        filtered_df = self._df_cache.loc[mask]

        for ticker in tickers:
            if ticker in available_columns:
                result[ticker] = filtered_df[ticker]
            else:
                logger.warning(
                    "Ticker not found in single-file data",
                    ticker=ticker,
                    data_path=str(self._data_path),
                )

        return result

    def _fetch_per_ticker(
        self,
        tickers: list[str],
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
    ) -> dict[str, pd.Series]:
        """Fetch prices from per-ticker files in the directory.

        Parameters
        ----------
        tickers : list[str]
            List of ticker symbols to fetch.
        start_ts : pd.Timestamp
            Start timestamp (inclusive).
        end_ts : pd.Timestamp
            End timestamp (inclusive).

        Returns
        -------
        dict[str, pd.Series]
            Mapping of ticker to daily close price Series.
        """
        result: dict[str, pd.Series] = {}
        for ticker in tickers:
            series = self._read_ticker(ticker, start_ts, end_ts)
            if series is not None:
                result[ticker] = series
        return result

    def _read_ticker(
        self,
        ticker: str,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
    ) -> pd.Series | None:
        """Read a single ticker's close prices from disk.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        start_ts : pd.Timestamp
            Start timestamp (inclusive).
        end_ts : pd.Timestamp
            End timestamp (inclusive).

        Returns
        -------
        pd.Series | None
            Daily close prices, or None if no file found.
        """
        parquet_path = self._data_path / f"{ticker}.parquet"
        csv_path = self._data_path / f"{ticker}.csv"

        try:
            if parquet_path.exists():
                df = pd.read_parquet(parquet_path, columns=["close"])
            elif csv_path.exists():
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            else:
                logger.warning(
                    "No price file found for ticker",
                    ticker=ticker,
                    data_dir=str(self._data_path),
                )
                return None
        except Exception as e:
            logger.warning(
                "Failed to read price file for ticker",
                ticker=ticker,
                error=str(e),
            )
            return None

        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.DatetimeIndex(df.index)

        # Filter by date range
        mask = (df.index >= start_ts) & (df.index <= end_ts)
        filtered = df.loc[mask, "close"]

        return filtered
