"""embedding.types モジュールの単体テスト.

テストTODOリスト:
- [x] ArticleRecord 必須フィールドのみで作成できること
- [x] ArticleRecord 全フィールドで作成できること
- [x] ArticleRecord デフォルト値が正しいこと
- [x] PipelineConfig デフォルト値で作成できること
- [x] PipelineConfig カスタム値で作成できること
- [x] PipelineConfig sources が None でデフォルト設定
- [x] ExtractionResult 必須フィールドで作成できること
- [x] ExtractionResult error デフォルト値が空文字であること
- [x] ExtractionResult error フィールドを設定できること
"""

from pathlib import Path

import pytest

from embedding.types import ArticleRecord, ExtractionResult, PipelineConfig


class TestArticleRecord:
    """ArticleRecord データクラスのテスト."""

    def test_正常系_必須フィールドのみで作成できる(self) -> None:
        """url と title のみで ArticleRecord を作成できることを確認。"""
        record = ArticleRecord(
            url="https://example.com/article/1",
            title="Test Article",
        )

        assert record.url == "https://example.com/article/1"
        assert record.title == "Test Article"

    def test_正常系_全フィールドで作成できる(self) -> None:
        """全フィールドを指定して ArticleRecord を作成できることを確認。"""
        record = ArticleRecord(
            url="https://example.com/article/1",
            title="Full Article",
            published="2024-01-15T10:00:00+00:00",
            summary="Article summary",
            category="technology",
            source="cnbc",
            ticker="AAPL",
            author="John Doe",
            article_id="article-001",
            content="Full content here",
            extraction_method="trafilatura",
            extracted_at="2024-01-15T10:05:00+00:00",
            json_file="/data/raw/news/cnbc/2024-01-15.json",
        )

        assert record.url == "https://example.com/article/1"
        assert record.title == "Full Article"
        assert record.published == "2024-01-15T10:00:00+00:00"
        assert record.summary == "Article summary"
        assert record.category == "technology"
        assert record.source == "cnbc"
        assert record.ticker == "AAPL"
        assert record.author == "John Doe"
        assert record.article_id == "article-001"
        assert record.content == "Full content here"
        assert record.extraction_method == "trafilatura"
        assert record.extracted_at == "2024-01-15T10:05:00+00:00"
        assert record.json_file == "/data/raw/news/cnbc/2024-01-15.json"

    def test_正常系_オプションフィールドのデフォルト値が空文字(self) -> None:
        """オプションフィールドのデフォルト値が空文字であることを確認。"""
        record = ArticleRecord(
            url="https://example.com/article/1",
            title="Test Article",
        )

        assert record.published == ""
        assert record.summary == ""
        assert record.category == ""
        assert record.source == ""
        assert record.ticker == ""
        assert record.author == ""
        assert record.article_id == ""
        assert record.content == ""
        assert record.extraction_method == ""
        assert record.extracted_at == ""
        assert record.json_file == ""

    def test_正常系_13フィールドが定義されている(self) -> None:
        """ArticleRecord が 13 フィールドを持つことを確認。"""
        record = ArticleRecord(url="https://example.com", title="Title")
        fields = list(record.__dataclass_fields__.keys())
        assert len(fields) == 13

    def test_正常系_urlによる等値比較ができる(self) -> None:
        """同じ値を持つ ArticleRecord が等しいことを確認。"""
        record1 = ArticleRecord(url="https://example.com", title="Article")
        record2 = ArticleRecord(url="https://example.com", title="Article")
        assert record1 == record2

    def test_正常系_異なるurlで等値比較が失敗する(self) -> None:
        """異なる URL を持つ ArticleRecord が等しくないことを確認。"""
        record1 = ArticleRecord(url="https://example.com/1", title="Article")
        record2 = ArticleRecord(url="https://example.com/2", title="Article")
        assert record1 != record2


class TestPipelineConfig:
    """PipelineConfig データクラスのテスト."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """デフォルト値で PipelineConfig を作成できることを確認。"""
        config = PipelineConfig()

        assert config.news_dir == Path("data/raw/news")
        assert config.chromadb_path == Path("data/chromadb")
        assert config.collection_name == "gemini-embedding-001"
        assert config.dummy_dim == 768
        assert config.max_concurrency == 3
        assert config.delay == 1.5
        assert config.timeout == 30
        assert config.use_playwright_fallback is True
        assert config.sources is None

    def test_正常系_カスタム値で作成できる(self) -> None:
        """カスタム値で PipelineConfig を作成できることを確認。"""
        config = PipelineConfig(
            news_dir=Path("/custom/news"),
            chromadb_path=Path("/custom/chromadb"),
            collection_name="custom-model",
            dummy_dim=1536,
            max_concurrency=5,
            delay=0.5,
            timeout=60,
            use_playwright_fallback=False,
            sources=["cnbc", "nasdaq"],
        )

        assert config.news_dir == Path("/custom/news")
        assert config.chromadb_path == Path("/custom/chromadb")
        assert config.collection_name == "custom-model"
        assert config.dummy_dim == 1536
        assert config.max_concurrency == 5
        assert config.delay == 0.5
        assert config.timeout == 60
        assert config.use_playwright_fallback is False
        assert config.sources == ["cnbc", "nasdaq"]

    def test_正常系_デフォルトのnews_dirはPathオブジェクト(self) -> None:
        """news_dir が Path オブジェクトであることを確認。"""
        config = PipelineConfig()
        assert isinstance(config.news_dir, Path)

    def test_正常系_sourcesにNoneを設定できる(self) -> None:
        """sources に None を明示的に設定できることを確認。"""
        config = PipelineConfig(sources=None)
        assert config.sources is None

    def test_正常系_sourcesに空リストを設定できる(self) -> None:
        """sources に空リストを設定できることを確認。"""
        config = PipelineConfig(sources=[])
        assert config.sources == []

    def test_正常系_10フィールドが定義されている(self) -> None:
        """PipelineConfig が 9 フィールドを持つことを確認。"""
        config = PipelineConfig()
        fields = list(config.__dataclass_fields__.keys())
        assert len(fields) == 9


class TestExtractionResult:
    """ExtractionResult データクラスのテスト."""

    def test_正常系_必須フィールドで作成できる(self) -> None:
        """必須フィールドのみで ExtractionResult を作成できることを確認。"""
        result = ExtractionResult(
            url="https://example.com/article/1",
            content="Extracted content",
            method="trafilatura",
            extracted_at="2024-01-15T10:05:00+00:00",
        )

        assert result.url == "https://example.com/article/1"
        assert result.content == "Extracted content"
        assert result.method == "trafilatura"
        assert result.extracted_at == "2024-01-15T10:05:00+00:00"

    def test_正常系_errorのデフォルト値が空文字(self) -> None:
        """error フィールドのデフォルト値が空文字であることを確認。"""
        result = ExtractionResult(
            url="https://example.com",
            content="content",
            method="trafilatura",
            extracted_at="2024-01-15T10:05:00+00:00",
        )
        assert result.error == ""

    def test_正常系_errorフィールドを設定できる(self) -> None:
        """error フィールドに値を設定できることを確認。"""
        result = ExtractionResult(
            url="https://example.com",
            content="",
            method="failed",
            extracted_at="2024-01-15T10:05:00+00:00",
            error="Connection timeout",
        )
        assert result.error == "Connection timeout"

    def test_正常系_playwright方法で作成できる(self) -> None:
        """method が 'playwright' の ExtractionResult を作成できることを確認。"""
        result = ExtractionResult(
            url="https://example.com",
            content="JS rendered content",
            method="playwright",
            extracted_at="2024-01-15T10:05:00+00:00",
        )
        assert result.method == "playwright"

    def test_正常系_failed方法で作成できる(self) -> None:
        """method が 'failed' の ExtractionResult を作成できることを確認。"""
        result = ExtractionResult(
            url="https://example.com",
            content="",
            method="failed",
            extracted_at="2024-01-15T10:05:00+00:00",
            error="All methods failed",
        )
        assert result.method == "failed"
        assert result.content == ""

    def test_正常系_5フィールドが定義されている(self) -> None:
        """ExtractionResult が 5 フィールドを持つことを確認。"""
        result = ExtractionResult(
            url="https://example.com",
            content="",
            method="failed",
            extracted_at="2024-01-15T10:05:00",
        )
        fields = list(result.__dataclass_fields__.keys())
        assert len(fields) == 5
