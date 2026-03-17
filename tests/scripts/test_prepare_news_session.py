"""Tests for prepare_news_session.py script.

This module tests the deterministic preprocessing script that prepares
news session data for the finance news workflow.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_theme_config() -> dict[str, Any]:
    """Provide sample theme configuration for testing."""
    return {
        "version": "2.1",
        "themes": {
            "index": {
                "name": "Index",
                "name_ja": "株価指数",
                "github_status_id": "3925acc3",
                "feeds": [
                    {"feed_id": "feed-001", "title": "CNBC - Markets"},
                    {"feed_id": "feed-002", "title": "CNBC - Investing"},
                ],
            },
            "stock": {
                "name": "Stock",
                "name_ja": "個別銘柄",
                "github_status_id": "f762022e",
                "feeds": [{"feed_id": "feed-003", "title": "CNBC - Earnings"}],
            },
        },
        "project": {
            "project_id": "PVT_test123",
            "status_field_id": "PVTSSF_test",
            "published_date_field_id": "PVTF_test",
            "owner": "YH-05",
            "number": 15,
        },
    }


@pytest.fixture
def sample_existing_issues() -> list[dict[str, Any]]:
    """Provide sample existing issues from GitHub."""
    return [
        {
            "number": 100,
            "title": "[株価指数] S&P 500 Hits Record High",
            "url": "https://github.com/YH-05/quants/issues/100",
            "body": "詳細は元記事を参照: https://www.cnbc.com/2026/01/15/sp500-record.html",
        },
        {
            "number": 101,
            "title": "[個別銘柄] Apple Reports Q4 Earnings",
            "url": "https://github.com/YH-05/quants/issues/101",
            "body": "詳細は元記事を参照: https://www.cnbc.com/2026/01/16/apple-earnings.html",
        },
    ]


@pytest.fixture
def sample_rss_items() -> list[dict[str, Any]]:
    """Provide sample RSS feed items."""
    now = datetime.now(timezone.utc)
    return [
        {
            "item_id": "item-001",
            "title": "New Article About Markets",
            "link": "https://www.cnbc.com/2026/01/29/new-market-article.html",
            "published": (now - timedelta(hours=2)).isoformat(),
            "summary": "A new article about market conditions.",
            "content": None,
            "author": None,
            "fetched_at": now.isoformat(),
        },
        {
            "item_id": "item-002",
            "title": "S&P 500 Hits Record High",  # Duplicate title
            "link": "https://www.cnbc.com/2026/01/15/sp500-record.html",  # Duplicate URL
            "published": (now - timedelta(hours=1)).isoformat(),
            "summary": "S&P 500 reaches new all-time high.",
            "content": None,
            "author": None,
            "fetched_at": now.isoformat(),
        },
        {
            "item_id": "item-003",
            "title": "Old News Article",
            "link": "https://www.cnbc.com/2026/01/01/old-article.html",
            "published": (now - timedelta(days=30)).isoformat(),  # Too old
            "summary": "An old article.",
            "content": None,
            "author": None,
            "fetched_at": now.isoformat(),
        },
    ]


# ---------------------------------------------------------------------------
# Test: CLI Argument Parsing
# ---------------------------------------------------------------------------


class TestCLIArgumentParsing:
    """Test CLI argument parsing functionality."""

    def test_正常系_デフォルト引数で実行できる(self) -> None:
        """Test running with default arguments."""
        from scripts.prepare_news_session import parse_args

        args = parse_args([])
        assert args.days == 7
        assert args.themes == "all"
        assert args.output is None

    def test_正常系_カスタム引数で実行できる(self) -> None:
        """Test running with custom arguments."""
        from scripts.prepare_news_session import parse_args

        args = parse_args(
            ["--days", "14", "--themes", "index,stock", "--output", "test.json"]
        )
        assert args.days == 14
        assert args.themes == "index,stock"
        assert args.output == "test.json"

    def test_異常系_無効なdays値でエラー(self) -> None:
        """Test error handling for invalid days value."""
        from scripts.prepare_news_session import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--days", "invalid"])


# ---------------------------------------------------------------------------
# Test: Existing Issues Retrieval
# ---------------------------------------------------------------------------


class TestExistingIssuesRetrieval:
    """Test existing issues retrieval from GitHub."""

    def test_正常系_既存IssueからURLを抽出できる(
        self, sample_existing_issues: list[dict[str, Any]]
    ) -> None:
        """Test URL extraction from existing issues."""
        from scripts.prepare_news_session import extract_urls_from_issues

        urls = extract_urls_from_issues(sample_existing_issues)

        assert len(urls) == 2
        # URLs are normalized (www. removed)
        assert "https://cnbc.com/2026/01/15/sp500-record.html" in urls
        assert "https://cnbc.com/2026/01/16/apple-earnings.html" in urls

    def test_正常系_Issue本文がない場合は空リストを返す(self) -> None:
        """Test handling of issues without body."""
        from scripts.prepare_news_session import extract_urls_from_issues

        issues = [{"number": 100, "title": "Test", "body": ""}]
        urls = extract_urls_from_issues(issues)

        assert urls == set()

    @patch("scripts.prepare_news_session.subprocess.run")
    def test_正常系_gh_CLIでIssueを取得できる(
        self, mock_run: MagicMock, sample_existing_issues: list[dict[str, Any]]
    ) -> None:
        """Test fetching issues via gh CLI."""
        from scripts.prepare_news_session import get_existing_issues_with_urls

        # Mock gh project item-list response format
        mock_response = {
            "items": [
                {
                    "content": {
                        "type": "Issue",
                        "number": issue["number"],
                        "title": issue["title"],
                        "body": issue["body"],
                        "url": issue["url"],
                    }
                }
                for issue in sample_existing_issues
            ]
        }
        mock_run.return_value.stdout = json.dumps(mock_response)
        mock_run.return_value.returncode = 0

        issues, urls = get_existing_issues_with_urls(
            project_number=15, owner="YH-05", days_back=7
        )

        assert len(issues) == 2
        assert len(urls) == 2


# ---------------------------------------------------------------------------
# Test: RSS Feed Fetching
# ---------------------------------------------------------------------------


class TestRSSFeedFetching:
    """Test RSS feed fetching functionality."""

    def test_正常系_テーマ別にRSSアイテムを取得できる(
        self, sample_theme_config: dict[str, Any]
    ) -> None:
        """Test fetching RSS items by theme."""
        from scripts.prepare_news_session import fetch_rss_items_by_theme

        with patch("scripts.prepare_news_session.FeedReader") as mock_reader:
            mock_instance = mock_reader.return_value
            mock_instance.get_items.return_value = []

            items_by_theme = fetch_rss_items_by_theme(
                theme_config=sample_theme_config,
                data_dir=Path("data/raw/rss"),
            )

            assert "index" in items_by_theme
            assert "stock" in items_by_theme


# ---------------------------------------------------------------------------
# Test: Date Filtering
# ---------------------------------------------------------------------------


class TestDateFiltering:
    """Test date filtering functionality."""

    def test_正常系_指定日数以内の記事のみ返す(
        self, sample_rss_items: list[dict[str, Any]]
    ) -> None:
        """Test filtering articles within specified days."""
        from scripts.prepare_news_session import filter_by_date

        filtered = filter_by_date(sample_rss_items, days=7)

        # item-001 and item-002 should pass, item-003 is too old
        assert len(filtered) == 2
        assert all(item["item_id"] != "item-003" for item in filtered)

    def test_正常系_publishedがNoneの記事は除外される(self) -> None:
        """Test filtering excludes items without published date."""
        from scripts.prepare_news_session import filter_by_date

        items = [
            {"item_id": "item-001", "published": None},
            {
                "item_id": "item-002",
                "published": datetime.now(timezone.utc).isoformat(),
            },
        ]
        filtered = filter_by_date(items, days=7)

        assert len(filtered) == 1
        assert filtered[0]["item_id"] == "item-002"


# ---------------------------------------------------------------------------
# Test: Duplicate Checking
# ---------------------------------------------------------------------------


class TestDuplicateChecking:
    """Test duplicate checking functionality."""

    def test_正常系_重複URLを検出できる(
        self,
        sample_rss_items: list[dict[str, Any]],
        sample_existing_issues: list[dict[str, Any]],
    ) -> None:
        """Test detection of duplicate URLs."""
        from scripts.prepare_news_session import (
            check_duplicates,
            extract_urls_from_issues,
        )

        existing_urls = extract_urls_from_issues(sample_existing_issues)
        unique, duplicates = check_duplicates(sample_rss_items, existing_urls)

        # item-002 has duplicate URL
        assert len(duplicates) == 1
        assert duplicates[0]["item_id"] == "item-002"
        assert len(unique) == 2

    def test_正常系_正規化URLで比較できる(self) -> None:
        """Test URL normalization during comparison."""
        from scripts.prepare_news_session import check_duplicates

        items = [
            {"item_id": "item-001", "link": "https://www.cnbc.com/article/"},
        ]
        existing_urls = {"https://cnbc.com/article"}  # Normalized form

        _unique, duplicates = check_duplicates(items, existing_urls)

        assert len(duplicates) == 1


# ---------------------------------------------------------------------------
# Test: Paywall Detection
# (Removed: paywall detection is no longer part of this preprocessing script)


# ---------------------------------------------------------------------------
# Test: Session Generation
# ---------------------------------------------------------------------------


class TestSessionGeneration:
    """Test session file generation functionality."""

    def test_正常系_セッションファイルを生成できる(
        self, sample_theme_config: dict[str, Any]
    ) -> None:
        """Test generating session file with correct structure."""
        from scripts.prepare_news_session import generate_session

        theme_results = {
            "index": {
                "articles": [
                    {
                        "link": "https://example.com/article1",
                        "title": "Article 1",
                        "summary": "Summary 1",
                        "feed_source": "CNBC - Markets",
                        "published": "2026-01-29T12:00:00+00:00",
                    }
                ],
                "blocked": [],
            },
            "stock": {"articles": [], "blocked": []},
        }

        session = generate_session(
            theme_results=theme_results,
            theme_config=sample_theme_config,
            stats={"total": 5, "duplicates": 2, "accessible": 2},
        )

        assert session.session_id.startswith("news-")
        assert session.config.project_id == "PVT_test123"
        assert len(session.themes["index"].articles) == 1
        assert session.stats.accessible == 2

    def test_正常系_セッションIDが正しい形式である(self) -> None:
        """Test session ID format."""
        from scripts.prepare_news_session import generate_session_id

        session_id = generate_session_id()

        # Format: news-{YYYYMMDD}-{HHMMSS}
        assert session_id.startswith("news-")
        parts = session_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS


# ---------------------------------------------------------------------------
# Test: Output File
# ---------------------------------------------------------------------------


class TestOutputFile:
    """Test session file output functionality."""

    def test_正常系_JSONファイルを出力できる(
        self, tmp_path: Path, sample_theme_config: dict[str, Any]
    ) -> None:
        """Test writing session to JSON file."""
        from scripts.prepare_news_session import (
            NewsSession,
            SessionConfig,
            SessionStats,
            write_session_file,
        )

        session = NewsSession(
            session_id="news-20260129-120000",
            timestamp="2026-01-29T12:00:00+09:00",
            config=SessionConfig(
                project_id=sample_theme_config["project"]["project_id"],
                project_number=sample_theme_config["project"]["number"],
                project_owner=sample_theme_config["project"]["owner"],
                status_field_id=sample_theme_config["project"]["status_field_id"],
                published_date_field_id=sample_theme_config["project"][
                    "published_date_field_id"
                ],
            ),
            themes={},
            stats=SessionStats(total=0, duplicates=0, accessible=0),
        )

        output_path = tmp_path / "test-session.json"
        write_session_file(session, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["session_id"] == "news-20260129-120000"

    def test_正常系_tmpディレクトリに自動保存できる(self) -> None:
        """Test automatic saving to .tmp directory."""
        from scripts.prepare_news_session import get_default_output_path

        output_path = get_default_output_path()

        assert ".tmp" in str(output_path)
        assert output_path.suffix == ".json"


# ---------------------------------------------------------------------------
# Test: Stats Calculation
# ---------------------------------------------------------------------------


class TestStatsCalculation:
    """Test statistics calculation functionality."""

    def test_正常系_統計を正しく計算できる(self) -> None:
        """Test correct calculation of stats."""
        from scripts.prepare_news_session import calculate_stats

        theme_results = {
            "index": {"articles": [{"url": "a"}] * 10, "blocked": [{"url": "b"}] * 2},
            "stock": {"articles": [{"url": "c"}] * 5, "blocked": [{"url": "d"}] * 1},
        }

        stats = calculate_stats(
            theme_results=theme_results,
            total_fetched=25,
            duplicates_count=7,
        )

        assert stats["total"] == 25
        assert stats["duplicates"] == 7
        # Note: paywall_blocked is no longer tracked in this script
        assert stats["accessible"] == 15  # 10 + 5


# ---------------------------------------------------------------------------
# Test: Integration (End-to-End)
# ---------------------------------------------------------------------------


class TestIntegration:
    """Test end-to-end integration of the script."""

    @patch("scripts.prepare_news_session.subprocess.run")
    def test_正常系_メイン処理が正常に完了する(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
        sample_theme_config: dict[str, Any],
        sample_existing_issues: list[dict[str, Any]],
    ) -> None:
        """Test main function completes successfully."""
        from scripts.prepare_news_session import main

        # Mock gh CLI with proper response format
        mock_response = {
            "items": [
                {
                    "content": {
                        "type": "Issue",
                        "number": issue["number"],
                        "title": issue["title"],
                        "body": issue["body"],
                        "url": issue["url"],
                    }
                }
                for issue in sample_existing_issues
            ]
        }
        mock_run.return_value.stdout = json.dumps(mock_response)
        mock_run.return_value.returncode = 0

        with (
            patch("scripts.prepare_news_session.load_theme_config") as mock_config,
            patch("scripts.prepare_news_session.FeedReader") as mock_reader,
        ):
            mock_config.return_value = sample_theme_config
            mock_reader.return_value.get_items.return_value = []

            output_path = tmp_path / "output.json"
            result = main(
                [
                    "--output",
                    str(output_path),
                    "--themes",
                    "index",
                ]
            )

            assert result == 0
            assert output_path.exists()
