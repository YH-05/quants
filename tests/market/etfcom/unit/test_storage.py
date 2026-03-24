"""Unit tests for the ETF.com storage layer.

Tests cover DDL management (ensure_tables), upsert methods for all 9 tables,
get methods with filters, idempotent upsert behaviour, DDL-dataclass alignment,
the factory function, helper functions, and introspection utilities.

See Also
--------
market.etfcom.storage : Implementation under test.
market.etfcom.models : Record dataclasses.
"""

from __future__ import annotations

import dataclasses
import os
from typing import TYPE_CHECKING

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path

from market.etfcom.models import (
    AllocationRecord,
    FundFlowsRecord,
    HoldingRecord,
    PerformanceRecord,
    PortfolioRecord,
    QuoteRecord,
    StructureRecord,
    TickerRecord,
    TradabilityRecord,
)
from market.etfcom.storage import (
    _VALID_TABLE_NAMES,
    ETFComStorage,
    _build_insert_sql,
    _dataclass_to_tuple,
    get_etfcom_storage,
)
from market.etfcom.storage_constants import (
    ETFCOM_DB_PATH_ENV,
    TABLE_ALLOCATIONS,
    TABLE_FUND_FLOWS,
    TABLE_HOLDINGS,
    TABLE_PERFORMANCE,
    TABLE_PORTFOLIO,
    TABLE_QUOTES,
    TABLE_STRUCTURE,
    TABLE_TICKERS,
    TABLE_TRADABILITY,
)

# =============================================================================
# Helpers
# =============================================================================

FETCHED_AT = "2026-03-24T12:00:00"


def _make_ticker(
    ticker: str = "SPY",
    fund_id: int = 1,
    **kwargs: object,
) -> TickerRecord:
    """Create a TickerRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "fund_id": fund_id,
        "name": "SPDR S&P 500 ETF Trust",
        "issuer": "State Street",
        "asset_class": "Equity",
        "inception_date": "1993-01-22",
        "segment": "Equity: U.S. - Large Cap",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return TickerRecord(**defaults)  # type: ignore[arg-type]


def _make_fund_flows(
    ticker: str = "SPY",
    nav_date: str = "2026-01-15",
    **kwargs: object,
) -> FundFlowsRecord:
    """Create a FundFlowsRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "nav_date": nav_date,
        "nav": 580.25,
        "nav_change": 2.15,
        "nav_change_percent": 0.48,
        "premium_discount": -0.02,
        "fund_flows": 1_500_000_000.0,
        "shares_outstanding": 920_000_000.0,
        "aum": 414_230_000_000.0,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return FundFlowsRecord(**defaults)  # type: ignore[arg-type]


def _make_holding(
    ticker: str = "SPY",
    holding_ticker: str = "AAPL",
    as_of_date: str = "2026-01-10",
    **kwargs: object,
) -> HoldingRecord:
    """Create a HoldingRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "holding_ticker": holding_ticker,
        "as_of_date": as_of_date,
        "holding_name": "Apple Inc",
        "weight": 0.072,
        "market_value": 28_000_000_000.0,
        "shares": 160_000_000.0,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return HoldingRecord(**defaults)  # type: ignore[arg-type]


def _make_portfolio(
    ticker: str = "SPY",
    **kwargs: object,
) -> PortfolioRecord:
    """Create a PortfolioRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "pe_ratio": 22.5,
        "pb_ratio": 4.1,
        "dividend_yield": 0.013,
        "weighted_avg_market_cap": 700_000_000_000.0,
        "number_of_holdings": 503,
        "expense_ratio": 0.0009,
        "tracking_difference": -0.0005,
        "median_tracking_difference": -0.0004,
        "as_of_date": "2026-01-10",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return PortfolioRecord(**defaults)  # type: ignore[arg-type]


def _make_allocation(
    ticker: str = "SPY",
    allocation_type: str = "sector",
    name: str = "Technology",
    as_of_date: str = "2026-01-10",
    **kwargs: object,
) -> AllocationRecord:
    """Create an AllocationRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "allocation_type": allocation_type,
        "name": name,
        "as_of_date": as_of_date,
        "weight": 0.32,
        "market_value": 160_000_000_000.0,
        "count": 75,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return AllocationRecord(**defaults)  # type: ignore[arg-type]


def _make_tradability(
    ticker: str = "SPY",
    **kwargs: object,
) -> TradabilityRecord:
    """Create a TradabilityRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "avg_daily_volume": 75_000_000.0,
        "avg_daily_dollar_volume": 43_000_000_000.0,
        "median_bid_ask_spread": 0.0001,
        "avg_bid_ask_spread": 0.00012,
        "creation_unit_size": 50000,
        "open_interest": 10_000_000.0,
        "short_interest": 0.015,
        "implied_liquidity": 50_000_000_000.0,
        "block_liquidity": 30_000_000_000.0,
        "as_of_date": "2026-01-10",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return TradabilityRecord(**defaults)  # type: ignore[arg-type]


def _make_structure(
    ticker: str = "SPY",
    **kwargs: object,
) -> StructureRecord:
    """Create a StructureRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "legal_structure": "UIT",
        "fund_type": "Index Fund",
        "index_tracked": "S&P 500",
        "replication_method": "Full Replication",
        "uses_derivatives": False,
        "securities_lending": True,
        "tax_form": "1099",
        "as_of_date": "2026-01-10",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return StructureRecord(**defaults)  # type: ignore[arg-type]


def _make_performance(
    ticker: str = "SPY",
    **kwargs: object,
) -> PerformanceRecord:
    """Create a PerformanceRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "return_1m": 0.025,
        "return_3m": 0.08,
        "return_ytd": 0.03,
        "return_1y": 0.265,
        "return_3y": 0.10,
        "return_5y": 0.12,
        "return_10y": 0.13,
        "r_squared": 0.9998,
        "beta": 1.0,
        "standard_deviation": 0.15,
        "as_of_date": "2026-01-10",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return PerformanceRecord(**defaults)  # type: ignore[arg-type]


def _make_quote(
    ticker: str = "SPY",
    quote_date: str = "2026-01-15",
    **kwargs: object,
) -> QuoteRecord:
    """Create a QuoteRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "ticker": ticker,
        "quote_date": quote_date,
        "open": 578.0,
        "high": 582.5,
        "low": 576.0,
        "close": 580.25,
        "volume": 75_000_000.0,
        "bid": 580.20,
        "ask": 580.30,
        "bid_size": 500.0,
        "ask_size": 600.0,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return QuoteRecord(**defaults)  # type: ignore[arg-type]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def storage(tmp_path: Path) -> ETFComStorage:
    """Create a temporary ETFComStorage instance."""
    db_path = tmp_path / "etfcom_test.db"
    return ETFComStorage(db_path=db_path)


# =============================================================================
# TestEnsureTables
# =============================================================================


class TestEnsureTables:
    """Tests for ``ETFComStorage.ensure_tables()``."""

    def test_正常系_9テーブルが作成される(self, storage: ETFComStorage) -> None:
        tables = storage.get_table_names()
        assert len(tables) == 9

    def test_正常系_全テーブル名が正しい(self, storage: ETFComStorage) -> None:
        tables = storage.get_table_names()
        expected = sorted(
            [
                TABLE_TICKERS,
                TABLE_FUND_FLOWS,
                TABLE_HOLDINGS,
                TABLE_PORTFOLIO,
                TABLE_ALLOCATIONS,
                TABLE_TRADABILITY,
                TABLE_STRUCTURE,
                TABLE_PERFORMANCE,
                TABLE_QUOTES,
            ]
        )
        assert tables == expected

    def test_正常系_ensure_tablesは冪等に動作する(self, storage: ETFComStorage) -> None:
        storage.ensure_tables()
        storage.ensure_tables()
        assert len(storage.get_table_names()) == 9

    def test_正常系_全テーブルの初期行数が0(self, storage: ETFComStorage) -> None:
        stats = storage.get_stats()
        assert all(count == 0 for count in stats.values())


# =============================================================================
# TestHelpers
# =============================================================================


class TestHelpers:
    """Tests for helper functions."""

    def test_正常系_dataclass_to_tupleで全フィールドが変換される(self) -> None:
        record = _make_ticker()
        result = _dataclass_to_tuple(record)
        fields = dataclasses.fields(record)
        assert len(result) == len(fields)
        assert result[0] == "SPY"

    def test_正常系_build_insert_sqlで正しいSQL生成(self) -> None:
        sql = _build_insert_sql(TABLE_TICKERS, ("ticker", "fund_id", "fetched_at"))
        assert "INSERT OR REPLACE INTO" in sql
        assert TABLE_TICKERS in sql
        assert "ticker, fund_id, fetched_at" in sql
        assert "?, ?, ?" in sql

    def test_異常系_build_insert_sqlで不正テーブル名がValueError(self) -> None:
        with pytest.raises(ValueError, match="Invalid table name"):
            _build_insert_sql("invalid_table", ("col1",))

    def test_正常系_build_insert_sqlはキャッシュされる(self) -> None:
        sql1 = _build_insert_sql(TABLE_TICKERS, ("ticker", "fetched_at"))
        sql2 = _build_insert_sql(TABLE_TICKERS, ("ticker", "fetched_at"))
        assert sql1 is sql2


# =============================================================================
# TestValidTableNames
# =============================================================================


class TestValidTableNames:
    """Tests for ``_VALID_TABLE_NAMES``."""

    def test_正常系_9テーブルが登録されている(self) -> None:
        assert len(_VALID_TABLE_NAMES) == 9

    def test_正常系_全テーブル名がetfcomプレフィックスを持つ(self) -> None:
        for name in _VALID_TABLE_NAMES:
            assert name.startswith("etfcom_"), f"{name} lacks etfcom_ prefix"


# =============================================================================
# TestUpsertTickers
# =============================================================================


class TestUpsertTickers:
    """Tests for ``ETFComStorage.upsert_tickers()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_ticker()
        count = storage.upsert_tickers([record])
        assert count == 1
        assert storage.get_row_count(TABLE_TICKERS) == 1

    def test_正常系_複数レコードのupsert(self, storage: ETFComStorage) -> None:
        records = [
            _make_ticker(ticker="SPY", fund_id=1),
            _make_ticker(ticker="VOO", fund_id=2),
            _make_ticker(ticker="QQQ", fund_id=3),
        ]
        count = storage.upsert_tickers(records)
        assert count == 3
        assert storage.get_row_count(TABLE_TICKERS) == 3

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_ticker(name="Old Name")
        record2 = _make_ticker(name="New Name")
        storage.upsert_tickers([record1])
        storage.upsert_tickers([record2])
        assert storage.get_row_count(TABLE_TICKERS) == 1
        df = storage.get_tickers()
        assert df.iloc[0]["name"] == "New Name"

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_tickers([])
        assert count == 0


# =============================================================================
# TestUpsertFundFlows
# =============================================================================


class TestUpsertFundFlows:
    """Tests for ``ETFComStorage.upsert_fund_flows()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_fund_flows()
        count = storage.upsert_fund_flows([record])
        assert count == 1
        assert storage.get_row_count(TABLE_FUND_FLOWS) == 1

    def test_正常系_複数日のupsert(self, storage: ETFComStorage) -> None:
        records = [
            _make_fund_flows(nav_date="2026-01-15"),
            _make_fund_flows(nav_date="2026-01-16"),
            _make_fund_flows(nav_date="2026-01-17"),
        ]
        count = storage.upsert_fund_flows(records)
        assert count == 3

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_fund_flows(nav=580.0)
        record2 = _make_fund_flows(nav=590.0)
        storage.upsert_fund_flows([record1])
        storage.upsert_fund_flows([record2])
        assert storage.get_row_count(TABLE_FUND_FLOWS) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_fund_flows([])
        assert count == 0


# =============================================================================
# TestUpsertHoldings
# =============================================================================


class TestUpsertHoldings:
    """Tests for ``ETFComStorage.upsert_holdings()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_holding()
        count = storage.upsert_holdings([record])
        assert count == 1

    def test_正常系_複数銘柄のupsert(self, storage: ETFComStorage) -> None:
        records = [
            _make_holding(holding_ticker="AAPL"),
            _make_holding(holding_ticker="MSFT"),
            _make_holding(holding_ticker="GOOGL"),
        ]
        count = storage.upsert_holdings(records)
        assert count == 3

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_holding(weight=0.07)
        record2 = _make_holding(weight=0.08)
        storage.upsert_holdings([record1])
        storage.upsert_holdings([record2])
        assert storage.get_row_count(TABLE_HOLDINGS) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_holdings([])
        assert count == 0


# =============================================================================
# TestUpsertPortfolio
# =============================================================================


class TestUpsertPortfolio:
    """Tests for ``ETFComStorage.upsert_portfolio()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_portfolio()
        count = storage.upsert_portfolio([record])
        assert count == 1

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_portfolio(pe_ratio=22.5)
        record2 = _make_portfolio(pe_ratio=23.0)
        storage.upsert_portfolio([record1])
        storage.upsert_portfolio([record2])
        assert storage.get_row_count(TABLE_PORTFOLIO) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_portfolio([])
        assert count == 0


# =============================================================================
# TestUpsertAllocations
# =============================================================================


class TestUpsertAllocations:
    """Tests for ``ETFComStorage.upsert_allocations()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_allocation()
        count = storage.upsert_allocations([record])
        assert count == 1

    def test_正常系_複数タイプのupsert(self, storage: ETFComStorage) -> None:
        records = [
            _make_allocation(allocation_type="sector", name="Technology"),
            _make_allocation(allocation_type="sector", name="Healthcare"),
            _make_allocation(allocation_type="region", name="North America"),
        ]
        count = storage.upsert_allocations(records)
        assert count == 3

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_allocation(weight=0.30)
        record2 = _make_allocation(weight=0.35)
        storage.upsert_allocations([record1])
        storage.upsert_allocations([record2])
        assert storage.get_row_count(TABLE_ALLOCATIONS) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_allocations([])
        assert count == 0


# =============================================================================
# TestUpsertTradability
# =============================================================================


class TestUpsertTradability:
    """Tests for ``ETFComStorage.upsert_tradability()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_tradability()
        count = storage.upsert_tradability([record])
        assert count == 1

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_tradability(avg_daily_volume=75_000_000.0)
        record2 = _make_tradability(avg_daily_volume=80_000_000.0)
        storage.upsert_tradability([record1])
        storage.upsert_tradability([record2])
        assert storage.get_row_count(TABLE_TRADABILITY) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_tradability([])
        assert count == 0


# =============================================================================
# TestUpsertStructure
# =============================================================================


class TestUpsertStructure:
    """Tests for ``ETFComStorage.upsert_structure()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_structure()
        count = storage.upsert_structure([record])
        assert count == 1

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_structure(legal_structure="UIT")
        record2 = _make_structure(legal_structure="Open-End Fund")
        storage.upsert_structure([record1])
        storage.upsert_structure([record2])
        assert storage.get_row_count(TABLE_STRUCTURE) == 1

    def test_正常系_boolフィールドがINTEGERとして保存される(
        self, storage: ETFComStorage
    ) -> None:
        record = _make_structure(uses_derivatives=True, securities_lending=False)
        storage.upsert_structure([record])
        df = storage.get_structure("SPY")
        assert len(df) == 1
        # SQLite stores bool as INTEGER (0/1)
        assert df.iloc[0]["uses_derivatives"] == 1
        assert df.iloc[0]["securities_lending"] == 0

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_structure([])
        assert count == 0


# =============================================================================
# TestUpsertPerformance
# =============================================================================


class TestUpsertPerformance:
    """Tests for ``ETFComStorage.upsert_performance()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_performance()
        count = storage.upsert_performance([record])
        assert count == 1

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_performance(return_1y=0.265)
        record2 = _make_performance(return_1y=0.280)
        storage.upsert_performance([record1])
        storage.upsert_performance([record2])
        assert storage.get_row_count(TABLE_PERFORMANCE) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_performance([])
        assert count == 0


# =============================================================================
# TestUpsertQuotes
# =============================================================================


class TestUpsertQuotes:
    """Tests for ``ETFComStorage.upsert_quotes()``."""

    def test_正常系_単一レコードのupsert(self, storage: ETFComStorage) -> None:
        record = _make_quote()
        count = storage.upsert_quotes([record])
        assert count == 1

    def test_正常系_複数日のupsert(self, storage: ETFComStorage) -> None:
        records = [
            _make_quote(quote_date="2026-01-15"),
            _make_quote(quote_date="2026-01-16"),
        ]
        count = storage.upsert_quotes(records)
        assert count == 2

    def test_正常系_同一PKで冪等にupsertされる(self, storage: ETFComStorage) -> None:
        record1 = _make_quote(close=580.0)
        record2 = _make_quote(close=585.0)
        storage.upsert_quotes([record1])
        storage.upsert_quotes([record2])
        assert storage.get_row_count(TABLE_QUOTES) == 1

    def test_エッジケース_空リストでupsertすると0(self, storage: ETFComStorage) -> None:
        count = storage.upsert_quotes([])
        assert count == 0


# =============================================================================
# TestGetTickers
# =============================================================================


class TestGetTickers:
    """Tests for ``ETFComStorage.get_tickers()``."""

    def test_正常系_全tickerが取得できる(self, storage: ETFComStorage) -> None:
        records = [
            _make_ticker(ticker="SPY", fund_id=1),
            _make_ticker(ticker="VOO", fund_id=2),
        ]
        storage.upsert_tickers(records)
        df = storage.get_tickers()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df["ticker"]) == ["SPY", "VOO"]

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_tickers()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# =============================================================================
# TestGetFundFlows
# =============================================================================


class TestGetFundFlows:
    """Tests for ``ETFComStorage.get_fund_flows()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_fund_flows(ticker="SPY", nav_date="2026-01-15"),
            _make_fund_flows(ticker="VOO", nav_date="2026-01-15"),
        ]
        storage.upsert_fund_flows(records)
        df = storage.get_fund_flows("SPY")
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "SPY"

    def test_正常系_start_dateでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_fund_flows(nav_date="2026-01-14"),
            _make_fund_flows(nav_date="2026-01-15"),
            _make_fund_flows(nav_date="2026-01-16"),
        ]
        storage.upsert_fund_flows(records)
        df = storage.get_fund_flows("SPY", start_date="2026-01-15")
        assert len(df) == 2

    def test_正常系_end_dateでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_fund_flows(nav_date="2026-01-14"),
            _make_fund_flows(nav_date="2026-01-15"),
            _make_fund_flows(nav_date="2026-01-16"),
        ]
        storage.upsert_fund_flows(records)
        df = storage.get_fund_flows("SPY", end_date="2026-01-15")
        assert len(df) == 2

    def test_正常系_start_dateとend_dateの範囲フィルタ(
        self, storage: ETFComStorage
    ) -> None:
        records = [
            _make_fund_flows(nav_date="2026-01-14"),
            _make_fund_flows(nav_date="2026-01-15"),
            _make_fund_flows(nav_date="2026-01-16"),
            _make_fund_flows(nav_date="2026-01-17"),
        ]
        storage.upsert_fund_flows(records)
        df = storage.get_fund_flows(
            "SPY", start_date="2026-01-15", end_date="2026-01-16"
        )
        assert len(df) == 2

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_fund_flows("NONEXISTENT")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# =============================================================================
# TestGetHoldings
# =============================================================================


class TestGetHoldings:
    """Tests for ``ETFComStorage.get_holdings()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_holding(ticker="SPY", holding_ticker="AAPL"),
            _make_holding(ticker="VOO", holding_ticker="AAPL"),
        ]
        storage.upsert_holdings(records)
        df = storage.get_holdings("SPY")
        assert len(df) == 1

    def test_正常系_as_of_dateでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_holding(as_of_date="2026-01-10"),
            _make_holding(holding_ticker="MSFT", as_of_date="2026-01-11"),
        ]
        storage.upsert_holdings(records)
        df = storage.get_holdings("SPY", as_of_date="2026-01-10")
        assert len(df) == 1

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_holdings("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetPortfolio
# =============================================================================


class TestGetPortfolio:
    """Tests for ``ETFComStorage.get_portfolio()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        storage.upsert_portfolio([_make_portfolio()])
        df = storage.get_portfolio("SPY")
        assert len(df) == 1
        assert df.iloc[0]["pe_ratio"] == pytest.approx(22.5)

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_portfolio("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetAllocations
# =============================================================================


class TestGetAllocations:
    """Tests for ``ETFComStorage.get_allocations()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_allocation(allocation_type="sector", name="Technology"),
            _make_allocation(allocation_type="region", name="North America"),
        ]
        storage.upsert_allocations(records)
        df = storage.get_allocations("SPY")
        assert len(df) == 2

    def test_正常系_allocation_typeでフィルタされる(
        self, storage: ETFComStorage
    ) -> None:
        records = [
            _make_allocation(allocation_type="sector", name="Technology"),
            _make_allocation(allocation_type="region", name="North America"),
        ]
        storage.upsert_allocations(records)
        df = storage.get_allocations("SPY", allocation_type="sector")
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Technology"

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_allocations("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetTradability
# =============================================================================


class TestGetTradability:
    """Tests for ``ETFComStorage.get_tradability()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        storage.upsert_tradability([_make_tradability()])
        df = storage.get_tradability("SPY")
        assert len(df) == 1

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_tradability("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetStructure
# =============================================================================


class TestGetStructure:
    """Tests for ``ETFComStorage.get_structure()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        storage.upsert_structure([_make_structure()])
        df = storage.get_structure("SPY")
        assert len(df) == 1
        assert df.iloc[0]["legal_structure"] == "UIT"

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_structure("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetPerformance
# =============================================================================


class TestGetPerformance:
    """Tests for ``ETFComStorage.get_performance()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        storage.upsert_performance([_make_performance()])
        df = storage.get_performance("SPY")
        assert len(df) == 1
        assert df.iloc[0]["return_1y"] == pytest.approx(0.265)

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_performance("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetQuotes
# =============================================================================


class TestGetQuotes:
    """Tests for ``ETFComStorage.get_quotes()``."""

    def test_正常系_tickerでフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_quote(ticker="SPY"),
            _make_quote(ticker="VOO"),
        ]
        storage.upsert_quotes(records)
        df = storage.get_quotes("SPY")
        assert len(df) == 1

    def test_正常系_日付範囲でフィルタされる(self, storage: ETFComStorage) -> None:
        records = [
            _make_quote(quote_date="2026-01-14"),
            _make_quote(quote_date="2026-01-15"),
            _make_quote(quote_date="2026-01-16"),
        ]
        storage.upsert_quotes(records)
        df = storage.get_quotes("SPY", start_date="2026-01-15", end_date="2026-01-15")
        assert len(df) == 1

    def test_エッジケース_データなしで空DataFrame(self, storage: ETFComStorage) -> None:
        df = storage.get_quotes("NONEXISTENT")
        assert len(df) == 0


# =============================================================================
# TestGetRowCount
# =============================================================================


class TestGetRowCount:
    """Tests for ``ETFComStorage.get_row_count()``."""

    def test_正常系_データありで正しいカウント(self, storage: ETFComStorage) -> None:
        records = [
            _make_ticker(ticker="SPY", fund_id=1),
            _make_ticker(ticker="VOO", fund_id=2),
        ]
        storage.upsert_tickers(records)
        assert storage.get_row_count(TABLE_TICKERS) == 2

    def test_正常系_データなしで0(self, storage: ETFComStorage) -> None:
        assert storage.get_row_count(TABLE_TICKERS) == 0

    def test_異常系_不正テーブル名でValueError(self, storage: ETFComStorage) -> None:
        with pytest.raises(ValueError, match="Invalid table name"):
            storage.get_row_count("nonexistent_table")


# =============================================================================
# TestGetStats
# =============================================================================


class TestGetStats:
    """Tests for ``ETFComStorage.get_stats()``."""

    def test_正常系_全テーブルの統計が取得できる(self, storage: ETFComStorage) -> None:
        storage.upsert_tickers([_make_ticker()])
        stats = storage.get_stats()
        assert len(stats) == 9
        assert stats[TABLE_TICKERS] == 1
        assert stats[TABLE_FUND_FLOWS] == 0


# =============================================================================
# TestDDLDataclassAlignment
# =============================================================================


class TestDDLDataclassAlignment:
    """Tests ensuring DDL column definitions match dataclass fields."""

    @pytest.mark.parametrize(
        ("table_name", "record_cls"),
        [
            (TABLE_TICKERS, TickerRecord),
            (TABLE_FUND_FLOWS, FundFlowsRecord),
            (TABLE_HOLDINGS, HoldingRecord),
            (TABLE_PORTFOLIO, PortfolioRecord),
            (TABLE_ALLOCATIONS, AllocationRecord),
            (TABLE_TRADABILITY, TradabilityRecord),
            (TABLE_STRUCTURE, StructureRecord),
            (TABLE_PERFORMANCE, PerformanceRecord),
            (TABLE_QUOTES, QuoteRecord),
        ],
    )
    def test_パラメトライズ_DDLカラム数とdataclassフィールド数が一致(
        self,
        table_name: str,
        record_cls: type,
    ) -> None:
        from market.etfcom.storage import _TABLE_DDL

        ddl = _TABLE_DDL[table_name]
        # Count column definitions (lines with SQL type keywords)
        import re

        col_re = re.compile(
            r"^\s+(\w+)\s+(TEXT|INTEGER|REAL|BLOB|NUMERIC)",
            re.MULTILINE,
        )
        ddl_columns = {m.group(1) for m in col_re.finditer(ddl)}
        field_names = {f.name for f in dataclasses.fields(record_cls)}
        assert ddl_columns == field_names, (
            f"DDL columns {sorted(ddl_columns)} != "
            f"dataclass fields {sorted(field_names)} for {table_name}"
        )


# =============================================================================
# TestFactoryFunction
# =============================================================================


class TestFactoryFunction:
    """Tests for ``get_etfcom_storage()``."""

    def test_正常系_明示的なdb_pathでインスタンスが作成される(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "factory_test.db"
        storage = get_etfcom_storage(db_path=db_path)
        assert isinstance(storage, ETFComStorage)
        assert len(storage.get_table_names()) == 9

    def test_正常系_環境変数からdb_pathが解決される(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_path = str(tmp_path / "env_test.db")
        monkeypatch.setenv(ETFCOM_DB_PATH_ENV, env_path)
        storage = get_etfcom_storage()
        assert isinstance(storage, ETFComStorage)
        assert len(storage.get_table_names()) == 9


# =============================================================================
# TestNullableFields
# =============================================================================


class TestNullableFields:
    """Tests for records with None optional fields."""

    def test_正常系_オプショナルフィールドがNoneでもupsertできる(
        self, storage: ETFComStorage
    ) -> None:
        record = TickerRecord(
            ticker="TEST",
            fund_id=999,
            fetched_at=FETCHED_AT,
        )
        count = storage.upsert_tickers([record])
        assert count == 1
        df = storage.get_tickers()
        assert len(df) == 1
        assert df.iloc[0]["name"] is None

    def test_正常系_fund_flowsのオプショナルフィールドがNoneでもupsertできる(
        self, storage: ETFComStorage
    ) -> None:
        record = FundFlowsRecord(
            ticker="TEST",
            nav_date="2026-01-15",
            fetched_at=FETCHED_AT,
        )
        count = storage.upsert_fund_flows([record])
        assert count == 1
