"""ASEAN common foundation module.

Provides shared constants, types, error definitions, storage layer,
and screener integration for all ASEAN market sub-packages
(SGX, Bursa, SET, IDX, HOSE, PSE).

Public API
----------
Constants : AseanMarket, YFINANCE_SUFFIX_MAP, SCREENER_EXCHANGE_MAP,
    SCREENER_MARKET_MAP, TABLE_TICKERS, DB_PATH
Types : TickerRecord
Storage : AseanTickerStorage
Errors : AseanError, AseanStorageError, AseanScreenerError, AseanLookupError
Screener : fetch_tickers_from_screener, fetch_all_asean_tickers

Examples
--------
>>> from market.asean_common import AseanMarket, TickerRecord
>>> record = TickerRecord(
...     ticker="D05",
...     name="DBS Group Holdings Ltd",
...     market=AseanMarket.SGX,
...     yfinance_suffix=".SI",
... )
>>> record.yfinance_ticker
'D05.SI'

See Also
--------
market.asean_common.constants : Enum and mapping definitions.
market.asean_common.types : TickerRecord dataclass.
market.asean_common.storage : DuckDB storage layer.
market.asean_common.screener : tradingview-screener integration.
market.asean_common.errors : Exception hierarchy.
"""

from market.asean_common.constants import (
    DB_PATH,
    SCREENER_EXCHANGE_MAP,
    SCREENER_MARKET_MAP,
    TABLE_TICKERS,
    YFINANCE_SUFFIX_MAP,
    AseanMarket,
)
from market.asean_common.errors import (
    AseanError,
    AseanLookupError,
    AseanScreenerError,
    AseanStorageError,
)
from market.asean_common.screener import (
    fetch_all_asean_tickers,
    fetch_tickers_from_screener,
)
from market.asean_common.storage import AseanTickerStorage
from market.asean_common.types import TickerRecord

__all__ = [
    "DB_PATH",
    "SCREENER_EXCHANGE_MAP",
    "SCREENER_MARKET_MAP",
    "TABLE_TICKERS",
    "YFINANCE_SUFFIX_MAP",
    "AseanError",
    "AseanLookupError",
    "AseanMarket",
    "AseanScreenerError",
    "AseanStorageError",
    "AseanTickerStorage",
    "TickerRecord",
    "fetch_all_asean_tickers",
    "fetch_tickers_from_screener",
]
