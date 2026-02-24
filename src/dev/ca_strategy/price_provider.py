"""Price data provider abstraction for the CA Strategy package.

Defines the ``PriceDataProvider`` Protocol for fetching daily close price
data and a ``NullPriceDataProvider`` null-object implementation for testing.

The Protocol allows swapping concrete data sources (yfinance, Bloomberg,
FactSet) without changing downstream code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pandas as pd

if TYPE_CHECKING:
    from datetime import date

__all__ = ["NullPriceDataProvider", "PriceDataProvider"]


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
        ...


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
