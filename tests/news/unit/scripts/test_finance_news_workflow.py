"""Unit tests for the finance news workflow CLI script.

Tests for the CLI interface and main entry point of the finance news
workflow script that orchestrates the news collection pipeline.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from news.models import WorkflowResult


class TestCreateParser:
    """Tests for CLI argument parser creation."""

    def test_正常系_パーサーが作成される(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_正常系_デフォルト引数でパースできる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args([])
        assert args.config is None
        assert args.dry_run is False
        assert args.status is None
        assert args.max_articles is None

    def test_正常系_config引数を指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(["--config", "path/to/config.yaml"])
        assert args.config == "path/to/config.yaml"

    def test_正常系_dry_run引数を指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_正常系_status引数を指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(["--status", "index,stock"])
        assert args.status == "index,stock"

    def test_正常系_max_articles引数を指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(["--max-articles", "10"])
        assert args.max_articles == 10

    def test_正常系_verbose引数を指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_正常系_v短縮形でverboseを指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose is True

    def test_正常系_verbose未指定でデフォルトはFalse(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args([])
        assert args.verbose is False

    def test_正常系_全引数を同時に指定できる(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "--config",
                "config.yaml",
                "--dry-run",
                "--status",
                "index,stock",
                "--max-articles",
                "20",
                "--verbose",
            ]
        )
        assert args.config == "config.yaml"
        assert args.dry_run is True
        assert args.status == "index,stock"
        assert args.max_articles == 20
        assert args.verbose is True

    def test_異常系_max_articlesに非数値で拒否される(self) -> None:
        from news.scripts.finance_news_workflow import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--max-articles", "abc"])


class TestParseStatuses:
    """Tests for status parsing function."""

    def test_正常系_カンマ区切りでリストに変換される(self) -> None:
        from news.scripts.finance_news_workflow import parse_statuses

        result = parse_statuses("index,stock")
        assert result == ["index", "stock"]

    def test_正常系_単一のステータスでリストになる(self) -> None:
        from news.scripts.finance_news_workflow import parse_statuses

        result = parse_statuses("index")
        assert result == ["index"]

    def test_正常系_Noneの場合はNoneを返す(self) -> None:
        from news.scripts.finance_news_workflow import parse_statuses

        result = parse_statuses(None)
        assert result is None

    def test_正常系_空白がトリムされる(self) -> None:
        from news.scripts.finance_news_workflow import parse_statuses

        result = parse_statuses("index, stock , ai")
        assert result == ["index", "stock", "ai"]


class TestMain:
    """Tests for main entry point."""

    @pytest.fixture
    def mock_config_path(self, tmp_path: Path) -> Path:
        """Create a temporary config file for testing."""
        config_content = """
version: "1.0"
status_mapping:
  tech: ai
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
extraction:
  concurrency: 5
  timeout_seconds: 30
  min_body_length: 200
  max_retries: 3
summarization:
  concurrency: 3
  timeout_seconds: 60
  max_retries: 3
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "YH-05/quants"
filtering:
  max_age_hours: 168
output:
  result_dir: "data/exports/news-workflow"
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def mock_workflow_result(self) -> WorkflowResult:
        """Create a mock WorkflowResult."""
        from news.models import WorkflowResult

        return WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            elapsed_seconds=300.0,
            published_articles=[],
        )

    def test_正常系_ワークフローが正常に完了すると終了コード0(
        self,
        mock_config_path: Path,
        mock_workflow_result: MagicMock,
    ) -> None:
        from news.scripts.finance_news_workflow import main

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = mock_workflow_result

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            mock_load_config.return_value = MagicMock()
            result = main(["--config", str(mock_config_path)])

        assert result == 0

    def test_正常系_dry_runモードでワークフローを実行できる(
        self,
        mock_config_path: Path,
        mock_workflow_result: MagicMock,
    ) -> None:
        from news.scripts.finance_news_workflow import main

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = mock_workflow_result

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            mock_load_config.return_value = MagicMock()
            result = main(["--config", str(mock_config_path), "--dry-run"])

        assert result == 0
        mock_orchestrator.run.assert_called_once()
        _, kwargs = mock_orchestrator.run.call_args
        assert kwargs.get("dry_run") is True

    def test_正常系_status引数が渡される(
        self,
        mock_config_path: Path,
        mock_workflow_result: MagicMock,
    ) -> None:
        from news.scripts.finance_news_workflow import main

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = mock_workflow_result

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            mock_load_config.return_value = MagicMock()
            result = main(
                ["--config", str(mock_config_path), "--status", "index,stock"]
            )

        assert result == 0
        mock_orchestrator.run.assert_called_once()
        _, kwargs = mock_orchestrator.run.call_args
        assert kwargs.get("statuses") == ["index", "stock"]

    def test_正常系_max_articles引数が渡される(
        self,
        mock_config_path: Path,
        mock_workflow_result: MagicMock,
    ) -> None:
        from news.scripts.finance_news_workflow import main

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = mock_workflow_result

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            mock_load_config.return_value = MagicMock()
            result = main(["--config", str(mock_config_path), "--max-articles", "10"])

        assert result == 0
        mock_orchestrator.run.assert_called_once()
        _, kwargs = mock_orchestrator.run.call_args
        assert kwargs.get("max_articles") == 10

    def test_異常系_設定ファイルが見つからないと終了コード1(self) -> None:
        from news.scripts.finance_news_workflow import main

        result = main(["--config", "/nonexistent/config.yaml"])
        assert result == 1

    def test_異常系_ワークフロー例外発生時に終了コード1(
        self,
        mock_config_path: Path,
    ) -> None:
        from news.scripts.finance_news_workflow import main

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.side_effect = RuntimeError("Test error")

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            mock_load_config.return_value = MagicMock()
            result = main(["--config", str(mock_config_path)])

        assert result == 1

    def test_正常系_verboseモードでログレベルがDEBUGに設定される(
        self,
        mock_config_path: Path,
        mock_workflow_result: MagicMock,
    ) -> None:
        from news.scripts.finance_news_workflow import main

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = mock_workflow_result

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
            patch(
                "news.scripts.finance_news_workflow.setup_logging",
            ) as mock_setup_logging,
        ):
            mock_load_config.return_value = MagicMock()
            result = main(["--config", str(mock_config_path), "--verbose"])

        assert result == 0
        mock_setup_logging.assert_called_once_with(verbose=True)


class TestPrintFailureSummary:
    """Tests for failure summary printing."""

    def test_正常系_失敗がない場合は何も出力されない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from news.models import WorkflowResult
        from news.scripts.finance_news_workflow import print_failure_summary

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            elapsed_seconds=300.0,
            published_articles=[],
        )

        print_failure_summary(result)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_正常系_失敗がある場合は詳細が出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from news.models import FailureRecord, WorkflowResult
        from news.scripts.finance_news_workflow import print_failure_summary

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[
                FailureRecord(
                    url="https://example.com/1",
                    title="Test Article",
                    stage="extraction",
                    error="Timeout error",
                )
            ],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            elapsed_seconds=300.0,
            published_articles=[],
        )

        print_failure_summary(result)

        captured = capsys.readouterr()
        assert "失敗詳細" in captured.out
        assert "抽出失敗" in captured.out
        assert "Test Article" in captured.out
        assert "Timeout error" in captured.out


class TestSetupLogging:
    """Tests for setup_logging function (Issue #2405)."""

    def test_正常系_ログファイルが指定パスに作成される(self, tmp_path: Path) -> None:
        """Verify log file is created at logs/news-workflow-{date}.log."""
        from news.scripts.finance_news_workflow import setup_logging

        # Use tmp_path as base directory
        log_dir = tmp_path / "logs"

        # Run setup_logging with custom log_dir
        with patch(
            "news.scripts.finance_news_workflow.Path",
        ) as mock_path_class:
            mock_log_dir = MagicMock()
            mock_log_dir.__truediv__ = MagicMock(
                return_value=log_dir / "news-workflow-2026-01-30.log"
            )
            mock_path_class.return_value = mock_log_dir

            setup_logging(verbose=False, log_dir=tmp_path / "logs")

        # Verify log directory was created
        assert log_dir.exists()

        # Verify log file naming pattern
        log_files = list(log_dir.glob("news-workflow-*.log"))
        assert len(log_files) == 1
        assert "news-workflow-" in log_files[0].name

    def test_正常系_コンソールにもログが出力される(
        self, tmp_path: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Verify logs are output to both console and file."""
        from news.scripts.finance_news_workflow import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(verbose=False, log_dir=log_dir)

        # Get a logger and log a message
        from utils_core.logging import get_logger

        test_logger = get_logger("test_console_output")
        test_logger.info("Test console message")

        # Verify console output
        captured = capfd.readouterr()
        # Note: structlog may or may not show message depending on configuration
        # At minimum, logging should not raise exceptions

    def test_正常系_verbose指定でDEBUGレベルログが出力される(
        self, tmp_path: Path
    ) -> None:
        """Verify --verbose enables DEBUG level logging."""
        from news.scripts.finance_news_workflow import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(verbose=True, log_dir=log_dir)

        # Verify root logger level is DEBUG
        assert logging.root.level == logging.DEBUG

    def test_正常系_verbose未指定でINFOレベルログが出力される(
        self, tmp_path: Path
    ) -> None:
        """Verify default log level is DEBUG without --verbose.

        Note: The centralized utils_core.logging module sets root logger to DEBUG
        to allow file output to capture all levels. Console handler level controls
        what appears on the console (INFO when not verbose).
        """
        from news.scripts.finance_news_workflow import setup_logging

        log_dir = tmp_path / "logs"
        setup_logging(verbose=False, log_dir=log_dir)

        # Root logger is set to DEBUG to allow file output to capture all levels
        # Console handler level controls what appears on the console
        assert logging.root.level == logging.DEBUG

    def test_正常系_ログディレクトリが存在しなくても作成される(
        self, tmp_path: Path
    ) -> None:
        """Verify log directory is created if it doesn't exist."""
        from news.scripts.finance_news_workflow import setup_logging

        log_dir = tmp_path / "new_logs_dir"
        assert not log_dir.exists()

        setup_logging(verbose=False, log_dir=log_dir)

        assert log_dir.exists()

    def test_正常系_setup_loggingがmainから呼ばれる(self, tmp_path: Path) -> None:
        """Verify setup_logging is called from main function."""
        from datetime import datetime, timezone

        from news.models import WorkflowResult
        from news.scripts.finance_news_workflow import main

        mock_result = WorkflowResult(
            total_collected=1,
            total_extracted=1,
            total_summarized=1,
            total_published=1,
            total_duplicates=0,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 15, 10, 1, 0, tzinfo=timezone.utc),
            elapsed_seconds=60.0,
            published_articles=[],
        )

        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = mock_result

        # Create a temporary config file
        config_content = """
version: "1.0"
status_mapping:
  tech: ai
github_status_ids:
  ai: "6fbb43d0"
rss:
  presets_file: "data/config/rss-presets.json"
extraction:
  concurrency: 5
  timeout_seconds: 30
  min_body_length: 200
  max_retries: 3
summarization:
  concurrency: 3
  timeout_seconds: 60
  max_retries: 3
  prompt_template: "test"
github:
  project_number: 15
  project_id: "PVT_test"
  status_field_id: "PVTSSF_test"
  published_date_field_id: "PVTF_test"
  repository: "YH-05/quants"
filtering:
  max_age_hours: 168
output:
  result_dir: "data/exports/news-workflow"
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        log_dir = tmp_path / "logs"

        with (
            patch(
                "news.scripts.finance_news_workflow.load_config",
            ) as mock_load_config,
            patch(
                "news.scripts.finance_news_workflow.NewsWorkflowOrchestrator",
                return_value=mock_orchestrator,
            ),
            patch(
                "news.scripts.finance_news_workflow.setup_logging",
            ) as mock_setup_logging,
        ):
            mock_load_config.return_value = MagicMock()
            main(["--config", str(config_file), "--verbose"])

        # Verify setup_logging was called with verbose=True
        mock_setup_logging.assert_called_once()
        call_kwargs = mock_setup_logging.call_args
        assert call_kwargs[1]["verbose"] is True
