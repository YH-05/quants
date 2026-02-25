"""Unit tests for EdinetStorage DuckDB storage layer.

Tests cover:
- ensure_tables(): Creates 8 tables with correct schemas
- upsert_companies(), upsert_financials(), etc.: Correct key_columns for store_df
- get_company(), get_financials(), get_all_company_codes(): Query methods
- get_stats(): Table row counts
- query(): Arbitrary SQL execution
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from market.edinet.constants import (
    TABLE_ANALYSES,
    TABLE_COMPANIES,
    TABLE_FINANCIALS,
    TABLE_INDUSTRIES,
    TABLE_INDUSTRY_DETAILS,
    TABLE_RANKINGS,
    TABLE_RATIOS,
    TABLE_TEXT_BLOCKS,
)
from market.edinet.types import (
    AnalysisResult,
    Company,
    FinancialRecord,
    Industry,
    RankingEntry,
    RatioRecord,
    TextBlock,
)

if TYPE_CHECKING:
    from pathlib import Path

    from market.edinet.types import EdinetConfig


# ============================================================================
# Test: __init__
# ============================================================================


class TestEdinetStorageInit:
    """Tests for EdinetStorage initialization."""

    def test_正常系_DuckDBClientが設定のDB_pathで初期化される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """EdinetStorageがEdinetConfigのresolved_db_pathでDuckDBClientを初期化すること."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)

            mock_cls.assert_called_once_with(sample_config.resolved_db_path)
            assert storage._client is mock_cls.return_value

    def test_正常系_ensure_tablesが自動呼び出しされる(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """EdinetStorage初期化時にensure_tablesが自動で呼ばれること."""
        with (
            patch("market.edinet.storage.DuckDBClient"),
            patch.object(
                __import__(
                    "market.edinet.storage", fromlist=["EdinetStorage"]
                ).EdinetStorage,
                "ensure_tables",
            ) as mock_ensure,
        ):
            from market.edinet.storage import EdinetStorage

            EdinetStorage(config=sample_config)

            mock_ensure.assert_called_once()


# ============================================================================
# Test: ensure_tables
# ============================================================================


class TestEnsureTables:
    """Tests for ensure_tables method."""

    def test_正常系_8テーブルのDDLが実行される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """ensure_tablesが8テーブル分のCREATE TABLE IF NOT EXISTSを実行すること."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            EdinetStorage(config=sample_config)

            # ensure_tables is called in __init__
            execute_calls = mock_client.execute.call_args_list
            # Should have at least 8 calls for 8 tables
            assert len(execute_calls) >= 8

            # Verify all 8 table names appear in the DDL statements
            all_sql = " ".join(c.args[0] for c in execute_calls)
            expected_tables = [
                TABLE_COMPANIES,
                TABLE_FINANCIALS,
                TABLE_RATIOS,
                TABLE_ANALYSES,
                TABLE_TEXT_BLOCKS,
                TABLE_RANKINGS,
                TABLE_INDUSTRIES,
                TABLE_INDUSTRY_DETAILS,
            ]
            for table_name in expected_tables:
                assert table_name in all_sql, f"DDL for {table_name} not found"

    def test_正常系_CREATE_TABLE_IF_NOT_EXISTS構文を使用する(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """ensure_tablesがCREATE TABLE IF NOT EXISTS構文を使用すること."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            EdinetStorage(config=sample_config)

            execute_calls = mock_client.execute.call_args_list
            for c in execute_calls:
                sql = c.args[0]
                assert "CREATE TABLE IF NOT EXISTS" in sql


# ============================================================================
# Test: upsert methods
# ============================================================================


class TestUpsertCompanies:
    """Tests for upsert_companies method."""

    def test_正常系_store_dfが正しいkey_columnsで呼ばれる(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesがedinet_codeをkey_columnsとしてstore_dfを呼ぶこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([sample_company])

            mock_client.store_df.assert_called_once()
            call_kwargs = mock_client.store_df.call_args
            assert call_kwargs.kwargs.get("key_columns") == ["edinet_code"] or (
                len(call_kwargs.args) >= 2
                and call_kwargs.kwargs.get("key_columns") == ["edinet_code"]
            )

    def test_正常系_DataFrameに全フィールドが含まれる(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesが全フィールドを含むDataFrameをstore_dfに渡すこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([sample_company])

            df_arg = mock_client.store_df.call_args.args[0]
            assert isinstance(df_arg, pd.DataFrame)
            expected_columns = {
                "edinet_code",
                "sec_code",
                "corp_name",
                "industry_code",
                "industry_name",
                "listing_status",
            }
            assert set(df_arg.columns) == expected_columns

    def test_正常系_テーブル名がTABLE_COMPANIESである(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesがTABLE_COMPANIESテーブルに書き込むこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([sample_company])

            call_args = mock_client.store_df.call_args
            assert call_args.args[1] == TABLE_COMPANIES

    def test_エッジケース_空リストでstore_dfが呼ばれない(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_companiesに空リストを渡すとstore_dfが呼ばれないこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([])

            mock_client.store_df.assert_not_called()


class TestUpsertFinancials:
    """Tests for upsert_financials method."""

    def test_正常系_store_dfが複合key_columnsで呼ばれる(
        self,
        sample_config: EdinetConfig,
        sample_financial_record: FinancialRecord,
    ) -> None:
        """upsert_financialsがedinet_code, fiscal_yearをkey_columnsとして呼ぶこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_financials([sample_financial_record])

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == [
                "edinet_code",
                "fiscal_year",
            ]

    def test_正常系_テーブル名がTABLE_FINANCIALSである(
        self,
        sample_config: EdinetConfig,
        sample_financial_record: FinancialRecord,
    ) -> None:
        """upsert_financialsがTABLE_FINANCIALSテーブルに書き込むこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_financials([sample_financial_record])

            call_args = mock_client.store_df.call_args
            assert call_args.args[1] == TABLE_FINANCIALS


class TestUpsertRatios:
    """Tests for upsert_ratios method."""

    def test_正常系_store_dfが複合key_columnsで呼ばれる(
        self,
        sample_config: EdinetConfig,
        sample_ratio_record: RatioRecord,
    ) -> None:
        """upsert_ratiosがedinet_code, fiscal_yearをkey_columnsとして呼ぶこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_ratios([sample_ratio_record])

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == [
                "edinet_code",
                "fiscal_year",
            ]


class TestUpsertAnalyses:
    """Tests for upsert_analyses method."""

    def test_正常系_store_dfがedinet_codeをkey_columnsで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_analysesがedinet_codeをkey_columnsとしてstore_dfを呼ぶこと."""
        analysis = AnalysisResult(
            edinet_code="E00001",
            health_score=75.0,
            benchmark_comparison="above_average",
            commentary="Good financial health.",
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_analyses([analysis])

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == ["edinet_code"]
            assert mock_client.store_df.call_args.args[1] == TABLE_ANALYSES


class TestUpsertTextBlocks:
    """Tests for upsert_text_blocks method."""

    def test_正常系_store_dfが複合key_columnsで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_text_blocksがedinet_code, fiscal_yearをkey_columnsとして呼ぶこと."""
        block = TextBlock(
            edinet_code="E00001",
            fiscal_year="2025",
            business_overview="事業概要",
            risk_factors="リスク",
            management_analysis="分析",
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_text_blocks([block])

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == [
                "edinet_code",
                "fiscal_year",
            ]
            assert mock_client.store_df.call_args.args[1] == TABLE_TEXT_BLOCKS


class TestUpsertRankings:
    """Tests for upsert_rankings method."""

    def test_正常系_store_dfが複合key_columnsで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_rankingsがmetric, rankをkey_columnsとしてstore_dfを呼ぶこと."""
        entry = RankingEntry(
            metric="roe",
            rank=1,
            edinet_code="E00001",
            corp_name="テスト株式会社",
            value=25.5,
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_rankings([entry])

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == ["metric", "rank"]
            assert mock_client.store_df.call_args.args[1] == TABLE_RANKINGS


class TestUpsertIndustries:
    """Tests for upsert_industries method."""

    def test_正常系_store_dfがslugをkey_columnsで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_industriesがslugをkey_columnsとしてstore_dfを呼ぶこと."""
        industry = Industry(
            slug="information-communication",
            name="情報・通信業",
            company_count=500,
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_industries([industry])

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == ["slug"]
            assert mock_client.store_df.call_args.args[1] == TABLE_INDUSTRIES


class TestUpsertIndustryDetails:
    """Tests for upsert_industry_details method."""

    def test_正常系_store_dfがslugをkey_columnsで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_industry_detailsがslugをkey_columnsとしてstore_dfを呼ぶこと."""
        details_df = pd.DataFrame(
            {
                "slug": ["information-communication"],
                "name": ["情報・通信業"],
                "avg_roe": [10.5],
            }
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_industry_details(details_df)

            call_kwargs = mock_client.store_df.call_args.kwargs
            assert call_kwargs.get("key_columns") == ["slug"]
            assert mock_client.store_df.call_args.args[1] == TABLE_INDUSTRY_DETAILS


# ============================================================================
# Test: query methods
# ============================================================================


class TestGetCompany:
    """Tests for get_company method."""

    def test_正常系_edinet_codeで企業データを取得する(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_companyがedinet_codeに一致するDataFrameを返すこと."""
        expected_df = pd.DataFrame(
            {
                "edinet_code": ["E00001"],
                "sec_code": ["10000"],
                "corp_name": ["テスト株式会社"],
                "industry_code": ["3050"],
                "industry_name": ["情報・通信業"],
                "listing_status": ["上場"],
            }
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = expected_df
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.get_company("E00001")

            assert result is not None
            assert len(result) == 1
            # Verify the query includes the edinet_code
            query_sql = mock_client.query_df.call_args.args[0]
            assert "E00001" in query_sql

    def test_正常系_存在しないedinet_codeでNoneを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_companyが存在しないedinet_codeに対してNoneを返すこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = pd.DataFrame()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.get_company("E99999")

            assert result is None


class TestGetFinancials:
    """Tests for get_financials method."""

    def test_正常系_edinet_codeで財務データを取得する(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_financialsがedinet_codeに一致するDataFrameを返すこと."""
        expected_df = pd.DataFrame(
            {
                "edinet_code": ["E00001", "E00001"],
                "fiscal_year": ["2024", "2025"],
                "revenue": [900_000_000, 1_000_000_000],
            }
        )

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = expected_df
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.get_financials("E00001")

            assert result is not None
            assert len(result) == 2

    def test_正常系_存在しないedinet_codeでNoneを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_financialsが存在しないedinet_codeに対してNoneを返すこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = pd.DataFrame()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.get_financials("E99999")

            assert result is None


class TestGetAllCompanyCodes:
    """Tests for get_all_company_codes method."""

    def test_正常系_全edinet_codeのリストを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_all_company_codesが全edinet_codeのリストを返すこと."""
        expected_df = pd.DataFrame({"edinet_code": ["E00001", "E00002", "E00003"]})

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = expected_df
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.get_all_company_codes()

            assert result == ["E00001", "E00002", "E00003"]

    def test_正常系_テーブルが空で空リストを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_all_company_codesがテーブル空で空リストを返すこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = pd.DataFrame(
                {"edinet_code": pd.Series([], dtype="str")}
            )
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.get_all_company_codes()

            assert result == []


# ============================================================================
# Test: get_stats
# ============================================================================


class TestGetStats:
    """Tests for get_stats method."""

    def test_正常系_全テーブルの行数を返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_statsが全8テーブルの行数を辞書で返すこと."""
        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            # Return a count for each query_df call
            mock_client.query_df.return_value = pd.DataFrame({"count": [42]})
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            stats = storage.get_stats()

            assert isinstance(stats, dict)
            expected_keys = {
                TABLE_COMPANIES,
                TABLE_FINANCIALS,
                TABLE_RATIOS,
                TABLE_ANALYSES,
                TABLE_TEXT_BLOCKS,
                TABLE_RANKINGS,
                TABLE_INDUSTRIES,
                TABLE_INDUSTRY_DETAILS,
            }
            assert set(stats.keys()) == expected_keys


# ============================================================================
# Test: query
# ============================================================================


class TestQuery:
    """Tests for query method."""

    def test_正常系_任意SQLを実行してDataFrameを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """queryが任意SQLをquery_dfに委譲してDataFrameを返すこと."""
        expected_df = pd.DataFrame({"count": [100]})

        with patch("market.edinet.storage.DuckDBClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.query_df.return_value = expected_df
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            result = storage.query("SELECT COUNT(*) as count FROM companies")

            assert len(result) == 1
            assert result["count"].iloc[0] == 100


# ============================================================================
# Test: Integration with real DuckDB (tmp_path)
# ============================================================================


class TestEdinetStorageIntegration:
    """Integration tests using real DuckDB with tmp_path."""

    def test_正常系_ensure_tablesで実際にテーブルが作成される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """ensure_tablesで実際のDuckDBに8テーブルが作成されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)

        # Verify tables exist by querying
        tables = storage._client.get_table_names()
        expected_tables = {
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_ANALYSES,
            TABLE_TEXT_BLOCKS,
            TABLE_RANKINGS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        }
        assert set(tables) == expected_tables

    def test_正常系_upsert_companiesで実際にデータが保存される(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesで実際のDuckDBにデータが保存されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        storage.upsert_companies([sample_company])

        result = storage.get_company("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["edinet_code"].iloc[0] == "E00001"
        assert result["corp_name"].iloc[0] == "テスト株式会社"

    def test_正常系_upsert_companiesが同一キーでupsertする(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """同じedinet_codeのデータをupsertすると上書きされること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)

        company_v1 = Company(
            edinet_code="E00001",
            sec_code="10000",
            corp_name="テスト株式会社V1",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        )
        storage.upsert_companies([company_v1])

        company_v2 = Company(
            edinet_code="E00001",
            sec_code="10000",
            corp_name="テスト株式会社V2",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        )
        storage.upsert_companies([company_v2])

        result = storage.get_company("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["corp_name"].iloc[0] == "テスト株式会社V2"

    def test_正常系_upsert_financialsで実際にデータが保存される(
        self,
        sample_config: EdinetConfig,
        sample_financial_record: FinancialRecord,
    ) -> None:
        """upsert_financialsで実際のDuckDBにデータが保存されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        storage.upsert_financials([sample_financial_record])

        result = storage.get_financials("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["revenue"].iloc[0] == 1_000_000_000

    def test_正常系_get_all_company_codesが実際のデータを返す(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """get_all_company_codesが実際に保存された全コードを返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)

        company2 = Company(
            edinet_code="E00002",
            sec_code="20000",
            corp_name="テスト株式会社2",
            industry_code="3050",
            industry_name="情報・通信業",
            listing_status="上場",
        )
        storage.upsert_companies([sample_company, company2])

        codes = storage.get_all_company_codes()
        assert sorted(codes) == ["E00001", "E00002"]

    def test_正常系_get_statsが実際のテーブル行数を返す(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
        sample_financial_record: FinancialRecord,
    ) -> None:
        """get_statsが実際のテーブル行数を正しく返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        storage.upsert_companies([sample_company])
        storage.upsert_financials([sample_financial_record])

        stats = storage.get_stats()
        assert stats[TABLE_COMPANIES] == 1
        assert stats[TABLE_FINANCIALS] == 1
        assert stats[TABLE_RATIOS] == 0

    def test_正常系_queryで任意SQLを実行できる(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """queryメソッドで任意SQLを実行できること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        storage.upsert_companies([sample_company])

        result = storage.query(
            f"SELECT COUNT(*) as cnt FROM {TABLE_COMPANIES}"  # nosec B608
        )
        assert result["cnt"].iloc[0] == 1
