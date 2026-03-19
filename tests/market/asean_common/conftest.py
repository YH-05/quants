"""Pytest configuration and fixtures for market.asean_common tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from database.db.duckdb_client import DuckDBClient
from market.asean_common.constants import YFINANCE_SUFFIX_MAP, AseanMarket
from market.asean_common.types import TickerRecord

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary DuckDB database path.

    Parameters
    ----------
    tmp_path : Path
        pytest provided temporary directory.

    Returns
    -------
    Path
        Path to a temporary DuckDB file.
    """
    return tmp_path / "asean_test.duckdb"


@pytest.fixture
def duckdb_client(tmp_db_path: Path) -> DuckDBClient:
    """Provide a DuckDBClient connected to a temporary database.

    Parameters
    ----------
    tmp_db_path : Path
        Temporary database path.

    Returns
    -------
    DuckDBClient
        Client instance for testing.
    """
    return DuckDBClient(tmp_db_path)


@pytest.fixture
def sample_ticker_sgx() -> TickerRecord:
    """Provide a sample SGX TickerRecord.

    Returns
    -------
    TickerRecord
        DBS Group ticker on SGX.
    """
    return TickerRecord(
        ticker="D05",
        name="DBS Group Holdings Ltd",
        market=AseanMarket.SGX,
        yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.SGX],
        sector="Financial Services",
        industry="Banks - Diversified",
        market_cap=100_000_000_000,
        currency="SGD",
    )


@pytest.fixture
def sample_ticker_bursa() -> TickerRecord:
    """Provide a sample Bursa TickerRecord.

    Returns
    -------
    TickerRecord
        Maybank ticker on Bursa Malaysia.
    """
    return TickerRecord(
        ticker="1155",
        name="Maybank",
        market=AseanMarket.BURSA,
        yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.BURSA],
        sector="Financial Services",
        industry="Banks - Diversified",
        market_cap=50_000_000_000,
        currency="MYR",
    )


@pytest.fixture
def sample_tickers() -> list[TickerRecord]:
    """Provide a list of sample TickerRecords across multiple markets.

    Returns
    -------
    list[TickerRecord]
        List of 3 tickers from SGX, Bursa, and SET.
    """
    return [
        TickerRecord(
            ticker="D05",
            name="DBS Group Holdings Ltd",
            market=AseanMarket.SGX,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.SGX],
            sector="Financial Services",
            industry="Banks - Diversified",
            market_cap=100_000_000_000,
            currency="SGD",
        ),
        TickerRecord(
            ticker="1155",
            name="Maybank",
            market=AseanMarket.BURSA,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.BURSA],
            sector="Financial Services",
            industry="Banks - Diversified",
            market_cap=50_000_000_000,
            currency="MYR",
        ),
        TickerRecord(
            ticker="SCB",
            name="SCB X Public Company Limited",
            market=AseanMarket.SET,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.SET],
            sector="Financial Services",
            industry="Banks - Regional",
            market_cap=20_000_000_000,
            currency="THB",
        ),
    ]
