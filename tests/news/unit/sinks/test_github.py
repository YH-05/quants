"""Unit tests for GitHubSink in the news package.

Tests for the GitHubSink class that outputs news articles to GitHub Issues
and adds them to a specified GitHub Project.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl

from news.core.article import Article, ArticleSource, ContentType, Provider
from news.core.result import FetchResult
from news.core.sink import SinkProtocol, SinkType
from news.sinks.github import GitHubSink, GitHubSinkConfig

if TYPE_CHECKING:
    from pathlib import Path


class TestGitHubSinkConfigModel:
    """Test GitHubSinkConfig model."""

    def test_正常系_必須フィールドのみで初期化できる(self) -> None:
        """必須フィールドのみでGitHubSinkConfigを初期化できることを確認。"""
        config = GitHubSinkConfig(
            project_number=24,
        )

        assert config.project_number == 24
        assert config.repository is None
        assert config.labels == []
        assert config.dry_run is False

    def test_正常系_全フィールドで初期化できる(self) -> None:
        """全フィールドを指定してGitHubSinkConfigを初期化できることを確認。"""
        config = GitHubSinkConfig(
            project_number=24,
            repository="YH-05/quants",
            labels=["news", "finance"],
            dry_run=True,
        )

        assert config.project_number == 24
        assert config.repository == "YH-05/quants"
        assert config.labels == ["news", "finance"]
        assert config.dry_run is True

    def test_異常系_project_numberが負の数でエラー(self) -> None:
        """project_numberが負の数の場合にエラーになることを確認。"""
        with pytest.raises(ValueError):
            GitHubSinkConfig(project_number=-1)

    def test_異常系_project_numberがゼロでエラー(self) -> None:
        """project_numberがゼロの場合にエラーになることを確認。"""
        with pytest.raises(ValueError):
            GitHubSinkConfig(project_number=0)


class TestGitHubSinkInitialization:
    """Test GitHubSink initialization."""

    def test_正常系_設定で初期化できる(self) -> None:
        """設定でGitHubSinkを初期化できることを確認。"""
        config = GitHubSinkConfig(project_number=24)
        sink = GitHubSink(config=config)

        assert sink.config == config

    def test_正常系_project_numberのみで初期化できる(self) -> None:
        """project_numberのみでGitHubSinkを初期化できることを確認。"""
        sink = GitHubSink(project_number=24)

        assert sink.config.project_number == 24


class TestGitHubSinkProtocolCompliance:
    """Test GitHubSink implements SinkProtocol."""

    def test_正常系_SinkProtocolに準拠する(self) -> None:
        """GitHubSinkがSinkProtocolに準拠することを確認。"""
        sink = GitHubSink(project_number=24)

        assert isinstance(sink, SinkProtocol)

    def test_正常系_sink_nameが正しい(self) -> None:
        """sink_nameが正しい値を返すことを確認。"""
        sink = GitHubSink(project_number=24)

        assert sink.sink_name == "github_issue"

    def test_正常系_sink_typeがGITHUBである(self) -> None:
        """sink_typeがSinkType.GITHUBであることを確認。"""
        sink = GitHubSink(project_number=24)

        assert sink.sink_type == SinkType.GITHUB


class TestGitHubSinkWrite:
    """Test GitHubSink.write() method."""

    @pytest.fixture
    def sample_article(self) -> Article:
        """テスト用のArticleを提供するフィクスチャ。"""
        return Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article"),
            title="Test Article Title",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
            summary="This is a test article summary.",
            content_type=ContentType.ARTICLE,
            provider=Provider(
                name="Yahoo Finance",
                url=HttpUrl("https://finance.yahoo.com/"),
            ),
            related_tickers=["AAPL"],
            tags=["technology"],
        )

    @pytest.fixture
    def sample_articles(self, sample_article: Article) -> list[Article]:
        """テスト用の複数Articleを提供するフィクスチャ。"""
        article2 = Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article-2"),
            title="Test Article Title 2",
            published_at=datetime(2026, 1, 27, 22, 0, 0, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_SEARCH,
            summary="This is another test article.",
            tags=["macro"],
        )
        return [sample_article, article2]

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_単一記事でIssueが作成される(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """単一の記事からGitHub Issueが作成されることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24)

        result = sink.write([sample_article])

        assert result is True
        # gh issue create が呼ばれていることを確認
        assert mock_run.called

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_複数記事でIssueが作成される(
        self,
        mock_run: MagicMock,
        sample_articles: list[Article],
    ) -> None:
        """複数の記事からGitHub Issueが作成されることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24)

        result = sink.write(sample_articles)

        assert result is True
        # 2つの記事に対して2回呼ばれることを確認
        assert mock_run.call_count >= 2

    def test_正常系_空の記事リストでTrueを返す(self) -> None:
        """空の記事リストでwriteしてもTrueを返すことを確認。"""
        sink = GitHubSink(project_number=24)

        result = sink.write([])

        assert result is True

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_dry_runモードでghコマンドは実行されない(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """dry_runモードでghコマンドが実行されないことを確認。"""
        sink = GitHubSink(
            config=GitHubSinkConfig(project_number=24, dry_run=True),
        )

        result = sink.write([sample_article])

        assert result is True
        # dry_runモードではghコマンドは実行されない
        mock_run.assert_not_called()

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_ラベルが指定されている場合追加される(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """ラベルが指定されている場合、Issueに追加されることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(
            config=GitHubSinkConfig(
                project_number=24,
                labels=["news", "finance"],
            ),
            check_duplicates=False,  # 重複チェックをスキップ
        )

        result = sink.write([sample_article])

        assert result is True
        # gh issue create コマンドにラベルオプションが含まれていることを確認
        # check_duplicates=False なので最初の呼び出しが gh issue create
        call_args = mock_run.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        assert "--label" in cmd


class TestGitHubSinkIssueFormat:
    """Test GitHubSink Issue format."""

    @pytest.fixture
    def sample_article(self) -> Article:
        """テスト用のArticleを提供するフィクスチャ。"""
        return Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article"),
            title="Apple Reports Q1 Earnings",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
            summary="Apple announced strong Q1 earnings...",
            provider=Provider(
                name="Yahoo Finance",
                url=HttpUrl("https://finance.yahoo.com/"),
            ),
            related_tickers=["AAPL", "GOOGL"],
            tags=["earnings", "technology"],
        )

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_Issueタイトルが正しいフォーマットである(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """IssueタイトルがArticleのタイトルと一致することを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24, check_duplicates=False)

        sink.write([sample_article])

        # gh issue create コマンドのタイトル引数を確認
        # check_duplicates=False なので最初の呼び出しが gh issue create
        call_args = mock_run.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "Apple Reports Q1 Earnings" in cmd_str

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_Issue本文にURLが含まれる(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """Issue本文にArticleのURLが含まれることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24, check_duplicates=False)

        sink.write([sample_article])

        # gh issue create コマンドのbody引数にURLが含まれていることを確認
        call_args = mock_run.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "https://finance.yahoo.com/news/test-article" in cmd_str

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_Issue本文に公開日時が含まれる(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """Issue本文に公開日時が含まれることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24, check_duplicates=False)

        sink.write([sample_article])

        # gh issue create コマンドのbody引数に公開日時が含まれていることを確認
        call_args = mock_run.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "2026-01-27" in cmd_str

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_Issue本文にプロバイダー情報が含まれる(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """Issue本文にプロバイダー情報が含まれることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24, check_duplicates=False)

        sink.write([sample_article])

        # gh issue create コマンドのbody引数にプロバイダー名が含まれていることを確認
        call_args = mock_run.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "Yahoo Finance" in cmd_str

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_Issue本文に関連ティッカーが含まれる(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """Issue本文に関連ティッカーが含まれることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24, check_duplicates=False)

        sink.write([sample_article])

        # gh issue create コマンドのbody引数に関連ティッカーが含まれていることを確認
        call_args = mock_run.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        assert "AAPL" in cmd_str


class TestGitHubSinkProjectIntegration:
    """Test GitHubSink Project integration."""

    @pytest.fixture
    def sample_article(self) -> Article:
        """テスト用のArticleを提供するフィクスチャ。"""
        return Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article"),
            title="Test Article",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_IssueがProjectに追加される(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """作成されたIssueが指定のProjectに追加されることを確認。"""
        # Issue作成とProject追加の両方が成功
        mock_run.side_effect = [
            # gh issue create
            MagicMock(
                returncode=0,
                stdout="https://github.com/YH-05/quants/issues/100\n",
            ),
            # gh project item-add
            MagicMock(returncode=0, stdout=""),
        ]
        sink = GitHubSink(project_number=24, check_duplicates=False)

        result = sink.write([sample_article])

        assert result is True
        # Issue作成とProject追加の両方が呼ばれていることを確認
        assert mock_run.call_count == 2

    @patch("news.sinks.github.subprocess.run")
    def test_異常系_Project追加が失敗してもIssue作成は成功扱い(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """Project追加が失敗してもIssue自体は作成成功として扱うことを確認。"""
        mock_run.side_effect = [
            # gh issue create - 成功
            MagicMock(
                returncode=0,
                stdout="https://github.com/YH-05/quants/issues/100\n",
            ),
            # gh project item-add - 失敗
            MagicMock(returncode=1, stderr="Project not found"),
        ]
        sink = GitHubSink(project_number=24, check_duplicates=False)

        # Issueは作成されるのでTrueを返す（警告はログに出力）
        result = sink.write([sample_article])

        assert result is True


class TestGitHubSinkDuplicateCheck:
    """Test GitHubSink duplicate check functionality."""

    @pytest.fixture
    def sample_article(self) -> Article:
        """テスト用のArticleを提供するフィクスチャ。"""
        return Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article"),
            title="Test Article",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_重複URLの記事はIssue作成されない(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """既にIssue化されているURLの記事は重複作成されないことを確認。"""
        # 重複チェック: 既存Issueを返す
        mock_run.side_effect = [
            # gh issue list で既存Issue検索 - 既存あり
            MagicMock(
                returncode=0,
                stdout='[{"number": 99, "title": "Test Article", "body": "URL: https://finance.yahoo.com/news/test-article"}]\n',
            ),
        ]
        sink = GitHubSink(project_number=24, check_duplicates=True)

        result = sink.write([sample_article])

        assert result is True
        # 重複のため gh issue create は呼ばれない
        # gh issue list のみが呼ばれる
        assert mock_run.call_count == 1

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_重複チェック無効時は常にIssue作成される(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """重複チェックが無効の場合、常にIssueが作成されることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24, check_duplicates=False)

        result = sink.write([sample_article])

        assert result is True
        # 重複チェックなしでIssue作成
        assert mock_run.called


class TestGitHubSinkWriteBatch:
    """Test GitHubSink.write_batch() method."""

    @pytest.fixture
    def sample_fetch_results(self) -> list[FetchResult]:
        """テスト用のFetchResultリストを提供するフィクスチャ。"""
        article1 = Article(
            url=HttpUrl("https://finance.yahoo.com/news/aapl-1"),
            title="AAPL Article",
            published_at=datetime(2026, 1, 27, 10, 0, 0, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )
        article2 = Article(
            url=HttpUrl("https://finance.yahoo.com/news/googl-1"),
            title="GOOGL Article",
            published_at=datetime(2026, 1, 27, 11, 0, 0, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )
        return [
            FetchResult(articles=[article1], success=True, ticker="AAPL"),
            FetchResult(articles=[article2], success=True, ticker="GOOGL"),
        ]

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_write_batchで複数FetchResultのIssueが作成される(
        self,
        mock_run: MagicMock,
        sample_fetch_results: list[FetchResult],
    ) -> None:
        """write_batchで複数のFetchResultからIssueが作成されることを確認。"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24)

        result = sink.write_batch(sample_fetch_results)

        assert result is True

    def test_正常系_空のwrite_batchでTrueを返す(self) -> None:
        """空のFetchResultリストでwrite_batchしてもTrueを返すことを確認。"""
        sink = GitHubSink(project_number=24)

        result = sink.write_batch([])

        assert result is True

    @patch("news.sinks.github.subprocess.run")
    def test_正常系_失敗したFetchResultは無視される(
        self,
        mock_run: MagicMock,
    ) -> None:
        """success=FalseのFetchResultの記事はIssue化されないことを確認。"""
        article = Article(
            url=HttpUrl("https://finance.yahoo.com/news/test"),
            title="Test",
            published_at=datetime(2026, 1, 27, 10, 0, 0, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )
        results = [
            FetchResult(articles=[article], success=True, ticker="AAPL"),
            FetchResult(articles=[], success=False, ticker="INVALID"),
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/YH-05/quants/issues/100\n",
        )
        sink = GitHubSink(project_number=24)

        result = sink.write_batch(results)

        assert result is True


class TestGitHubSinkErrorHandling:
    """Test GitHubSink error handling."""

    @pytest.fixture
    def sample_article(self) -> Article:
        """テスト用のArticleを提供するフィクスチャ。"""
        return Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article"),
            title="Test Article",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )

    @patch("news.sinks.github.subprocess.run")
    def test_異常系_ghコマンドが失敗した場合Falseを返す(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """ghコマンドが失敗した場合にFalseを返すことを確認。"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="gh: command not found",
        )
        sink = GitHubSink(project_number=24)

        result = sink.write([sample_article])

        assert result is False

    @patch("news.sinks.github.subprocess.run")
    def test_異常系_subprocess例外が発生した場合Falseを返す(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """subprocess実行時に例外が発生した場合にFalseを返すことを確認。"""
        mock_run.side_effect = subprocess.SubprocessError("Process failed")
        sink = GitHubSink(project_number=24)

        result = sink.write([sample_article])

        assert result is False

    @patch("news.sinks.github.subprocess.run")
    def test_異常系_認証エラーの場合Falseを返す(
        self,
        mock_run: MagicMock,
        sample_article: Article,
    ) -> None:
        """GitHub認証エラーの場合にFalseを返すことを確認。"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="gh: not authenticated",
        )
        sink = GitHubSink(project_number=24)

        result = sink.write([sample_article])

        assert result is False


class TestGitHubSinkBuildIssueBody:
    """Test GitHubSink._build_issue_body() method."""

    @pytest.fixture
    def sample_article(self) -> Article:
        """テスト用のArticleを提供するフィクスチャ。"""
        return Article(
            url=HttpUrl("https://finance.yahoo.com/news/test-article"),
            title="Apple Reports Q1 Earnings",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
            summary="Apple announced strong Q1 earnings with record revenue.",
            provider=Provider(
                name="Yahoo Finance",
                url=HttpUrl("https://finance.yahoo.com/"),
            ),
            related_tickers=["AAPL", "GOOGL"],
            tags=["earnings", "technology"],
        )

    def test_正常系_Issue本文がproject_md仕様に準拠する(
        self,
        sample_article: Article,
    ) -> None:
        """Issue本文がproject.mdで定義されたフォーマットに準拠することを確認。"""
        sink = GitHubSink(project_number=24)

        body = sink._build_issue_body(sample_article)

        # 必須セクションが含まれていることを確認
        assert "## 概要" in body
        assert "## 詳細" in body
        assert "## タグ" in body

        # 必須フィールドが含まれていることを確認
        assert "Apple announced strong Q1 earnings" in body
        assert "https://finance.yahoo.com/news/test-article" in body
        assert "2026-01-27" in body
        assert "Yahoo Finance" in body
        assert "AAPL" in body
        assert "GOOGL" in body
        assert "earnings" in body
        assert "technology" in body

    def test_正常系_プロバイダーがNoneの場合も正しく生成される(self) -> None:
        """プロバイダーがNoneの場合もIssue本文が正しく生成されることを確認。"""
        article = Article(
            url=HttpUrl("https://finance.yahoo.com/news/test"),
            title="Test Article",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_TICKER,
        )
        sink = GitHubSink(project_number=24)

        body = sink._build_issue_body(article)

        # エラーなく生成されることを確認
        assert "## 概要" in body
        assert "## 詳細" in body

    def test_正常系_関連ティッカーが空の場合も正しく生成される(self) -> None:
        """関連ティッカーが空の場合もIssue本文が正しく生成されることを確認。"""
        article = Article(
            url=HttpUrl("https://finance.yahoo.com/news/test"),
            title="Test Article",
            published_at=datetime(2026, 1, 27, 23, 33, 53, tzinfo=timezone.utc),
            source=ArticleSource.YFINANCE_SEARCH,
            related_tickers=[],
        )
        sink = GitHubSink(project_number=24)

        body = sink._build_issue_body(article)

        # エラーなく生成されることを確認
        assert "## 詳細" in body
