"""embedding.chromadb_store モジュールの単体テスト.

テストTODOリスト:
- [x] url_to_chromadb_id: 同じ URL から同じ ID を生成すること
- [x] url_to_chromadb_id: 異なる URL から異なる ID を生成すること
- [x] url_to_chromadb_id: 16文字の16進数文字列を返すこと
- [x] get_existing_ids: chromadb 未インストール時に ImportError を raise すること
- [x] get_existing_ids: 空コレクションで空セットを返すこと
- [x] get_existing_ids: 既存 ID のセットを返すこと
- [x] _build_document: extraction.content あり時に content を使用すること
- [x] _build_document: extraction.content なし時に article.summary にフォールバックすること
- [x] _build_metadata: 全フィールドが文字列型であること
- [x] store_articles: 空リストで 0 を返すこと
- [x] store_articles: chromadb 未インストール時に ImportError を raise すること
- [x] store_articles: 新規記事のみを格納すること（バッチ）
- [x] store_articles: 既存 ID の記事をスキップすること
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from embedding.chromadb_store import (
    _build_document,
    _build_metadata,
    get_existing_ids,
    store_articles,
    url_to_chromadb_id,
)
from embedding.types import ArticleRecord, ExtractionResult


@pytest.fixture
def sample_article() -> ArticleRecord:
    """テスト用記事レコード."""
    return ArticleRecord(
        url="https://example.com/article/1",
        title="Test Article",
        published="2024-01-15T10:00:00+00:00",
        summary="Test summary",
        category="technology",
        source="cnbc",
        ticker="AAPL",
        author="John Doe",
        article_id="article-001",
        content="Full content",
        extraction_method="trafilatura",
        extracted_at="2024-01-15T10:05:00+00:00",
        json_file="/data/raw/news/cnbc/2024-01-15.json",
    )


@pytest.fixture
def sample_extraction() -> ExtractionResult:
    """テスト用抽出結果."""
    return ExtractionResult(
        url="https://example.com/article/1",
        content="Extracted content",
        method="trafilatura",
        extracted_at="2024-01-15T10:05:00+00:00",
    )


@pytest.fixture
def failed_extraction() -> ExtractionResult:
    """失敗した抽出結果（content が空）."""
    return ExtractionResult(
        url="https://example.com/article/1",
        content="",
        method="failed",
        extracted_at="2024-01-15T10:05:00+00:00",
        error="All extraction methods failed",
    )


class TestUrlToChromadbId:
    def test_正常系_同じURLから同じIDを生成すること(self) -> None:
        url = "https://example.com/article/1"
        id1 = url_to_chromadb_id(url)
        id2 = url_to_chromadb_id(url)
        assert id1 == id2

    def test_正常系_異なるURLから異なるIDを生成すること(self) -> None:
        id1 = url_to_chromadb_id("https://example.com/article/1")
        id2 = url_to_chromadb_id("https://example.com/article/2")
        assert id1 != id2

    def test_正常系_16文字の16進数文字列を返すこと(self) -> None:
        result = url_to_chromadb_id("https://example.com/article/1")
        assert len(result) == 16
        # 16進数文字のみで構成されていること
        assert all(c in "0123456789abcdef" for c in result)

    def test_エッジケース_空文字列URLでも動作すること(self) -> None:
        result = url_to_chromadb_id("")
        assert len(result) == 16


class TestGetExistingIds:
    def test_異常系_chromadb未インストール時にImportErrorを発生させること(
        self,
    ) -> None:
        with (
            patch("embedding.chromadb_store._chromadb", None),
            pytest.raises(ImportError, match="chromadb is not installed"),
        ):
            get_existing_ids(Path("/tmp/chromadb"), "test-collection")

    def test_正常系_空コレクションで空セットを返すこと(self) -> None:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        with patch("embedding.chromadb_store._chromadb", mock_chromadb):
            result = get_existing_ids(Path("/tmp/chromadb"), "test-collection")

        assert result == set()

    def test_正常系_既存IDのセットを返すこと(self) -> None:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 3
        mock_collection.get.return_value = {
            "ids": ["id1", "id2", "id3"],
        }

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        with patch("embedding.chromadb_store._chromadb", mock_chromadb):
            result = get_existing_ids(Path("/tmp/chromadb"), "test-collection")

        assert result == {"id1", "id2", "id3"}


class TestBuildDocument:
    def test_正常系_extraction_contentありの場合にcontentを使用すること(
        self,
        sample_article: ArticleRecord,
        sample_extraction: ExtractionResult,
    ) -> None:
        doc = _build_document(sample_article, sample_extraction)
        assert doc == f"{sample_article.title}\n\n{sample_extraction.content}"

    def test_正常系_extraction_contentなし時にsummaryにフォールバックすること(
        self,
        sample_article: ArticleRecord,
        failed_extraction: ExtractionResult,
    ) -> None:
        doc = _build_document(sample_article, failed_extraction)
        assert doc == f"{sample_article.title}\n\n{sample_article.summary}"

    def test_エッジケース_contentもsummaryも空の場合に空改行を返すこと(
        self,
    ) -> None:
        article = ArticleRecord(url="https://example.com", title="Title")
        extraction = ExtractionResult(
            url="https://example.com",
            content="",
            method="failed",
            extracted_at="2024-01-15T10:05:00+00:00",
        )
        doc = _build_document(article, extraction)
        assert doc == "Title\n\n"


class TestBuildMetadata:
    def test_正常系_全フィールドが文字列型であること(
        self,
        sample_article: ArticleRecord,
        sample_extraction: ExtractionResult,
    ) -> None:
        metadata = _build_metadata(sample_article, sample_extraction)
        for key, value in metadata.items():
            assert isinstance(value, str), f"Field '{key}' is not a string: {value!r}"

    def test_正常系_必須フィールドが含まれること(
        self,
        sample_article: ArticleRecord,
        sample_extraction: ExtractionResult,
    ) -> None:
        metadata = _build_metadata(sample_article, sample_extraction)
        required_fields = {
            "url",
            "title",
            "source",
            "category",
            "ticker",
            "published",
            "author",
            "extraction_method",
            "extracted_at",
            "has_embedding",
            "json_file",
        }
        assert required_fields.issubset(metadata.keys())

    def test_正常系_has_embeddingがfalseであること(
        self,
        sample_article: ArticleRecord,
        sample_extraction: ExtractionResult,
    ) -> None:
        metadata = _build_metadata(sample_article, sample_extraction)
        assert metadata["has_embedding"] == "false"


class TestStoreArticles:
    def test_正常系_空リストで0を返すこと(self) -> None:
        mock_chromadb = MagicMock()

        with patch("embedding.chromadb_store._chromadb", mock_chromadb):
            result = store_articles([], [], Path("/tmp/chromadb"), "test", 768)

        assert result == 0

    def test_異常系_chromadb未インストール時にImportErrorを発生させること(
        self,
    ) -> None:
        with (
            patch("embedding.chromadb_store._chromadb", None),
            pytest.raises(ImportError, match="chromadb is not installed"),
        ):
            store_articles([], [], Path("/tmp/chromadb"), "test", 768)

    def test_正常系_新規記事をバッチ格納すること(
        self,
        sample_article: ArticleRecord,
        sample_extraction: ExtractionResult,
    ) -> None:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_collection.get.return_value = {"ids": []}
        mock_collection.add = MagicMock()

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        import numpy as real_np

        with patch("embedding.chromadb_store._chromadb", mock_chromadb):
            result = store_articles(
                [sample_article],
                [sample_extraction],
                Path("/tmp/chromadb"),
                "test-collection",
                768,
            )

        assert result == 1
        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args.kwargs
        assert len(call_kwargs["ids"]) == 1
        assert len(call_kwargs["documents"]) == 1
        assert len(call_kwargs["embeddings"]) == 1
        assert len(call_kwargs["metadatas"]) == 1

    def test_正常系_既存IDの記事をスキップすること(
        self,
        sample_article: ArticleRecord,
        sample_extraction: ExtractionResult,
    ) -> None:
        existing_id = url_to_chromadb_id(sample_article.url)

        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {"ids": [existing_id]}
        mock_collection.add = MagicMock()

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        with patch("embedding.chromadb_store._chromadb", mock_chromadb):
            result = store_articles(
                [sample_article],
                [sample_extraction],
                Path("/tmp/chromadb"),
                "test-collection",
                768,
            )

        assert result == 0
        mock_collection.add.assert_not_called()

    def test_正常系_バッチ分割で格納すること(self) -> None:
        """100件を超える場合にバッチ分割されること."""
        from embedding.chromadb_store import _BATCH_SIZE

        num_articles = _BATCH_SIZE + 10

        articles = [
            ArticleRecord(url=f"https://example.com/article/{i}", title=f"Article {i}")
            for i in range(num_articles)
        ]
        extractions = [
            ExtractionResult(
                url=f"https://example.com/article/{i}",
                content=f"Content {i}",
                method="trafilatura",
                extracted_at="2024-01-15T10:05:00+00:00",
            )
            for i in range(num_articles)
        ]

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_collection.get.return_value = {"ids": []}
        mock_collection.add = MagicMock()

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        with patch("embedding.chromadb_store._chromadb", mock_chromadb):
            result = store_articles(
                articles,
                extractions,
                Path("/tmp/chromadb"),
                "test-collection",
                768,
            )

        assert result == num_articles
        # バッチが 2 回呼ばれること（100件 + 10件）
        assert mock_collection.add.call_count == 2
