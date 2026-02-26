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
    RANKING_METRICS,
    RATE_LIMIT_FILENAME,
    SAFE_MARGIN,
    SYNC_STATE_FILENAME,
    TABLE_ANALYSES,
    TABLE_COMPANIES,
    TABLE_FINANCIALS,
    TABLE_INDUSTRIES,
    TABLE_INDUSTRY_DETAILS,
    TABLE_RANKINGS,
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
        assert DEFAULT_DB_SUBDIR == "duckdb"

    def test_正常系_DEFAULT_DB_NAMEが正しい値であること(self) -> None:
        assert DEFAULT_DB_NAME == "edinet"


class TestRateLimitConstants:
    """レート制限定数のテスト。"""

    def test_正常系_DAILY_RATE_LIMITが1000であること(self) -> None:
        assert DAILY_RATE_LIMIT == 1000

    def test_正常系_DAILY_RATE_LIMITが正の整数であること(self) -> None:
        assert isinstance(DAILY_RATE_LIMIT, int)
        assert DAILY_RATE_LIMIT > 0

    def test_正常系_SAFE_MARGINが50であること(self) -> None:
        assert SAFE_MARGIN == 50

    def test_正常系_SAFE_MARGINが正の整数であること(self) -> None:
        assert isinstance(SAFE_MARGIN, int)
        assert SAFE_MARGIN > 0

    def test_正常系_SAFE_MARGINがDAILY_RATE_LIMITより小さいこと(self) -> None:
        assert SAFE_MARGIN < DAILY_RATE_LIMIT

    def test_正常系_実効上限が950であること(self) -> None:
        effective_limit = DAILY_RATE_LIMIT - SAFE_MARGIN
        assert effective_limit == 950


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

    def test_正常系_TABLE_ANALYSESが正しい値であること(self) -> None:
        assert TABLE_ANALYSES == "analyses"

    def test_正常系_TABLE_TEXT_BLOCKSが正しい値であること(self) -> None:
        assert TABLE_TEXT_BLOCKS == "text_blocks"

    def test_正常系_TABLE_RANKINGSが正しい値であること(self) -> None:
        assert TABLE_RANKINGS == "rankings"

    def test_正常系_TABLE_INDUSTRIESが正しい値であること(self) -> None:
        assert TABLE_INDUSTRIES == "industries"

    def test_正常系_TABLE_INDUSTRY_DETAILSが正しい値であること(self) -> None:
        assert TABLE_INDUSTRY_DETAILS == "industry_details"

    def test_正常系_全テーブル名が文字列であること(self) -> None:
        table_names = [
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_ANALYSES,
            TABLE_TEXT_BLOCKS,
            TABLE_RANKINGS,
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
            TABLE_ANALYSES,
            TABLE_TEXT_BLOCKS,
            TABLE_RANKINGS,
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
            TABLE_ANALYSES,
            TABLE_TEXT_BLOCKS,
            TABLE_RANKINGS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        ]
        assert len(table_names) == len(set(table_names))

    def test_正常系_テーブル数が8であること(self) -> None:
        table_names = [
            TABLE_COMPANIES,
            TABLE_FINANCIALS,
            TABLE_RATIOS,
            TABLE_ANALYSES,
            TABLE_TEXT_BLOCKS,
            TABLE_RANKINGS,
            TABLE_INDUSTRIES,
            TABLE_INDUSTRY_DETAILS,
        ]
        assert len(table_names) == 8


class TestRankingMetrics:
    """ランキングメトリクス定数のテスト。"""

    def test_正常系_RANKING_METRICSが20指標を含むこと(self) -> None:
        assert len(RANKING_METRICS) == 20

    def test_正常系_RANKING_METRICSがリストであること(self) -> None:
        assert isinstance(RANKING_METRICS, list)

    def test_正常系_全メトリクスが文字列であること(self) -> None:
        for metric in RANKING_METRICS:
            assert isinstance(metric, str), f"{metric} is not a string"

    def test_正常系_全メトリクスが空でないこと(self) -> None:
        for metric in RANKING_METRICS:
            assert len(metric) > 0, "Empty metric found"

    def test_正常系_全メトリクスが一意であること(self) -> None:
        assert len(RANKING_METRICS) == len(set(RANKING_METRICS))

    def test_正常系_roeが含まれること(self) -> None:
        assert "roe" in RANKING_METRICS

    def test_正常系_operating_marginが含まれること(self) -> None:
        assert "operating-margin" in RANKING_METRICS

    def test_正常系_net_marginが含まれること(self) -> None:
        assert "net-margin" in RANKING_METRICS

    def test_正常系_roaが含まれること(self) -> None:
        assert "roa" in RANKING_METRICS

    def test_正常系_equity_ratioが含まれること(self) -> None:
        assert "equity-ratio" in RANKING_METRICS

    def test_正常系_perが含まれること(self) -> None:
        assert "per" in RANKING_METRICS

    def test_正常系_epsが含まれること(self) -> None:
        assert "eps" in RANKING_METRICS

    def test_正常系_dividend_yieldが含まれること(self) -> None:
        assert "dividend-yield" in RANKING_METRICS

    def test_正常系_payout_ratioが含まれること(self) -> None:
        assert "payout-ratio" in RANKING_METRICS

    def test_正常系_revenueが含まれること(self) -> None:
        assert "revenue" in RANKING_METRICS

    def test_正常系_health_scoreが含まれること(self) -> None:
        assert "health-score" in RANKING_METRICS

    def test_正常系_revenue_growthが含まれること(self) -> None:
        assert "revenue-growth" in RANKING_METRICS

    def test_正常系_ni_growthが含まれること(self) -> None:
        assert "ni-growth" in RANKING_METRICS

    def test_正常系_eps_growthが含まれること(self) -> None:
        assert "eps-growth" in RANKING_METRICS

    def test_正常系_revenue_cagr_3yが含まれること(self) -> None:
        assert "revenue-cagr-3y" in RANKING_METRICS

    def test_正常系_oi_cagr_3yが含まれること(self) -> None:
        assert "oi-cagr-3y" in RANKING_METRICS

    def test_正常系_ni_cagr_3yが含まれること(self) -> None:
        assert "ni-cagr-3y" in RANKING_METRICS

    def test_正常系_eps_cagr_3yが含まれること(self) -> None:
        assert "eps-cagr-3y" in RANKING_METRICS

    @pytest.mark.parametrize(
        "metric",
        [
            "roe",
            "operating-margin",
            "net-margin",
            "roa",
            "equity-ratio",
            "per",
            "eps",
            "dividend-yield",
            "payout-ratio",
            "free-cf",
            "revenue",
            "health-score",
            "credit-score",
            "revenue-growth",
            "ni-growth",
            "eps-growth",
            "revenue-cagr-3y",
            "oi-cagr-3y",
            "ni-cagr-3y",
            "eps-cagr-3y",
        ],
    )
    def test_パラメトライズ_全20メトリクスが含まれること(self, metric: str) -> None:
        assert metric in RANKING_METRICS

    def test_正常系_メトリクスがURLパスセグメントとして有効であること(self) -> None:
        """Each metric must be valid as a URL path segment (lowercase, hyphens only)."""
        import re

        pattern = re.compile(r"^[a-z][a-z0-9\-]*$")
        for metric in RANKING_METRICS:
            assert pattern.match(metric), (
                f"Metric '{metric}' is not a valid URL path segment"
            )


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
            "TABLE_ANALYSES",
            "TABLE_TEXT_BLOCKS",
            "TABLE_RANKINGS",
            "TABLE_INDUSTRIES",
            "TABLE_INDUSTRY_DETAILS",
            "RANKING_METRICS",
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
            "RANKING_METRICS",
            "RATE_LIMIT_FILENAME",
            "SAFE_MARGIN",
            "SYNC_STATE_FILENAME",
            "TABLE_ANALYSES",
            "TABLE_COMPANIES",
            "TABLE_FINANCIALS",
            "TABLE_INDUSTRIES",
            "TABLE_INDUSTRY_DETAILS",
            "TABLE_RANKINGS",
            "TABLE_RATIOS",
            "TABLE_TEXT_BLOCKS",
        }
        assert set(mod.__all__) == expected

    def test_正常系_allの要素数が20であること(self) -> None:
        import market.edinet.constants as mod

        assert len(mod.__all__) == 20
