"""Unit tests for news.progress module.

Tests for ProgressCallback Protocol, ConsoleProgressCallback, and SilentCallback.

Covers:
- ConsoleProgressCallback output verification for all methods
- SilentCallback no-op behavior verification
- SilentCallback Protocol conformance
- Boundary values (total=0, current > total)

Issue: #3447 - progress.py の単体テスト・統合テスト作成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from news.models import (
    CategoryPublishResult,
    DomainExtractionRate,
    FeedError,
    PublicationStatus,
    StageMetrics,
)
from news.progress import ConsoleProgressCallback, ProgressCallback, SilentCallback

# --- Helpers ---


def _make_workflow_result(**overrides: Any) -> Any:
    """Create a minimal WorkflowResult-like object for testing on_workflow_complete.

    Uses a dataclass instead of the real WorkflowResult to avoid heavy model
    construction while still exercising the on_workflow_complete output logic.
    """

    @dataclass
    class FakeWorkflowResult:
        total_collected: int = 10
        total_extracted: int = 8
        total_summarized: int = 7
        total_published: int = 5
        total_duplicates: int = 1
        total_early_duplicates: int = 0
        elapsed_seconds: float = 30.5
        feed_errors: list[Any] = field(default_factory=list)
        stage_metrics: list[Any] = field(default_factory=list)
        domain_extraction_rates: list[Any] = field(default_factory=list)
        category_results: list[Any] = field(default_factory=list)

    return FakeWorkflowResult(**overrides)


# --- ConsoleProgressCallback Tests ---


class TestConsoleProgressCallback:
    """Tests for ConsoleProgressCallback output verification."""

    def test_正常系_on_stage_startでステージヘッダーが出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_stage_start prints stage header with visual separator.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_stage_start("1/6", "RSSフィードから記事を収集") is called
        Then:
            - Output contains separator lines and stage info
        """
        cb = ConsoleProgressCallback()
        cb.on_stage_start("1/6", "RSSフィードから記事を収集")

        captured = capsys.readouterr().out
        assert "=" * 60 in captured
        assert "[1/6]" in captured
        assert "RSSフィードから記事を収集" in captured

    def test_正常系_on_progressで進捗行が出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_progress prints progress line with count indicator.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_progress(3, 10, "記事タイトル") is called
        Then:
            - Output contains "[3/10]" and message
        """
        cb = ConsoleProgressCallback()
        cb.on_progress(3, 10, "記事タイトル")

        captured = capsys.readouterr().out
        assert "[3/10]" in captured
        assert "記事タイトル" in captured
        assert "ERROR" not in captured

    def test_正常系_on_progressでエラー時にERRORプレフィックスが出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_progress prints ERROR prefix when is_error=True.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_progress(2, 5, "失敗メッセージ", is_error=True) is called
        Then:
            - Output contains "ERROR" prefix
        """
        cb = ConsoleProgressCallback()
        cb.on_progress(2, 5, "失敗メッセージ", is_error=True)

        captured = capsys.readouterr().out
        assert "ERROR" in captured
        assert "[2/5]" in captured
        assert "失敗メッセージ" in captured

    def test_正常系_on_stage_completeで完了メッセージが出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_stage_complete prints completion with success rate.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_stage_complete("抽出", 8, 10) is called
        Then:
            - Output contains stage name, counts, and percentage
        """
        cb = ConsoleProgressCallback()
        cb.on_stage_complete("抽出", 8, 10)

        captured = capsys.readouterr().out
        assert "抽出" in captured
        assert "8/10" in captured
        assert "80%" in captured
        assert "完了" in captured

    def test_正常系_on_stage_completeでextra付きの出力(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_stage_complete appends extra string when provided.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_stage_complete("要約", 5, 5, extra="(10.5秒)") is called
        Then:
            - Output contains the extra string
        """
        cb = ConsoleProgressCallback()
        cb.on_stage_complete("要約", 5, 5, extra="(10.5秒)")

        captured = capsys.readouterr().out
        assert "100%" in captured
        assert "(10.5秒)" in captured

    def test_正常系_on_infoでメッセージが出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_info prints the informational message.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_info("テスト情報メッセージ") is called
        Then:
            - Output contains the exact message
        """
        cb = ConsoleProgressCallback()
        cb.on_info("テスト情報メッセージ")

        captured = capsys.readouterr().out
        assert "テスト情報メッセージ" in captured

    def test_正常系_on_workflow_completeで最終サマリーが出力される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete prints the final workflow summary.

        Given:
            - ConsoleProgressCallback instance
            - A WorkflowResult-like object with typical values
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains workflow completion header and statistics
        """
        cb = ConsoleProgressCallback()

        # We need to mock the import of PublicationStatus inside the method
        result = _make_workflow_result()
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "ワークフロー完了" in captured
        assert "収集: 10件" in captured
        assert "抽出: 8件" in captured
        assert "要約: 7件" in captured
        assert "公開: 5件" in captured
        assert "処理時間: 30.5秒" in captured

    def test_正常系_on_workflow_completeでfeed_errorsが表示される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete shows feed error count when present.

        Given:
            - WorkflowResult with feed_errors
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains feed error count
        """
        cb = ConsoleProgressCallback()

        result = _make_workflow_result(
            feed_errors=[MagicMock(), MagicMock()],
        )
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "フィードエラー: 2件" in captured

    def test_正常系_on_workflow_completeで早期重複が表示される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete shows early duplicate count when > 0.

        Given:
            - WorkflowResult with total_early_duplicates > 0
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains early duplicate count
        """
        cb = ConsoleProgressCallback()

        result = _make_workflow_result(total_early_duplicates=3)
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "重複除外（早期）: 3件" in captured

    def test_正常系_on_workflow_completeで重複が表示される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete shows duplicate count when > 0.

        Given:
            - WorkflowResult with total_duplicates > 0
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains duplicate count
        """
        cb = ConsoleProgressCallback()

        result = _make_workflow_result(total_duplicates=2)
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "重複（公開時）: 2件" in captured

    def test_正常系_on_workflow_completeでステージメトリクスが表示される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete shows stage metrics when present.

        Given:
            - WorkflowResult with stage_metrics
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains stage timing information
        """
        cb = ConsoleProgressCallback()

        metrics = [
            StageMetrics(stage="collection", elapsed_seconds=5.2, item_count=10),
            StageMetrics(stage="extraction", elapsed_seconds=12.3, item_count=8),
        ]
        result = _make_workflow_result(stage_metrics=metrics)
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "ステージ別処理時間" in captured
        assert "collection: 5.2秒 (10件)" in captured
        assert "extraction: 12.3秒 (8件)" in captured

    def test_正常系_on_workflow_completeでドメイン抽出率が表示される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete shows domain extraction rates when present.

        Given:
            - WorkflowResult with domain_extraction_rates
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains domain extraction rate information
        """
        cb = ConsoleProgressCallback()

        rates = [
            DomainExtractionRate(
                domain="cnbc.com", total=10, success=8, failed=2, success_rate=80.0
            ),
            DomainExtractionRate(
                domain="reuters.com", total=5, success=5, failed=0, success_rate=100.0
            ),
        ]
        result = _make_workflow_result(domain_extraction_rates=rates)
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "ドメイン別抽出成功率" in captured
        assert "cnbc.com: 8/10 (80%)" in captured
        assert "reuters.com: 5/5 (100%)" in captured

    def test_正常系_on_workflow_completeでcategory_resultsが表示される(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_workflow_complete shows category publish count when category_results present.

        Given:
            - WorkflowResult with category_results
        When:
            - on_workflow_complete(result) is called
        Then:
            - Output contains category publish count instead of total published
        """
        cb = ConsoleProgressCallback()

        cat_results = [
            CategoryPublishResult(
                category="index",
                category_label="株価指数",
                date="2026-02-10",
                issue_number=100,
                issue_url="https://github.com/YH-05/quants/issues/100",
                article_count=5,
                status=PublicationStatus.SUCCESS,
            ),
            CategoryPublishResult(
                category="stock",
                category_label="個別銘柄",
                date="2026-02-10",
                issue_number=None,
                issue_url=None,
                article_count=3,
                status=PublicationStatus.FAILED,
                error_message="API error",
            ),
        ]
        result = _make_workflow_result(category_results=cat_results)
        cb.on_workflow_complete(result)

        captured = capsys.readouterr().out
        assert "カテゴリ別公開: 1/2件" in captured

    def test_エッジケース_on_stage_completeでtotal_0のときゼロ除算しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_stage_complete does not raise ZeroDivisionError when total=0.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_stage_complete("抽出", 0, 0) is called
        Then:
            - No exception is raised and rate shows 0%
        """
        cb = ConsoleProgressCallback()
        cb.on_stage_complete("抽出", 0, 0)

        captured = capsys.readouterr().out
        assert "0/0" in captured
        assert "0%" in captured

    def test_エッジケース_on_progressでcurrentがtotalを超える場合(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_progress handles current > total without error.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_progress(15, 10, "超過テスト") is called
        Then:
            - No exception is raised and output contains [15/10]
        """
        cb = ConsoleProgressCallback()
        cb.on_progress(15, 10, "超過テスト")

        captured = capsys.readouterr().out
        assert "[15/10]" in captured
        assert "超過テスト" in captured

    def test_正常系_on_stage_completeでextra空文字の場合(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """on_stage_complete does not add trailing space when extra is empty.

        Given:
            - ConsoleProgressCallback instance
        When:
            - on_stage_complete("公開", 3, 5) is called (no extra)
        Then:
            - Output does not have trailing extra content
        """
        cb = ConsoleProgressCallback()
        cb.on_stage_complete("公開", 3, 5)

        captured = capsys.readouterr().out
        assert "60%" in captured
        # The output should end with the percentage, no trailing extra
        assert captured.strip().endswith("(60%)")


# --- SilentCallback Tests ---


class TestSilentCallback:
    """Tests for SilentCallback no-op behavior."""

    def test_正常系_on_stage_startで何も出力しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SilentCallback.on_stage_start produces no output.

        Given:
            - SilentCallback instance
        When:
            - on_stage_start is called
        Then:
            - No output is produced
        """
        cb = SilentCallback()
        cb.on_stage_start("1/6", "テスト")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_正常系_on_progressで何も出力しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SilentCallback.on_progress produces no output.

        Given:
            - SilentCallback instance
        When:
            - on_progress is called
        Then:
            - No output is produced
        """
        cb = SilentCallback()
        cb.on_progress(1, 10, "テスト")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_正常系_on_progress_エラー時も何も出力しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SilentCallback.on_progress produces no output even with is_error=True.

        Given:
            - SilentCallback instance
        When:
            - on_progress is called with is_error=True
        Then:
            - No output is produced
        """
        cb = SilentCallback()
        cb.on_progress(1, 10, "エラー", is_error=True)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_正常系_on_stage_completeで何も出力しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SilentCallback.on_stage_complete produces no output.

        Given:
            - SilentCallback instance
        When:
            - on_stage_complete is called
        Then:
            - No output is produced
        """
        cb = SilentCallback()
        cb.on_stage_complete("抽出", 5, 10)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_正常系_on_infoで何も出力しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SilentCallback.on_info produces no output.

        Given:
            - SilentCallback instance
        When:
            - on_info is called
        Then:
            - No output is produced
        """
        cb = SilentCallback()
        cb.on_info("テストメッセージ")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_正常系_on_workflow_completeで何も出力しない(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SilentCallback.on_workflow_complete produces no output.

        Given:
            - SilentCallback instance
        When:
            - on_workflow_complete is called
        Then:
            - No output is produced
        """
        cb = SilentCallback()
        cb.on_workflow_complete(MagicMock())

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_正常系_SilentCallbackがProgressCallbackProtocolに準拠する(
        self,
    ) -> None:
        """SilentCallback conforms to the ProgressCallback Protocol.

        Given:
            - SilentCallback instance
        When:
            - Checking Protocol conformance via isinstance and structural typing
        Then:
            - SilentCallback has all methods defined by ProgressCallback
        """
        cb = SilentCallback()

        # Verify structural conformance: all Protocol methods exist
        assert hasattr(cb, "on_stage_start")
        assert hasattr(cb, "on_progress")
        assert hasattr(cb, "on_stage_complete")
        assert hasattr(cb, "on_info")
        assert hasattr(cb, "on_workflow_complete")

        # Verify callable
        assert callable(cb.on_stage_start)
        assert callable(cb.on_progress)
        assert callable(cb.on_stage_complete)
        assert callable(cb.on_info)
        assert callable(cb.on_workflow_complete)

        # Verify it can be used where ProgressCallback is expected
        # by calling all methods without error
        cb.on_stage_start("1/6", "test")
        cb.on_progress(1, 10, "test")
        cb.on_stage_complete("test", 1, 1)
        cb.on_info("test")
        cb.on_workflow_complete(MagicMock())

    def test_正常系_SilentCallbackをProgressCallback型として代入可能(
        self,
    ) -> None:
        """SilentCallback can be assigned to a ProgressCallback typed variable.

        Given:
            - SilentCallback instance
        When:
            - Assigned to a variable typed as ProgressCallback
        Then:
            - No type error at runtime
        """
        callback: ProgressCallback = SilentCallback()
        # Verify it works through the protocol interface
        callback.on_stage_start("1/1", "test")
        callback.on_progress(1, 1, "test")
        callback.on_stage_complete("test", 1, 1)
        callback.on_info("test")
        callback.on_workflow_complete(MagicMock())


# --- ConsoleProgressCallback also conforms to Protocol ---


class TestConsoleProgressCallbackProtocol:
    """Tests for ConsoleProgressCallback Protocol conformance."""

    def test_正常系_ConsoleProgressCallbackをProgressCallback型として代入可能(
        self,
    ) -> None:
        """ConsoleProgressCallback can be assigned to a ProgressCallback typed variable.

        Given:
            - ConsoleProgressCallback instance
        When:
            - Assigned to a variable typed as ProgressCallback
        Then:
            - No type error at runtime
        """
        callback: ProgressCallback = ConsoleProgressCallback()
        assert callable(callback.on_stage_start)
        assert callable(callback.on_progress)
        assert callable(callback.on_stage_complete)
        assert callable(callback.on_info)
        assert callable(callback.on_workflow_complete)
