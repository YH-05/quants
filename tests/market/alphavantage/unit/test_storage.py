"""Unit tests for the Alpha Vantage storage layer.

Tests cover DDL management (ensure_tables), upsert methods for all 8 tables,
get methods with filters, migration logic, DDL-dataclass alignment,
and the factory function.

See Also
--------
market.alphavantage.storage : Implementation under test.
market.alphavantage.models : Record dataclasses.
tests.market.alphavantage.conftest : ``av_storage`` fixture.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pandas as pd
import pytest

from market.alphavantage.models import (
    AnnualEarningsRecord,
    BalanceSheetRecord,
    CashFlowRecord,
    CompanyOverviewRecord,
    DailyPriceRecord,
    EconomicIndicatorRecord,
    ForexDailyRecord,
    IncomeStatementRecord,
    QuarterlyEarningsRecord,
)
from market.alphavantage.storage import (
    _VALID_FILTER_COLUMNS,
    _VALID_TABLE_NAMES,
    AlphaVantageStorage,
    _build_insert_sql,
    _dataclass_to_tuple,
    _parse_ddl_columns,
    get_alphavantage_storage,
)
from market.alphavantage.storage_constants import (
    AV_DB_PATH_ENV,
    TABLE_BALANCE_SHEETS,
    TABLE_CASH_FLOWS,
    TABLE_COMPANY_OVERVIEW,
    TABLE_DAILY_PRICES,
    TABLE_EARNINGS,
    TABLE_ECONOMIC_INDICATORS,
    TABLE_FOREX_DAILY,
    TABLE_INCOME_STATEMENTS,
)

# =============================================================================
# Helpers
# =============================================================================

FETCHED_AT = "2026-03-24T12:00:00"


def _make_daily_price(
    symbol: str = "AAPL",
    date: str = "2026-01-15",
    **kwargs: object,
) -> DailyPriceRecord:
    """Create a DailyPriceRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "date": date,
        "open": 150.0,
        "high": 155.0,
        "low": 149.0,
        "close": 153.0,
        "adjusted_close": 153.0,
        "volume": 1_000_000,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return DailyPriceRecord(**defaults)  # type: ignore[arg-type]


def _make_company_overview(
    symbol: str = "AAPL",
    **kwargs: object,
) -> CompanyOverviewRecord:
    """Create a CompanyOverviewRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "name": "Apple Inc",
        "description": "Tech company",
        "exchange": "NASDAQ",
        "currency": "USD",
        "country": "USA",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "fiscal_year_end": "September",
        "latest_quarter": "2025-12-31",
        "market_capitalization": 3_000_000_000_000.0,
        "ebitda": 130_000_000_000.0,
        "pe_ratio": 33.5,
        "peg_ratio": 2.1,
        "book_value": 4.38,
        "dividend_per_share": 1.0,
        "dividend_yield": 0.0043,
        "eps": 6.88,
        "diluted_eps_ttm": 6.88,
        "week_52_high": 260.10,
        "week_52_low": 164.08,
        "day_50_moving_average": 230.0,
        "day_200_moving_average": 220.0,
        "shares_outstanding": 15_000_000_000.0,
        "revenue_per_share_ttm": 25.0,
        "profit_margin": 0.25,
        "operating_margin_ttm": 0.30,
        "return_on_assets_ttm": 0.28,
        "return_on_equity_ttm": 1.60,
        "revenue_ttm": 380_000_000_000.0,
        "gross_profit_ttm": 170_000_000_000.0,
        "quarterly_earnings_growth_yoy": 0.10,
        "quarterly_revenue_growth_yoy": 0.05,
        "analyst_target_price": 250.0,
        "analyst_rating_strong_buy": 15.0,
        "analyst_rating_buy": 10.0,
        "analyst_rating_hold": 5.0,
        "analyst_rating_sell": 2.0,
        "analyst_rating_strong_sell": 1.0,
        "trailing_pe": 33.5,
        "forward_pe": 28.0,
        "price_to_sales_ratio_ttm": 8.5,
        "price_to_book_ratio": 50.0,
        "ev_to_revenue": 9.0,
        "ev_to_ebitda": 25.0,
        "beta": 1.2,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return CompanyOverviewRecord(**defaults)  # type: ignore[arg-type]


def _make_income_statement(
    symbol: str = "AAPL",
    fiscal_date_ending: str = "2025-12-31",
    report_type: str = "annual",
    **kwargs: object,
) -> IncomeStatementRecord:
    """Create an IncomeStatementRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "fiscal_date_ending": fiscal_date_ending,
        "report_type": report_type,
        "reported_currency": "USD",
        "gross_profit": 170_000_000_000.0,
        "total_revenue": 380_000_000_000.0,
        "cost_of_revenue": 210_000_000_000.0,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return IncomeStatementRecord(**defaults)  # type: ignore[arg-type]


def _make_balance_sheet(
    symbol: str = "AAPL",
    fiscal_date_ending: str = "2025-12-31",
    report_type: str = "annual",
    **kwargs: object,
) -> BalanceSheetRecord:
    """Create a BalanceSheetRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "fiscal_date_ending": fiscal_date_ending,
        "report_type": report_type,
        "reported_currency": "USD",
        "total_assets": 350_000_000_000.0,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return BalanceSheetRecord(**defaults)  # type: ignore[arg-type]


def _make_cash_flow(
    symbol: str = "AAPL",
    fiscal_date_ending: str = "2025-12-31",
    report_type: str = "annual",
    **kwargs: object,
) -> CashFlowRecord:
    """Create a CashFlowRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "fiscal_date_ending": fiscal_date_ending,
        "report_type": report_type,
        "reported_currency": "USD",
        "operating_cashflow": 110_000_000_000.0,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return CashFlowRecord(**defaults)  # type: ignore[arg-type]


def _make_annual_earnings(
    symbol: str = "AAPL",
    fiscal_date_ending: str = "2025-09-30",
    **kwargs: object,
) -> AnnualEarningsRecord:
    """Create an AnnualEarningsRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "fiscal_date_ending": fiscal_date_ending,
        "period_type": "annual",
        "reported_eps": 6.88,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return AnnualEarningsRecord(**defaults)  # type: ignore[arg-type]


def _make_quarterly_earnings(
    symbol: str = "AAPL",
    fiscal_date_ending: str = "2025-12-31",
    **kwargs: object,
) -> QuarterlyEarningsRecord:
    """Create a QuarterlyEarningsRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "fiscal_date_ending": fiscal_date_ending,
        "period_type": "quarterly",
        "reported_date": "2026-01-30",
        "reported_eps": 2.40,
        "estimated_eps": 2.35,
        "surprise": 0.05,
        "surprise_percentage": 2.13,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return QuarterlyEarningsRecord(**defaults)  # type: ignore[arg-type]


def _make_economic_indicator(
    indicator: str = "REAL_GDP",
    date: str = "2025-10-01",
    **kwargs: object,
) -> EconomicIndicatorRecord:
    """Create an EconomicIndicatorRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "indicator": indicator,
        "date": date,
        "value": 23_500.0,
        "interval": "quarterly",
        "maturity": "",
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return EconomicIndicatorRecord(**defaults)  # type: ignore[arg-type]


def _make_forex_daily(
    from_currency: str = "USD",
    to_currency: str = "JPY",
    date: str = "2026-01-15",
    **kwargs: object,
) -> ForexDailyRecord:
    """Create a ForexDailyRecord with sensible defaults."""
    defaults: dict[str, object] = {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "date": date,
        "open": 150.0,
        "high": 151.0,
        "low": 149.0,
        "close": 150.5,
        "fetched_at": FETCHED_AT,
    }
    defaults.update(kwargs)
    return ForexDailyRecord(**defaults)  # type: ignore[arg-type]


# =============================================================================
# Tests: Helper functions
# =============================================================================


class TestDataclassToTuple:
    """Tests for _dataclass_to_tuple helper."""

    def test_正常系_DailyPriceRecordをタプルに変換(self) -> None:
        record = _make_daily_price()
        result = _dataclass_to_tuple(record)
        assert isinstance(result, tuple)
        assert result[0] == "AAPL"
        assert result[1] == "2026-01-15"
        assert len(result) == 9

    def test_正常系_CompanyOverviewRecordをタプルに変換(self) -> None:
        record = _make_company_overview()
        result = _dataclass_to_tuple(record)
        assert isinstance(result, tuple)
        assert result[0] == "AAPL"
        # 1 symbol + 9 text + 36 numeric + 1 fetched_at = 47 fields
        assert len(result) == 47


class TestBuildInsertSql:
    """Tests for _build_insert_sql helper."""

    def test_正常系_有効なテーブル名でSQL生成(self) -> None:
        sql = _build_insert_sql(TABLE_DAILY_PRICES, ("symbol", "date"))
        assert "INSERT OR REPLACE INTO" in sql
        assert TABLE_DAILY_PRICES in sql
        assert "symbol, date" in sql
        assert "?, ?" in sql

    def test_異常系_無効なテーブル名でValueError(self) -> None:
        with pytest.raises(ValueError, match="Invalid table name"):
            _build_insert_sql("invalid_table", ("col1",))


class TestParseDdlColumns:
    """Tests for _parse_ddl_columns helper."""

    def test_正常系_DDLからカラム名を抽出(self) -> None:
        ddl = """
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER NOT NULL,
                name TEXT,
                value REAL,
                PRIMARY KEY (id)
            )
        """
        cols = _parse_ddl_columns(ddl)
        assert cols == {"id", "name", "value"}


# =============================================================================
# Tests: EnsureTables
# =============================================================================


class TestEnsureTables:
    """Tests for ensure_tables and schema management."""

    def test_正常系_8テーブルが作成される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        tables = av_storage.get_table_names()
        assert len(tables) == 8

    def test_正常系_全テーブル名がav_プレフィックスを持つ(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        tables = av_storage.get_table_names()
        for table in tables:
            assert table.startswith("av_"), f"Table '{table}' missing 'av_' prefix"

    def test_正常系_冪等性_2回呼んでもエラーなし(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        av_storage.ensure_tables()
        av_storage.ensure_tables()
        tables = av_storage.get_table_names()
        assert len(tables) == 8

    def test_正常系_期待されるテーブルが全て存在する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        expected = {
            TABLE_DAILY_PRICES,
            TABLE_COMPANY_OVERVIEW,
            TABLE_INCOME_STATEMENTS,
            TABLE_BALANCE_SHEETS,
            TABLE_CASH_FLOWS,
            TABLE_EARNINGS,
            TABLE_ECONOMIC_INDICATORS,
            TABLE_FOREX_DAILY,
        }
        actual = set(av_storage.get_table_names())
        assert actual == expected

    def test_正常系_全テーブルの行数が0で初期化される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        stats = av_storage.get_stats()
        assert all(count == 0 for count in stats.values())
        assert len(stats) == 8


# =============================================================================
# Tests: Upsert Daily Prices
# =============================================================================


class TestUpsertDailyPrices:
    """Tests for upsert_daily_prices method."""

    def test_正常系_レコードが保存される(self, av_storage: AlphaVantageStorage) -> None:
        records = [_make_daily_price(date="2026-01-15")]
        count = av_storage.upsert_daily_prices(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_DAILY_PRICES) == 1

    def test_正常系_複数レコードが保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_daily_price(date="2026-01-15"),
            _make_daily_price(date="2026-01-16"),
            _make_daily_price(date="2026-01-17"),
        ]
        count = av_storage.upsert_daily_prices(records)
        assert count == 3
        assert av_storage.get_row_count(TABLE_DAILY_PRICES) == 3

    def test_正常系_冪等性_同一PK再投入でレコード数が変わらない(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [_make_daily_price(date="2026-01-15")]
        av_storage.upsert_daily_prices(records)
        av_storage.upsert_daily_prices(records)
        assert av_storage.get_row_count(TABLE_DAILY_PRICES) == 1

    def test_正常系_同一PKで最新データに上書きされる(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        original = _make_daily_price(date="2026-01-15", close=150.0)
        updated = _make_daily_price(date="2026-01-15", close=160.0)
        av_storage.upsert_daily_prices([original])
        av_storage.upsert_daily_prices([updated])
        df = av_storage.get_daily_prices("AAPL")
        assert len(df) == 1
        assert df.iloc[0]["close"] == pytest.approx(160.0)

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_daily_prices([])
        assert count == 0
        assert av_storage.get_row_count(TABLE_DAILY_PRICES) == 0


# =============================================================================
# Tests: Upsert Company Overview
# =============================================================================


class TestUpsertCompanyOverview:
    """Tests for upsert_company_overview method."""

    def test_正常系_全フィールドが保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        record = _make_company_overview()
        count = av_storage.upsert_company_overview(record)
        assert count == 1

        result = av_storage.get_company_overview("AAPL")
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.name == "Apple Inc"
        assert result.market_capitalization == pytest.approx(3_000_000_000_000.0)
        assert result.pe_ratio == pytest.approx(33.5)
        assert result.beta == pytest.approx(1.2)
        assert result.fetched_at == FETCHED_AT

    def test_正常系_Noneフィールドが保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        record = CompanyOverviewRecord(
            symbol="MSFT",
            fetched_at=FETCHED_AT,
        )
        av_storage.upsert_company_overview(record)
        result = av_storage.get_company_overview("MSFT")
        assert result is not None
        assert result.name is None
        assert result.pe_ratio is None

    def test_正常系_上書き更新で最新データが返される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        original = _make_company_overview(pe_ratio=30.0)
        updated = _make_company_overview(pe_ratio=35.0)
        av_storage.upsert_company_overview(original)
        av_storage.upsert_company_overview(updated)
        result = av_storage.get_company_overview("AAPL")
        assert result is not None
        assert result.pe_ratio == pytest.approx(35.0)


# =============================================================================
# Tests: Upsert Income Statements
# =============================================================================


class TestUpsertIncomeStatements:
    """Tests for upsert_income_statements method."""

    def test_正常系_レコードが保存される(self, av_storage: AlphaVantageStorage) -> None:
        records = [_make_income_statement()]
        count = av_storage.upsert_income_statements(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_INCOME_STATEMENTS) == 1

    def test_正常系_annualとquarterlyが別レコードとして保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_income_statement(report_type="annual"),
            _make_income_statement(report_type="quarterly"),
        ]
        count = av_storage.upsert_income_statements(records)
        assert count == 2
        assert av_storage.get_row_count(TABLE_INCOME_STATEMENTS) == 2

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_income_statements([])
        assert count == 0


# =============================================================================
# Tests: Upsert Balance Sheets
# =============================================================================


class TestUpsertBalanceSheets:
    """Tests for upsert_balance_sheets method."""

    def test_正常系_レコードが保存される(self, av_storage: AlphaVantageStorage) -> None:
        records = [_make_balance_sheet()]
        count = av_storage.upsert_balance_sheets(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_BALANCE_SHEETS) == 1

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_balance_sheets([])
        assert count == 0


# =============================================================================
# Tests: Upsert Cash Flows
# =============================================================================


class TestUpsertCashFlows:
    """Tests for upsert_cash_flows method."""

    def test_正常系_レコードが保存される(self, av_storage: AlphaVantageStorage) -> None:
        records = [_make_cash_flow()]
        count = av_storage.upsert_cash_flows(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_CASH_FLOWS) == 1

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_cash_flows([])
        assert count == 0


# =============================================================================
# Tests: Upsert Earnings
# =============================================================================


class TestUpsertEarnings:
    """Tests for upsert_earnings method."""

    def test_正常系_AnnualEarningsRecordが保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            _make_annual_earnings(),
        ]
        count = av_storage.upsert_earnings(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_EARNINGS) == 1

    def test_正常系_QuarterlyEarningsRecordが保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            _make_quarterly_earnings(),
        ]
        count = av_storage.upsert_earnings(records)
        assert count == 1

    def test_正常系_AnnualとQuarterlyの混在upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            _make_annual_earnings(fiscal_date_ending="2025-09-30"),
            _make_quarterly_earnings(fiscal_date_ending="2025-12-31"),
            _make_annual_earnings(fiscal_date_ending="2024-09-30", reported_eps=6.57),
        ]
        count = av_storage.upsert_earnings(records)
        assert count == 3
        assert av_storage.get_row_count(TABLE_EARNINGS) == 3

    def test_正常系_AnnualのNullフィールドが保存される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            _make_annual_earnings(),
        ]
        av_storage.upsert_earnings(records)
        df = av_storage.get_earnings("AAPL", period_type="annual")
        assert len(df) == 1
        # Annual records have no reported_date, estimated_eps, surprise, surprise_percentage
        assert (
            pd.isna(df.iloc[0]["reported_date"]) or df.iloc[0]["reported_date"] is None
        )
        assert (
            pd.isna(df.iloc[0]["estimated_eps"]) or df.iloc[0]["estimated_eps"] is None
        )

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_earnings([])
        assert count == 0


# =============================================================================
# Tests: Upsert Economic Indicators
# =============================================================================


class TestUpsertEconomicIndicators:
    """Tests for upsert_economic_indicators method."""

    def test_正常系_レコードが保存される(self, av_storage: AlphaVantageStorage) -> None:
        records = [_make_economic_indicator()]
        count = av_storage.upsert_economic_indicators(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_ECONOMIC_INDICATORS) == 1

    def test_正常系_異なるindicatorが区別される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_economic_indicator(indicator="REAL_GDP", date="2025-10-01"),
            _make_economic_indicator(indicator="CPI", date="2025-10-01"),
        ]
        count = av_storage.upsert_economic_indicators(records)
        assert count == 2
        assert av_storage.get_row_count(TABLE_ECONOMIC_INDICATORS) == 2

    def test_正常系_maturityが区別される(self, av_storage: AlphaVantageStorage) -> None:
        records = [
            _make_economic_indicator(
                indicator="TREASURY_YIELD",
                date="2025-10-01",
                interval="daily",
                maturity="10year",
            ),
            _make_economic_indicator(
                indicator="TREASURY_YIELD",
                date="2025-10-01",
                interval="daily",
                maturity="30year",
            ),
        ]
        count = av_storage.upsert_economic_indicators(records)
        assert count == 2
        assert av_storage.get_row_count(TABLE_ECONOMIC_INDICATORS) == 2

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_economic_indicators([])
        assert count == 0


# =============================================================================
# Tests: Upsert Forex Daily
# =============================================================================


class TestUpsertForexDaily:
    """Tests for upsert_forex_daily method."""

    def test_正常系_レコードが保存される(self, av_storage: AlphaVantageStorage) -> None:
        records = [_make_forex_daily()]
        count = av_storage.upsert_forex_daily(records)
        assert count == 1
        assert av_storage.get_row_count(TABLE_FOREX_DAILY) == 1

    def test_エッジケース_空リストで0行upsert(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        count = av_storage.upsert_forex_daily([])
        assert count == 0


# =============================================================================
# Tests: Get Methods
# =============================================================================


class TestGetDailyPrices:
    """Tests for get_daily_prices method."""

    def test_正常系_シンボルで取得できる(self, av_storage: AlphaVantageStorage) -> None:
        records = [
            _make_daily_price(symbol="AAPL", date="2026-01-15"),
            _make_daily_price(symbol="GOOGL", date="2026-01-15"),
        ]
        av_storage.upsert_daily_prices(records)
        df = av_storage.get_daily_prices("AAPL")
        assert len(df) == 1
        assert df.iloc[0]["symbol"] == "AAPL"

    def test_正常系_日付範囲フィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_daily_price(date="2026-01-13"),
            _make_daily_price(date="2026-01-14"),
            _make_daily_price(date="2026-01-15"),
            _make_daily_price(date="2026-01-16"),
            _make_daily_price(date="2026-01-17"),
        ]
        av_storage.upsert_daily_prices(records)
        df = av_storage.get_daily_prices(
            "AAPL", start_date="2026-01-14", end_date="2026-01-16"
        )
        assert len(df) == 3
        assert df.iloc[0]["date"] == "2026-01-14"
        assert df.iloc[-1]["date"] == "2026-01-16"

    def test_正常系_start_dateのみフィルタ(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_daily_price(date="2026-01-13"),
            _make_daily_price(date="2026-01-15"),
        ]
        av_storage.upsert_daily_prices(records)
        df = av_storage.get_daily_prices("AAPL", start_date="2026-01-14")
        assert len(df) == 1
        assert df.iloc[0]["date"] == "2026-01-15"

    def test_正常系_end_dateのみフィルタ(self, av_storage: AlphaVantageStorage) -> None:
        records = [
            _make_daily_price(date="2026-01-13"),
            _make_daily_price(date="2026-01-15"),
        ]
        av_storage.upsert_daily_prices(records)
        df = av_storage.get_daily_prices("AAPL", end_date="2026-01-14")
        assert len(df) == 1
        assert df.iloc[0]["date"] == "2026-01-13"

    def test_エッジケース_データなしで空DataFrame(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        df = av_storage.get_daily_prices("UNKNOWN")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_正常系_日付順にソートされる(self, av_storage: AlphaVantageStorage) -> None:
        records = [
            _make_daily_price(date="2026-01-17"),
            _make_daily_price(date="2026-01-13"),
            _make_daily_price(date="2026-01-15"),
        ]
        av_storage.upsert_daily_prices(records)
        df = av_storage.get_daily_prices("AAPL")
        dates = df["date"].tolist()
        assert dates == sorted(dates)


class TestGetCompanyOverview:
    """Tests for get_company_overview method."""

    def test_正常系_CompanyOverviewRecordが返される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        record = _make_company_overview()
        av_storage.upsert_company_overview(record)
        result = av_storage.get_company_overview("AAPL")
        assert result is not None
        assert isinstance(result, CompanyOverviewRecord)
        assert result.symbol == "AAPL"

    def test_正常系_存在しないシンボルでNone(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        result = av_storage.get_company_overview("UNKNOWN")
        assert result is None


class TestGetIncomeStatements:
    """Tests for get_income_statements method."""

    def test_正常系_シンボルで取得できる(self, av_storage: AlphaVantageStorage) -> None:
        records = [
            _make_income_statement(report_type="annual"),
            _make_income_statement(report_type="quarterly"),
        ]
        av_storage.upsert_income_statements(records)
        df = av_storage.get_income_statements("AAPL")
        assert len(df) == 2

    def test_正常系_report_typeフィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_income_statement(report_type="annual"),
            _make_income_statement(report_type="quarterly"),
        ]
        av_storage.upsert_income_statements(records)
        df = av_storage.get_income_statements("AAPL", report_type="annual")
        assert len(df) == 1
        assert df.iloc[0]["report_type"] == "annual"

    def test_エッジケース_データなしで空DataFrame(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        df = av_storage.get_income_statements("UNKNOWN")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetBalanceSheets:
    """Tests for get_balance_sheets method."""

    def test_正常系_report_typeフィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_balance_sheet(report_type="annual"),
            _make_balance_sheet(report_type="quarterly"),
        ]
        av_storage.upsert_balance_sheets(records)
        df = av_storage.get_balance_sheets("AAPL", report_type="quarterly")
        assert len(df) == 1
        assert df.iloc[0]["report_type"] == "quarterly"


class TestGetCashFlows:
    """Tests for get_cash_flows method."""

    def test_正常系_report_typeフィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_cash_flow(report_type="annual"),
            _make_cash_flow(report_type="quarterly"),
        ]
        av_storage.upsert_cash_flows(records)
        df = av_storage.get_cash_flows("AAPL", report_type="annual")
        assert len(df) == 1
        assert df.iloc[0]["report_type"] == "annual"


class TestGetEarnings:
    """Tests for get_earnings method."""

    def test_正常系_period_typeフィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            _make_annual_earnings(),
            _make_quarterly_earnings(),
        ]
        av_storage.upsert_earnings(records)
        df = av_storage.get_earnings("AAPL", period_type="quarterly")
        assert len(df) == 1
        assert df.iloc[0]["period_type"] == "quarterly"

    def test_正常系_全period_type取得(self, av_storage: AlphaVantageStorage) -> None:
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            _make_annual_earnings(),
            _make_quarterly_earnings(),
        ]
        av_storage.upsert_earnings(records)
        df = av_storage.get_earnings("AAPL")
        assert len(df) == 2


class TestGetEconomicIndicators:
    """Tests for get_economic_indicators method."""

    def test_正常系_indicatorで取得できる(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_economic_indicator(indicator="REAL_GDP"),
            _make_economic_indicator(indicator="CPI", date="2025-10-01"),
        ]
        av_storage.upsert_economic_indicators(records)
        df = av_storage.get_economic_indicators("REAL_GDP")
        assert len(df) == 1
        assert df.iloc[0]["indicator"] == "REAL_GDP"

    def test_正常系_intervalフィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_economic_indicator(
                indicator="REAL_GDP",
                date="2025-10-01",
                interval="quarterly",
            ),
        ]
        av_storage.upsert_economic_indicators(records)
        df = av_storage.get_economic_indicators("REAL_GDP", interval="quarterly")
        assert len(df) == 1

    def test_正常系_maturityフィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_economic_indicator(
                indicator="TREASURY_YIELD",
                date="2025-10-01",
                interval="daily",
                maturity="10year",
            ),
            _make_economic_indicator(
                indicator="TREASURY_YIELD",
                date="2025-10-01",
                interval="daily",
                maturity="30year",
            ),
        ]
        av_storage.upsert_economic_indicators(records)
        df = av_storage.get_economic_indicators("TREASURY_YIELD", maturity="10year")
        assert len(df) == 1

    def test_エッジケース_データなしで空DataFrame(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        df = av_storage.get_economic_indicators("UNKNOWN")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetForexDaily:
    """Tests for get_forex_daily method."""

    def test_正常系_通貨ペアで取得できる(self, av_storage: AlphaVantageStorage) -> None:
        records = [
            _make_forex_daily(from_currency="USD", to_currency="JPY"),
            _make_forex_daily(
                from_currency="EUR", to_currency="USD", date="2026-01-15"
            ),
        ]
        av_storage.upsert_forex_daily(records)
        df = av_storage.get_forex_daily("USD", "JPY")
        assert len(df) == 1
        assert df.iloc[0]["from_currency"] == "USD"
        assert df.iloc[0]["to_currency"] == "JPY"

    def test_正常系_日付範囲フィルタが機能する(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_forex_daily(date="2026-01-13"),
            _make_forex_daily(date="2026-01-14"),
            _make_forex_daily(date="2026-01-15"),
        ]
        av_storage.upsert_forex_daily(records)
        df = av_storage.get_forex_daily(
            "USD", "JPY", start_date="2026-01-14", end_date="2026-01-14"
        )
        assert len(df) == 1

    def test_エッジケース_データなしで空DataFrame(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        df = av_storage.get_forex_daily("UNKNOWN", "PAIR")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# =============================================================================
# Tests: Migration
# =============================================================================


class TestMigration:
    """Tests for _migrate_add_missing_columns."""

    def test_正常系_不足カラムが自動追加される(self, tmp_path: Path) -> None:
        """Simulate a schema evolution by creating a table with fewer columns,
        then calling ensure_tables() which should add the missing columns.
        """
        db_path = tmp_path / "migration_test.db"

        # Create storage normally (full schema)
        storage = AlphaVantageStorage(db_path=db_path)

        # Verify the column exists
        col_info = storage._get_column_info(TABLE_DAILY_PRICES)
        assert "adjusted_close" in col_info

    def test_正常系_マイグレーションが冪等(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        """Calling _migrate_add_missing_columns multiple times should not error."""
        av_storage._migrate_add_missing_columns()
        av_storage._migrate_add_missing_columns()
        # Should not raise

    def test_異常系_不正なテーブル名でValueError(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        with pytest.raises(ValueError, match="Unknown table"):
            av_storage._get_column_info("invalid_table")


# =============================================================================
# Tests: DDL-Dataclass Alignment
# =============================================================================


class TestDDLDataclassAlignment:
    """Tests that DDL column names match dataclass field names exactly.

    This ensures that dataclass→tuple conversion and INSERT SQL generation
    remain consistent when either DDL or models change.
    """

    @pytest.mark.parametrize(
        ("table_name", "record_cls"),
        [
            (TABLE_DAILY_PRICES, DailyPriceRecord),
            (TABLE_COMPANY_OVERVIEW, CompanyOverviewRecord),
            (TABLE_INCOME_STATEMENTS, IncomeStatementRecord),
            (TABLE_BALANCE_SHEETS, BalanceSheetRecord),
            (TABLE_CASH_FLOWS, CashFlowRecord),
            (TABLE_ECONOMIC_INDICATORS, EconomicIndicatorRecord),
            (TABLE_FOREX_DAILY, ForexDailyRecord),
        ],
        ids=[
            "daily_prices",
            "company_overview",
            "income_statements",
            "balance_sheets",
            "cash_flows",
            "economic_indicators",
            "forex_daily",
        ],
    )
    def test_正常系_DDLカラムとdataclassフィールドが一致する(
        self,
        table_name: str,
        record_cls: type,
    ) -> None:
        from market.alphavantage.storage import _TABLE_EXPECTED_COLUMNS

        ddl_cols = _TABLE_EXPECTED_COLUMNS[table_name]
        dc_fields = {f.name for f in dataclasses.fields(record_cls)}
        assert ddl_cols == dc_fields, (
            f"Mismatch for {table_name}: "
            f"DDL-only={ddl_cols - dc_fields}, "
            f"dataclass-only={dc_fields - ddl_cols}"
        )

    def test_正常系_earnings用DDLと両レコード型のフィールド整合(
        self,
    ) -> None:
        """Earnings DDL has 9 columns. AnnualEarningsRecord has 5 fields,
        QuarterlyEarningsRecord has 9 fields. Verify the union covers
        the DDL columns.
        """
        from market.alphavantage.storage import _TABLE_EXPECTED_COLUMNS

        ddl_cols = _TABLE_EXPECTED_COLUMNS[TABLE_EARNINGS]
        annual_fields = {f.name for f in dataclasses.fields(AnnualEarningsRecord)}
        quarterly_fields = {f.name for f in dataclasses.fields(QuarterlyEarningsRecord)}

        # Quarterly should match DDL exactly
        assert ddl_cols == quarterly_fields, (
            f"QuarterlyEarningsRecord mismatch: "
            f"DDL-only={ddl_cols - quarterly_fields}, "
            f"dataclass-only={quarterly_fields - ddl_cols}"
        )

        # Annual should be a subset of DDL
        assert annual_fields.issubset(ddl_cols), (
            f"AnnualEarningsRecord has fields not in DDL: {annual_fields - ddl_cols}"
        )


# =============================================================================
# Tests: Row Count & Stats
# =============================================================================


class TestGetRowCount:
    """Tests for get_row_count method."""

    def test_正常系_空テーブルで0を返す(self, av_storage: AlphaVantageStorage) -> None:
        assert av_storage.get_row_count(TABLE_DAILY_PRICES) == 0

    def test_正常系_レコード追加後のカウントが正しい(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        records = [
            _make_daily_price(date="2026-01-15"),
            _make_daily_price(date="2026-01-16"),
        ]
        av_storage.upsert_daily_prices(records)
        assert av_storage.get_row_count(TABLE_DAILY_PRICES) == 2

    def test_異常系_不正なテーブル名でValueError(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        with pytest.raises(ValueError, match="Invalid table name"):
            av_storage.get_row_count("invalid_table")


class TestGetStats:
    """Tests for get_stats method."""

    def test_正常系_全テーブルの統計が返される(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        stats = av_storage.get_stats()
        assert len(stats) == 8
        assert all(count == 0 for count in stats.values())

    def test_正常系_データ追加後の統計が正しい(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        av_storage.upsert_daily_prices([_make_daily_price(date="2026-01-15")])
        av_storage.upsert_company_overview(_make_company_overview())
        stats = av_storage.get_stats()
        assert stats[TABLE_DAILY_PRICES] == 1
        assert stats[TABLE_COMPANY_OVERVIEW] == 1


# =============================================================================
# Tests: Factory function
# =============================================================================


class TestGetAlphaVantageStorage:
    """Tests for get_alphavantage_storage factory function."""

    def test_正常系_明示的パスでインスタンス生成(self, tmp_path: Path) -> None:
        db_path = tmp_path / "factory_test.db"
        storage = get_alphavantage_storage(db_path=db_path)
        assert isinstance(storage, AlphaVantageStorage)
        assert len(storage.get_table_names()) == 8

    def test_正常系_環境変数オーバーライド(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_path = str(tmp_path / "env_override.db")
        monkeypatch.setenv(AV_DB_PATH_ENV, env_path)
        storage = get_alphavantage_storage()
        assert isinstance(storage, AlphaVantageStorage)
        assert Path(env_path).exists()

    def test_正常系_毎回新しいインスタンスが返される(self, tmp_path: Path) -> None:
        db_path = tmp_path / "no_cache_test.db"
        s1 = get_alphavantage_storage(db_path=db_path)
        s2 = get_alphavantage_storage(db_path=db_path)
        assert s1 is not s2


# =============================================================================
# Tests: VALID_TABLE_NAMES
# =============================================================================


class TestValidTableNames:
    """Tests for _VALID_TABLE_NAMES constant."""

    def test_正常系_8テーブルが含まれる(self) -> None:
        assert len(_VALID_TABLE_NAMES) == 8

    def test_正常系_frozenset型である(self) -> None:
        assert isinstance(_VALID_TABLE_NAMES, frozenset)


# =============================================================================
# Tests: VALID_FILTER_COLUMNS
# =============================================================================


class TestValidFilterColumns:
    """Tests for _VALID_FILTER_COLUMNS constant."""

    def test_正常系_期待されるカラムが含まれる(self) -> None:
        assert {"report_type", "period_type"} == _VALID_FILTER_COLUMNS

    def test_正常系_frozenset型である(self) -> None:
        assert isinstance(_VALID_FILTER_COLUMNS, frozenset)


# =============================================================================
# Tests: _query_financial_table invalid filter
# =============================================================================


class TestQueryFinancialTableValidation:
    """Tests for _query_financial_table filter column validation."""

    def test_異常系_不正なfilter_columnでValueError(
        self, av_storage: AlphaVantageStorage
    ) -> None:
        with pytest.raises(ValueError, match="Invalid filter column"):
            av_storage._query_financial_table(
                TABLE_INCOME_STATEMENTS,
                "AAPL",
                filter_column="invalid_column",
                filter_value="annual",
            )
