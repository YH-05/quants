"""Tests for market.etfcom.storage_constants module."""

from market.etfcom.storage_constants import (
    DEFAULT_DB_NAME,
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


class TestTableNamePrefix:
    """全テーブル名定数が etfcom_ プレフィックスを持つことを検証する。"""

    def test_正常系_tickersがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_TICKERS.startswith("etfcom_")

    def test_正常系_fund_flowsがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_FUND_FLOWS.startswith("etfcom_")

    def test_正常系_holdingsがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_HOLDINGS.startswith("etfcom_")

    def test_正常系_portfolioがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_PORTFOLIO.startswith("etfcom_")

    def test_正常系_allocationsがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_ALLOCATIONS.startswith("etfcom_")

    def test_正常系_tradabilityがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_TRADABILITY.startswith("etfcom_")

    def test_正常系_structureがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_STRUCTURE.startswith("etfcom_")

    def test_正常系_performanceがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_PERFORMANCE.startswith("etfcom_")

    def test_正常系_quotesがetfcomプレフィックスを持つ(self) -> None:
        assert TABLE_QUOTES.startswith("etfcom_")


class TestTableNameValues:
    """テーブル名定数の具体値を検証する。"""

    def test_正常系_tickersの値(self) -> None:
        assert TABLE_TICKERS == "etfcom_tickers"

    def test_正常系_fund_flowsの値(self) -> None:
        assert TABLE_FUND_FLOWS == "etfcom_fund_flows"

    def test_正常系_holdingsの値(self) -> None:
        assert TABLE_HOLDINGS == "etfcom_holdings"

    def test_正常系_portfolioの値(self) -> None:
        assert TABLE_PORTFOLIO == "etfcom_portfolio"

    def test_正常系_allocationsの値(self) -> None:
        assert TABLE_ALLOCATIONS == "etfcom_allocations"

    def test_正常系_tradabilityの値(self) -> None:
        assert TABLE_TRADABILITY == "etfcom_tradability"

    def test_正常系_structureの値(self) -> None:
        assert TABLE_STRUCTURE == "etfcom_structure"

    def test_正常系_performanceの値(self) -> None:
        assert TABLE_PERFORMANCE == "etfcom_performance"

    def test_正常系_quotesの値(self) -> None:
        assert TABLE_QUOTES == "etfcom_quotes"


class TestTableNameTypes:
    """テーブル名定数の型が str であることを検証する。"""

    def test_正常系_全テーブル名がstr型(self) -> None:
        table_constants = [
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
        for const in table_constants:
            assert isinstance(const, str), f"Expected str, got {type(const)}"


class TestDatabaseSettings:
    """DB設定定数を検証する。"""

    def test_正常系_DB環境変数名(self) -> None:
        assert ETFCOM_DB_PATH_ENV == "ETFCOM_DB_PATH"

    def test_正常系_DB環境変数名はstr型(self) -> None:
        assert isinstance(ETFCOM_DB_PATH_ENV, str)

    def test_正常系_デフォルトDB名(self) -> None:
        assert DEFAULT_DB_NAME == "etfcom"

    def test_正常系_デフォルトDB名はstr型(self) -> None:
        assert isinstance(DEFAULT_DB_NAME, str)


class TestAllExports:
    """__all__ の網羅性を検証する。"""

    def test_正常系_allが定義されている(self) -> None:
        from market.etfcom import storage_constants

        assert hasattr(storage_constants, "__all__")

    def test_正常系_全定数がallに含まれる(self) -> None:
        from market.etfcom import storage_constants

        expected = {
            "DEFAULT_DB_NAME",
            "ETFCOM_DB_PATH_ENV",
            "TABLE_ALLOCATIONS",
            "TABLE_FUND_FLOWS",
            "TABLE_HOLDINGS",
            "TABLE_NOT_PERSISTED",
            "TABLE_PERFORMANCE",
            "TABLE_PORTFOLIO",
            "TABLE_QUOTES",
            "TABLE_STRUCTURE",
            "TABLE_TICKERS",
            "TABLE_TRADABILITY",
        }
        assert set(storage_constants.__all__) == expected

    def test_正常系_allの要素数は12(self) -> None:
        from market.etfcom import storage_constants

        assert len(storage_constants.__all__) == 12

    def test_正常系_allの要素がアルファベット順(self) -> None:
        from market.etfcom import storage_constants

        assert storage_constants.__all__ == sorted(storage_constants.__all__)


class TestTableNameUniqueness:
    """テーブル名定数の値が全て一意であることを検証する。"""

    def test_正常系_全テーブル名が一意(self) -> None:
        table_names = [
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
        assert len(table_names) == len(set(table_names))

    def test_正常系_テーブル名が9個(self) -> None:
        table_names = [
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
        assert len(table_names) == 9
