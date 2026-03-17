"""Tests for prepare_ai_research_session.py script.

This module tests the deterministic preprocessing script that prepares
AI research session data for the AI investment value chain tracking workflow.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_scraped_articles() -> list[Any]:
    """Provide sample ScrapedArticleData instances for testing."""
    from scripts.prepare_ai_research_session import ScrapedArticleData

    now = datetime.now(timezone.utc)
    return [
        ScrapedArticleData(
            url="https://openai.com/news/gpt-5-release",
            title="GPT-5 Release Announcement",
            text="OpenAI today announced GPT-5...",
            company_key="openai",
            company_name="OpenAI",
            category="ai_llm",
            source_type="blog",
            pdf_url=None,
            published=(now - timedelta(hours=2)).isoformat(),
        ),
        ScrapedArticleData(
            url="https://blogs.nvidia.com/blackwell-update",
            title="NVIDIA Blackwell Architecture Update",
            text="NVIDIA unveiled the latest Blackwell updates...",
            company_key="nvidia",
            company_name="NVIDIA",
            category="gpu_chips",
            source_type="blog",
            pdf_url=None,
            published=(now - timedelta(hours=1)).isoformat(),
        ),
        ScrapedArticleData(
            url="https://openai.com/news/old-article",
            title="Old OpenAI Article",
            text="This is an old article...",
            company_key="openai",
            company_name="OpenAI",
            category="ai_llm",
            source_type="blog",
            pdf_url=None,
            published=(now - timedelta(days=30)).isoformat(),
        ),
    ]


@pytest.fixture
def sample_existing_issues() -> list[dict[str, Any]]:
    """Provide sample existing issues from GitHub."""
    return [
        {
            "number": 100,
            "title": "[AI/LLM] GPT-5 Release",
            "url": "https://github.com/YH-05/quants/issues/100",
            "body": "詳細は元記事を参照: https://openai.com/news/gpt-5-release",
        },
        {
            "number": 101,
            "title": "[GPU] Blackwell News",
            "url": "https://github.com/YH-05/quants/issues/101",
            "body": "詳細は元記事を参照: https://blogs.nvidia.com/blackwell-old",
        },
    ]


# ---------------------------------------------------------------------------
# Test: CLI Argument Parsing
# ---------------------------------------------------------------------------


class TestCLIArgumentParsing:
    """Test CLI argument parsing functionality."""

    def test_正常系_デフォルト引数で実行できる(self) -> None:
        """Test running with default arguments."""
        from scripts.prepare_ai_research_session import parse_args

        args = parse_args([])
        assert args.days == 7
        assert args.categories == "all"
        assert args.top_n == 10

    def test_正常系_カスタム引数で実行できる(self) -> None:
        """Test running with custom arguments."""
        from scripts.prepare_ai_research_session import parse_args

        args = parse_args(
            ["--days", "14", "--categories", "ai_llm,gpu_chips", "--top-n", "5"]
        )
        assert args.days == 14
        assert args.categories == "ai_llm,gpu_chips"
        assert args.top_n == 5

    def test_正常系_verboseフラグが設定できる(self) -> None:
        """Test verbose flag."""
        from scripts.prepare_ai_research_session import parse_args

        args = parse_args(["-v"])
        assert args.verbose is True

    def test_異常系_無効なdays値でエラー(self) -> None:
        """Test error handling for invalid days value."""
        from scripts.prepare_ai_research_session import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--days", "invalid"])


# ---------------------------------------------------------------------------
# Test: Category Loading
# ---------------------------------------------------------------------------


class TestCategoryLoading:
    """Test category configuration loading."""

    def test_正常系_全カテゴリを読み込める(self) -> None:
        """Test loading all categories."""
        from scripts.prepare_ai_research_session import get_category_companies

        categories = get_category_companies(None)
        assert len(categories) == 10
        assert "ai_llm" in categories
        assert "gpu_chips" in categories
        assert "semiconductor" in categories
        assert "data_center" in categories
        assert "networking" in categories
        assert "power_energy" in categories
        assert "nuclear_fusion" in categories
        assert "physical_ai" in categories
        assert "saas" in categories
        assert "ai_infra" in categories

    def test_正常系_特定カテゴリを選択できる(self) -> None:
        """Test loading specific categories."""
        from scripts.prepare_ai_research_session import get_category_companies

        categories = get_category_companies(["ai_llm", "gpu_chips"])
        assert len(categories) == 2
        assert "ai_llm" in categories
        assert "gpu_chips" in categories

    def test_異常系_不明なカテゴリでValueError(self) -> None:
        """Test error for unknown category."""
        from scripts.prepare_ai_research_session import get_category_companies

        with pytest.raises(ValueError, match="Unknown category"):
            get_category_companies(["ai_llm", "nonexistent_category"])

    def test_正常系_全カテゴリに企業が含まれる(self) -> None:
        """Test that all categories have at least one company."""
        from scripts.prepare_ai_research_session import get_category_companies

        categories = get_category_companies(None)
        for key, companies in categories.items():
            assert len(companies) > 0, f"Category {key} has no companies"

    def test_正常系_合計企業数が正しい(self) -> None:
        """Test total company count across all categories."""
        from scripts.prepare_ai_research_session import (
            count_total_companies,
            get_category_companies,
        )

        categories = get_category_companies(None)
        total = count_total_companies(categories)
        # Should be 77 companies total per project doc
        assert total > 0
        assert total >= 70  # At least 70 companies


# ---------------------------------------------------------------------------
# Test: Existing Issues URL Extraction
# ---------------------------------------------------------------------------


class TestExistingIssueURLExtraction:
    """Test URL extraction from existing GitHub issues."""

    def test_正常系_Issue本文からURLを抽出できる(
        self,
        sample_existing_issues: list[dict[str, Any]],
    ) -> None:
        """Test extracting URLs from issue bodies."""
        from scripts.prepare_ai_research_session import extract_urls_from_issues

        urls = extract_urls_from_issues(sample_existing_issues)
        assert len(urls) >= 2
        # Should contain normalized article URLs
        assert any("openai.com" in url for url in urls)
        assert any("nvidia.com" in url for url in urls)

    def test_正常系_GitHubのURLは除外される(self) -> None:
        """Test that GitHub URLs are excluded."""
        from scripts.prepare_ai_research_session import extract_urls_from_issues

        issues = [
            {
                "number": 1,
                "title": "Test",
                "body": "https://github.com/YH-05/quants/issues/1 and https://example.com/article",
            }
        ]
        urls = extract_urls_from_issues(issues)
        assert not any("github.com" in url for url in urls)
        assert any("example.com" in url for url in urls)

    def test_エッジケース_空のIssueリストで空セット(self) -> None:
        """Test empty issue list returns empty set."""
        from scripts.prepare_ai_research_session import extract_urls_from_issues

        urls = extract_urls_from_issues([])
        assert urls == set()

    def test_エッジケース_本文がNoneの場合もエラーなし(self) -> None:
        """Test handling None body."""
        from scripts.prepare_ai_research_session import extract_urls_from_issues

        issues = [{"number": 1, "title": "Test", "body": None}]
        urls = extract_urls_from_issues(issues)
        assert urls == set()


# ---------------------------------------------------------------------------
# Test: Duplicate Checking
# ---------------------------------------------------------------------------


class TestDuplicateChecking:
    """Test duplicate URL checking functionality."""

    def test_正常系_重複URLが検出される(
        self,
        sample_scraped_articles: list[Any],
    ) -> None:
        """Test that duplicate URLs are detected."""
        from rss.utils.url_normalizer import normalize_url
        from scripts.prepare_ai_research_session import check_duplicates

        # Use normalized URL form to match what check_duplicates produces
        normalized = normalize_url("https://openai.com/news/gpt-5-release")
        existing_urls = {normalized}
        unique, duplicates = check_duplicates(sample_scraped_articles, existing_urls)

        # The openai.com article with matching URL should be duplicate
        assert len(duplicates) >= 1
        assert len(unique) <= len(sample_scraped_articles)

    def test_正常系_重複なしの場合全て返される(self) -> None:
        """Test when no duplicates exist."""
        from scripts.prepare_ai_research_session import (
            ScrapedArticleData,
            check_duplicates,
        )

        articles = [
            ScrapedArticleData(
                url="https://unique.com/article1",
                title="Unique Article",
                text="Content",
                company_key="test",
                company_name="Test",
                category="ai_llm",
                published="2026-01-15T00:00:00+00:00",
            )
        ]
        existing_urls: set[str] = set()
        unique, duplicates = check_duplicates(articles, existing_urls)

        assert len(unique) == 1
        assert len(duplicates) == 0

    def test_正常系_バッチ内重複も検出される(self) -> None:
        """Test that duplicates within the same batch are detected."""
        from scripts.prepare_ai_research_session import (
            ScrapedArticleData,
            check_duplicates,
        )

        articles = [
            ScrapedArticleData(
                url="https://example.com/same-article",
                title="Article 1",
                text="Content 1",
                company_key="test1",
                company_name="Test1",
                category="ai_llm",
                published="2026-01-15T00:00:00+00:00",
            ),
            ScrapedArticleData(
                url="https://example.com/same-article",
                title="Article 2",
                text="Content 2",
                company_key="test2",
                company_name="Test2",
                category="ai_llm",
                published="2026-01-16T00:00:00+00:00",
            ),
        ]
        existing_urls: set[str] = set()
        unique, duplicates = check_duplicates(articles, existing_urls)

        assert len(unique) == 1
        assert len(duplicates) == 1

    def test_エッジケース_空の記事リストで空結果(self) -> None:
        """Test empty article list."""
        from scripts.prepare_ai_research_session import check_duplicates

        unique, duplicates = check_duplicates([], set())
        assert unique == []
        assert duplicates == []


# ---------------------------------------------------------------------------
# Test: Top-N Selection
# ---------------------------------------------------------------------------


class TestTopNSelection:
    """Test Top-N article selection."""

    def test_正常系_新しい記事が優先される(self) -> None:
        """Test that newer articles are selected first."""
        from scripts.prepare_ai_research_session import (
            ScrapedArticleData,
            select_top_n,
        )

        articles = [
            ScrapedArticleData(
                url="https://example.com/old",
                title="Old",
                text="Old content",
                company_key="test",
                company_name="Test",
                category="ai_llm",
                published="2026-01-01T00:00:00+00:00",
            ),
            ScrapedArticleData(
                url="https://example.com/new",
                title="New",
                text="New content",
                company_key="test",
                company_name="Test",
                category="ai_llm",
                published="2026-01-15T00:00:00+00:00",
            ),
        ]

        selected = select_top_n(articles, 1)
        assert len(selected) == 1
        assert selected[0].title == "New"

    def test_正常系_全記事がTopN以下の場合全て返される(self) -> None:
        """Test when articles count is less than top_n."""
        from scripts.prepare_ai_research_session import (
            ScrapedArticleData,
            select_top_n,
        )

        articles = [
            ScrapedArticleData(
                url="https://example.com/1",
                title="Article 1",
                text="Content",
                company_key="test",
                company_name="Test",
                category="ai_llm",
                published="2026-01-15T00:00:00+00:00",
            ),
        ]

        selected = select_top_n(articles, 10)
        assert len(selected) == 1

    def test_正常系_TopNが0以下の場合全て返される(self) -> None:
        """Test that top_n <= 0 returns all articles."""
        from scripts.prepare_ai_research_session import (
            ScrapedArticleData,
            select_top_n,
        )

        articles = [
            ScrapedArticleData(
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                text="Content",
                company_key="test",
                company_name="Test",
                category="ai_llm",
                published=f"2026-01-{i + 1:02d}T00:00:00+00:00",
            )
            for i in range(5)
        ]

        selected = select_top_n(articles, 0)
        assert len(selected) == 5

    def test_エッジケース_空のリストで空結果(self) -> None:
        """Test empty article list."""
        from scripts.prepare_ai_research_session import select_top_n

        selected = select_top_n([], 10)
        assert selected == []


# ---------------------------------------------------------------------------
# Test: Article Conversion
# ---------------------------------------------------------------------------


class TestArticleConversion:
    """Test ScrapedArticle to ScrapedArticleData conversion."""

    def test_正常系_ScrapedArticleを変換できる(self) -> None:
        """Test converting ScrapedArticle to ScrapedArticleData."""
        from rss.services.company_scrapers.types import (
            CompanyConfig,
            InvestmentContext,
            ScrapedArticle,
        )
        from scripts.prepare_ai_research_session import convert_to_article_data

        config = CompanyConfig(
            key="openai",
            name="OpenAI",
            category="ai_llm",
            blog_url="https://openai.com/news/",
            investment_context=InvestmentContext(
                tickers=("MSFT",),
                sectors=("AI/LLM",),
                keywords=("ChatGPT",),
            ),
        )

        article = ScrapedArticle(
            url="https://openai.com/news/test-article",
            title="Test Article",
            text="Article body text...",
            source_type="blog",
            pdf=None,
            attached_pdfs=(),
        )

        result = convert_to_article_data(config, article)

        assert result.url == "https://openai.com/news/test-article"
        assert result.title == "Test Article"
        assert result.text == "Article body text..."
        assert result.company_key == "openai"
        assert result.company_name == "OpenAI"
        assert result.category == "ai_llm"
        assert result.source_type == "blog"
        assert result.published != ""  # Should have a timestamp

    def test_正常系_PDF記事も変換できる(self) -> None:
        """Test converting PDF article."""
        from rss.services.company_scrapers.types import CompanyConfig, ScrapedArticle
        from scripts.prepare_ai_research_session import convert_to_article_data

        config = CompanyConfig(
            key="nvidia",
            name="NVIDIA",
            category="gpu_chips",
            blog_url="https://blogs.nvidia.com/",
        )

        article = ScrapedArticle(
            url="https://blogs.nvidia.com/report.pdf",
            title="NVIDIA Report",
            text="[PDF: report.pdf]",
            source_type="press_release",
            pdf="https://blogs.nvidia.com/report.pdf",
            attached_pdfs=(),
        )

        result = convert_to_article_data(config, article)

        assert result.pdf_url == "https://blogs.nvidia.com/report.pdf"
        assert result.source_type == "press_release"


# ---------------------------------------------------------------------------
# Test: Batch Output
# ---------------------------------------------------------------------------


class TestBatchOutput:
    """Test category batch JSON output."""

    def test_正常系_カテゴリバッチファイルが作成される(self, tmp_path: Path) -> None:
        """Test writing category batch JSON file."""
        from scripts.prepare_ai_research_session import (
            ScrapedArticleData,
            write_category_batch,
        )

        articles = [
            ScrapedArticleData(
                url="https://openai.com/news/test",
                title="Test Article",
                text="Content",
                company_key="openai",
                company_name="OpenAI",
                category="ai_llm",
                published="2026-01-15T00:00:00+00:00",
            ),
        ]

        stats = {"total_scraped": 5, "duplicates": 2, "selected": 1}

        output_path = write_category_batch(
            category_key="ai_llm",
            articles=articles,
            stats=stats,
            output_dir=tmp_path,
        )

        assert output_path.exists()
        assert output_path.name == "ai_llm.json"

        with open(output_path) as f:
            data = json.load(f)

        assert data["category_key"] == "ai_llm"
        assert data["category_label"] == "AI/LLM開発"
        assert len(data["articles"]) == 1
        assert data["articles"][0]["url"] == "https://openai.com/news/test"
        assert data["stats"]["total_scraped"] == 5

    def test_正常系_空のカテゴリバッチも作成できる(self, tmp_path: Path) -> None:
        """Test writing empty category batch."""
        from scripts.prepare_ai_research_session import write_category_batch

        output_path = write_category_batch(
            category_key="networking",
            articles=[],
            stats={"total_scraped": 0, "duplicates": 0, "selected": 0},
            output_dir=tmp_path,
        )

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["category_key"] == "networking"
        assert len(data["articles"]) == 0


# ---------------------------------------------------------------------------
# Test: Structure Change Report
# ---------------------------------------------------------------------------


class TestStructureChangeReport:
    """Test structure change report generation."""

    def test_正常系_構造変更レポートが生成される(self, tmp_path: Path) -> None:
        """Test writing structure change report."""
        from scripts.prepare_ai_research_session import (
            StructureChangeReport,
            write_structure_change_report,
        )

        report = StructureChangeReport(
            timestamp="2026-01-15T00:00:00+00:00",
            entries=[],
            summary={
                "healthy": 5,
                "partial_change": 1,
                "major_change": 0,
                "complete_change": 0,
            },
        )

        output_path = write_structure_change_report(report, tmp_path)
        assert output_path.exists()
        assert output_path.name == "_structure_report.json"


# ---------------------------------------------------------------------------
# Test: Scraping Stats Report
# ---------------------------------------------------------------------------


class TestScrapingStatsReport:
    """Test scraping statistics report generation."""

    def test_正常系_スクレイピング統計レポートが生成される(
        self, tmp_path: Path
    ) -> None:
        """Test writing scraping stats report."""
        from scripts.prepare_ai_research_session import (
            CompanyScrapeStats,
            ScrapingStatsReport,
            write_scraping_stats_report,
        )

        report = ScrapingStatsReport(
            timestamp="2026-01-15T00:00:00+00:00",
            total_companies=77,
            total_articles=150,
            categories_processed=10,
            company_stats=[
                CompanyScrapeStats(
                    company_key="openai",
                    company_name="OpenAI",
                    articles_found=5,
                    validation_status="valid",
                    duration_seconds=3.5,
                ),
            ],
            category_summary={
                "ai_llm": {"companies": 11, "articles": 25, "failures": 1},
            },
        )

        output_path = write_scraping_stats_report(report, tmp_path)
        assert output_path.exists()
        assert output_path.name == "_scraping_stats.json"

        with open(output_path) as f:
            data = json.load(f)

        assert data["total_companies"] == 77
        assert data["total_articles"] == 150
        assert len(data["company_stats"]) == 1
        assert data["company_stats"][0]["company_key"] == "openai"


# ---------------------------------------------------------------------------
# Test: Pydantic Models
# ---------------------------------------------------------------------------


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_正常系_ScrapedArticleDataモデルが作成できる(self) -> None:
        """Test ScrapedArticleData model creation."""
        from scripts.prepare_ai_research_session import ScrapedArticleData

        article = ScrapedArticleData(
            url="https://example.com/article",
            title="Test Article",
            text="Content here",
            company_key="test_co",
            company_name="Test Company",
            category="ai_llm",
        )

        assert article.url == "https://example.com/article"
        assert article.source_type == "blog"  # Default
        assert article.pdf_url is None  # Default
        assert article.published == ""  # Default

    def test_正常系_CategoryBatchモデルが作成できる(self) -> None:
        """Test CategoryBatch model creation."""
        from scripts.prepare_ai_research_session import CategoryBatch

        batch = CategoryBatch(
            category_key="ai_llm",
            category_label="AI/LLM開発",
            timestamp="2026-01-15T00:00:00+00:00",
        )

        assert batch.category_key == "ai_llm"
        assert batch.articles == []
        assert batch.stats == {}

    def test_正常系_CompanyScrapeStatsモデルが作成できる(self) -> None:
        """Test CompanyScrapeStats model creation."""
        from scripts.prepare_ai_research_session import CompanyScrapeStats

        stat = CompanyScrapeStats(
            company_key="openai",
            company_name="OpenAI",
            articles_found=5,
            validation_status="valid",
            duration_seconds=2.5,
        )

        assert stat.company_key == "openai"
        assert stat.error is None

    def test_正常系_StructureChangeEntryモデルが作成できる(self) -> None:
        """Test StructureChangeEntry model creation."""
        from scripts.prepare_ai_research_session import StructureChangeEntry

        entry = StructureChangeEntry(
            company_key="openai",
            company_name="OpenAI",
            hit_rate=0.95,
            article_list_hits=10,
            title_found_count=10,
            date_found_count=9,
            blog_url="https://openai.com/news/",
            status="healthy",
        )

        assert entry.hit_rate == 0.95
        assert entry.status == "healthy"


# ---------------------------------------------------------------------------
# Test: Category Labels
# ---------------------------------------------------------------------------


class TestCategoryLabels:
    """Test category label mapping."""

    def test_正常系_全カテゴリにラベルがある(self) -> None:
        """Test that all categories have Japanese labels."""
        from scripts.prepare_ai_research_session import (
            CATEGORY_CONFIGS,
            CATEGORY_LABELS,
        )

        for key in CATEGORY_CONFIGS:
            assert key in CATEGORY_LABELS, f"Missing label for category: {key}"
            assert len(CATEGORY_LABELS[key]) > 0

    def test_正常系_ラベル数とカテゴリ数が一致(self) -> None:
        """Test that label count matches category count."""
        from scripts.prepare_ai_research_session import (
            CATEGORY_CONFIGS,
            CATEGORY_LABELS,
        )

        assert len(CATEGORY_LABELS) == len(CATEGORY_CONFIGS)
