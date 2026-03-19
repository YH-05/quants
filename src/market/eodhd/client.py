"""API client skeleton for the EODHD API.

This module provides the ``EodhdClient`` class, a skeleton client
for the EODHD API (https://eodhd.com/financial-apis/).

All public methods currently raise ``NotImplementedError`` because
the API key has not been obtained yet. This skeleton defines the
interface contract for future implementation.

Planned Features
----------------
- End-of-day historical prices
- Fundamental data (financials, balance sheet, etc.)
- Exchange symbol lists
- Exchange details and trading hours
- Dividends data
- Splits data
- Intraday data

Examples
--------
>>> from market.eodhd import EodhdClient, EodhdConfig
>>> config = EodhdConfig(api_key="demo")
>>> with EodhdClient(config=config) as client:
...     df = client.get_eod_data("AAPL.US")  # NotImplementedError

See Also
--------
market.jquants.client : Reference implementation with similar structure.
"""

from typing import Any

import pandas as pd

from market.eodhd.types import EodhdConfig
from utils_core.logging import get_logger

logger = get_logger(__name__)


class EodhdClient:
    """Skeleton client for the EODHD API.

    Provides typed method signatures for each planned API endpoint.
    All methods currently raise ``NotImplementedError`` as the API key
    has not been obtained yet.

    Parameters
    ----------
    config : EodhdConfig | None
        EODHD configuration. If ``None``, defaults are used.

    Examples
    --------
    >>> with EodhdClient() as client:
    ...     # All methods raise NotImplementedError
    ...     pass
    """

    def __init__(
        self,
        config: EodhdConfig | None = None,
    ) -> None:
        self._config = config or EodhdConfig()
        logger.info("EodhdClient initialized (skeleton)")

    # =========================================================================
    # Context Manager
    # =========================================================================

    def __enter__(self) -> "EodhdClient":
        """Enter the context manager and return the client instance.

        Returns
        -------
        EodhdClient
            The client instance itself.

        Examples
        --------
        >>> with EodhdClient() as client:
        ...     pass
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager and close the client.

        Delegates to :meth:`close` to release any held resources.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            The exception type, if an exception was raised in the ``with``
            block, otherwise ``None``.
        exc_val : BaseException | None
            The exception instance, if an exception was raised, otherwise
            ``None``.
        exc_tb : Any
            The traceback object, if an exception was raised, otherwise
            ``None``.
        """
        self.close()

    def close(self) -> None:
        """Close the client and release resources.

        This method is called automatically when exiting a ``with`` block.
        It can also be called manually to release resources early.

        Examples
        --------
        >>> client = EodhdClient()
        >>> client.close()
        """
        logger.debug("EodhdClient closed")

    # =========================================================================
    # Public API Methods (all raise NotImplementedError)
    # =========================================================================

    def get_eod_data(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> pd.DataFrame:
        """Get end-of-day historical stock price data.

        Planned endpoint: ``GET /eod/{symbol}``

        Parameters
        ----------
        symbol : str
            Ticker symbol with exchange suffix (e.g., ``"AAPL.US"``).
        from_date : str | None
            Start date in ``YYYY-MM-DD`` format.
        to_date : str | None
            End date in ``YYYY-MM-DD`` format.

        Returns
        -------
        pd.DataFrame
            DataFrame with OHLCV data.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_eod_data is not yet implemented. "
            "EODHD API key has not been obtained."
        )

    def get_fundamentals(
        self,
        symbol: str,
    ) -> dict[str, Any]:
        """Get fundamental data for a symbol.

        Planned endpoint: ``GET /fundamentals/{symbol}``

        Parameters
        ----------
        symbol : str
            Ticker symbol with exchange suffix (e.g., ``"AAPL.US"``).

        Returns
        -------
        dict[str, Any]
            Fundamental data including financials, balance sheet,
            earnings, and company information.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_fundamentals is not yet implemented. "
            "EODHD API key has not been obtained."
        )

    def get_exchange_symbols(
        self,
        exchange_code: str,
    ) -> pd.DataFrame:
        """Get list of symbols for an exchange.

        Planned endpoint: ``GET /exchange-symbol-list/{exchange_code}``

        Parameters
        ----------
        exchange_code : str
            Exchange code (e.g., ``"US"``, ``"SG"``, ``"KLSE"``).

        Returns
        -------
        pd.DataFrame
            DataFrame with symbol, name, exchange, currency, etc.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_exchange_symbols is not yet implemented. "
            "EODHD API key has not been obtained."
        )

    def get_exchange_details(
        self,
        exchange_code: str,
    ) -> dict[str, Any]:
        """Get exchange details including trading hours.

        Planned endpoint: ``GET /exchange-details/{exchange_code}``

        Parameters
        ----------
        exchange_code : str
            Exchange code (e.g., ``"US"``, ``"SG"``).

        Returns
        -------
        dict[str, Any]
            Exchange metadata including name, operating hours,
            country, and currency.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_exchange_details is not yet implemented. "
            "EODHD API key has not been obtained."
        )

    def get_dividends(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> pd.DataFrame:
        """Get dividend data for a symbol.

        Planned endpoint: ``GET /div/{symbol}``

        Parameters
        ----------
        symbol : str
            Ticker symbol with exchange suffix (e.g., ``"AAPL.US"``).
        from_date : str | None
            Start date in ``YYYY-MM-DD`` format.
        to_date : str | None
            End date in ``YYYY-MM-DD`` format.

        Returns
        -------
        pd.DataFrame
            DataFrame with dividend dates and amounts.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_dividends is not yet implemented. "
            "EODHD API key has not been obtained."
        )

    def get_splits(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> pd.DataFrame:
        """Get stock split data for a symbol.

        Planned endpoint: ``GET /splits/{symbol}``

        Parameters
        ----------
        symbol : str
            Ticker symbol with exchange suffix (e.g., ``"AAPL.US"``).
        from_date : str | None
            Start date in ``YYYY-MM-DD`` format.
        to_date : str | None
            End date in ``YYYY-MM-DD`` format.

        Returns
        -------
        pd.DataFrame
            DataFrame with split dates and ratios.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_splits is not yet implemented. "
            "EODHD API key has not been obtained."
        )

    def get_intraday_data(
        self,
        symbol: str,
        interval: str = "5m",
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> pd.DataFrame:
        """Get intraday price data for a symbol.

        Planned endpoint: ``GET /intraday/{symbol}``

        Parameters
        ----------
        symbol : str
            Ticker symbol with exchange suffix (e.g., ``"AAPL.US"``).
        interval : str
            Data interval (``"1m"``, ``"5m"``, ``"1h"``).
            Default is ``"5m"``.
        from_timestamp : int | None
            UNIX timestamp for start.
        to_timestamp : int | None
            UNIX timestamp for end.

        Returns
        -------
        pd.DataFrame
            DataFrame with intraday OHLCV data.

        Raises
        ------
        NotImplementedError
            Always raised (API key not yet obtained).
        """
        raise NotImplementedError(
            "EodhdClient.get_intraday_data is not yet implemented. "
            "EODHD API key has not been obtained."
        )


__all__ = ["EodhdClient"]
