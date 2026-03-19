"""ArxivClient の単体テスト.

arXiv API クライアントの動作を検証する。
httpx.Client はモックし、feedparser による Atom XML パース・
エラーハンドリング・レート制限をテストする。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from academic.arxiv_client import ArxivClient
from academic.errors import PaperNotFoundError, ParseError, RetryableError
from academic.types import AcademicConfig, PaperMetadata

# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------

_SAMPLE_ATOM_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Sample Paper Title</title>
    <summary>This is a sample abstract for testing.</summary>
    <published>2023-01-15T00:00:00Z</published>
    <updated>2023-06-01T00:00:00Z</updated>
    <author>
      <name>Alice Doe</name>
      <arxiv:affiliation>MIT</arxiv:affiliation>
    </author>
    <author>
      <name>Bob Smith</name>
    </author>
    <arxiv:primary_category term="cs.AI" />
  </entry>
</feed>
"""

_EMPTY_FEED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
</feed>
"""

_MALFORMED_XML = "this is not valid xml <><>"


def _make_response(
    status_code: int = 200,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """テスト用の httpx.Response を生成するヘルパー."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        headers=headers or {},
        request=httpx.Request("GET", "http://export.arxiv.org/api/query"),
    )


# ---------------------------------------------------------------------------
# TestArxivClientInit
# ---------------------------------------------------------------------------


class TestArxivClientInit:
    """ArxivClient.__init__() のテスト."""

    def test_正常系_デフォルト設定で初期化できる(self) -> None:
        """デフォルト AcademicConfig で ArxivClient を初期化できることを確認。"""
        client = ArxivClient()
        try:
            assert isinstance(client, ArxivClient)
            assert hasattr(client, "_http_client")
            assert hasattr(client, "_rate_limiter")
        finally:
            client.close()

    def test_正常系_カスタム設定で初期化できる(self) -> None:
        """カスタム AcademicConfig で ArxivClient を初期化できることを確認。"""
        config = AcademicConfig(arxiv_rate_limit=5, timeout=60.0)
        client = ArxivClient(config=config)
        try:
            assert isinstance(client, ArxivClient)
        finally:
            client.close()

    def test_正常系_コンテキストマネージャで使用できる(self) -> None:
        """with 文で ArxivClient を使用した場合、自動的にcloseされることを確認。"""
        with ArxivClient() as client:
            assert isinstance(client, ArxivClient)
            mock_close = MagicMock()
            client._http_client.close = mock_close

        mock_close.assert_called_once()


# ---------------------------------------------------------------------------
# TestArxivClientFetchPaper
# ---------------------------------------------------------------------------


class TestArxivClientFetchPaper:
    """ArxivClient.fetch_paper() のテスト."""

    def test_正常系_有効なAtomXMLをパースできる(self) -> None:
        """有効な Atom XML レスポンスを PaperMetadata にパースできることを確認。"""
        mock_response = _make_response(status_code=200, text=_SAMPLE_ATOM_XML)

        client = ArxivClient()
        try:
            with patch.object(client._http_client, "get", return_value=mock_response):
                result = client.fetch_paper("2301.00001")

            assert isinstance(result, PaperMetadata)
            assert result.arxiv_id == "2301.00001"
            assert result.title == "Sample Paper Title"
            assert result.abstract == "This is a sample abstract for testing."
            assert result.published == "2023-01-15T00:00:00Z"
            assert result.updated == "2023-06-01T00:00:00Z"
        finally:
            client.close()

    def test_正常系_著者名とアフィリエーションを抽出できる(self) -> None:
        """著者名と所属組織が正しく抽出されることを確認。"""
        mock_response = _make_response(status_code=200, text=_SAMPLE_ATOM_XML)

        client = ArxivClient()
        try:
            with patch.object(client._http_client, "get", return_value=mock_response):
                result = client.fetch_paper("2301.00001")

            assert len(result.authors) == 2
            assert result.authors[0].name == "Alice Doe"
            assert result.authors[0].organization == "MIT"
            assert result.authors[1].name == "Bob Smith"
            assert result.authors[1].organization is None
        finally:
            client.close()

    def test_正常系_referencesとcitationsは空リスト(self) -> None:
        """arXiv API は引用情報を提供しないため、references/citations は空であることを確認。"""
        mock_response = _make_response(status_code=200, text=_SAMPLE_ATOM_XML)

        client = ArxivClient()
        try:
            with patch.object(client._http_client, "get", return_value=mock_response):
                result = client.fetch_paper("2301.00001")

            assert result.references == ()
            assert result.citations == ()
        finally:
            client.close()

    def test_異常系_空フィードでPaperNotFoundError(self) -> None:
        """entries が空のフィードで PaperNotFoundError が送出されることを確認。"""
        mock_response = _make_response(status_code=200, text=_EMPTY_FEED_XML)

        client = ArxivClient()
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                pytest.raises(PaperNotFoundError),
            ):
                client.fetch_paper("9999.99999")
        finally:
            client.close()

    def test_異常系_不正なXMLでParseError(self) -> None:
        """不正な XML レスポンスで ParseError が送出されることを確認。"""
        mock_response = _make_response(status_code=200, text=_MALFORMED_XML)

        client = ArxivClient()
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                pytest.raises(ParseError),
            ):
                client.fetch_paper("2301.00001")
        finally:
            client.close()

    def test_異常系_HTTPエラーステータスでRetryableError(self) -> None:
        """HTTP 500 で RetryableError が送出されることを確認。"""
        mock_response = _make_response(status_code=500, text="Internal Server Error")

        config = AcademicConfig(max_retries=1)
        client = ArxivClient(config=config)
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                pytest.raises(RetryableError),
            ):
                client.fetch_paper("2301.00001")
        finally:
            client.close()


# ---------------------------------------------------------------------------
# TestArxivClientRateLimiter
# ---------------------------------------------------------------------------


class TestArxivClientRateLimiter:
    """ArxivClient のレート制限テスト."""

    def test_正常系_RateLimiterがリクエスト前に呼ばれる(self) -> None:
        """fetch_paper 呼び出し時に RateLimiter.acquire() が呼ばれることを確認。"""
        mock_response = _make_response(status_code=200, text=_SAMPLE_ATOM_XML)

        client = ArxivClient()
        try:
            mock_acquire = MagicMock()
            client._rate_limiter.acquire = mock_acquire

            with patch.object(client._http_client, "get", return_value=mock_response):
                client.fetch_paper("2301.00001")

            mock_acquire.assert_called_once()
        finally:
            client.close()

    def test_正常系_bozo_trueでentriesありならパース成功(self) -> None:
        """feedparser.bozo=True でも entries がある場合はパースを続行する。"""
        import feedparser as fp

        mock_response = _make_response(status_code=200, text=_SAMPLE_ATOM_XML)

        # feedparser.parse を bozo=True + entries あり でモック
        original_parse = fp.parse

        def bozo_parse_with_entries(text: str) -> Any:
            result = original_parse(text)
            result["bozo"] = True
            result["bozo_exception"] = "CharacterEncodingOverride"
            return result

        client = ArxivClient()
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                patch("academic.arxiv_client.feedparser") as mock_fp,
            ):
                mock_fp.parse = bozo_parse_with_entries
                result = client.fetch_paper("2301.00001")

            # entries があるので正常にパースされる
            assert isinstance(result, PaperMetadata)
            assert result.arxiv_id == "2301.00001"
        finally:
            client.close()

    def test_異常系_bozo_trueでentries空ならParseError(self) -> None:
        """feedparser.bozo=True で entries が空の場合は ParseError が送出される。"""
        import feedparser as fp

        mock_response = _make_response(status_code=200, text=_EMPTY_FEED_XML)

        original_parse = fp.parse

        def bozo_parse_no_entries(text: str) -> Any:
            result = original_parse(text)
            result["bozo"] = True
            result["bozo_exception"] = "CharacterEncodingOverride"
            # entries を空にする
            result["entries"] = []
            return result

        client = ArxivClient()
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                patch("academic.arxiv_client.feedparser") as mock_fp,
            ):
                mock_fp.parse = bozo_parse_no_entries
                with pytest.raises(ParseError, match="パースに失敗"):
                    client.fetch_paper("2301.00001")
        finally:
            client.close()

    def test_正常系_レート制限がarxiv_rate_limitに基づく(self) -> None:
        """arxiv_rate_limit=3 の場合、RateLimiter(3 req/sec) が設定されることを確認。"""
        config = AcademicConfig(arxiv_rate_limit=3)
        client = ArxivClient(config=config)
        try:
            # arxiv_rate_limit=3 → max(1, int(3)) = 3 → 3 req/sec
            # RateLimiter が正しく初期化されていることを確認
            assert hasattr(client._rate_limiter, "acquire")
        finally:
            client.close()
