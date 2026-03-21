"""Unit tests for EdinetStorage SQLite storage layer.

Tests cover:
- ensure_tables(): Creates 6 tables with correct schemas
- upsert_companies(), upsert_financials(), etc.: Correct INSERT OR REPLACE
- get_company(), get_financials(), get_all_company_codes(): Query methods
- get_stats(): Table row counts
- query(): Arbitrary SQL execution
- DDL/dataclass field consistency
- _get_column_info(): PRAGMA table_info based inspection
- _migrate_add_missing_columns(): Forward-only schema migration
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.edinet.constants import (
    TABLE_COMPANIES,
    TABLE_FINANCIALS,
    TABLE_INDUSTRIES,
    TABLE_INDUSTRY_DETAILS,
    TABLE_RATIOS,
    TABLE_TEXT_BLOCKS,
)
from market.edinet.storage import _TABLE_DDL
from market.edinet.types import (
    Company,
    FinancialRecord,
    Industry,
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

    def test_正常系_SQLiteClientが設定のDB_pathで初期化される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """EdinetStorageがEdinetConfigのresolved_db_pathでSQLiteClientを初期化すること."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
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
            patch("market.edinet.storage.SQLiteClient"),
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

    def test_正常系_6テーブルのDDLが実行される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """ensure_tablesが6テーブル分のCREATE TABLE IF NOT EXISTSを実行すること."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            EdinetStorage(config=sample_config)

            # ensure_tables is called in __init__
            execute_calls = mock_client.execute.call_args_list
            # Should have at least 6 calls for 6 tables
            assert len(execute_calls) >= 6

            # Verify all 6 table names appear in the DDL statements
            all_sql = " ".join(str(c) for c in execute_calls)
            expected_tables = [
                TABLE_COMPANIES,
                TABLE_FINANCIALS,
                TABLE_RATIOS,
                TABLE_TEXT_BLOCKS,
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
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            EdinetStorage(config=sample_config)

            execute_calls = mock_client.execute.call_args_list
            # At least the first 6 calls should be CREATE TABLE
            create_calls = [
                c
                for c in execute_calls
                if "CREATE TABLE IF NOT EXISTS" in str(c.args[0])
            ]
            assert len(create_calls) >= 6


# ============================================================================
# Test: upsert methods
# ============================================================================


class TestUpsertCompanies:
    """Tests for upsert_companies method."""

    def test_正常系_execute_manyがINSERT_OR_REPLACEで呼ばれる(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesがINSERT OR REPLACEでexecute_manyを呼ぶこと."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([sample_company])

            mock_client.execute_many.assert_called_once()
            call_args = mock_client.execute_many.call_args
            sql = call_args.args[0]
            assert "INSERT OR REPLACE" in sql
            assert TABLE_COMPANIES in sql

    def test_正常系_パラメータに全フィールドが含まれる(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesが全フィールド分のパラメータを渡すこと."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([sample_company])

            call_args = mock_client.execute_many.call_args
            params_list = call_args.args[1]
            assert len(params_list) == 1
            # Tuple should have same number of elements as Company fields
            expected_field_count = len(dataclasses.fields(Company))
            assert len(params_list[0]) == expected_field_count

    def test_エッジケース_空リストでexecute_manyが呼ばれない(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_companiesに空リストを渡すとexecute_manyが呼ばれないこと."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_companies([])

            mock_client.execute_many.assert_not_called()


class TestUpsertFinancials:
    """Tests for upsert_financials method."""

    def test_正常系_execute_manyがINSERT_OR_REPLACEで呼ばれる(
        self,
        sample_config: EdinetConfig,
        sample_financial_record: FinancialRecord,
    ) -> None:
        """upsert_financialsがINSERT OR REPLACEでexecute_manyを呼ぶこと."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_financials([sample_financial_record])

            call_args = mock_client.execute_many.call_args
            sql = call_args.args[0]
            assert "INSERT OR REPLACE" in sql
            assert TABLE_FINANCIALS in sql


class TestUpsertRatios:
    """Tests for upsert_ratios method."""

    def test_正常系_execute_manyがINSERT_OR_REPLACEで呼ばれる(
        self,
        sample_config: EdinetConfig,
        sample_ratio_record: RatioRecord,
    ) -> None:
        """upsert_ratiosがINSERT OR REPLACEでexecute_manyを呼ぶこと."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_ratios([sample_ratio_record])

            call_args = mock_client.execute_many.call_args
            sql = call_args.args[0]
            assert "INSERT OR REPLACE" in sql
            assert TABLE_RATIOS in sql


class TestUpsertTextBlocks:
    """Tests for upsert_text_blocks method."""

    def test_正常系_execute_manyがINSERT_OR_REPLACEで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_text_blocksがINSERT OR REPLACEでexecute_manyを呼ぶこと."""
        block = TextBlock(
            edinet_code="E00001",
            fiscal_year=2025,
            section="事業の内容",
            text="事業概要テキスト",
        )

        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_text_blocks([block])

            call_args = mock_client.execute_many.call_args
            sql = call_args.args[0]
            assert "INSERT OR REPLACE" in sql
            assert TABLE_TEXT_BLOCKS in sql


class TestUpsertIndustries:
    """Tests for upsert_industries method."""

    def test_正常系_execute_manyがINSERT_OR_REPLACEで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_industriesがINSERT OR REPLACEでexecute_manyを呼ぶこと."""
        industry = Industry(
            slug="information-communication",
            name="情報・通信業",
            company_count=500,
        )

        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_industries([industry])

            call_args = mock_client.execute_many.call_args
            sql = call_args.args[0]
            assert "INSERT OR REPLACE" in sql
            assert TABLE_INDUSTRIES in sql


class TestUpsertIndustryDetails:
    """Tests for upsert_industry_details method."""

    def test_正常系_execute_manyがINSERT_OR_REPLACEで呼ぶ(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_industry_detailsがINSERT OR REPLACEでexecute_manyを呼ぶこと."""
        details_df = pd.DataFrame(
            {
                "slug": ["information-communication"],
                "name": ["情報・通信業"],
                "avg_roe": [10.5],
            }
        )

        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)
            storage.upsert_industry_details(details_df)

            call_args = mock_client.execute_many.call_args
            sql = call_args.args[0]
            assert "INSERT OR REPLACE" in sql
            assert TABLE_INDUSTRY_DETAILS in sql


# ============================================================================
# Test: query methods (mocked)
# ============================================================================


class TestQuery:
    """Tests for query method."""

    def test_異常系_SELECT以外のSQLでValueError(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """INSERT/UPDATE/DROP等のSQLがValueErrorで拒否されること."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_cls.return_value = MagicMock()

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)

            for sql in [
                "INSERT INTO companies VALUES ('E00001')",
                "UPDATE companies SET name='test'",
                "DROP TABLE companies",
                "DELETE FROM companies",
            ]:
                with pytest.raises(ValueError, match="Only SELECT"):
                    storage.query(sql)

    def test_異常系_セミコロン含むSQLでValueError(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """セミコロンを含む複数ステートメントSQLがValueErrorで拒否されること."""
        with patch("market.edinet.storage.SQLiteClient") as mock_cls:
            mock_cls.return_value = MagicMock()

            from market.edinet.storage import EdinetStorage

            storage = EdinetStorage(config=sample_config)

            with pytest.raises(ValueError, match="Multiple statements"):
                storage.query("SELECT 1; DROP TABLE companies")


# ============================================================================
# Test: Integration with real SQLite (tmp_path)
# ============================================================================


class TestEdinetStorageIntegration:
    """Integration tests using real SQLite with tmp_path."""

    def test_正常系_ensure_tablesで実際にテーブルが作成される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """ensure_tablesで実際のSQLiteに6テーブルが作成されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)

        # Verify tables exist by querying
        tables = storage._client.get_tables()
        expected_tables = {
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_TEXT_BLOCKS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        }
        assert set(tables) == expected_tables

    def test_正常系_upsert_companiesで実際にデータが保存される(
        self,
        sample_config: EdinetConfig,
        sample_company: Company,
    ) -> None:
        """upsert_companiesで実際のSQLiteにデータが保存されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        storage.upsert_companies([sample_company])

        result = storage.get_company("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["edinet_code"].iloc[0] == "E00001"
        assert result["name"].iloc[0] == "テスト株式会社"

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
            name="テスト株式会社V1",
            industry="情報・通信業",
        )
        storage.upsert_companies([company_v1])

        company_v2 = Company(
            edinet_code="E00001",
            sec_code="10000",
            name="テスト株式会社V2",
            industry="情報・通信業",
        )
        storage.upsert_companies([company_v2])

        result = storage.get_company("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["name"].iloc[0] == "テスト株式会社V2"

    def test_正常系_upsert_financialsで実際にデータが保存される(
        self,
        sample_config: EdinetConfig,
        sample_financial_record: FinancialRecord,
    ) -> None:
        """upsert_financialsで実際のSQLiteにデータが保存されること."""
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
            name="テスト株式会社2",
            industry="情報・通信業",
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

    def test_正常系_get_companyが存在しないedinet_codeでNoneを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_companyが存在しないedinet_codeに対してNoneを返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        result = storage.get_company("E99999")
        assert result is None

    def test_正常系_get_financialsが存在しないedinet_codeでNoneを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """get_financialsが存在しないedinet_codeに対してNoneを返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        result = storage.get_financials("E99999")
        assert result is None


# ============================================================================
# Test: DDL / dataclass consistency
# ============================================================================


class TestDDLDataclassConsistency:
    """Tests for DDL and dataclass field name consistency."""

    def test_正常系_FinancialRecordフィールドとDDLカラムが完全一致する(self) -> None:
        """dataclasses.fields(FinancialRecord)のフィールド名がDDLカラム名と完全一致すること."""
        from market.edinet.storage import _parse_ddl_columns

        dataclass_fields = {f.name for f in dataclasses.fields(FinancialRecord)}
        ddl_columns = _parse_ddl_columns(_TABLE_DDL[TABLE_FINANCIALS])

        assert dataclass_fields == ddl_columns, (
            f"FinancialRecord fields and DDL columns mismatch.\n"
            f"Only in dataclass: {dataclass_fields - ddl_columns}\n"
            f"Only in DDL: {ddl_columns - dataclass_fields}"
        )

    def test_正常系_RatioRecordフィールドとDDLカラムが完全一致する(self) -> None:
        """dataclasses.fields(RatioRecord)のフィールド名がDDLカラム名と完全一致すること."""
        from market.edinet.storage import _parse_ddl_columns

        dataclass_fields = {f.name for f in dataclasses.fields(RatioRecord)}
        ddl_columns = _parse_ddl_columns(_TABLE_DDL[TABLE_RATIOS])

        assert dataclass_fields == ddl_columns, (
            f"RatioRecord fields and DDL columns mismatch.\n"
            f"Only in dataclass: {dataclass_fields - ddl_columns}\n"
            f"Only in DDL: {ddl_columns - dataclass_fields}"
        )

    def test_正常系_financials_DDLのカラム数がFinancialRecordと一致する(self) -> None:
        """financials DDLのカラム数がFinancialRecordのフィールド数と一致すること."""
        from market.edinet.storage import _parse_ddl_columns

        ddl_count = len(_parse_ddl_columns(_TABLE_DDL[TABLE_FINANCIALS]))
        field_count = len(dataclasses.fields(FinancialRecord))
        assert ddl_count == field_count, (
            f"Column count mismatch: DDL={ddl_count}, dataclass={field_count}"
        )

    def test_正常系_ratios_DDLのカラム数がRatioRecordと一致する(self) -> None:
        """ratios DDLのカラム数がRatioRecordのフィールド数と一致すること."""
        from market.edinet.storage import _parse_ddl_columns

        ddl_count = len(_parse_ddl_columns(_TABLE_DDL[TABLE_RATIOS]))
        field_count = len(dataclasses.fields(RatioRecord))
        assert ddl_count == field_count, (
            f"Column count mismatch: DDL={ddl_count}, dataclass={field_count}"
        )

    def test_正常系_TextBlockフィールドとDDLカラムが完全一致する(self) -> None:
        """dataclasses.fields(TextBlock)のフィールド名がDDLカラム名と完全一致すること."""
        from market.edinet.storage import _parse_ddl_columns

        dataclass_fields = {f.name for f in dataclasses.fields(TextBlock)}
        ddl_columns = _parse_ddl_columns(_TABLE_DDL[TABLE_TEXT_BLOCKS])

        assert dataclass_fields == ddl_columns, (
            f"TextBlock fields and DDL columns mismatch.\n"
            f"Only in dataclass: {dataclass_fields - ddl_columns}\n"
            f"Only in DDL: {ddl_columns - dataclass_fields}"
        )


# ============================================================================
# Test: _parse_ddl_columns
# ============================================================================


class TestParseDdlColumns:
    """Tests for _parse_ddl_columns helper."""

    def test_正常系_シンプルなDDLからカラム名を抽出する(self) -> None:
        """_parse_ddl_columnsが簡単なDDLからカラム名を正しく抽出すること."""
        from market.edinet.storage import _parse_ddl_columns

        ddl = """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER NOT NULL,
                name TEXT,
                value REAL
            )
        """
        result = _parse_ddl_columns(ddl)
        assert result == {"id", "name", "value"}

    def test_正常系_financials_DDLからカラム名を抽出する(self) -> None:
        """_parse_ddl_columnsがfinancialsテーブルDDLから正しいカラム名を抽出すること."""
        from market.edinet.storage import _parse_ddl_columns

        result = _parse_ddl_columns(_TABLE_DDL[TABLE_FINANCIALS])
        assert "edinet_code" in result
        assert "fiscal_year" in result
        assert "revenue" in result


# ============================================================================
# Test: _table_exists
# ============================================================================


class TestTableExists:
    """Tests for _table_exists helper."""

    def test_正常系_存在するテーブルでTrueを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """_table_existsが存在するテーブルに対してTrueを返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        assert storage._table_exists(TABLE_FINANCIALS) is True

    def test_正常系_存在しないテーブルでFalseを返す(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """_table_existsが存在しないテーブルに対してFalseを返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        assert storage._table_exists("nonexistent_table") is False


# ============================================================================
# Test: _get_column_info
# ============================================================================


class TestGetColumnInfo:
    """Tests for _get_column_info helper."""

    def test_正常系_既存テーブルのカラム情報を取得する(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """_get_column_infoが既存テーブルのカラム名と型を返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        columns = storage._get_column_info(TABLE_FINANCIALS)
        assert isinstance(columns, dict)
        assert "edinet_code" in columns
        assert "fiscal_year" in columns
        assert "revenue" in columns

    def test_正常系_カラム型がTEXTやREALを含む(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """_get_column_infoがカラム型を正しく返すこと."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        columns = storage._get_column_info(TABLE_FINANCIALS)
        assert "TEXT" in columns["edinet_code"].upper()
        assert "INTEGER" in columns["fiscal_year"].upper()

    def test_異常系_不正テーブル名でValueError(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """_get_column_infoが不正なテーブル名でValueErrorを発生させること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        with pytest.raises(ValueError, match="Unknown table"):
            storage._get_column_info("unknown_table")


# ============================================================================
# Test: _migrate_add_missing_columns
# ============================================================================


class TestMigrateAddMissingColumns:
    """Tests for _migrate_add_missing_columns method."""

    def test_正常系_スキーマ一致時にマイグレーションが不要(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """_migrate_add_missing_columnsがスキーマ一致時にデータを保持すること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        # Insert test data
        storage.upsert_financials(
            [
                FinancialRecord(
                    edinet_code="E00001",
                    fiscal_year=2025,
                    revenue=1_000_000.0,
                )
            ]
        )
        # Manually call migration - should be a no-op
        storage._migrate_add_missing_columns()
        # Data should still be there
        result = storage.get_financials("E00001")
        assert result is not None
        assert len(result) == 1

    def test_正常系_カラム不足テーブルにカラムが追加される(
        self,
        tmp_path: Path,
    ) -> None:
        """旧スキーマ（カラム不足）のテーブルに不足カラムが追加されること."""
        import sqlite3

        from market.edinet.storage import EdinetStorage
        from market.edinet.types import EdinetConfig as EC

        db_path = tmp_path / "migrate_test.db"
        config = EC(api_key="test_key", db_path=db_path)

        # Create old schema manually (fewer columns)
        conn = sqlite3.connect(db_path)
        conn.execute(
            f"CREATE TABLE {TABLE_FINANCIALS} ("
            "edinet_code TEXT NOT NULL, "
            "fiscal_year INTEGER NOT NULL, "
            "revenue REAL, "
            "PRIMARY KEY (edinet_code, fiscal_year)"
            ")"
        )
        conn.execute(
            f"INSERT INTO {TABLE_FINANCIALS} VALUES ('E00001', 2025, 1000000.0)"
        )
        # Create all other tables so ensure_tables doesn't fail
        for tbl, ddl in _TABLE_DDL.items():
            if tbl != TABLE_FINANCIALS:
                conn.execute(ddl)
        conn.commit()
        conn.close()

        # Initialize storage - should trigger migration
        storage = EdinetStorage(config=config)

        # Verify the table now has additional columns
        columns = storage._get_column_info(TABLE_FINANCIALS)
        expected_fields = {f.name for f in dataclasses.fields(FinancialRecord)}
        assert set(columns.keys()) == expected_fields

        # Verify data was preserved
        result = storage.get_financials("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["edinet_code"].iloc[0] == "E00001"
        assert result["fiscal_year"].iloc[0] == 2025
        assert result["revenue"].iloc[0] == pytest.approx(1_000_000.0)

    def test_正常系_ensure_tablesからmigrate_add_missing_columnsが呼ばれる(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """ensure_tablesの後に_migrate_add_missing_columnsが呼び出されること."""
        from market.edinet.storage import EdinetStorage

        with patch.object(
            EdinetStorage, "_migrate_add_missing_columns"
        ) as mock_migrate:
            EdinetStorage(config=sample_config)
            mock_migrate.assert_called_once()

    def test_正常系_upsert_ratiosで実際にデータが保存される(
        self,
        sample_config: EdinetConfig,
        sample_ratio_record: RatioRecord,
    ) -> None:
        """upsert_ratiosで実際のSQLiteにデータが保存されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        storage.upsert_ratios([sample_ratio_record])

        with storage._client.connection() as conn:
            df = pd.read_sql_query(
                f"SELECT * FROM {TABLE_RATIOS} WHERE edinet_code = ?",
                conn,
                params=["E00001"],
            )
        assert len(df) == 1
        assert df["roe"].iloc[0] == pytest.approx(3.89)

    def test_正常系_upsert_text_blocksで実際にデータが保存される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_text_blocksで実際のSQLiteにデータが保存されること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        block = TextBlock(
            edinet_code="E00001",
            fiscal_year=2025,
            section="事業の内容",
            text="事業概要テキスト",
        )
        storage.upsert_text_blocks([block])

        with storage._client.connection() as conn:
            df = pd.read_sql_query(
                f"SELECT * FROM {TABLE_TEXT_BLOCKS} WHERE edinet_code = ?",
                conn,
                params=["E00001"],
            )
        assert len(df) == 1
        assert df["section"].iloc[0] == "事業の内容"

    def test_正常系_upsert_industry_detailsで実際にJSON保存される(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """upsert_industry_detailsでJSON文字列が正しく保存されること."""
        import json

        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)
        details_df = pd.DataFrame(
            {
                "slug": ["info-comm"],
                "name": ["情報・通信業"],
                "avg_roe": [10.5],
            }
        )
        storage.upsert_industry_details(details_df)

        with storage._client.connection() as conn:
            df = pd.read_sql_query(
                f"SELECT * FROM {TABLE_INDUSTRY_DETAILS} WHERE slug = ?",
                conn,
                params=["info-comm"],
            )
        assert len(df) == 1
        data = json.loads(df["data"].iloc[0])
        assert data["slug"] == "info-comm"
        assert data["name"] == "情報・通信業"


# ============================================================================
# Test: PRIMARY KEY enforcement (upsert behavior)
# ============================================================================


class TestPrimaryKeyEnforcement:
    """Tests for PRIMARY KEY constraint in DDL."""

    def test_正常系_DDLにPRIMARY_KEYが含まれる(self) -> None:
        """全テーブルのDDLにPRIMARY KEY制約が含まれること."""
        for table_name, ddl in _TABLE_DDL.items():
            assert "PRIMARY KEY" in ddl, (
                f"Table {table_name!r} DDL does not contain PRIMARY KEY"
            )

    def test_正常系_financialsの複合PKでupsertが動作する(
        self,
        sample_config: EdinetConfig,
    ) -> None:
        """同一PKのfinancialsデータがupsertで上書きされること."""
        from market.edinet.storage import EdinetStorage

        storage = EdinetStorage(config=sample_config)

        record_v1 = FinancialRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            revenue=500_000.0,
        )
        storage.upsert_financials([record_v1])

        record_v2 = FinancialRecord(
            edinet_code="E00001",
            fiscal_year=2025,
            revenue=999_999.0,
        )
        storage.upsert_financials([record_v2])

        result = storage.get_financials("E00001")
        assert result is not None
        assert len(result) == 1
        assert result["revenue"].iloc[0] == pytest.approx(999_999.0)
