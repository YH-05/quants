"""Unit tests for ETF.com storage record models.

Verifies that all 11 frozen dataclass record types are correctly defined
with the expected field counts, immutability (frozen), primary key fields,
Optional data fields, and the ``has_failures`` property on CollectionSummary.

See Also
--------
market.etfcom.models : Implementation under test.
market.alphavantage.models : Reference pattern for frozen dataclass records.
"""

from __future__ import annotations

import dataclasses

import pytest

from market.etfcom.models import (
    AllocationRecord,
    CollectionResult,
    CollectionSummary,
    FundFlowsRecord,
    HoldingRecord,
    PerformanceRecord,
    PortfolioRecord,
    QuoteRecord,
    StructureRecord,
    TickerRecord,
    TradabilityRecord,
)

# =========================================================================
# Helper
# =========================================================================


def _field_names(cls: type) -> set[str]:
    """Return the set of field names for a dataclass."""
    return {f.name for f in dataclasses.fields(cls)}


# =========================================================================
# frozen 検証 — 全 11 dataclass
# =========================================================================


class TestFrozen:
    """全 dataclass が frozen=True であることを検証する。"""

    def test_正常系_TickerRecordはfrozenである(self) -> None:
        record = TickerRecord(
            ticker="SPY",
            fund_id=1,
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_FundFlowsRecordはfrozenである(self) -> None:
        record = FundFlowsRecord(
            ticker="SPY",
            nav_date="2026-01-15",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_HoldingRecordはfrozenである(self) -> None:
        record = HoldingRecord(
            ticker="SPY",
            holding_ticker="AAPL",
            as_of_date="2026-01-10",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_PortfolioRecordはfrozenである(self) -> None:
        record = PortfolioRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_AllocationRecordはfrozenである(self) -> None:
        record = AllocationRecord(
            ticker="SPY",
            allocation_type="sector",
            name="Technology",
            as_of_date="2026-01-10",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_TradabilityRecordはfrozenである(self) -> None:
        record = TradabilityRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_StructureRecordはfrozenである(self) -> None:
        record = StructureRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_PerformanceRecordはfrozenである(self) -> None:
        record = PerformanceRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_QuoteRecordはfrozenである(self) -> None:
        record = QuoteRecord(
            ticker="SPY",
            quote_date="2026-01-15",
            fetched_at="2026-01-15T20:00:00",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ticker = "VOO"

    def test_正常系_CollectionResultはfrozenである(self) -> None:
        result = CollectionResult(
            ticker="SPY",
            table="etfcom_fund_flows",
            rows_upserted=250,
            success=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.ticker = "VOO"

    def test_正常系_CollectionSummaryはfrozenである(self) -> None:
        summary = CollectionSummary(
            total_tickers=1,
            successful=1,
            failed=0,
            total_rows=250,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            summary.total_tickers = 10


# =========================================================================
# フィールド数チェック
# =========================================================================


class TestFieldCount:
    """各 dataclass のフィールド数が設計と一致することを検証する。"""

    def test_正常系_TickerRecordは8フィールド(self) -> None:
        assert len(dataclasses.fields(TickerRecord)) == 8

    def test_正常系_FundFlowsRecordは10フィールド(self) -> None:
        assert len(dataclasses.fields(FundFlowsRecord)) == 10

    def test_正常系_HoldingRecordは8フィールド(self) -> None:
        assert len(dataclasses.fields(HoldingRecord)) == 8

    def test_正常系_PortfolioRecordは11フィールド(self) -> None:
        assert len(dataclasses.fields(PortfolioRecord)) == 11

    def test_正常系_AllocationRecordは8フィールド(self) -> None:
        assert len(dataclasses.fields(AllocationRecord)) == 8

    def test_正常系_TradabilityRecordは12フィールド(self) -> None:
        assert len(dataclasses.fields(TradabilityRecord)) == 12

    def test_正常系_StructureRecordは10フィールド(self) -> None:
        assert len(dataclasses.fields(StructureRecord)) == 10

    def test_正常系_PerformanceRecordは13フィールド(self) -> None:
        assert len(dataclasses.fields(PerformanceRecord)) == 13

    def test_正常系_QuoteRecordは12フィールド(self) -> None:
        assert len(dataclasses.fields(QuoteRecord)) == 12

    def test_正常系_CollectionResultは5フィールド(self) -> None:
        assert len(dataclasses.fields(CollectionResult)) == 5

    def test_正常系_CollectionSummaryは5フィールド(self) -> None:
        assert len(dataclasses.fields(CollectionSummary)) == 5


# =========================================================================
# PK フィールド存在検証
# =========================================================================


class TestPrimaryKeyFields:
    """各テーブル対応レコード型に正しい PK フィールドが存在することを検証する。"""

    def test_正常系_TickerRecordにtickerフィールドが存在する(self) -> None:
        fields = _field_names(TickerRecord)
        assert "ticker" in fields
        assert "fund_id" in fields

    def test_正常系_FundFlowsRecordにticker_nav_dateフィールドが存在する(self) -> None:
        fields = _field_names(FundFlowsRecord)
        assert "ticker" in fields
        assert "nav_date" in fields

    def test_正常系_HoldingRecordにticker_holding_ticker_as_of_dateフィールドが存在する(
        self,
    ) -> None:
        fields = _field_names(HoldingRecord)
        assert "ticker" in fields
        assert "holding_ticker" in fields
        assert "as_of_date" in fields

    def test_正常系_PortfolioRecordにtickerフィールドが存在する(self) -> None:
        fields = _field_names(PortfolioRecord)
        assert "ticker" in fields

    def test_正常系_AllocationRecordに4PKフィールドが存在する(self) -> None:
        fields = _field_names(AllocationRecord)
        assert "ticker" in fields
        assert "allocation_type" in fields
        assert "name" in fields
        assert "as_of_date" in fields

    def test_正常系_TradabilityRecordにtickerフィールドが存在する(self) -> None:
        fields = _field_names(TradabilityRecord)
        assert "ticker" in fields

    def test_正常系_StructureRecordにtickerフィールドが存在する(self) -> None:
        fields = _field_names(StructureRecord)
        assert "ticker" in fields

    def test_正常系_PerformanceRecordにtickerフィールドが存在する(self) -> None:
        fields = _field_names(PerformanceRecord)
        assert "ticker" in fields

    def test_正常系_QuoteRecordにticker_quote_dateフィールドが存在する(self) -> None:
        fields = _field_names(QuoteRecord)
        assert "ticker" in fields
        assert "quote_date" in fields


# =========================================================================
# fetched_at フィールド検証
# =========================================================================


class TestFetchedAt:
    """全テーブル対応レコード型に fetched_at フィールドが存在することを検証する。"""

    @pytest.mark.parametrize(
        "cls",
        [
            TickerRecord,
            FundFlowsRecord,
            HoldingRecord,
            PortfolioRecord,
            AllocationRecord,
            TradabilityRecord,
            StructureRecord,
            PerformanceRecord,
            QuoteRecord,
        ],
    )
    def test_パラメトライズ_全レコード型にfetched_atフィールドが存在する(
        self, cls: type
    ) -> None:
        fields = _field_names(cls)
        assert "fetched_at" in fields


# =========================================================================
# Optional フィールド検証
# =========================================================================


class TestOptionalFields:
    """Optional フィールドに None を指定できることを検証する。"""

    def test_正常系_TickerRecordのOptionalフィールドにNone指定可(self) -> None:
        record = TickerRecord(
            ticker="SPY",
            fund_id=1,
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.name is None
        assert record.issuer is None
        assert record.asset_class is None
        assert record.inception_date is None
        assert record.segment is None

    def test_正常系_FundFlowsRecordのOptionalフィールドにNone指定可(self) -> None:
        record = FundFlowsRecord(
            ticker="SPY",
            nav_date="2026-01-15",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.nav is None
        assert record.nav_change is None
        assert record.fund_flows is None
        assert record.aum is None

    def test_正常系_HoldingRecordのOptionalフィールドにNone指定可(self) -> None:
        record = HoldingRecord(
            ticker="SPY",
            holding_ticker="AAPL",
            as_of_date="2026-01-10",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.holding_name is None
        assert record.weight is None
        assert record.market_value is None
        assert record.shares is None

    def test_正常系_PortfolioRecordのOptionalフィールドにNone指定可(self) -> None:
        record = PortfolioRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.pe_ratio is None
        assert record.pb_ratio is None
        assert record.dividend_yield is None
        assert record.number_of_holdings is None

    def test_正常系_AllocationRecordのOptionalフィールドにNone指定可(self) -> None:
        record = AllocationRecord(
            ticker="SPY",
            allocation_type="sector",
            name="Technology",
            as_of_date="2026-01-10",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.weight is None
        assert record.market_value is None
        assert record.count is None

    def test_正常系_TradabilityRecordのOptionalフィールドにNone指定可(self) -> None:
        record = TradabilityRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.avg_daily_volume is None
        assert record.median_bid_ask_spread is None
        assert record.implied_liquidity is None

    def test_正常系_StructureRecordのOptionalフィールドにNone指定可(self) -> None:
        record = StructureRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.legal_structure is None
        assert record.index_tracked is None
        assert record.uses_derivatives is None

    def test_正常系_PerformanceRecordのOptionalフィールドにNone指定可(self) -> None:
        record = PerformanceRecord(
            ticker="SPY",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.return_1y is None
        assert record.r_squared is None
        assert record.standard_deviation is None

    def test_正常系_QuoteRecordのOptionalフィールドにNone指定可(self) -> None:
        record = QuoteRecord(
            ticker="SPY",
            quote_date="2026-01-15",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.open is None
        assert record.close is None
        assert record.volume is None
        assert record.bid is None
        assert record.ask is None


# =========================================================================
# データ値アクセス検証
# =========================================================================


class TestDataAccess:
    """各レコード型のデータフィールドにアクセスできることを検証する。"""

    def test_正常系_TickerRecordの全フィールドにアクセス可(self) -> None:
        record = TickerRecord(
            ticker="SPY",
            fund_id=1,
            name="SPDR S&P 500 ETF Trust",
            issuer="State Street",
            asset_class="Equity",
            inception_date="1993-01-22",
            segment="Equity: U.S. - Large Cap",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.ticker == "SPY"
        assert record.fund_id == 1
        assert record.name == "SPDR S&P 500 ETF Trust"
        assert record.issuer == "State Street"
        assert record.asset_class == "Equity"
        assert record.inception_date == "1993-01-22"
        assert record.segment == "Equity: U.S. - Large Cap"
        assert record.fetched_at == "2026-01-15T20:00:00"

    def test_正常系_FundFlowsRecordの全フィールドにアクセス可(self) -> None:
        record = FundFlowsRecord(
            ticker="SPY",
            nav_date="2026-01-15",
            nav=580.25,
            nav_change=2.15,
            nav_change_percent=0.48,
            premium_discount=-0.02,
            fund_flows=1_500_000_000.0,
            shares_outstanding=920_000_000.0,
            aum=414_230_000_000.0,
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.ticker == "SPY"
        assert record.nav_date == "2026-01-15"
        assert record.nav == 580.25
        assert record.nav_change == 2.15
        assert record.nav_change_percent == 0.48
        assert record.premium_discount == -0.02
        assert record.fund_flows == 1_500_000_000.0
        assert record.shares_outstanding == 920_000_000.0
        assert record.aum == 414_230_000_000.0
        assert record.fetched_at == "2026-01-15T20:00:00"

    def test_正常系_PerformanceRecordのreturnフィールドにアクセス可(self) -> None:
        record = PerformanceRecord(
            ticker="SPY",
            return_1m=0.035,
            return_3m=0.085,
            return_ytd=0.125,
            return_1y=0.265,
            return_3y=0.098,
            return_5y=0.112,
            return_10y=0.128,
            r_squared=0.9998,
            beta=1.0,
            standard_deviation=0.15,
            as_of_date="2026-01-15",
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.return_1m == 0.035
        assert record.return_1y == 0.265
        assert record.return_10y == 0.128
        assert record.r_squared == 0.9998

    def test_正常系_QuoteRecordのOHLCフィールドにアクセス可(self) -> None:
        record = QuoteRecord(
            ticker="SPY",
            quote_date="2026-01-15",
            open=578.50,
            high=582.10,
            low=577.30,
            close=580.25,
            volume=75_000_000.0,
            bid=580.20,
            ask=580.30,
            bid_size=500.0,
            ask_size=300.0,
            fetched_at="2026-01-15T20:00:00",
        )
        assert record.open == 578.50
        assert record.high == 582.10
        assert record.low == 577.30
        assert record.close == 580.25
        assert record.volume == 75_000_000.0


# =========================================================================
# CollectionResult / CollectionSummary 検証
# =========================================================================


class TestCollectionResult:
    """CollectionResult のフィールドとデフォルト値を検証する。"""

    def test_正常系_成功結果の作成(self) -> None:
        result = CollectionResult(
            ticker="SPY",
            table="etfcom_fund_flows",
            rows_upserted=250,
            success=True,
        )
        assert result.ticker == "SPY"
        assert result.table == "etfcom_fund_flows"
        assert result.rows_upserted == 250
        assert result.success is True
        assert result.error_message is None

    def test_正常系_失敗結果の作成(self) -> None:
        result = CollectionResult(
            ticker="SPY",
            table="etfcom_fund_flows",
            rows_upserted=0,
            success=False,
            error_message="API returned 403",
        )
        assert result.success is False
        assert result.error_message == "API returned 403"

    def test_正常系_デフォルト値(self) -> None:
        result = CollectionResult(
            ticker="SPY",
            table="etfcom_tickers",
        )
        assert result.rows_upserted == 0
        assert result.success is True
        assert result.error_message is None


class TestCollectionSummary:
    """CollectionSummary のフィールドと has_failures プロパティを検証する。"""

    def test_正常系_失敗なしの場合has_failuresはFalse(self) -> None:
        summary = CollectionSummary(
            results=(
                CollectionResult("SPY", "etfcom_fund_flows", 250, True),
                CollectionResult("VOO", "etfcom_fund_flows", 200, True),
            ),
            total_tickers=2,
            successful=2,
            failed=0,
            total_rows=450,
        )
        assert summary.has_failures is False

    def test_正常系_失敗ありの場合has_failuresはTrue(self) -> None:
        summary = CollectionSummary(
            results=(
                CollectionResult("SPY", "etfcom_fund_flows", 250, True),
                CollectionResult(
                    "QQQ",
                    "etfcom_fund_flows",
                    0,
                    False,
                    "API error",
                ),
            ),
            total_tickers=2,
            successful=1,
            failed=1,
            total_rows=250,
        )
        assert summary.has_failures is True

    def test_正常系_デフォルト値(self) -> None:
        summary = CollectionSummary()
        assert summary.results == ()
        assert summary.total_tickers == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.total_rows == 0
        assert summary.has_failures is False


# =========================================================================
# __all__ エクスポート検証
# =========================================================================


class TestModuleExports:
    """models モジュールの __all__ エクスポートを検証する。"""

    def test_正常系_allに11クラスが含まれる(self) -> None:
        from market.etfcom import models

        assert len(models.__all__) == 11

    def test_正常系_全レコード型がallに含まれる(self) -> None:
        from market.etfcom import models

        expected = {
            "AllocationRecord",
            "CollectionResult",
            "CollectionSummary",
            "FundFlowsRecord",
            "HoldingRecord",
            "PerformanceRecord",
            "PortfolioRecord",
            "QuoteRecord",
            "StructureRecord",
            "TickerRecord",
            "TradabilityRecord",
        }
        assert set(models.__all__) == expected
