"""PaperFetcher の単体テスト.

S2Client + ArxivClient + SQLiteCache を統合するオーケストレータの
動作を検証する。全外部依存はモックし、フォールバックロジック・
キャッシュ連携・バッチ処理をテストする。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from academic.errors import (
    PaperNotFoundError,
    RetryableError,
)
from academic.fetcher import PaperFetcher
from academic.types import (
    AcademicConfig,
    AuthorInfo,
    PaperMetadata,
)


def _sample_s2_response(arxiv_id: str = "2301.00001") -> dict[str, Any]:
    """S2Client.fetch_paper() が返すサンプル JSON を生成する."""
    return {
        "paperId": "s2-paper-abc123",
        "externalIds": {"ArXiv": arxiv_id},
        "title": "Sample Paper Title",
        "abstract": "This is a sample abstract.",
        "authors": [
            {"authorId": "auth-1", "name": "Alice Doe"},
            {"authorId": "auth-2", "name": "Bob Smith"},
        ],
        "references": [
            {
                "paperId": "s2-ref-001",
                "title": "Reference Paper 1",
                "externalIds": {"ArXiv": "2001.00001"},
            },
        ],
        "citations": [
            {
                "paperId": "s2-cite-001",
                "title": "Citing Paper 1",
                "externalIds": {},
            },
        ],
        "publicationDate": "2023-01-15",
        "fieldsOfStudy": ["Computer Science"],
    }


def _sample_arxiv_paper_metadata(arxiv_id: str = "2301.00001") -> PaperMetadata:
    """ArxivClient.fetch_paper() が返すサンプル PaperMetadata を生成する."""
    return PaperMetadata(
        arxiv_id=arxiv_id,
        title="Sample Paper Title (arXiv)",
        authors=(AuthorInfo(name="Alice Doe"),),
        references=(),
        citations=(),
        abstract="Abstract from arXiv.",
    )


@pytest.fixture
def mock_s2_client() -> MagicMock:
    """モック S2Client を返すフィクスチャ."""
    return MagicMock()


@pytest.fixture
def mock_arxiv_client() -> MagicMock:
    """モック ArxivClient を返すフィクスチャ."""
    return MagicMock()


@pytest.fixture
def mock_cache() -> MagicMock:
    """モック SQLiteCache を返すフィクスチャ."""
    return MagicMock()


@pytest.fixture
def fetcher(
    mock_s2_client: MagicMock,
    mock_arxiv_client: MagicMock,
    mock_cache: MagicMock,
) -> PaperFetcher:
    """DI でモックを注入した PaperFetcher を返すフィクスチャ."""
    return PaperFetcher(
        s2_client=mock_s2_client,
        arxiv_client=mock_arxiv_client,
        cache=mock_cache,
    )


class TestPaperFetcherInit:
    """PaperFetcher.__init__() のテスト."""

    def test_正常系_DI注入で初期化できる(
        self,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2Client, ArxivClient, Cache をDI注入して初期化できることを確認。"""
        fetcher = PaperFetcher(
            s2_client=mock_s2_client,
            arxiv_client=mock_arxiv_client,
            cache=mock_cache,
        )
        assert fetcher is not None

    def test_正常系_デフォルト設定で初期化できる(self) -> None:
        """引数なしでデフォルト設定の PaperFetcher を初期化できることを確認。"""
        with (
            patch("academic.fetcher.S2Client") as mock_s2_cls,
            patch("academic.fetcher.ArxivClient") as mock_arxiv_cls,
            patch("academic.fetcher.get_academic_cache") as mock_cache_fn,
        ):
            mock_s2_cls.return_value = MagicMock()
            mock_arxiv_cls.return_value = MagicMock()
            mock_cache_fn.return_value = MagicMock()

            fetcher = PaperFetcher()
            assert fetcher is not None

    def test_正常系_カスタムConfigで初期化できる(self) -> None:
        """AcademicConfig を渡して初期化できることを確認。"""
        config = AcademicConfig(s2_api_key="test-key", cache_ttl=3600)
        with (
            patch("academic.fetcher.S2Client") as mock_s2_cls,
            patch("academic.fetcher.ArxivClient") as mock_arxiv_cls,
            patch("academic.fetcher.get_academic_cache") as mock_cache_fn,
        ):
            mock_s2_cls.return_value = MagicMock()
            mock_arxiv_cls.return_value = MagicMock()
            mock_cache_fn.return_value = MagicMock()

            fetcher = PaperFetcher(config=config)
            assert fetcher is not None
            mock_s2_cls.assert_called_once_with(config=config)
            mock_arxiv_cls.assert_called_once_with(config=config)
            mock_cache_fn.assert_called_once_with(config=config)


class TestPaperFetcherFetchPaper:
    """PaperFetcher.fetch_paper() のテスト."""

    def test_正常系_キャッシュヒットでAPI呼び出しなし(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """キャッシュにデータがある場合、API を呼ばずにキャッシュから返すことを確認。"""
        cached_data = {
            "arxiv_id": "2301.00001",
            "title": "Cached Paper",
            "authors": [{"name": "Alice"}],
            "references": [],
            "citations": [],
            "abstract": "Cached abstract.",
            "s2_paper_id": "s2-cached",
            "published": "2023-01-01",
            "updated": None,
        }
        mock_cache.get.return_value = cached_data

        result = fetcher.fetch_paper("2301.00001")

        assert result.arxiv_id == "2301.00001"
        assert result.title == "Cached Paper"
        mock_s2_client.fetch_paper.assert_not_called()
        mock_arxiv_client.fetch_paper.assert_not_called()

    def test_正常系_S2成功パスでPaperMetadataを返す(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2Client が成功した場合、PaperMetadata に変換して返すことを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_paper.return_value = _sample_s2_response("2301.00001")

        result = fetcher.fetch_paper("2301.00001")

        assert isinstance(result, PaperMetadata)
        assert result.arxiv_id == "2301.00001"
        assert result.title == "Sample Paper Title"
        assert result.s2_paper_id == "s2-paper-abc123"
        assert len(result.authors) == 2
        assert result.authors[0].name == "Alice Doe"
        assert result.authors[0].s2_author_id == "auth-1"
        assert len(result.references) == 1
        assert len(result.citations) == 1
        mock_s2_client.fetch_paper.assert_called_once_with("2301.00001")

    def test_正常系_S2成功後にキャッシュに保存される(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2 から取得成功後、キャッシュに保存されることを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_paper.return_value = _sample_s2_response("2301.00001")

        fetcher.fetch_paper("2301.00001")

        mock_cache.set.assert_called_once()
        cache_key = mock_cache.set.call_args[0][0]
        assert "2301.00001" in cache_key

    def test_正常系_S2_404でarXivフォールバック(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2 で PaperNotFoundError が発生した場合、arXiv にフォールバックすることを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_paper.side_effect = PaperNotFoundError(
            "Paper not found", status_code=404
        )
        mock_arxiv_client.fetch_paper.return_value = _sample_arxiv_paper_metadata(
            "2301.00001"
        )

        result = fetcher.fetch_paper("2301.00001")

        assert isinstance(result, PaperMetadata)
        assert result.title == "Sample Paper Title (arXiv)"
        mock_s2_client.fetch_paper.assert_called_once_with("2301.00001")
        mock_arxiv_client.fetch_paper.assert_called_once_with("2301.00001")

    def test_正常系_S2_500リトライ後arXivフォールバック(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2 で RetryableError（500系）が発生した場合、arXiv にフォールバックすることを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_paper.side_effect = RetryableError(
            "Server error", status_code=500
        )
        mock_arxiv_client.fetch_paper.return_value = _sample_arxiv_paper_metadata(
            "2301.00001"
        )

        result = fetcher.fetch_paper("2301.00001")

        assert isinstance(result, PaperMetadata)
        assert result.title == "Sample Paper Title (arXiv)"
        mock_arxiv_client.fetch_paper.assert_called_once_with("2301.00001")

    def test_正常系_arXivフォールバック成功後もキャッシュに保存される(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """arXiv フォールバック成功後もキャッシュに保存されることを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_paper.side_effect = PaperNotFoundError(
            "Not found", status_code=404
        )
        mock_arxiv_client.fetch_paper.return_value = _sample_arxiv_paper_metadata(
            "2301.00001"
        )

        fetcher.fetch_paper("2301.00001")

        mock_cache.set.assert_called_once()

    def test_異常系_S2とarXiv両方失敗で例外送出(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2 と arXiv 両方が失敗した場合、例外が送出されることを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_paper.side_effect = PaperNotFoundError(
            "Not found (S2)", status_code=404
        )
        mock_arxiv_client.fetch_paper.side_effect = PaperNotFoundError(
            "Not found (arXiv)", status_code=404
        )

        with pytest.raises(PaperNotFoundError):
            fetcher.fetch_paper("9999.99999")


class TestPaperFetcherFetchPapersBatch:
    """PaperFetcher.fetch_papers_batch() のテスト."""

    def test_正常系_キャッシュ済みと未キャッシュの混合バッチ(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """キャッシュ済みと未キャッシュの ID が混在するバッチを正しく処理することを確認。"""
        # "2301.00001" はキャッシュヒット、"2301.00002" はキャッシュミス
        cached_data = {
            "arxiv_id": "2301.00001",
            "title": "Cached Paper",
            "authors": [],
            "references": [],
            "citations": [],
            "abstract": None,
            "s2_paper_id": None,
            "published": None,
            "updated": None,
        }

        def cache_get_side_effect(key: str) -> dict[str, Any] | None:
            if "2301.00001" in key:
                return cached_data
            return None

        mock_cache.get.side_effect = cache_get_side_effect

        # 未キャッシュ分の S2 バッチレスポンス
        mock_s2_client.fetch_papers_batch.return_value = [
            _sample_s2_response("2301.00002"),
        ]

        results = fetcher.fetch_papers_batch(["2301.00001", "2301.00002"])

        assert len(results) == 2
        # キャッシュ済みの論文
        assert results[0].arxiv_id == "2301.00001"
        assert results[0].title == "Cached Paper"
        # S2 から取得した論文
        assert results[1].arxiv_id == "2301.00002"

    def test_正常系_全てキャッシュヒットでAPI呼び出しなし(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """全 ID がキャッシュにある場合、API を呼ばないことを確認。"""
        cached_data = {
            "arxiv_id": "2301.00001",
            "title": "Cached Paper",
            "authors": [],
            "references": [],
            "citations": [],
            "abstract": None,
            "s2_paper_id": None,
            "published": None,
            "updated": None,
        }
        mock_cache.get.return_value = cached_data

        results = fetcher.fetch_papers_batch(["2301.00001", "2301.00002"])

        assert len(results) == 2
        mock_s2_client.fetch_papers_batch.assert_not_called()

    def test_正常系_S2バッチで取得できなかったIDはarXivフォールバック(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_arxiv_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """S2 バッチで取得できなかった ID は arXiv 個別フォールバックすることを確認。"""
        mock_cache.get.return_value = None

        # S2 バッチは "2301.00001" のみ返す（"2301.00002" は None = 取得失敗）
        mock_s2_client.fetch_papers_batch.return_value = [
            _sample_s2_response("2301.00001"),
            None,  # "2301.00002" は S2 で取得できなかった
        ]

        mock_arxiv_client.fetch_paper.return_value = _sample_arxiv_paper_metadata(
            "2301.00002"
        )

        results = fetcher.fetch_papers_batch(["2301.00001", "2301.00002"])

        assert len(results) == 2
        assert results[0].title == "Sample Paper Title"
        assert results[1].title == "Sample Paper Title (arXiv)"
        mock_arxiv_client.fetch_paper.assert_called_once_with("2301.00002")

    def test_正常系_バッチ取得成功後にキャッシュに保存される(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """バッチ取得で成功した分がキャッシュに保存されることを確認。"""
        mock_cache.get.return_value = None
        mock_s2_client.fetch_papers_batch.return_value = [
            _sample_s2_response("2301.00001"),
            _sample_s2_response("2301.00002"),
        ]

        fetcher.fetch_papers_batch(["2301.00001", "2301.00002"])

        # 2件分のキャッシュ set が呼ばれる
        assert mock_cache.set.call_count == 2

    def test_エッジケース_空リストで空結果を返す(
        self,
        fetcher: PaperFetcher,
        mock_s2_client: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """空のリストを渡した場合、空のリストが返ることを確認。"""
        results = fetcher.fetch_papers_batch([])

        assert results == []
        mock_s2_client.fetch_papers_batch.assert_not_called()
        mock_cache.get.assert_not_called()


class TestPaperFetcherParseS2Response:
    """PaperFetcher._parse_s2_response() のテスト."""

    def test_正常系_完全なレスポンスをPaperMetadataに変換(
        self,
        fetcher: PaperFetcher,
    ) -> None:
        """完全な S2 レスポンスを PaperMetadata に正しく変換することを確認。"""
        raw = _sample_s2_response("2301.00001")

        result = fetcher._parse_s2_response(raw, "2301.00001")

        assert isinstance(result, PaperMetadata)
        assert result.arxiv_id == "2301.00001"
        assert result.title == "Sample Paper Title"
        assert result.abstract == "This is a sample abstract."
        assert result.s2_paper_id == "s2-paper-abc123"
        assert result.published == "2023-01-15"
        assert len(result.authors) == 2
        assert result.authors[0].name == "Alice Doe"
        assert result.authors[0].s2_author_id == "auth-1"
        assert len(result.references) == 1
        assert result.references[0].title == "Reference Paper 1"
        assert result.references[0].arxiv_id == "2001.00001"
        assert result.references[0].s2_paper_id == "s2-ref-001"
        assert len(result.citations) == 1
        assert result.citations[0].title == "Citing Paper 1"
        assert result.citations[0].s2_paper_id == "s2-cite-001"

    def test_正常系_欠損フィールドでもパースできる(
        self,
        fetcher: PaperFetcher,
    ) -> None:
        """一部フィールドが欠損している S2 レスポンスでもパースできることを確認。"""
        raw: dict[str, Any] = {
            "paperId": None,
            "title": "Minimal Paper",
            "authors": [],
            "references": None,
            "citations": None,
            "abstract": None,
            "publicationDate": None,
            "externalIds": {},
        }

        result = fetcher._parse_s2_response(raw, "2301.00001")

        assert result.arxiv_id == "2301.00001"
        assert result.title == "Minimal Paper"
        assert result.authors == ()
        assert result.references == ()
        assert result.citations == ()
        assert result.abstract is None
        assert result.s2_paper_id is None

    def test_正常系_著者にauthorIdがない場合Noneになる(
        self,
        fetcher: PaperFetcher,
    ) -> None:
        """著者に authorId がない場合、s2_author_id が None になることを確認。"""
        raw: dict[str, Any] = {
            "paperId": "s2-001",
            "title": "Paper",
            "authors": [{"name": "Unknown Author"}],
            "references": [],
            "citations": [],
            "abstract": None,
            "publicationDate": None,
            "externalIds": {},
        }

        result = fetcher._parse_s2_response(raw, "2301.00001")

        assert result.authors[0].name == "Unknown Author"
        assert result.authors[0].s2_author_id is None

    def test_正常系_引用のexternalIdsからarXivIDを抽出(
        self,
        fetcher: PaperFetcher,
    ) -> None:
        """引用の externalIds から arXiv ID を正しく抽出することを確認。"""
        raw: dict[str, Any] = {
            "paperId": "s2-001",
            "title": "Paper",
            "authors": [],
            "references": [
                {
                    "paperId": "s2-ref-001",
                    "title": "Ref with ArXiv",
                    "externalIds": {"ArXiv": "2001.00001"},
                },
                {
                    "paperId": "s2-ref-002",
                    "title": "Ref without ArXiv",
                    "externalIds": {"DOI": "10.1234/test"},
                },
            ],
            "citations": [],
            "abstract": None,
            "publicationDate": None,
            "externalIds": {},
        }

        result = fetcher._parse_s2_response(raw, "2301.00001")

        assert result.references[0].arxiv_id == "2001.00001"
        assert result.references[1].arxiv_id is None
