"""Unit tests for NasdaqClient type definitions (client_types module).

Tests cover:
- Frozen validation: all dataclass types reject attribute assignment
- Default values: NasdaqFetchOptions defaults are correct
- MoverSection Enum: 3 values (most_advanced, most_declined, most_active)
- Field completeness: each type has expected fields

Test TODO List:
- [x] test_正常系_全型がfrozenで属性代入を拒否する
- [x] test_正常系_NasdaqFetchOptionsのデフォルト値が正しい
- [x] test_正常系_MoverSectionEnumが3値を持つ
- [x] test_正常系_各型が期待するフィールドを持つ

See Also
--------
market.nasdaq.client_types : Type definitions under test.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from market.nasdaq.client_types import (
    AnalystRatings,
    AnalystSummary,
    DividendCalendarRecord,
    DividendRecord,
    EarningsDate,
    EarningsForecast,
    EarningsForecastPeriod,
    EarningsRecord,
    EtfRecord,
    FinancialStatement,
    FinancialStatementRow,
    InsiderTrade,
    InstitutionalHolding,
    IpoRecord,
    MarketMover,
    MoverSection,
    NasdaqFetchOptions,
    RatingCount,
    ShortInterestRecord,
    SplitRecord,
    TargetPrice,
)

# =============================================================================
# Frozen Validation Tests
# =============================================================================


class TestFrozenDataclasses:
    """All client_types dataclasses are frozen (immutable)."""

    @pytest.mark.parametrize(
        ("instance", "attr", "value"),
        [
            pytest.param(
                NasdaqFetchOptions(),
                "use_cache",
                False,
                id="NasdaqFetchOptions",
            ),
            pytest.param(
                EarningsRecord(symbol="AAPL"),
                "symbol",
                "MSFT",
                id="EarningsRecord",
            ),
            pytest.param(
                DividendCalendarRecord(symbol="AAPL"),
                "symbol",
                "MSFT",
                id="DividendCalendarRecord",
            ),
            pytest.param(
                SplitRecord(symbol="NVDA"),
                "symbol",
                "AAPL",
                id="SplitRecord",
            ),
            pytest.param(
                IpoRecord(symbol="NEWCO"),
                "symbol",
                "OTHER",
                id="IpoRecord",
            ),
            pytest.param(
                MarketMover(symbol="AAPL"),
                "symbol",
                "MSFT",
                id="MarketMover",
            ),
            pytest.param(
                EtfRecord(symbol="SPY"),
                "symbol",
                "QQQ",
                id="EtfRecord",
            ),
            pytest.param(
                EarningsForecastPeriod(fiscal_end="Dec 2025"),
                "fiscal_end",
                "Mar 2026",
                id="EarningsForecastPeriod",
            ),
            pytest.param(
                EarningsForecast(symbol="AAPL", yearly=[], quarterly=[]),
                "symbol",
                "MSFT",
                id="EarningsForecast",
            ),
            pytest.param(
                RatingCount(date="Current Quarter"),
                "strong_buy",
                99,
                id="RatingCount",
            ),
            pytest.param(
                AnalystRatings(symbol="AAPL", ratings=[]),
                "symbol",
                "MSFT",
                id="AnalystRatings",
            ),
            pytest.param(
                TargetPrice(symbol="AAPL"),
                "symbol",
                "MSFT",
                id="TargetPrice",
            ),
            pytest.param(
                EarningsDate(symbol="AAPL"),
                "symbol",
                "MSFT",
                id="EarningsDate",
            ),
            pytest.param(
                AnalystSummary(symbol="AAPL"),
                "symbol",
                "MSFT",
                id="AnalystSummary",
            ),
            pytest.param(
                ShortInterestRecord(settlement_date="03/15/2026"),
                "settlement_date",
                "04/01/2026",
                id="ShortInterestRecord",
            ),
            pytest.param(
                DividendRecord(ex_date="02/07/2026"),
                "ex_date",
                "03/01/2026",
                id="DividendRecord",
            ),
            pytest.param(
                InsiderTrade(insider_name="COOK TIMOTHY D"),
                "insider_name",
                "OTHER",
                id="InsiderTrade",
            ),
            pytest.param(
                InstitutionalHolding(holder_name="Vanguard"),
                "holder_name",
                "BlackRock",
                id="InstitutionalHolding",
            ),
            pytest.param(
                FinancialStatementRow(label="Revenue", values=["100"]),
                "label",
                "Cost",
                id="FinancialStatementRow",
            ),
            pytest.param(
                FinancialStatement(
                    symbol="AAPL",
                    frequency="annual",
                    headers=["2025"],
                    income_statement=[],
                    balance_sheet=[],
                    cash_flow=[],
                ),
                "symbol",
                "MSFT",
                id="FinancialStatement",
            ),
        ],
    )
    def test_正常系_frozen型への属性代入でFrozenInstanceError(
        self,
        instance: object,
        attr: str,
        value: object,
    ) -> None:
        """Frozen dataclasses reject attribute assignment with FrozenInstanceError."""
        with pytest.raises(FrozenInstanceError):
            setattr(instance, attr, value)


# =============================================================================
# Default Value Tests
# =============================================================================


class TestNasdaqFetchOptionsDefaults:
    """NasdaqFetchOptions default values."""

    def test_正常系_use_cacheのデフォルトはTrue(self) -> None:
        """Default use_cache is True."""
        opts = NasdaqFetchOptions()
        assert opts.use_cache is True

    def test_正常系_force_refreshのデフォルトはFalse(self) -> None:
        """Default force_refresh is False."""
        opts = NasdaqFetchOptions()
        assert opts.force_refresh is False

    def test_正常系_use_cache_Falseで生成可能(self) -> None:
        """Can create with use_cache=False."""
        opts = NasdaqFetchOptions(use_cache=False)
        assert opts.use_cache is False
        assert opts.force_refresh is False

    def test_正常系_force_refresh_Trueで生成可能(self) -> None:
        """Can create with force_refresh=True."""
        opts = NasdaqFetchOptions(force_refresh=True)
        assert opts.use_cache is True
        assert opts.force_refresh is True


# =============================================================================
# MoverSection Enum Tests
# =============================================================================


class TestMoverSectionEnum:
    """MoverSection Enum validation."""

    def test_正常系_MoverSectionが3値を持つ(self) -> None:
        """MoverSection has exactly 3 members."""
        assert len(MoverSection) == 3

    def test_正常系_MOST_ADVANCEDの値が正しい(self) -> None:
        """MOST_ADVANCED has value 'most_advanced'."""
        assert MoverSection.MOST_ADVANCED.value == "most_advanced"

    def test_正常系_MOST_DECLINEDの値が正しい(self) -> None:
        """MOST_DECLINED has value 'most_declined'."""
        assert MoverSection.MOST_DECLINED.value == "most_declined"

    def test_正常系_MOST_ACTIVEの値が正しい(self) -> None:
        """MOST_ACTIVE has value 'most_active'."""
        assert MoverSection.MOST_ACTIVE.value == "most_active"

    def test_正常系_文字列からEnumに変換できる(self) -> None:
        """String values can be converted to MoverSection."""
        assert MoverSection("most_advanced") is MoverSection.MOST_ADVANCED
        assert MoverSection("most_declined") is MoverSection.MOST_DECLINED
        assert MoverSection("most_active") is MoverSection.MOST_ACTIVE

    def test_正常系_MoverSectionはstrのサブクラス(self) -> None:
        """MoverSection is a str Enum."""
        assert isinstance(MoverSection.MOST_ADVANCED, str)


# =============================================================================
# RatingCount Default Value Tests
# =============================================================================


class TestRatingCountDefaults:
    """RatingCount default values."""

    def test_正常系_全カウントのデフォルトは0(self) -> None:
        """All count fields default to 0."""
        rc = RatingCount()
        assert rc.date is None
        assert rc.strong_buy == 0
        assert rc.buy == 0
        assert rc.hold == 0
        assert rc.sell == 0
        assert rc.strong_sell == 0


# =============================================================================
# Field Existence Tests
# =============================================================================


class TestEarningsRecordFields:
    """EarningsRecord field existence."""

    def test_正常系_必須フィールドsymbolが存在(self) -> None:
        """EarningsRecord has required 'symbol' field."""
        record = EarningsRecord(symbol="AAPL")
        assert record.symbol == "AAPL"

    def test_正常系_オプショナルフィールドがNoneデフォルト(self) -> None:
        """Optional fields default to None."""
        record = EarningsRecord(symbol="AAPL")
        assert record.name is None
        assert record.date is None
        assert record.eps_estimate is None
        assert record.eps_actual is None
        assert record.surprise is None
        assert record.fiscal_quarter_ending is None
        assert record.market_cap is None


class TestInsiderTradeFields:
    """InsiderTrade field existence."""

    def test_正常系_全オプショナルフィールドがNoneデフォルト(self) -> None:
        """All InsiderTrade fields default to None."""
        trade = InsiderTrade()
        assert trade.insider_name is None
        assert trade.relation is None
        assert trade.transaction_type is None
        assert trade.ownership_type is None
        assert trade.shares_traded is None
        assert trade.price is None
        assert trade.value is None
        assert trade.date is None
        assert trade.shares_held is None
        assert trade.url is None


class TestFinancialStatementFields:
    """FinancialStatement field existence."""

    def test_正常系_必須フィールドが正しくセットされる(self) -> None:
        """All required fields are set correctly."""
        fs = FinancialStatement(
            symbol="AAPL",
            frequency="annual",
            headers=["2025", "2024"],
            income_statement=[],
            balance_sheet=[],
            cash_flow=[],
        )
        assert fs.symbol == "AAPL"
        assert fs.frequency == "annual"
        assert fs.headers == ["2025", "2024"]
        assert fs.income_statement == []
        assert fs.balance_sheet == []
        assert fs.cash_flow == []
