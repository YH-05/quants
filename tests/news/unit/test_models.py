"""Unit tests for news/models.py - SourceType, ArticleSource, CollectedArticle models.

Tests follow t-wada TDD naming conventions with Japanese test names.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


class TestSourceType:
    """SourceType StrEnum のテストクラス."""

    def test_正常系_RSS値が定義されている(self) -> None:
        """SourceType.RSS が "rss" 値で定義されていること."""
        from news.models import SourceType

        assert SourceType.RSS == "rss"
        assert SourceType.RSS.value == "rss"

    def test_正常系_YFINANCE値が定義されている(self) -> None:
        """SourceType.YFINANCE が "yfinance" 値で定義されていること."""
        from news.models import SourceType

        assert SourceType.YFINANCE == "yfinance"
        assert SourceType.YFINANCE.value == "yfinance"

    def test_正常系_SCRAPE値が定義されている(self) -> None:
        """SourceType.SCRAPE が "scrape" 値で定義されていること."""
        from news.models import SourceType

        assert SourceType.SCRAPE == "scrape"
        assert SourceType.SCRAPE.value == "scrape"

    def test_正常系_全3種類の値が存在する(self) -> None:
        """SourceType は RSS, YFINANCE, SCRAPE の3種類のみ."""
        from news.models import SourceType

        members = list(SourceType)
        assert len(members) == 3
        assert SourceType.RSS in members
        assert SourceType.YFINANCE in members
        assert SourceType.SCRAPE in members

    def test_正常系_StrEnumなので文字列として比較可能(self) -> None:
        """SourceType は StrEnum なので文字列との比較が可能."""
        from news.models import SourceType

        assert SourceType.RSS == "rss"
        assert SourceType.YFINANCE == "yfinance"
        assert SourceType.SCRAPE == "scrape"


class TestArticleSource:
    """ArticleSource Pydantic モデルのテストクラス."""

    def test_正常系_必須フィールドで作成できる(self) -> None:
        """source_type, source_name, category で ArticleSource を作成できる."""
        from news.models import ArticleSource, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )

        assert source.source_type == SourceType.RSS
        assert source.source_name == "CNBC Markets"
        assert source.category == "market"
        assert source.feed_id is None

    def test_正常系_feed_idを指定して作成できる(self) -> None:
        """feed_id を指定して ArticleSource を作成できる."""
        from news.models import ArticleSource, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
            feed_id="cnbc-markets-001",
        )

        assert source.feed_id == "cnbc-markets-001"

    def test_正常系_YFINANCEソースで作成できる(self) -> None:
        """SourceType.YFINANCE で ArticleSource を作成できる."""
        from news.models import ArticleSource, SourceType

        source = ArticleSource(
            source_type=SourceType.YFINANCE,
            source_name="NVDA",
            category="yf_ai_stock",
        )

        assert source.source_type == SourceType.YFINANCE
        assert source.source_name == "NVDA"
        assert source.category == "yf_ai_stock"

    def test_正常系_SCRAPEソースで作成できる(self) -> None:
        """SourceType.SCRAPE で ArticleSource を作成できる."""
        from news.models import ArticleSource, SourceType

        source = ArticleSource(
            source_type=SourceType.SCRAPE,
            source_name="Custom Scraper",
            category="tech",
        )

        assert source.source_type == SourceType.SCRAPE
        assert source.source_name == "Custom Scraper"
        assert source.category == "tech"

    def test_異常系_source_typeが必須(self) -> None:
        """source_type がない場合は ValidationError."""
        from news.models import ArticleSource

        with pytest.raises(ValidationError) as exc_info:
            ArticleSource(
                source_name="CNBC Markets",
                category="market",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_type",) for e in errors)

    def test_異常系_source_nameが必須(self) -> None:
        """source_name がない場合は ValidationError."""
        from news.models import ArticleSource, SourceType

        with pytest.raises(ValidationError) as exc_info:
            ArticleSource(
                source_type=SourceType.RSS,
                category="market",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_name",) for e in errors)

    def test_異常系_categoryが必須(self) -> None:
        """category がない場合は ValidationError."""
        from news.models import ArticleSource, SourceType

        with pytest.raises(ValidationError) as exc_info:
            ArticleSource(
                source_type=SourceType.RSS,
                source_name="CNBC Markets",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("category",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """ArticleSource は model_dump() で dict に変換可能."""
        from news.models import ArticleSource, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
            feed_id="cnbc-001",
        )

        data = source.model_dump()

        assert data["source_type"] == SourceType.RSS
        assert data["source_name"] == "CNBC Markets"
        assert data["category"] == "market"
        assert data["feed_id"] == "cnbc-001"

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から ArticleSource を作成可能."""
        from news.models import ArticleSource, SourceType

        data = {
            "source_type": "rss",
            "source_name": "CNBC Markets",
            "category": "market",
        }

        source = ArticleSource.model_validate(data)

        assert source.source_type == SourceType.RSS
        assert source.source_name == "CNBC Markets"
        assert source.category == "market"

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """ArticleSource は JSON シリアライズ可能."""
        from news.models import ArticleSource, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )

        json_str = source.model_dump_json()

        assert '"source_type":"rss"' in json_str
        assert '"source_name":"CNBC Markets"' in json_str
        assert '"category":"market"' in json_str


class TestCollectedArticle:
    """CollectedArticle Pydantic モデルのテストクラス."""

    def test_正常系_必須フィールドで作成できる(self) -> None:
        """url, title, source, collected_at で CollectedArticle を作成できる."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime.now(tz=timezone.utc)

        article = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=collected_at,
        )

        assert str(article.url) == "https://www.cnbc.com/article/123"
        assert article.title == "Sample Article"
        assert article.source == source
        assert article.collected_at == collected_at
        assert article.published is None
        assert article.raw_summary is None

    def test_正常系_オプションフィールドを指定して作成できる(self) -> None:
        """published, raw_summary を指定して CollectedArticle を作成できる."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        published = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        collected_at = datetime.now(tz=timezone.utc)

        article = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            published=published,
            raw_summary="This is the RSS summary of the article.",
            source=source,
            collected_at=collected_at,
        )

        assert article.published == published
        assert article.raw_summary == "This is the RSS summary of the article."

    def test_正常系_YFINANCEソースで作成できる(self) -> None:
        """yfinance ソースの記事を作成できる."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.YFINANCE,
            source_name="NVDA",
            category="yf_ai_stock",
        )
        collected_at = datetime.now(tz=timezone.utc)

        article = CollectedArticle(
            url="https://finance.yahoo.com/news/nvda-article",  # type: ignore[arg-type]
            title="NVDA Q4 Earnings",
            source=source,
            collected_at=collected_at,
        )

        assert article.source.source_type == SourceType.YFINANCE
        assert article.source.source_name == "NVDA"

    def test_異常系_urlが必須(self) -> None:
        """url がない場合は ValidationError."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            CollectedArticle(
                title="Sample Article",
                source=source,
                collected_at=collected_at,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_異常系_titleが必須(self) -> None:
        """title がない場合は ValidationError."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            CollectedArticle(
                url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
                source=source,
                collected_at=collected_at,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_異常系_sourceが必須(self) -> None:
        """source がない場合は ValidationError."""
        from news.models import CollectedArticle

        collected_at = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            CollectedArticle(
                url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
                title="Sample Article",
                collected_at=collected_at,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_異常系_collected_atが必須(self) -> None:
        """collected_at がない場合は ValidationError."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )

        with pytest.raises(ValidationError) as exc_info:
            CollectedArticle(
                url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
                title="Sample Article",
                source=source,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("collected_at",) for e in errors)

    def test_異常系_不正なURLでValidationError(self) -> None:
        """不正なURL形式では ValidationError."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            CollectedArticle(
                url="not-a-valid-url",  # type: ignore[arg-type]
                title="Sample Article",
                source=source,
                collected_at=collected_at,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """CollectedArticle は model_dump() で dict に変換可能."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        article = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            raw_summary="Summary text",
            source=source,
            collected_at=collected_at,
        )

        data = article.model_dump()

        assert str(data["url"]) == "https://www.cnbc.com/article/123"
        assert data["title"] == "Sample Article"
        assert data["raw_summary"] == "Summary text"
        assert data["published"] is None
        assert data["source"]["source_type"] == SourceType.RSS
        assert data["collected_at"] == collected_at

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から CollectedArticle を作成可能."""
        from news.models import CollectedArticle, SourceType

        data = {
            "url": "https://www.cnbc.com/article/123",
            "title": "Sample Article",
            "published": "2025-01-15T10:30:00Z",
            "raw_summary": "Summary text",
            "source": {
                "source_type": "rss",
                "source_name": "CNBC Markets",
                "category": "market",
            },
            "collected_at": "2025-01-15T12:00:00Z",
        }

        article = CollectedArticle.model_validate(data)

        assert str(article.url) == "https://www.cnbc.com/article/123"
        assert article.title == "Sample Article"
        assert article.source.source_type == SourceType.RSS
        assert article.published is not None
        assert article.raw_summary == "Summary text"

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """CollectedArticle は JSON シリアライズ可能."""
        from news.models import ArticleSource, CollectedArticle, SourceType

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        article = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=collected_at,
        )

        json_str = article.model_dump_json()

        assert "https://www.cnbc.com/article/123" in json_str
        assert '"title":"Sample Article"' in json_str
        assert '"source_type":"rss"' in json_str


class TestExtractionStatus:
    """ExtractionStatus StrEnum のテストクラス."""

    def test_正常系_SUCCESS値が定義されている(self) -> None:
        """ExtractionStatus.SUCCESS が "success" 値で定義されていること."""
        from news.models import ExtractionStatus

        assert ExtractionStatus.SUCCESS == "success"
        assert ExtractionStatus.SUCCESS.value == "success"

    def test_正常系_FAILED値が定義されている(self) -> None:
        """ExtractionStatus.FAILED が "failed" 値で定義されていること."""
        from news.models import ExtractionStatus

        assert ExtractionStatus.FAILED == "failed"
        assert ExtractionStatus.FAILED.value == "failed"

    def test_正常系_PAYWALL値が定義されている(self) -> None:
        """ExtractionStatus.PAYWALL が "paywall" 値で定義されていること."""
        from news.models import ExtractionStatus

        assert ExtractionStatus.PAYWALL == "paywall"
        assert ExtractionStatus.PAYWALL.value == "paywall"

    def test_正常系_TIMEOUT値が定義されている(self) -> None:
        """ExtractionStatus.TIMEOUT が "timeout" 値で定義されていること."""
        from news.models import ExtractionStatus

        assert ExtractionStatus.TIMEOUT == "timeout"
        assert ExtractionStatus.TIMEOUT.value == "timeout"

    def test_正常系_全4種類の値が存在する(self) -> None:
        """ExtractionStatus は SUCCESS, FAILED, PAYWALL, TIMEOUT の4種類のみ."""
        from news.models import ExtractionStatus

        members = list(ExtractionStatus)
        assert len(members) == 4
        assert ExtractionStatus.SUCCESS in members
        assert ExtractionStatus.FAILED in members
        assert ExtractionStatus.PAYWALL in members
        assert ExtractionStatus.TIMEOUT in members

    def test_正常系_StrEnumなので文字列として比較可能(self) -> None:
        """ExtractionStatus は StrEnum なので文字列との比較が可能."""
        from news.models import ExtractionStatus

        assert ExtractionStatus.SUCCESS == "success"
        assert ExtractionStatus.FAILED == "failed"
        assert ExtractionStatus.PAYWALL == "paywall"
        assert ExtractionStatus.TIMEOUT == "timeout"


class TestExtractedArticle:
    """ExtractedArticle Pydantic モデルのテストクラス."""

    def test_正常系_必須フィールドで作成できる(self) -> None:
        """collected, body_text, extraction_status, extraction_method で作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text="This is the article body content.",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        assert extracted.collected == collected
        assert extracted.body_text == "This is the article body content."
        assert extracted.extraction_status == ExtractionStatus.SUCCESS
        assert extracted.extraction_method == "trafilatura"
        assert extracted.error_message is None

    def test_正常系_error_messageを指定して作成できる(self) -> None:
        """error_message を指定して ExtractedArticle を作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text=None,
            extraction_status=ExtractionStatus.FAILED,
            extraction_method="trafilatura",
            error_message="Failed to extract content",
        )

        assert extracted.error_message == "Failed to extract content"
        assert extracted.body_text is None
        assert extracted.extraction_status == ExtractionStatus.FAILED

    def test_正常系_PAYWALL状態で作成できる(self) -> None:
        """ペイウォール検出時の ExtractedArticle を作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="WSJ",
            category="finance",
        )
        collected = CollectedArticle(
            url="https://www.wsj.com/article/123",  # type: ignore[arg-type]
            title="Premium Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text=None,
            extraction_status=ExtractionStatus.PAYWALL,
            extraction_method="trafilatura",
            error_message="Paywall detected",
        )

        assert extracted.extraction_status == ExtractionStatus.PAYWALL
        assert extracted.body_text is None

    def test_正常系_TIMEOUT状態で作成できる(self) -> None:
        """タイムアウト時の ExtractedArticle を作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="Slow Site",
            category="tech",
        )
        collected = CollectedArticle(
            url="https://slow.example.com/article",  # type: ignore[arg-type]
            title="Slow Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text=None,
            extraction_status=ExtractionStatus.TIMEOUT,
            extraction_method="trafilatura",
            error_message="Request timed out after 30s",
        )

        assert extracted.extraction_status == ExtractionStatus.TIMEOUT
        assert extracted.body_text is None

    def test_正常系_fallback抽出方法で作成できる(self) -> None:
        """fallback 抽出方法の ExtractedArticle を作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text="Fallback extracted content.",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="fallback",
        )

        assert extracted.extraction_method == "fallback"

    def test_異常系_collectedが必須(self) -> None:
        """collected がない場合は ValidationError."""
        from news.models import ExtractedArticle, ExtractionStatus

        with pytest.raises(ValidationError) as exc_info:
            ExtractedArticle(
                body_text="Some content",
                extraction_status=ExtractionStatus.SUCCESS,
                extraction_method="trafilatura",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("collected",) for e in errors)

    def test_異常系_extraction_statusが必須(self) -> None:
        """extraction_status がない場合は ValidationError."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ValidationError) as exc_info:
            ExtractedArticle(
                collected=collected,
                body_text="Some content",
                extraction_method="trafilatura",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_status",) for e in errors)

    def test_異常系_extraction_methodが必須(self) -> None:
        """extraction_method がない場合は ValidationError."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ValidationError) as exc_info:
            ExtractedArticle(
                collected=collected,
                body_text="Some content",
                extraction_status=ExtractionStatus.SUCCESS,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_method",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """ExtractedArticle は model_dump() で dict に変換可能."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=collected_at,
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text="Article body content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        data = extracted.model_dump()

        assert data["body_text"] == "Article body content"
        assert data["extraction_status"] == ExtractionStatus.SUCCESS
        assert data["extraction_method"] == "trafilatura"
        assert data["error_message"] is None
        assert data["collected"]["title"] == "Sample Article"

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から ExtractedArticle を作成可能."""
        from news.models import ExtractedArticle, ExtractionStatus, SourceType

        data = {
            "collected": {
                "url": "https://www.cnbc.com/article/123",
                "title": "Sample Article",
                "source": {
                    "source_type": "rss",
                    "source_name": "CNBC Markets",
                    "category": "market",
                },
                "collected_at": "2025-01-15T12:00:00Z",
            },
            "body_text": "Article body content",
            "extraction_status": "success",
            "extraction_method": "trafilatura",
        }

        extracted = ExtractedArticle.model_validate(data)

        assert extracted.body_text == "Article body content"
        assert extracted.extraction_status == ExtractionStatus.SUCCESS
        assert extracted.extraction_method == "trafilatura"
        assert extracted.collected.title == "Sample Article"
        assert extracted.collected.source.source_type == SourceType.RSS

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """ExtractedArticle は JSON シリアライズ可能."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Sample Article",
            source=source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text="Article body content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        json_str = extracted.model_dump_json()

        assert '"body_text":"Article body content"' in json_str
        assert '"extraction_status":"success"' in json_str
        assert '"extraction_method":"trafilatura"' in json_str
        assert "https://www.cnbc.com/article/123" in json_str

    def test_正常系_CollectedArticleと関連が正しい(self) -> None:
        """ExtractedArticle から CollectedArticle の全プロパティにアクセスできる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
        )

        source = ArticleSource(
            source_type=SourceType.YFINANCE,
            source_name="NVDA",
            category="yf_ai_stock",
        )
        published = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        collected = CollectedArticle(
            url="https://finance.yahoo.com/news/nvda",  # type: ignore[arg-type]
            title="NVDA Earnings Report",
            published=published,
            raw_summary="NVDA reports quarterly earnings",
            source=source,
            collected_at=collected_at,
        )

        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article body about NVDA earnings...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        # CollectedArticle の全プロパティにアクセス可能
        assert str(extracted.collected.url) == "https://finance.yahoo.com/news/nvda"
        assert extracted.collected.title == "NVDA Earnings Report"
        assert extracted.collected.published == published
        assert extracted.collected.raw_summary == "NVDA reports quarterly earnings"
        assert extracted.collected.source.source_type == SourceType.YFINANCE
        assert extracted.collected.source.source_name == "NVDA"
        assert extracted.collected.collected_at == collected_at


class TestSummarizationStatus:
    """SummarizationStatus StrEnum のテストクラス."""

    def test_正常系_SUCCESS値が定義されている(self) -> None:
        """SummarizationStatus.SUCCESS が "success" 値で定義されていること."""
        from news.models import SummarizationStatus

        assert SummarizationStatus.SUCCESS == "success"
        assert SummarizationStatus.SUCCESS.value == "success"

    def test_正常系_FAILED値が定義されている(self) -> None:
        """SummarizationStatus.FAILED が "failed" 値で定義されていること."""
        from news.models import SummarizationStatus

        assert SummarizationStatus.FAILED == "failed"
        assert SummarizationStatus.FAILED.value == "failed"

    def test_正常系_TIMEOUT値が定義されている(self) -> None:
        """SummarizationStatus.TIMEOUT が "timeout" 値で定義されていること."""
        from news.models import SummarizationStatus

        assert SummarizationStatus.TIMEOUT == "timeout"
        assert SummarizationStatus.TIMEOUT.value == "timeout"

    def test_正常系_SKIPPED値が定義されている(self) -> None:
        """SummarizationStatus.SKIPPED が "skipped" 値で定義されていること."""
        from news.models import SummarizationStatus

        assert SummarizationStatus.SKIPPED == "skipped"
        assert SummarizationStatus.SKIPPED.value == "skipped"

    def test_正常系_全4種類の値が存在する(self) -> None:
        """SummarizationStatus は SUCCESS, FAILED, TIMEOUT, SKIPPED の4種類のみ."""
        from news.models import SummarizationStatus

        members = list(SummarizationStatus)
        assert len(members) == 4
        assert SummarizationStatus.SUCCESS in members
        assert SummarizationStatus.FAILED in members
        assert SummarizationStatus.TIMEOUT in members
        assert SummarizationStatus.SKIPPED in members

    def test_正常系_StrEnumなので文字列として比較可能(self) -> None:
        """SummarizationStatus は StrEnum なので文字列との比較が可能."""
        from news.models import SummarizationStatus

        assert SummarizationStatus.SUCCESS == "success"
        assert SummarizationStatus.FAILED == "failed"
        assert SummarizationStatus.TIMEOUT == "timeout"
        assert SummarizationStatus.SKIPPED == "skipped"


class TestStructuredSummary:
    """StructuredSummary Pydantic モデルのテストクラス."""

    def test_正常系_必須フィールドで作成できる(self) -> None:
        """overview, key_points, market_impact で StructuredSummary を作成できる."""
        from news.models import StructuredSummary

        summary = StructuredSummary(
            overview="米国株式市場は上昇基調を継続",
            key_points=["S&P500が最高値更新", "ナスダック続伸"],
            market_impact="投資家心理は楽観的",
        )

        assert summary.overview == "米国株式市場は上昇基調を継続"
        assert summary.key_points == ["S&P500が最高値更新", "ナスダック続伸"]
        assert summary.market_impact == "投資家心理は楽観的"
        assert summary.related_info is None

    def test_正常系_related_infoを指定して作成できる(self) -> None:
        """related_info を指定して StructuredSummary を作成できる."""
        from news.models import StructuredSummary

        summary = StructuredSummary(
            overview="FRBが金利を据え置き",
            key_points=["インフレ目標2%に近づく", "次回会合で利下げ示唆"],
            market_impact="債券市場に影響",
            related_info="FOMCは2024年中に3回の利下げを予想",
        )

        assert summary.related_info == "FOMCは2024年中に3回の利下げを予想"

    def test_正常系_key_pointsが空リストでも作成できる(self) -> None:
        """key_points が空リストでも StructuredSummary を作成できる."""
        from news.models import StructuredSummary

        summary = StructuredSummary(
            overview="概要のみの記事",
            key_points=[],
            market_impact="特になし",
        )

        assert summary.key_points == []

    def test_異常系_overviewが必須(self) -> None:
        """overview がない場合は ValidationError."""
        from news.models import StructuredSummary

        with pytest.raises(ValidationError) as exc_info:
            StructuredSummary(
                key_points=["ポイント1"],
                market_impact="影響",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("overview",) for e in errors)

    def test_異常系_key_pointsが必須(self) -> None:
        """key_points がない場合は ValidationError."""
        from news.models import StructuredSummary

        with pytest.raises(ValidationError) as exc_info:
            StructuredSummary(
                overview="概要",
                market_impact="影響",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("key_points",) for e in errors)

    def test_異常系_market_impactが必須(self) -> None:
        """market_impact がない場合は ValidationError."""
        from news.models import StructuredSummary

        with pytest.raises(ValidationError) as exc_info:
            StructuredSummary(
                overview="概要",
                key_points=["ポイント"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("market_impact",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """StructuredSummary は model_dump() で dict に変換可能."""
        from news.models import StructuredSummary

        summary = StructuredSummary(
            overview="概要テキスト",
            key_points=["ポイント1", "ポイント2"],
            market_impact="市場影響",
            related_info="関連情報",
        )

        data = summary.model_dump()

        assert data["overview"] == "概要テキスト"
        assert data["key_points"] == ["ポイント1", "ポイント2"]
        assert data["market_impact"] == "市場影響"
        assert data["related_info"] == "関連情報"

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から StructuredSummary を作成可能."""
        from news.models import StructuredSummary

        data = {
            "overview": "概要",
            "key_points": ["ポイント1", "ポイント2", "ポイント3"],
            "market_impact": "影響",
        }

        summary = StructuredSummary.model_validate(data)

        assert summary.overview == "概要"
        assert len(summary.key_points) == 3
        assert summary.market_impact == "影響"
        assert summary.related_info is None

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """StructuredSummary は JSON シリアライズ可能."""
        from news.models import StructuredSummary

        summary = StructuredSummary(
            overview="概要テキスト",
            key_points=["ポイント1"],
            market_impact="市場影響",
        )

        json_str = summary.model_dump_json()

        assert "概要テキスト" in json_str
        assert "ポイント1" in json_str
        assert "市場影響" in json_str


class TestSummarizedArticle:
    """SummarizedArticle Pydantic モデルのテストクラス."""

    def test_正常系_要約成功時のモデルを作成できる(self) -> None:
        """summarization_status が SUCCESS のとき正常に作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="米国株式市場が上昇",
            key_points=["S&P500上昇", "テック株が牽引"],
            market_impact="投資家心理改善",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        assert summarized.extracted == extracted
        assert summarized.summary == summary
        assert summarized.summarization_status == SummarizationStatus.SUCCESS
        assert summarized.error_message is None

    def test_正常系_要約失敗時のモデルを作成できる(self) -> None:
        """summarization_status が FAILED のとき正常に作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=None,
            summarization_status=SummarizationStatus.FAILED,
            error_message="API rate limit exceeded",
        )

        assert summarized.summary is None
        assert summarized.summarization_status == SummarizationStatus.FAILED
        assert summarized.error_message == "API rate limit exceeded"

    def test_正常系_タイムアウト時のモデルを作成できる(self) -> None:
        """summarization_status が TIMEOUT のとき正常に作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=None,
            summarization_status=SummarizationStatus.TIMEOUT,
            error_message="Request timed out after 60s",
        )

        assert summarized.summarization_status == SummarizationStatus.TIMEOUT
        assert summarized.error_message == "Request timed out after 60s"

    def test_正常系_本文抽出失敗でスキップ時のモデルを作成できる(self) -> None:
        """summarization_status が SKIPPED のとき正常に作成できる（本文抽出失敗時）."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="WSJ",
            category="finance",
        )
        collected = CollectedArticle(
            url="https://www.wsj.com/article/123",  # type: ignore[arg-type]
            title="Premium Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text=None,
            extraction_status=ExtractionStatus.PAYWALL,
            extraction_method="trafilatura",
            error_message="Paywall detected",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=None,
            summarization_status=SummarizationStatus.SKIPPED,
            error_message="Body extraction failed, summarization skipped",
        )

        assert summarized.summarization_status == SummarizationStatus.SKIPPED
        assert summarized.summary is None

    def test_異常系_extractedが必須(self) -> None:
        """extracted がない場合は ValidationError."""
        from news.models import SummarizationStatus, SummarizedArticle

        with pytest.raises(ValidationError) as exc_info:
            SummarizedArticle(
                summary=None,
                summarization_status=SummarizationStatus.FAILED,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extracted",) for e in errors)

    def test_異常系_summarization_statusが必須(self) -> None:
        """summarization_status がない場合は ValidationError."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )

        with pytest.raises(ValidationError) as exc_info:
            SummarizedArticle(
                extracted=extracted,
                summary=None,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("summarization_status",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """SummarizedArticle は model_dump() で dict に変換可能."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=collected_at,
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Article content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要",
            key_points=["ポイント1"],
            market_impact="影響",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        data = summarized.model_dump()

        assert data["summarization_status"] == SummarizationStatus.SUCCESS
        assert data["summary"]["overview"] == "概要"
        assert data["extracted"]["body_text"] == "Article content"
        assert data["error_message"] is None

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から SummarizedArticle を作成可能."""
        from news.models import SummarizationStatus, SummarizedArticle

        data = {
            "extracted": {
                "collected": {
                    "url": "https://www.cnbc.com/article/123",
                    "title": "Market Update",
                    "source": {
                        "source_type": "rss",
                        "source_name": "CNBC Markets",
                        "category": "market",
                    },
                    "collected_at": "2025-01-15T12:00:00Z",
                },
                "body_text": "Article content",
                "extraction_status": "success",
                "extraction_method": "trafilatura",
            },
            "summary": {
                "overview": "概要",
                "key_points": ["ポイント1", "ポイント2"],
                "market_impact": "市場への影響",
            },
            "summarization_status": "success",
        }

        summarized = SummarizedArticle.model_validate(data)

        assert summarized.summarization_status == SummarizationStatus.SUCCESS
        assert summarized.summary is not None
        assert summarized.summary.overview == "概要"
        assert len(summarized.summary.key_points) == 2
        assert summarized.extracted.body_text == "Article content"

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """SummarizedArticle は JSON シリアライズ可能."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Article content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要テキスト",
            key_points=["ポイント1"],
            market_impact="影響テキスト",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        json_str = summarized.model_dump_json()

        assert "概要テキスト" in json_str
        assert '"summarization_status":"success"' in json_str
        assert "https://www.cnbc.com/article/123" in json_str

    def test_正常系_ExtractedArticleと関連が正しい(self) -> None:
        """SummarizedArticle から ExtractedArticle の全プロパティにアクセスできる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.YFINANCE,
            source_name="NVDA",
            category="yf_ai_stock",
        )
        published = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        collected = CollectedArticle(
            url="https://finance.yahoo.com/news/nvda",  # type: ignore[arg-type]
            title="NVDA Earnings Report",
            published=published,
            raw_summary="NVDA reports quarterly earnings",
            source=source,
            collected_at=collected_at,
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article body about NVDA earnings...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="NVDA決算発表",
            key_points=["売上高予想超え", "AIセグメント好調"],
            market_impact="株価上昇期待",
        )

        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        # ExtractedArticle の全プロパティにアクセス可能
        assert (
            summarized.extracted.body_text == "Full article body about NVDA earnings..."
        )
        assert summarized.extracted.extraction_status == ExtractionStatus.SUCCESS
        assert summarized.extracted.extraction_method == "trafilatura"

        # CollectedArticle の全プロパティにもアクセス可能
        assert (
            str(summarized.extracted.collected.url)
            == "https://finance.yahoo.com/news/nvda"
        )
        assert summarized.extracted.collected.title == "NVDA Earnings Report"
        assert summarized.extracted.collected.published == published
        assert summarized.extracted.collected.source.source_type == SourceType.YFINANCE
        assert summarized.extracted.collected.source.source_name == "NVDA"


class TestPublicationStatus:
    """PublicationStatus StrEnum のテストクラス."""

    def test_正常系_SUCCESS値が定義されている(self) -> None:
        """PublicationStatus.SUCCESS が "success" 値で定義されていること."""
        from news.models import PublicationStatus

        assert PublicationStatus.SUCCESS == "success"
        assert PublicationStatus.SUCCESS.value == "success"

    def test_正常系_FAILED値が定義されている(self) -> None:
        """PublicationStatus.FAILED が "failed" 値で定義されていること."""
        from news.models import PublicationStatus

        assert PublicationStatus.FAILED == "failed"
        assert PublicationStatus.FAILED.value == "failed"

    def test_正常系_SKIPPED値が定義されている(self) -> None:
        """PublicationStatus.SKIPPED が "skipped" 値で定義されていること."""
        from news.models import PublicationStatus

        assert PublicationStatus.SKIPPED == "skipped"
        assert PublicationStatus.SKIPPED.value == "skipped"

    def test_正常系_DUPLICATE値が定義されている(self) -> None:
        """PublicationStatus.DUPLICATE が "duplicate" 値で定義されていること."""
        from news.models import PublicationStatus

        assert PublicationStatus.DUPLICATE == "duplicate"
        assert PublicationStatus.DUPLICATE.value == "duplicate"

    def test_正常系_全4種類の値が存在する(self) -> None:
        """PublicationStatus は SUCCESS, FAILED, SKIPPED, DUPLICATE の4種類のみ."""
        from news.models import PublicationStatus

        members = list(PublicationStatus)
        assert len(members) == 4
        assert PublicationStatus.SUCCESS in members
        assert PublicationStatus.FAILED in members
        assert PublicationStatus.SKIPPED in members
        assert PublicationStatus.DUPLICATE in members

    def test_正常系_StrEnumなので文字列として比較可能(self) -> None:
        """PublicationStatus は StrEnum なので文字列との比較が可能."""
        from news.models import PublicationStatus

        assert PublicationStatus.SUCCESS == "success"
        assert PublicationStatus.FAILED == "failed"
        assert PublicationStatus.SKIPPED == "skipped"
        assert PublicationStatus.DUPLICATE == "duplicate"


class TestPublishedArticle:
    """PublishedArticle Pydantic モデルのテストクラス."""

    def test_正常系_公開成功時のモデルを作成できる(self) -> None:
        """publication_status が SUCCESS のとき正常に作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="米国株式市場が上昇",
            key_points=["S&P500上昇", "テック株が牽引"],
            market_impact="投資家心理改善",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=123,
            issue_url="https://github.com/YH-05/quants/issues/123",
            publication_status=PublicationStatus.SUCCESS,
        )

        assert published.summarized == summarized
        assert published.issue_number == 123
        assert published.issue_url == "https://github.com/YH-05/quants/issues/123"
        assert published.publication_status == PublicationStatus.SUCCESS
        assert published.error_message is None

    def test_正常系_公開失敗時のモデルを作成できる(self) -> None:
        """publication_status が FAILED のとき正常に作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="米国株式市場が上昇",
            key_points=["S&P500上昇"],
            market_impact="投資家心理改善",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=None,
            issue_url=None,
            publication_status=PublicationStatus.FAILED,
            error_message="GitHub API rate limit exceeded",
        )

        assert published.issue_number is None
        assert published.issue_url is None
        assert published.publication_status == PublicationStatus.FAILED
        assert published.error_message == "GitHub API rate limit exceeded"

    def test_正常系_要約失敗でスキップ時のモデルを作成できる(self) -> None:
        """publication_status が SKIPPED のとき正常に作成できる（要約失敗時）."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="WSJ",
            category="finance",
        )
        collected = CollectedArticle(
            url="https://www.wsj.com/article/123",  # type: ignore[arg-type]
            title="Premium Article",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text=None,
            extraction_status=ExtractionStatus.PAYWALL,
            extraction_method="trafilatura",
            error_message="Paywall detected",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=None,
            summarization_status=SummarizationStatus.SKIPPED,
            error_message="Body extraction failed",
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=None,
            issue_url=None,
            publication_status=PublicationStatus.SKIPPED,
            error_message="Summarization failed, publication skipped",
        )

        assert published.publication_status == PublicationStatus.SKIPPED
        assert published.issue_number is None

    def test_正常系_重複検出時のモデルを作成できる(self) -> None:
        """publication_status が DUPLICATE のとき正常に作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article content here...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="米国株式市場が上昇",
            key_points=["S&P500上昇"],
            market_impact="投資家心理改善",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=None,
            issue_url=None,
            publication_status=PublicationStatus.DUPLICATE,
            error_message="Article already exists as Issue #100",
        )

        assert published.publication_status == PublicationStatus.DUPLICATE
        assert published.error_message == "Article already exists as Issue #100"

    def test_異常系_summarizedが必須(self) -> None:
        """summarized がない場合は ValidationError."""
        from news.models import PublicationStatus, PublishedArticle

        with pytest.raises(ValidationError) as exc_info:
            PublishedArticle(
                issue_number=123,
                issue_url="https://github.com/YH-05/quants/issues/123",
                publication_status=PublicationStatus.SUCCESS,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("summarized",) for e in errors)

    def test_異常系_publication_statusが必須(self) -> None:
        """publication_status がない場合は ValidationError."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要",
            key_points=["ポイント"],
            market_impact="影響",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        with pytest.raises(ValidationError) as exc_info:
            PublishedArticle(
                summarized=summarized,
                issue_number=123,
                issue_url="https://github.com/YH-05/quants/issues/123",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("publication_status",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """PublishedArticle は model_dump() で dict に変換可能."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=collected_at,
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Article content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要",
            key_points=["ポイント1"],
            market_impact="影響",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=456,
            issue_url="https://github.com/YH-05/quants/issues/456",
            publication_status=PublicationStatus.SUCCESS,
        )

        data = published.model_dump()

        assert data["publication_status"] == PublicationStatus.SUCCESS
        assert data["issue_number"] == 456
        assert data["issue_url"] == "https://github.com/YH-05/quants/issues/456"
        assert data["summarized"]["summarization_status"] == SummarizationStatus.SUCCESS
        assert data["error_message"] is None

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から PublishedArticle を作成可能."""
        from news.models import PublicationStatus, PublishedArticle, SummarizationStatus

        data = {
            "summarized": {
                "extracted": {
                    "collected": {
                        "url": "https://www.cnbc.com/article/123",
                        "title": "Market Update",
                        "source": {
                            "source_type": "rss",
                            "source_name": "CNBC Markets",
                            "category": "market",
                        },
                        "collected_at": "2025-01-15T12:00:00Z",
                    },
                    "body_text": "Article content",
                    "extraction_status": "success",
                    "extraction_method": "trafilatura",
                },
                "summary": {
                    "overview": "概要",
                    "key_points": ["ポイント1", "ポイント2"],
                    "market_impact": "市場への影響",
                },
                "summarization_status": "success",
            },
            "issue_number": 789,
            "issue_url": "https://github.com/YH-05/quants/issues/789",
            "publication_status": "success",
        }

        published = PublishedArticle.model_validate(data)

        assert published.publication_status == PublicationStatus.SUCCESS
        assert published.issue_number == 789
        assert published.issue_url == "https://github.com/YH-05/quants/issues/789"
        assert published.summarized.summarization_status == SummarizationStatus.SUCCESS

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """PublishedArticle は JSON シリアライズ可能."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC Markets",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/123",  # type: ignore[arg-type]
            title="Market Update",
            source=source,
            collected_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Article content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要テキスト",
            key_points=["ポイント1"],
            market_impact="影響テキスト",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=100,
            issue_url="https://github.com/YH-05/quants/issues/100",
            publication_status=PublicationStatus.SUCCESS,
        )

        json_str = published.model_dump_json()

        assert '"publication_status":"success"' in json_str
        assert '"issue_number":100' in json_str
        assert "https://github.com/YH-05/quants/issues/100" in json_str

    def test_正常系_SummarizedArticleと関連が正しい(self) -> None:
        """PublishedArticle から SummarizedArticle の全プロパティにアクセスできる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
        )

        source = ArticleSource(
            source_type=SourceType.YFINANCE,
            source_name="NVDA",
            category="yf_ai_stock",
        )
        published_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        collected_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        collected = CollectedArticle(
            url="https://finance.yahoo.com/news/nvda",  # type: ignore[arg-type]
            title="NVDA Earnings Report",
            published=published_time,
            raw_summary="NVDA reports quarterly earnings",
            source=source,
            collected_at=collected_at,
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Full article body about NVDA earnings...",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="NVDA決算発表",
            key_points=["売上高予想超え", "AIセグメント好調"],
            market_impact="株価上昇期待",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )

        published = PublishedArticle(
            summarized=summarized,
            issue_number=200,
            issue_url="https://github.com/YH-05/quants/issues/200",
            publication_status=PublicationStatus.SUCCESS,
        )

        # SummarizedArticle の全プロパティにアクセス可能
        assert published.summarized.summary is not None
        assert published.summarized.summary.overview == "NVDA決算発表"
        assert published.summarized.summarization_status == SummarizationStatus.SUCCESS

        # ExtractedArticle の全プロパティにもアクセス可能
        assert (
            published.summarized.extracted.body_text
            == "Full article body about NVDA earnings..."
        )
        assert (
            published.summarized.extracted.extraction_status == ExtractionStatus.SUCCESS
        )

        # CollectedArticle の全プロパティにもアクセス可能
        assert (
            str(published.summarized.extracted.collected.url)
            == "https://finance.yahoo.com/news/nvda"
        )
        assert published.summarized.extracted.collected.title == "NVDA Earnings Report"
        assert published.summarized.extracted.collected.published == published_time
        assert (
            published.summarized.extracted.collected.source.source_type
            == SourceType.YFINANCE
        )
        assert published.summarized.extracted.collected.source.source_name == "NVDA"


class TestFailureRecord:
    """FailureRecord Pydantic モデルのテストクラス."""

    def test_正常系_全フィールドで作成できる(self) -> None:
        """url, title, stage, error で FailureRecord を作成できる."""
        from news.models import FailureRecord

        record = FailureRecord(
            url="https://www.cnbc.com/article/123",
            title="Failed Article",
            stage="extraction",
            error="Connection timeout",
        )

        assert record.url == "https://www.cnbc.com/article/123"
        assert record.title == "Failed Article"
        assert record.stage == "extraction"
        assert record.error == "Connection timeout"

    def test_正常系_extraction_stageで作成できる(self) -> None:
        """stage が extraction の FailureRecord を作成できる."""
        from news.models import FailureRecord

        record = FailureRecord(
            url="https://example.com/article",
            title="Extraction Failed",
            stage="extraction",
            error="Paywall detected",
        )

        assert record.stage == "extraction"

    def test_正常系_summarization_stageで作成できる(self) -> None:
        """stage が summarization の FailureRecord を作成できる."""
        from news.models import FailureRecord

        record = FailureRecord(
            url="https://example.com/article",
            title="Summarization Failed",
            stage="summarization",
            error="API rate limit exceeded",
        )

        assert record.stage == "summarization"

    def test_正常系_publication_stageで作成できる(self) -> None:
        """stage が publication の FailureRecord を作成できる."""
        from news.models import FailureRecord

        record = FailureRecord(
            url="https://example.com/article",
            title="Publication Failed",
            stage="publication",
            error="GitHub API error",
        )

        assert record.stage == "publication"

    def test_異常系_urlが必須(self) -> None:
        """url がない場合は ValidationError."""
        from news.models import FailureRecord

        with pytest.raises(ValidationError) as exc_info:
            FailureRecord(
                title="Failed Article",
                stage="extraction",
                error="Error message",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_異常系_titleが必須(self) -> None:
        """title がない場合は ValidationError."""
        from news.models import FailureRecord

        with pytest.raises(ValidationError) as exc_info:
            FailureRecord(
                url="https://example.com/article",
                stage="extraction",
                error="Error message",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_異常系_stageが必須(self) -> None:
        """stage がない場合は ValidationError."""
        from news.models import FailureRecord

        with pytest.raises(ValidationError) as exc_info:
            FailureRecord(
                url="https://example.com/article",
                title="Failed Article",
                error="Error message",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("stage",) for e in errors)

    def test_異常系_errorが必須(self) -> None:
        """error がない場合は ValidationError."""
        from news.models import FailureRecord

        with pytest.raises(ValidationError) as exc_info:
            FailureRecord(
                url="https://example.com/article",
                title="Failed Article",
                stage="extraction",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("error",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """FailureRecord は model_dump() で dict に変換可能."""
        from news.models import FailureRecord

        record = FailureRecord(
            url="https://example.com/article",
            title="Failed Article",
            stage="extraction",
            error="Error details",
        )

        data = record.model_dump()

        assert data["url"] == "https://example.com/article"
        assert data["title"] == "Failed Article"
        assert data["stage"] == "extraction"
        assert data["error"] == "Error details"

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から FailureRecord を作成可能."""
        from news.models import FailureRecord

        data = {
            "url": "https://example.com/article",
            "title": "Failed Article",
            "stage": "summarization",
            "error": "API error",
        }

        record = FailureRecord.model_validate(data)

        assert record.url == "https://example.com/article"
        assert record.title == "Failed Article"
        assert record.stage == "summarization"
        assert record.error == "API error"

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """FailureRecord は JSON シリアライズ可能."""
        from news.models import FailureRecord

        record = FailureRecord(
            url="https://example.com/article",
            title="Failed Article",
            stage="publication",
            error="GitHub error",
        )

        json_str = record.model_dump_json()

        assert "https://example.com/article" in json_str
        assert '"title":"Failed Article"' in json_str
        assert '"stage":"publication"' in json_str
        assert '"error":"GitHub error"' in json_str


class TestWorkflowResult:
    """WorkflowResult Pydantic モデルのテストクラス."""

    def test_正常系_全フィールドで作成できる(self) -> None:
        """WorkflowResult を全フィールドで作成できる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            FailureRecord,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
            WorkflowResult,
        )

        # PublishedArticle を作成
        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要",
            key_points=["ポイント"],
            market_impact="影響",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        published = PublishedArticle(
            summarized=summarized,
            issue_number=100,
            issue_url="https://github.com/YH-05/quants/issues/100",
            publication_status=PublicationStatus.SUCCESS,
        )

        # FailureRecord を作成
        extraction_failure = FailureRecord(
            url="https://example.com/fail1",
            title="Failed 1",
            stage="extraction",
            error="Timeout",
        )
        summarization_failure = FailureRecord(
            url="https://example.com/fail2",
            title="Failed 2",
            stage="summarization",
            error="API error",
        )
        publication_failure = FailureRecord(
            url="https://example.com/fail3",
            title="Failed 3",
            stage="publication",
            error="GitHub error",
        )

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 30, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[extraction_failure],
            summarization_failures=[summarization_failure],
            publication_failures=[publication_failure],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=330.0,
            published_articles=[published],
        )

        assert result.total_collected == 10
        assert result.total_extracted == 8
        assert result.total_summarized == 7
        assert result.total_published == 5
        assert result.total_duplicates == 2
        assert len(result.extraction_failures) == 1
        assert len(result.summarization_failures) == 1
        assert len(result.publication_failures) == 1
        assert result.started_at == started
        assert result.finished_at == finished
        assert result.elapsed_seconds == 330.0
        assert len(result.published_articles) == 1

    def test_正常系_空のリストで作成できる(self) -> None:
        """失敗なし・公開記事なしでも WorkflowResult を作成できる."""
        from news.models import WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 1, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=0,
            total_extracted=0,
            total_summarized=0,
            total_published=0,
            total_duplicates=0,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=60.0,
            published_articles=[],
        )

        assert result.total_collected == 0
        assert result.extraction_failures == []
        assert result.summarization_failures == []
        assert result.publication_failures == []
        assert result.published_articles == []

    def test_正常系_複数の失敗記録で作成できる(self) -> None:
        """複数の FailureRecord を含む WorkflowResult を作成できる."""
        from news.models import FailureRecord, WorkflowResult

        failures = [
            FailureRecord(
                url=f"https://example.com/fail{i}",
                title=f"Failed {i}",
                stage="extraction",
                error=f"Error {i}",
            )
            for i in range(3)
        ]

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 2, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=5,
            total_extracted=2,
            total_summarized=2,
            total_published=2,
            total_duplicates=0,
            extraction_failures=failures,
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=120.0,
            published_articles=[],
        )

        assert len(result.extraction_failures) == 3

    def test_異常系_total_collectedが必須(self) -> None:
        """total_collected がない場合は ValidationError."""
        from news.models import WorkflowResult

        started = datetime.now(tz=timezone.utc)
        finished = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            WorkflowResult(
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=started,
                finished_at=finished,
                elapsed_seconds=0.0,
                published_articles=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("total_collected",) for e in errors)

    def test_異常系_started_atが必須(self) -> None:
        """started_at がない場合は ValidationError."""
        from news.models import WorkflowResult

        finished = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                finished_at=finished,
                elapsed_seconds=0.0,
                published_articles=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("started_at",) for e in errors)

    def test_異常系_finished_atが必須(self) -> None:
        """finished_at がない場合は ValidationError."""
        from news.models import WorkflowResult

        started = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=started,
                elapsed_seconds=0.0,
                published_articles=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("finished_at",) for e in errors)

    def test_異常系_elapsed_secondsが必須(self) -> None:
        """elapsed_seconds がない場合は ValidationError."""
        from news.models import WorkflowResult

        started = datetime.now(tz=timezone.utc)
        finished = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=started,
                finished_at=finished,
                published_articles=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("elapsed_seconds",) for e in errors)

    def test_異常系_published_articlesが必須(self) -> None:
        """published_articles がない場合は ValidationError."""
        from news.models import WorkflowResult

        started = datetime.now(tz=timezone.utc)
        finished = datetime.now(tz=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            WorkflowResult(
                total_collected=0,
                total_extracted=0,
                total_summarized=0,
                total_published=0,
                total_duplicates=0,
                extraction_failures=[],
                summarization_failures=[],
                publication_failures=[],
                started_at=started,
                finished_at=finished,
                elapsed_seconds=0.0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("published_articles",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """WorkflowResult は model_dump() で dict に変換可能."""
        from news.models import WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
        )

        data = result.model_dump()

        assert data["total_collected"] == 10
        assert data["total_extracted"] == 8
        assert data["total_summarized"] == 7
        assert data["total_published"] == 5
        assert data["total_duplicates"] == 2
        assert data["extraction_failures"] == []
        assert data["started_at"] == started
        assert data["finished_at"] == finished
        assert data["elapsed_seconds"] == 300.0

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から WorkflowResult を作成可能."""
        from news.models import WorkflowResult

        data = {
            "total_collected": 5,
            "total_extracted": 4,
            "total_summarized": 3,
            "total_published": 2,
            "total_duplicates": 1,
            "extraction_failures": [
                {
                    "url": "https://example.com/fail",
                    "title": "Failed",
                    "stage": "extraction",
                    "error": "Error",
                }
            ],
            "summarization_failures": [],
            "publication_failures": [],
            "started_at": "2025-01-15T10:00:00Z",
            "finished_at": "2025-01-15T10:05:00Z",
            "elapsed_seconds": 300.0,
            "published_articles": [],
        }

        result = WorkflowResult.model_validate(data)

        assert result.total_collected == 5
        assert result.total_extracted == 4
        assert len(result.extraction_failures) == 1
        assert result.extraction_failures[0].url == "https://example.com/fail"

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """WorkflowResult は JSON シリアライズ可能."""
        from news.models import WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
        )

        json_str = result.model_dump_json()

        assert '"total_collected":10' in json_str
        assert '"total_extracted":8' in json_str
        assert '"total_summarized":7' in json_str
        assert '"total_published":5' in json_str
        assert '"total_duplicates":2' in json_str
        assert '"elapsed_seconds":300.0' in json_str

    def test_正常系_PublishedArticleと関連が正しい(self) -> None:
        """WorkflowResult から PublishedArticle の全プロパティにアクセスできる."""
        from news.models import (
            ArticleSource,
            CollectedArticle,
            ExtractedArticle,
            ExtractionStatus,
            PublicationStatus,
            PublishedArticle,
            SourceType,
            StructuredSummary,
            SummarizationStatus,
            SummarizedArticle,
            WorkflowResult,
        )

        source = ArticleSource(
            source_type=SourceType.RSS,
            source_name="CNBC",
            category="market",
        )
        collected = CollectedArticle(
            url="https://www.cnbc.com/article/1",  # type: ignore[arg-type]
            title="Article 1",
            source=source,
            collected_at=datetime.now(tz=timezone.utc),
        )
        extracted = ExtractedArticle(
            collected=collected,
            body_text="Content",
            extraction_status=ExtractionStatus.SUCCESS,
            extraction_method="trafilatura",
        )
        summary = StructuredSummary(
            overview="概要",
            key_points=["ポイント"],
            market_impact="影響",
        )
        summarized = SummarizedArticle(
            extracted=extracted,
            summary=summary,
            summarization_status=SummarizationStatus.SUCCESS,
        )
        published = PublishedArticle(
            summarized=summarized,
            issue_number=100,
            issue_url="https://github.com/YH-05/quants/issues/100",
            publication_status=PublicationStatus.SUCCESS,
        )

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=1,
            total_extracted=1,
            total_summarized=1,
            total_published=1,
            total_duplicates=0,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[published],
        )

        # PublishedArticle の全プロパティにアクセス可能
        assert len(result.published_articles) == 1
        assert result.published_articles[0].issue_number == 100
        assert (
            result.published_articles[0].publication_status == PublicationStatus.SUCCESS
        )
        assert result.published_articles[0].summarized.summary is not None
        assert result.published_articles[0].summarized.summary.overview == "概要"
        assert (
            str(result.published_articles[0].summarized.extracted.collected.url)
            == "https://www.cnbc.com/article/1"
        )

    def test_正常系_FailureRecordと関連が正しい(self) -> None:
        """WorkflowResult から FailureRecord の全プロパティにアクセスできる."""
        from news.models import FailureRecord, WorkflowResult

        extraction_failure = FailureRecord(
            url="https://example.com/fail1",
            title="Extraction Failed",
            stage="extraction",
            error="Timeout error",
        )
        summarization_failure = FailureRecord(
            url="https://example.com/fail2",
            title="Summarization Failed",
            stage="summarization",
            error="API rate limit",
        )
        publication_failure = FailureRecord(
            url="https://example.com/fail3",
            title="Publication Failed",
            stage="publication",
            error="GitHub API error",
        )

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=3,
            total_extracted=2,
            total_summarized=1,
            total_published=0,
            total_duplicates=0,
            extraction_failures=[extraction_failure],
            summarization_failures=[summarization_failure],
            publication_failures=[publication_failure],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
        )

        # FailureRecord の全プロパティにアクセス可能
        assert len(result.extraction_failures) == 1
        assert result.extraction_failures[0].url == "https://example.com/fail1"
        assert result.extraction_failures[0].stage == "extraction"
        assert result.extraction_failures[0].error == "Timeout error"

        assert len(result.summarization_failures) == 1
        assert result.summarization_failures[0].url == "https://example.com/fail2"
        assert result.summarization_failures[0].stage == "summarization"

        assert len(result.publication_failures) == 1
        assert result.publication_failures[0].url == "https://example.com/fail3"
        assert result.publication_failures[0].stage == "publication"

    def test_正常系_total_early_duplicatesがデフォルトで0(self) -> None:
        """total_early_duplicates should default to 0."""
        from news.models import WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
        )

        assert result.total_early_duplicates == 0

    def test_正常系_total_early_duplicatesを指定して作成できる(self) -> None:
        """total_early_duplicates can be specified when creating WorkflowResult."""
        from news.models import WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            total_early_duplicates=3,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
        )

        assert result.total_early_duplicates == 3

    def test_正常系_feed_errorsがデフォルトで空リスト(self) -> None:
        """feed_errors should default to empty list."""
        from news.models import WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
        )

        assert result.feed_errors == []

    def test_正常系_feed_errorsを指定して作成できる(self) -> None:
        """feed_errors can be specified when creating WorkflowResult."""
        from news.models import FeedError, WorkflowResult

        started = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)

        feed_error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="Connection timeout",
            error_type="fetch",
            timestamp=started,
        )

        result = WorkflowResult(
            total_collected=10,
            total_extracted=8,
            total_summarized=7,
            total_published=5,
            total_duplicates=2,
            extraction_failures=[],
            summarization_failures=[],
            publication_failures=[],
            started_at=started,
            finished_at=finished,
            elapsed_seconds=300.0,
            published_articles=[],
            feed_errors=[feed_error],
        )

        assert len(result.feed_errors) == 1
        assert result.feed_errors[0].feed_url == "https://example.com/feed.xml"
        assert result.feed_errors[0].error_type == "fetch"


class TestFeedError:
    """FeedError Pydantic モデルのテストクラス."""

    def test_正常系_全フィールドで作成できる(self) -> None:
        """FeedError を全フィールドで作成できる."""
        from news.models import FeedError

        timestamp = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="Connection timeout",
            error_type="fetch",
            timestamp=timestamp,
        )

        assert error.feed_url == "https://example.com/feed.xml"
        assert error.feed_name == "Example Feed"
        assert error.error == "Connection timeout"
        assert error.error_type == "fetch"
        assert error.timestamp == timestamp

    def test_正常系_fetchエラータイプで作成できる(self) -> None:
        """FeedError を error_type='fetch' で作成できる."""
        from news.models import FeedError

        error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="HTTP 500",
            error_type="fetch",
            timestamp=datetime.now(tz=timezone.utc),
        )

        assert error.error_type == "fetch"

    def test_正常系_parseエラータイプで作成できる(self) -> None:
        """FeedError を error_type='parse' で作成できる."""
        from news.models import FeedError

        error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="Invalid XML",
            error_type="parse",
            timestamp=datetime.now(tz=timezone.utc),
        )

        assert error.error_type == "parse"

    def test_正常系_validationエラータイプで作成できる(self) -> None:
        """FeedError を error_type='validation' で作成できる."""
        from news.models import FeedError

        error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="Missing required field",
            error_type="validation",
            timestamp=datetime.now(tz=timezone.utc),
        )

        assert error.error_type == "validation"

    def test_異常系_feed_urlが必須(self) -> None:
        """feed_url がない場合は ValidationError."""
        from news.models import FeedError

        with pytest.raises(ValidationError) as exc_info:
            FeedError(
                feed_name="Example Feed",
                error="Error",
                error_type="fetch",
                timestamp=datetime.now(tz=timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("feed_url",) for e in errors)

    def test_異常系_feed_nameが必須(self) -> None:
        """feed_name がない場合は ValidationError."""
        from news.models import FeedError

        with pytest.raises(ValidationError) as exc_info:
            FeedError(
                feed_url="https://example.com/feed.xml",
                error="Error",
                error_type="fetch",
                timestamp=datetime.now(tz=timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("feed_name",) for e in errors)

    def test_異常系_errorが必須(self) -> None:
        """error がない場合は ValidationError."""
        from news.models import FeedError

        with pytest.raises(ValidationError) as exc_info:
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error_type="fetch",
                timestamp=datetime.now(tz=timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("error",) for e in errors)

    def test_異常系_error_typeが必須(self) -> None:
        """error_type がない場合は ValidationError."""
        from news.models import FeedError

        with pytest.raises(ValidationError) as exc_info:
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error="Error",
                timestamp=datetime.now(tz=timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("error_type",) for e in errors)

    def test_異常系_timestampが必須(self) -> None:
        """timestamp がない場合は ValidationError."""
        from news.models import FeedError

        with pytest.raises(ValidationError) as exc_info:
            FeedError(
                feed_url="https://example.com/feed.xml",
                feed_name="Example Feed",
                error="Error",
                error_type="fetch",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timestamp",) for e in errors)

    def test_正常系_モデルをdictに変換できる(self) -> None:
        """FeedError は model_dump() で dict に変換可能."""
        from news.models import FeedError

        timestamp = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="Connection timeout",
            error_type="fetch",
            timestamp=timestamp,
        )

        data = error.model_dump()

        assert data["feed_url"] == "https://example.com/feed.xml"
        assert data["feed_name"] == "Example Feed"
        assert data["error"] == "Connection timeout"
        assert data["error_type"] == "fetch"
        assert data["timestamp"] == timestamp

    def test_正常系_dictからモデルを作成できる(self) -> None:
        """dict から FeedError を作成可能."""
        from news.models import FeedError

        data = {
            "feed_url": "https://example.com/feed.xml",
            "feed_name": "Example Feed",
            "error": "Connection timeout",
            "error_type": "fetch",
            "timestamp": "2025-01-15T10:00:00Z",
        }

        error = FeedError.model_validate(data)

        assert error.feed_url == "https://example.com/feed.xml"
        assert error.error_type == "fetch"

    def test_正常系_JSONシリアライズ可能(self) -> None:
        """FeedError は JSON シリアライズ可能."""
        from news.models import FeedError

        timestamp = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        error = FeedError(
            feed_url="https://example.com/feed.xml",
            feed_name="Example Feed",
            error="Connection timeout",
            error_type="fetch",
            timestamp=timestamp,
        )

        json_str = error.model_dump_json()

        assert '"feed_url":"https://example.com/feed.xml"' in json_str
        assert '"feed_name":"Example Feed"' in json_str
        assert '"error":"Connection timeout"' in json_str
        assert '"error_type":"fetch"' in json_str
