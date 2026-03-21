"""Tests for the EDINET sync CLI runner (scripts/sync.py).

Tests cover:
- parse_args: all CLI options correctly parsed
- run_sync: each mode delegates to EdinetSyncer
- --db-path sets EdinetConfig.db_path
- main() returns 0 on success, 1 on error
- Module execution via python -m

All external dependencies (EdinetSyncer) are mocked.

See Also
--------
market.edinet.scripts.sync : The module under test.
market.fred.scripts.sync_historical : Reference pattern.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from market.edinet.scripts.sync import main, parse_args, run_sync
from market.edinet.syncer import SyncResult

# プロジェクトルートを動的に取得
PROJECT_ROOT = Path(__file__).resolve().parents[4]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_syncer() -> MagicMock:
    """モック EdinetSyncer を作成。"""
    syncer = MagicMock()
    syncer.run_initial.return_value = [
        SyncResult(
            phase="companies",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
        SyncResult(
            phase="industries",
            success=True,
            companies_processed=0,
            errors=(),
        ),
        SyncResult(
            phase="company_details",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
        SyncResult(
            phase="financials_ratios",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
        SyncResult(
            phase="text_blocks",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
    ]
    syncer.run_daily.return_value = [
        SyncResult(
            phase="companies",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
        SyncResult(
            phase="financials_ratios",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
        SyncResult(
            phase="text_blocks",
            success=True,
            companies_processed=3848,
            errors=(),
        ),
    ]
    syncer.resume.return_value = [
        SyncResult(
            phase="company_details",
            success=True,
            companies_processed=1000,
            errors=(),
        ),
    ]
    syncer.sync_company.return_value = SyncResult(
        phase="single_company",
        success=True,
        companies_processed=1,
        errors=(),
    )
    syncer.get_status.return_value = {
        "current_phase": "companies",
        "completed_codes_count": 0,
        "today_api_calls": 50,
        "remaining_api_calls": 900,
        "errors_count": 0,
        "db_stats": {
            "companies": 3848,
            "financials": 0,
            "ratios": 0,
        },
    }
    return syncer


# =============================================================================
# parse_args Tests
# =============================================================================


class TestParseArgs:
    """コマンドライン引数パースのテスト。"""

    def test_正常系_initialオプション(self) -> None:
        args = parse_args(["--initial"])

        assert args.initial is True
        assert args.daily is False
        assert args.resume is False
        assert args.status is False
        assert args.company is None

    def test_正常系_dailyオプション(self) -> None:
        args = parse_args(["--daily"])

        assert args.daily is True
        assert args.initial is False

    def test_正常系_resumeオプション(self) -> None:
        args = parse_args(["--resume"])

        assert args.resume is True
        assert args.initial is False

    def test_正常系_statusオプション(self) -> None:
        args = parse_args(["--status"])

        assert args.status is True
        assert args.initial is False

    def test_正常系_companyオプション(self) -> None:
        args = parse_args(["--company", "E00001"])

        assert args.company == "E00001"
        assert args.initial is False

    def test_正常系_phaseオプション(self) -> None:
        args = parse_args(["--initial", "--phase", "companies"])

        assert args.phase == "companies"
        assert args.initial is True

    def test_正常系_dbpathオプション(self) -> None:
        args = parse_args(["--initial", "--db-path", "/data/edinet.db"])

        assert args.db_path == "/data/edinet.db"

    def test_正常系_デフォルト値(self) -> None:
        args = parse_args([])

        assert args.initial is False
        assert args.daily is False
        assert args.resume is False
        assert args.status is False
        assert args.company is None
        assert args.phase is None
        assert args.db_path is None


# =============================================================================
# run_sync Tests
# =============================================================================


class TestRunSync:
    """run_sync 関数のテスト。"""

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_initialオプションで初期同期(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--initial"])
        result = run_sync(args)

        assert result == 0
        mock_syncer.run_initial.assert_called_once()

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_dailyオプションでデイリー同期(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--daily"])
        result = run_sync(args)

        assert result == 0
        mock_syncer.run_daily.assert_called_once()

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_resumeオプションでレジューム(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--resume"])
        result = run_sync(args)

        assert result == 0
        mock_syncer.resume.assert_called_once()

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_statusオプションでステータス表示(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--status"])
        result = run_sync(args)

        assert result == 0
        mock_syncer.get_status.assert_called_once()

        captured = capsys.readouterr()
        assert "EDINET DB Sync Status" in captured.out
        assert "companies" in captured.out

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_companyオプションで単一企業同期(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--company", "E00001"])
        result = run_sync(args)

        assert result == 0
        mock_syncer.sync_company.assert_called_once_with("E00001")

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_オプションなしでエラーメッセージ(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")

        args = parse_args([])
        result = run_sync(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "specify" in captured.err.lower() or "error" in captured.err.lower()


# =============================================================================
# --db-path Tests
# =============================================================================


class TestDbPath:
    """--db-path オプションのテスト。"""

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_dbpathがEdinetConfigに設定されること(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--status", "--db-path", "/custom/path/edinet.db"])
        run_sync(args)

        # Verify EdinetConfig was created with db_path
        mock_config_class.assert_called_once_with(
            api_key="test_key",
            db_path=Path("/custom/path/edinet.db"),
        )

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_正常系_dbpath未指定時はNoneが渡されること(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        mock_syncer_class.return_value = mock_syncer

        args = parse_args(["--status"])
        run_sync(args)

        mock_config_class.assert_called_once_with(
            api_key="test_key",
            db_path=None,
        )


# =============================================================================
# main() Exit Code Tests
# =============================================================================


class TestMain:
    """main() 関数の終了コードテスト。"""

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    @patch("market.edinet.scripts.sync.parse_args")
    def test_正常系_正常終了時に0を返すこと(
        self,
        mock_parse_args: MagicMock,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        mock_syncer: MagicMock,
    ) -> None:
        mock_parse_args.return_value = parse_args(["--status"])
        mock_syncer_class.return_value = mock_syncer

        result = main()

        assert result == 0

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    @patch("market.edinet.scripts.sync.parse_args")
    def test_異常系_エラー時に1を返すこと(
        self,
        mock_parse_args: MagicMock,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
    ) -> None:
        mock_parse_args.return_value = parse_args([])

        result = main()

        assert result == 1

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    @patch("market.edinet.scripts.sync.parse_args")
    def test_異常系_同期失敗時に1を返すこと(
        self,
        mock_parse_args: MagicMock,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
    ) -> None:
        mock_parse_args.return_value = parse_args(["--initial"])
        failed_syncer = MagicMock()
        failed_syncer.run_initial.return_value = [
            SyncResult(
                phase="companies",
                success=False,
                companies_processed=0,
                errors=("API error",),
                stopped_reason="rate_limit",
            ),
        ]
        mock_syncer_class.return_value = failed_syncer

        result = main()

        assert result == 1


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """エラーハンドリングのテスト。"""

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_異常系_company同期失敗時に1を返すこと(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        failed_syncer = MagicMock()
        failed_syncer.sync_company.return_value = SyncResult(
            phase="single_company",
            success=False,
            companies_processed=0,
            errors=("404: E99999",),
            stopped_reason=None,
        )
        mock_syncer_class.return_value = failed_syncer

        args = parse_args(["--company", "E99999"])
        result = run_sync(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Failed" in captured.out

    @patch("market.edinet.scripts.sync.EdinetSyncer")
    @patch("market.edinet.scripts.sync.EdinetConfig")
    def test_異常系_initial同期一部失敗時に1を返すこと(
        self,
        mock_config_class: MagicMock,
        mock_syncer_class: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("EDINET_DB_API_KEY", "test_key")
        partial_syncer = MagicMock()
        partial_syncer.run_initial.return_value = [
            SyncResult(
                phase="companies",
                success=True,
                companies_processed=3848,
                errors=(),
            ),
            SyncResult(
                phase="industries",
                success=False,
                companies_processed=0,
                errors=("API error",),
                stopped_reason="rate_limit",
            ),
        ]
        mock_syncer_class.return_value = partial_syncer

        args = parse_args(["--initial"])
        result = run_sync(args)

        assert result == 1


# =============================================================================
# Module Execution Tests
# =============================================================================


class TestModuleExecution:
    """モジュールとしての実行テスト。"""

    def test_正常系_helpオプション(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "market.edinet.scripts.sync", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            check=False,
        )

        assert result.returncode == 0
        assert "usage" in result.stdout.lower()
        assert "--initial" in result.stdout
        assert "--daily" in result.stdout
        assert "--resume" in result.stdout
        assert "--status" in result.stdout
        assert "--company" in result.stdout
        assert "--db-path" in result.stdout
        assert "--phase" in result.stdout
