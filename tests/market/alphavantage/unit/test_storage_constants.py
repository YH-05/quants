"""Tests for market.alphavantage.storage_constants module."""

from market.alphavantage.storage_constants import (
    AV_DB_PATH_ENV,
    DEFAULT_DB_NAME,
    TABLE_BALANCE_SHEETS,
    TABLE_CASH_FLOWS,
    TABLE_COMPANY_OVERVIEW,
    TABLE_DAILY_PRICES,
    TABLE_EARNINGS,
    TABLE_ECONOMIC_INDICATORS,
    TABLE_FOREX_DAILY,
    TABLE_INCOME_STATEMENTS,
)


class TestTableNamePrefix:
    """全テーブル名定数が av_ プレフィックスを持つことを検証する。"""

    def test_正常系_daily_pricesがavプレフィックスを持つ(self) -> None:
        assert TABLE_DAILY_PRICES.startswith("av_")

    def test_正常系_company_overviewがavプレフィックスを持つ(self) -> None:
        assert TABLE_COMPANY_OVERVIEW.startswith("av_")

    def test_正常系_income_statementsがavプレフィックスを持つ(self) -> None:
        assert TABLE_INCOME_STATEMENTS.startswith("av_")

    def test_正常系_balance_sheetsがavプレフィックスを持つ(self) -> None:
        assert TABLE_BALANCE_SHEETS.startswith("av_")

    def test_正常系_cash_flowsがavプレフィックスを持つ(self) -> None:
        assert TABLE_CASH_FLOWS.startswith("av_")

    def test_正常系_earningsがavプレフィックスを持つ(self) -> None:
        assert TABLE_EARNINGS.startswith("av_")

    def test_正常系_economic_indicatorsがavプレフィックスを持つ(self) -> None:
        assert TABLE_ECONOMIC_INDICATORS.startswith("av_")

    def test_正常系_forex_dailyがavプレフィックスを持つ(self) -> None:
        assert TABLE_FOREX_DAILY.startswith("av_")


class TestTableNameValues:
    """テーブル名定数の具体値を検証する。"""

    def test_正常系_daily_pricesの値(self) -> None:
        assert TABLE_DAILY_PRICES == "av_daily_prices"

    def test_正常系_company_overviewの値(self) -> None:
        assert TABLE_COMPANY_OVERVIEW == "av_company_overview"

    def test_正常系_income_statementsの値(self) -> None:
        assert TABLE_INCOME_STATEMENTS == "av_income_statements"

    def test_正常系_balance_sheetsの値(self) -> None:
        assert TABLE_BALANCE_SHEETS == "av_balance_sheets"

    def test_正常系_cash_flowsの値(self) -> None:
        assert TABLE_CASH_FLOWS == "av_cash_flows"

    def test_正常系_earningsの値(self) -> None:
        assert TABLE_EARNINGS == "av_earnings"

    def test_正常系_economic_indicatorsの値(self) -> None:
        assert TABLE_ECONOMIC_INDICATORS == "av_economic_indicators"

    def test_正常系_forex_dailyの値(self) -> None:
        assert TABLE_FOREX_DAILY == "av_forex_daily"


class TestTableNameTypes:
    """テーブル名定数の型が str であることを検証する。"""

    def test_正常系_全テーブル名がstr型(self) -> None:
        table_constants = [
            TABLE_DAILY_PRICES,
            TABLE_COMPANY_OVERVIEW,
            TABLE_INCOME_STATEMENTS,
            TABLE_BALANCE_SHEETS,
            TABLE_CASH_FLOWS,
            TABLE_EARNINGS,
            TABLE_ECONOMIC_INDICATORS,
            TABLE_FOREX_DAILY,
        ]
        for const in table_constants:
            assert isinstance(const, str), f"Expected str, got {type(const)}"


class TestDatabaseSettings:
    """DB設定定数を検証する。"""

    def test_正常系_DB環境変数名(self) -> None:
        assert AV_DB_PATH_ENV == "ALPHA_VANTAGE_DB_PATH"

    def test_正常系_DB環境変数名はstr型(self) -> None:
        assert isinstance(AV_DB_PATH_ENV, str)

    def test_正常系_デフォルトDB名(self) -> None:
        assert DEFAULT_DB_NAME == "alphavantage"

    def test_正常系_デフォルトDB名はstr型(self) -> None:
        assert isinstance(DEFAULT_DB_NAME, str)


class TestAllExports:
    """__all__ の網羅性を検証する。"""

    def test_正常系_allが定義されている(self) -> None:
        from market.alphavantage import storage_constants

        assert hasattr(storage_constants, "__all__")

    def test_正常系_全定数がallに含まれる(self) -> None:
        from market.alphavantage import storage_constants

        expected = {
            "AV_DB_PATH_ENV",
            "DEFAULT_DB_NAME",
            "TABLE_BALANCE_SHEETS",
            "TABLE_CASH_FLOWS",
            "TABLE_COMPANY_OVERVIEW",
            "TABLE_DAILY_PRICES",
            "TABLE_EARNINGS",
            "TABLE_ECONOMIC_INDICATORS",
            "TABLE_FOREX_DAILY",
            "TABLE_INCOME_STATEMENTS",
        }
        assert set(storage_constants.__all__) == expected

    def test_正常系_allの要素数は10(self) -> None:
        from market.alphavantage import storage_constants

        assert len(storage_constants.__all__) == 10

    def test_正常系_allの要素がアルファベット順(self) -> None:
        from market.alphavantage import storage_constants

        assert storage_constants.__all__ == sorted(storage_constants.__all__)
