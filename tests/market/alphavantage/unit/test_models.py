"""Unit tests for Alpha Vantage storage record models.

Verifies that all 9 frozen dataclass record types are correctly defined
with the expected field counts, immutability (frozen), and field presence/absence
for the split Earnings records.

See Also
--------
market.alphavantage.models : Implementation under test.
docs/superpowers/specs/2026-03-24-alphavantage-storage-design.md : Design spec.
"""

from __future__ import annotations

import dataclasses

import pytest

from market.alphavantage.models import (
    AnnualEarningsRecord,
    BalanceSheetRecord,
    CashFlowRecord,
    CompanyOverviewRecord,
    DailyPriceRecord,
    EarningsRecord,
    EconomicIndicatorRecord,
    ForexDailyRecord,
    IncomeStatementRecord,
    QuarterlyEarningsRecord,
)

# =========================================================================
# Helper
# =========================================================================


def _field_names(cls: type) -> set[str]:
    """Return the set of field names for a dataclass."""
    return {f.name for f in dataclasses.fields(cls)}


# =========================================================================
# frozen 検証 — 全 9 dataclass
# =========================================================================


class TestFrozen:
    """全 dataclass が frozen=True であることを検証する。"""

    def test_正常系_DailyPriceRecordはfrozenである(self) -> None:
        record = DailyPriceRecord(
            symbol="AAPL",
            date="2026-01-01",
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            adjusted_close=153.0,
            volume=1_000_000,
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_CompanyOverviewRecordはfrozenである(self) -> None:
        record = CompanyOverviewRecord(
            symbol="AAPL",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_IncomeStatementRecordはfrozenである(self) -> None:
        record = IncomeStatementRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            report_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_BalanceSheetRecordはfrozenである(self) -> None:
        record = BalanceSheetRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            report_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_CashFlowRecordはfrozenである(self) -> None:
        record = CashFlowRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            report_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_AnnualEarningsRecordはfrozenである(self) -> None:
        record = AnnualEarningsRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            period_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_QuarterlyEarningsRecordはfrozenである(self) -> None:
        record = QuarterlyEarningsRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            period_type="quarterly",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.symbol = "MSFT"

    def test_正常系_EconomicIndicatorRecordはfrozenである(self) -> None:
        record = EconomicIndicatorRecord(
            indicator="REAL_GDP",
            date="2026-01-01",
            interval="quarterly",
            maturity="",
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.indicator = "CPI"

    def test_正常系_ForexDailyRecordはfrozenである(self) -> None:
        record = ForexDailyRecord(
            from_currency="USD",
            to_currency="JPY",
            date="2026-01-01",
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            fetched_at="2026-01-01T00:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.from_currency = "EUR"


# =========================================================================
# フィールド数チェック
# =========================================================================


class TestFieldCount:
    """各 dataclass のフィールド数が設計と一致することを検証する。"""

    def test_正常系_DailyPriceRecordは9フィールド(self) -> None:
        assert len(dataclasses.fields(DailyPriceRecord)) == 9

    def test_正常系_CompanyOverviewRecordは47フィールド(self) -> None:
        # symbol(1) + 9 text + 36 numeric (DDL) + fetched_at(1) = 47
        assert len(dataclasses.fields(CompanyOverviewRecord)) == 47

    def test_正常系_IncomeStatementRecordは21フィールド(self) -> None:
        assert len(dataclasses.fields(IncomeStatementRecord)) == 21

    def test_正常系_BalanceSheetRecordは29フィールド(self) -> None:
        # symbol + fiscal_date_ending + report_type(3) + 25 financial + fetched_at(1) = 29
        assert len(dataclasses.fields(BalanceSheetRecord)) == 29

    def test_正常系_CashFlowRecordは22フィールド(self) -> None:
        # symbol + fiscal_date_ending + report_type(3) + 18 financial + fetched_at(1) = 22
        assert len(dataclasses.fields(CashFlowRecord)) == 22

    def test_正常系_AnnualEarningsRecordは5フィールド(self) -> None:
        assert len(dataclasses.fields(AnnualEarningsRecord)) == 5

    def test_正常系_QuarterlyEarningsRecordは9フィールド(self) -> None:
        assert len(dataclasses.fields(QuarterlyEarningsRecord)) == 9

    def test_正常系_EconomicIndicatorRecordは6フィールド(self) -> None:
        assert len(dataclasses.fields(EconomicIndicatorRecord)) == 6

    def test_正常系_ForexDailyRecordは8フィールド(self) -> None:
        assert len(dataclasses.fields(ForexDailyRecord)) == 8


# =========================================================================
# Earnings 分割検証
# =========================================================================


class TestEarningsSplit:
    """AnnualEarningsRecord と QuarterlyEarningsRecord のフィールド差異を検証する。"""

    def test_正常系_AnnualEarningsRecordにreported_dateが存在しない(self) -> None:
        fields = _field_names(AnnualEarningsRecord)
        assert "reported_date" not in fields

    def test_正常系_AnnualEarningsRecordにestimated_epsが存在しない(self) -> None:
        fields = _field_names(AnnualEarningsRecord)
        assert "estimated_eps" not in fields

    def test_正常系_AnnualEarningsRecordにsurpriseが存在しない(self) -> None:
        fields = _field_names(AnnualEarningsRecord)
        assert "surprise" not in fields

    def test_正常系_AnnualEarningsRecordにsurprise_percentageが存在しない(self) -> None:
        fields = _field_names(AnnualEarningsRecord)
        assert "surprise_percentage" not in fields

    def test_正常系_QuarterlyEarningsRecordにreported_dateが存在する(self) -> None:
        fields = _field_names(QuarterlyEarningsRecord)
        assert "reported_date" in fields

    def test_正常系_QuarterlyEarningsRecordにestimated_epsが存在する(self) -> None:
        fields = _field_names(QuarterlyEarningsRecord)
        assert "estimated_eps" in fields

    def test_正常系_QuarterlyEarningsRecordにsurpriseが存在する(self) -> None:
        fields = _field_names(QuarterlyEarningsRecord)
        assert "surprise" in fields

    def test_正常系_QuarterlyEarningsRecordにsurprise_percentageが存在する(self) -> None:
        fields = _field_names(QuarterlyEarningsRecord)
        assert "surprise_percentage" in fields


# =========================================================================
# EarningsRecord 型エイリアス検証
# =========================================================================


class TestEarningsRecordAlias:
    """EarningsRecord 型エイリアスが正しく定義されていることを検証する。"""

    def test_正常系_EarningsRecordはUnion型エイリアスである(self) -> None:
        # EarningsRecord = AnnualEarningsRecord | QuarterlyEarningsRecord
        # isinstance チェックで型エイリアスの構成型を検証
        annual = AnnualEarningsRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            period_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        quarterly = QuarterlyEarningsRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            period_type="quarterly",
            fetched_at="2026-01-01T00:00:00",
        )
        # Both should be valid EarningsRecord instances
        assert isinstance(annual, AnnualEarningsRecord)
        assert isinstance(quarterly, QuarterlyEarningsRecord)
        # Verify the alias is a Union type
        import typing

        args = typing.get_args(EarningsRecord)
        assert set(args) == {AnnualEarningsRecord, QuarterlyEarningsRecord}


# =========================================================================
# Optional フィールド検証
# =========================================================================


class TestOptionalFields:
    """Optional フィールドに None を指定できることを検証する。"""

    def test_正常系_DailyPriceRecordのadjusted_closeにNone指定可(self) -> None:
        record = DailyPriceRecord(
            symbol="AAPL",
            date="2026-01-01",
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            adjusted_close=None,
            volume=1_000_000,
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.adjusted_close is None

    def test_正常系_CompanyOverviewRecordのOptionalフィールドにNone指定可(self) -> None:
        record = CompanyOverviewRecord(
            symbol="AAPL",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.name is None
        assert record.pe_ratio is None
        assert record.beta is None

    def test_正常系_IncomeStatementRecordのOptionalフィールドにNone指定可(self) -> None:
        record = IncomeStatementRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            report_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.reported_currency is None
        assert record.gross_profit is None
        assert record.net_income is None

    def test_正常系_BalanceSheetRecordのOptionalフィールドにNone指定可(self) -> None:
        record = BalanceSheetRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            report_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.reported_currency is None
        assert record.total_assets is None

    def test_正常系_CashFlowRecordのOptionalフィールドにNone指定可(self) -> None:
        record = CashFlowRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            report_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.reported_currency is None
        assert record.operating_cashflow is None

    def test_正常系_AnnualEarningsRecordのreported_epsにNone指定可(self) -> None:
        record = AnnualEarningsRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            period_type="annual",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.reported_eps is None

    def test_正常系_QuarterlyEarningsRecordのOptionalフィールドにNone指定可(self) -> None:
        record = QuarterlyEarningsRecord(
            symbol="AAPL",
            fiscal_date_ending="2025-12-31",
            period_type="quarterly",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.reported_date is None
        assert record.reported_eps is None
        assert record.estimated_eps is None
        assert record.surprise is None
        assert record.surprise_percentage is None

    def test_正常系_EconomicIndicatorRecordのvalueにNone指定可(self) -> None:
        record = EconomicIndicatorRecord(
            indicator="REAL_GDP",
            date="2026-01-01",
            interval="quarterly",
            maturity="",
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.value is None

    def test_正常系_ForexDailyRecordは全フィールド必須(self) -> None:
        record = ForexDailyRecord(
            from_currency="USD",
            to_currency="JPY",
            date="2026-01-01",
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            fetched_at="2026-01-01T00:00:00",
        )
        assert record.from_currency == "USD"
        assert record.close == 150.5


# =========================================================================
# __all__ エクスポート検証
# =========================================================================


class TestModuleExports:
    """__all__ リストが全型を網羅していることを検証する。"""

    def test_正常系_allリストが全型を含む(self) -> None:
        from market.alphavantage import models

        expected_exports = {
            "AnnualEarningsRecord",
            "BalanceSheetRecord",
            "CashFlowRecord",
            "CompanyOverviewRecord",
            "DailyPriceRecord",
            "EarningsRecord",
            "EconomicIndicatorRecord",
            "ForexDailyRecord",
            "IncomeStatementRecord",
            "QuarterlyEarningsRecord",
        }
        assert set(models.__all__) == expected_exports
