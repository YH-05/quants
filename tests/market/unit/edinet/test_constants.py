"""Tests for market.edinet.constants module.

Verifies that all EDINET DB API constants have correct types, values,
and formats as specified in Issue #3669.
"""

from typing import Final, get_type_hints

import pytest

from market.edinet.constants import (
    DAILY_RATE_LIMIT,
    DEFAULT_BASE_URL,
    DEFAULT_DB_NAME,
    DEFAULT_DB_SUBDIR,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    EDINET_API_KEY_ENV,
    EDINET_DB_PATH_ENV,
    RATE_LIMIT_FILENAME,
    SAFE_MARGIN,
    SYNC_STATE_FILENAME,
    TABLE_COMPANIES,
    TABLE_FINANCIALS,
    TABLE_INDUSTRIES,
    TABLE_INDUSTRY_DETAILS,
    TABLE_RATIOS,
    TABLE_TEXT_BLOCKS,
)


class TestAPIConstants:
    """API設定定数のテスト。"""

    def test_正常系_DEFAULT_BASE_URLがhttpsで始まること(self) -> None:
        assert DEFAULT_BASE_URL.startswith("https://")

    def test_正常系_DEFAULT_BASE_URLが正しい値であること(self) -> None:
        assert DEFAULT_BASE_URL == "https://edinetdb.jp"

    def test_正常系_DEFAULT_BASE_URLが末尾スラッシュを含まないこと(self) -> None:
        assert not DEFAULT_BASE_URL.endswith("/")

    def test_正常系_EDINET_API_KEY_ENVが文字列であること(self) -> None:
        assert isinstance(EDINET_API_KEY_ENV, str)
        assert EDINET_API_KEY_ENV == "EDINET_DB_API_KEY"

    def test_正常系_EDINET_API_KEY_ENVが空でないこと(self) -> None:
        assert len(EDINET_API_KEY_ENV) > 0


class TestDatabasePathConstants:
    """データベースパス定数のテスト。"""

    def test_正常系_EDINET_DB_PATH_ENVが文字列であること(self) -> None:
        assert isinstance(EDINET_DB_PATH_ENV, str)
        assert EDINET_DB_PATH_ENV == "EDINET_DB_PATH"

    def test_正常系_DEFAULT_DB_SUBDIRが正しい値であること(self) -> None:
        assert DEFAULT_DB_SUBDIR == "sqlite"

    def test_正常系_DEFAULT_DB_NAMEが正しい値であること(self) -> None:
        assert DEFAULT_DB_NAME == "edinet"


class TestRateLimitConstants:
    """レート制限定数のテスト。"""

    def test_正常系_DAILY_RATE_LIMITが100であること(self) -> None:
        assert DAILY_RATE_LIMIT == 100

    def test_正常系_DAILY_RATE_LIMITが正の整数であること(self) -> None:
        assert isinstance(DAILY_RATE_LIMIT, int)
        assert DAILY_RATE_LIMIT > 0

    def test_正常系_SAFE_MARGINが5であること(self) -> None:
        assert SAFE_MARGIN == 5

    def test_正常系_SAFE_MARGINが正の整数であること(self) -> None:
        assert isinstance(SAFE_MARGIN, int)
        assert SAFE_MARGIN > 0

    def test_正常系_SAFE_MARGINがDAILY_RATE_LIMITより小さいこと(self) -> None:
        assert SAFE_MARGIN < DAILY_RATE_LIMIT

    def test_正常系_実効上限が95であること(self) -> None:
        effective_limit = DAILY_RATE_LIMIT - SAFE_MARGIN
        assert effective_limit == 95


class TestStateFileConstants:
    """状態ファイル名定数のテスト。"""

    def test_正常系_SYNC_STATE_FILENAMEがJSON拡張子であること(self) -> None:
        assert SYNC_STATE_FILENAME.endswith(".json")

    def test_正常系_SYNC_STATE_FILENAMEが正しい値であること(self) -> None:
        assert SYNC_STATE_FILENAME == "_sync_state.json"

    def test_正常系_SYNC_STATE_FILENAMEがアンダースコアで始まること(self) -> None:
        assert SYNC_STATE_FILENAME.startswith("_")

    def test_正常系_RATE_LIMIT_FILENAMEがJSON拡張子であること(self) -> None:
        assert RATE_LIMIT_FILENAME.endswith(".json")

    def test_正常系_RATE_LIMIT_FILENAMEが正しい値であること(self) -> None:
        assert RATE_LIMIT_FILENAME == "_rate_limit.json"

    def test_正常系_RATE_LIMIT_FILENAMEがアンダースコアで始まること(self) -> None:
        assert RATE_LIMIT_FILENAME.startswith("_")

    def test_正常系_状態ファイル名が重複しないこと(self) -> None:
        assert SYNC_STATE_FILENAME != RATE_LIMIT_FILENAME


class TestHTTPConstants:
    """HTTP設定定数のテスト。"""

    def test_正常系_DEFAULT_TIMEOUTが正の浮動小数点数であること(self) -> None:
        assert isinstance(DEFAULT_TIMEOUT, float)
        assert DEFAULT_TIMEOUT > 0

    def test_正常系_DEFAULT_TIMEOUTが30秒であること(self) -> None:
        assert DEFAULT_TIMEOUT == 30.0

    def test_正常系_DEFAULT_POLITE_DELAYが正の浮動小数点数であること(self) -> None:
        assert isinstance(DEFAULT_POLITE_DELAY, float)
        assert DEFAULT_POLITE_DELAY > 0

    def test_正常系_DEFAULT_POLITE_DELAYが0_1秒であること(self) -> None:
        assert DEFAULT_POLITE_DELAY == 0.1

    def test_正常系_DEFAULT_POLITE_DELAYがDEFAULT_TIMEOUTより小さいこと(self) -> None:
        assert DEFAULT_POLITE_DELAY < DEFAULT_TIMEOUT


class TestTableNameConstants:
    """DuckDBテーブル名定数のテスト。"""

    def test_正常系_TABLE_COMPANIESが正しい値であること(self) -> None:
        assert TABLE_COMPANIES == "companies"

    def test_正常系_TABLE_FINANCIALSが正しい値であること(self) -> None:
        assert TABLE_FINANCIALS == "financials"

    def test_正常系_TABLE_RATIOSが正しい値であること(self) -> None:
        assert TABLE_RATIOS == "ratios"

    def test_正常系_TABLE_TEXT_BLOCKSが正しい値であること(self) -> None:
        assert TABLE_TEXT_BLOCKS == "text_blocks"

    def test_正常系_TABLE_INDUSTRIESが正しい値であること(self) -> None:
        assert TABLE_INDUSTRIES == "industries"

    def test_正常系_TABLE_INDUSTRY_DETAILSが正しい値であること(self) -> None:
        assert TABLE_INDUSTRY_DETAILS == "industry_details"

    def test_正常系_全テーブル名が文字列であること(self) -> None:
        table_names = [
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_TEXT_BLOCKS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        ]
        for name in table_names:
            assert isinstance(name, str), f"{name} is not a string"

    def test_正常系_全テーブル名がsnake_caseであること(self) -> None:
        table_names = [
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_TEXT_BLOCKS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        ]
        for name in table_names:
            assert name == name.lower(), f"{name} is not lowercase"
            assert " " not in name, f"{name} contains spaces"

    def test_正常系_全テーブル名が一意であること(self) -> None:
        table_names = [
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_TEXT_BLOCKS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        ]
        assert len(table_names) == len(set(table_names))

    def test_正常系_テーブル数が6であること(self) -> None:
        table_names = [
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_TEXT_BLOCKS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        ]
        assert len(table_names) == 6


class TestTypingFinalAnnotations:
    """全定数にtyping.Final型注釈が付与されていることのテスト。"""

    def test_正常系_全定数がFinal型注釈を持つこと(self) -> None:
        """Verify all module-level constants use typing.Final annotations."""
        import market.edinet.constants as mod

        hints = get_type_hints(mod, include_extras=True)

        expected_constants = [
            "DEFAULT_BASE_URL",
            "EDINET_API_KEY_ENV",
            "EDINET_DB_PATH_ENV",
            "DEFAULT_DB_SUBDIR",
            "DEFAULT_DB_NAME",
            "DAILY_RATE_LIMIT",
            "SAFE_MARGIN",
            "SYNC_STATE_FILENAME",
            "RATE_LIMIT_FILENAME",
            "DEFAULT_TIMEOUT",
            "DEFAULT_POLITE_DELAY",
            "TABLE_COMPANIES",
            "TABLE_FINANCIALS",
            "TABLE_RATIOS",
            "TABLE_TEXT_BLOCKS",
            "TABLE_INDUSTRIES",
            "TABLE_INDUSTRY_DETAILS",
        ]

        for name in expected_constants:
            assert name in hints, f"{name} is missing type annotation"
            hint = hints[name]
            # typing.Final[X] has __origin__ of Final
            origin = getattr(hint, "__origin__", None)
            assert origin is Final, (
                f"{name} does not have Final type annotation, got {hint}"
            )


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_allがソート済みであること(self) -> None:
        import market.edinet.constants as mod

        assert mod.__all__ == sorted(mod.__all__)

    def test_正常系_allが全定数を含むこと(self) -> None:
        import market.edinet.constants as mod

        expected = {
            "DAILY_RATE_LIMIT",
            "DEFAULT_BASE_URL",
            "DEFAULT_DB_NAME",
            "DEFAULT_DB_SUBDIR",
            "DEFAULT_POLITE_DELAY",
            "DEFAULT_TIMEOUT",
            "EDINET_API_KEY_ENV",
            "EDINET_DB_PATH_ENV",
            "RATE_LIMIT_FILENAME",
            "SAFE_MARGIN",
            "SYNC_STATE_FILENAME",
            "TABLE_COMPANIES",
            "TABLE_FINANCIALS",
            "TABLE_INDUSTRIES",
            "TABLE_INDUSTRY_DETAILS",
            "TABLE_RATIOS",
            "TABLE_TEXT_BLOCKS",
        }
        assert set(mod.__all__) == expected

    def test_正常系_allの要素数が17であること(self) -> None:
        import market.edinet.constants as mod

        assert len(mod.__all__) == 17
