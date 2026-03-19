"""S2Client の単体テスト.

Semantic Scholar API クライアントの動作を検証する。
httpx.Client はモックし、HTTP レスポンスのパース・エラーハンドリング・
バッチ分割ロジックをテストする。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from academic.errors import (
    PaperNotFoundError,
    RateLimitError,
    RetryableError,
)
from academic.s2_client import S2Client
from academic.types import AcademicConfig


def _make_response(
    status_code: int = 200,
    json_data: Any = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """テスト用の httpx.Response を生成するヘルパー."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        headers=headers or {},
        request=httpx.Request("GET", "https://api.semanticscholar.org/test"),
    )
    return resp


def _sample_paper_json(arxiv_id: str = "2301.00001") -> dict[str, Any]:
    """Semantic Scholar API の論文レスポンスのサンプル JSON を返す."""
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


class TestS2ClientInit:
    """S2Client.__init__() のテスト."""

    def test_正常系_デフォルト設定で初期化できる(self) -> None:
        """デフォルト AcademicConfig で S2Client を初期化できることを確認。"""
        client = S2Client()
        try:
            assert isinstance(client, S2Client)
            assert hasattr(client, "_http_client")
            assert hasattr(client, "_rate_limiter")
        finally:
            client.close()

    def test_正常系_カスタム設定で初期化できる(self) -> None:
        """カスタム AcademicConfig で S2Client を初期化できることを確認。"""
        config = AcademicConfig(
            s2_api_key="test-key",
            s2_rate_limit=0.5,
            timeout=60.0,
        )
        client = S2Client(config=config)
        try:
            assert isinstance(client, S2Client)
            assert client._api_key == "test-key"
        finally:
            client.close()

    def test_正常系_環境変数からAPIキーを取得する(self) -> None:
        """S2_API_KEY 環境変数から API キーを取得できることを確認。"""
        with patch.dict("os.environ", {"S2_API_KEY": "env-api-key"}):
            config = AcademicConfig()
            client = S2Client(config=config)
            try:
                assert client._api_key == "env-api-key"
            finally:
                client.close()

    def test_正常系_設定のAPIキーが環境変数より優先される(self) -> None:
        """AcademicConfig.s2_api_key が環境変数より優先されることを確認。"""
        with patch.dict("os.environ", {"S2_API_KEY": "env-key"}):
            config = AcademicConfig(s2_api_key="config-key")
            client = S2Client(config=config)
            try:
                assert client._api_key == "config-key"
            finally:
                client.close()


class TestS2ClientFetchPaper:
    """S2Client.fetch_paper() のテスト."""

    def test_正常系_200レスポンスをパースできる(self) -> None:
        """200 レスポンスの JSON を正しくパースして dict を返すことを確認。"""
        sample_json = _sample_paper_json("2301.00001")
        mock_response = _make_response(status_code=200, json_data=sample_json)

        client = S2Client()
        try:
            with patch.object(client._http_client, "get", return_value=mock_response):
                result = client.fetch_paper("2301.00001")

            assert result["title"] == "Sample Paper Title"
            assert result["abstract"] == "This is a sample abstract."
            assert len(result["authors"]) == 2
            assert result["authors"][0]["name"] == "Alice Doe"
            assert len(result["references"]) == 1
            assert len(result["citations"]) == 1
        finally:
            client.close()

    def test_異常系_404でPaperNotFoundErrorが発生する(self) -> None:
        """HTTP 404 で PaperNotFoundError が送出されることを確認。"""
        mock_response = _make_response(
            status_code=404, json_data={"error": "Not Found"}
        )

        client = S2Client()
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                pytest.raises(PaperNotFoundError) as exc_info,
            ):
                client.fetch_paper("9999.99999")

            assert exc_info.value.status_code == 404
        finally:
            client.close()

    def test_異常系_429でRateLimitErrorが発生する(self) -> None:
        """HTTP 429 で RateLimitError が送出されることを確認。"""
        mock_response = _make_response(
            status_code=429,
            json_data={"error": "Too Many Requests"},
            headers={"Retry-After": "30"},
        )

        config = AcademicConfig(max_retries=1)
        client = S2Client(config=config)
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                pytest.raises(RateLimitError) as exc_info,
            ):
                client.fetch_paper("2301.00001")

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 30
        finally:
            client.close()

    def test_異常系_500でRetryableErrorが発生する(self) -> None:
        """HTTP 500 で RetryableError が送出されることを確認。"""
        mock_response = _make_response(
            status_code=500, json_data={"error": "Internal Server Error"}
        )

        config = AcademicConfig(max_retries=1)
        client = S2Client(config=config)
        try:
            with (
                patch.object(client._http_client, "get", return_value=mock_response),
                pytest.raises(RetryableError) as exc_info,
            ):
                client.fetch_paper("2301.00001")

            assert exc_info.value.status_code == 500
        finally:
            client.close()

    def test_正常系_APIキーがヘッダーに設定される(self) -> None:
        """API キーが x-api-key ヘッダーに設定されることを確認。"""
        sample_json = _sample_paper_json()
        mock_response = _make_response(status_code=200, json_data=sample_json)

        config = AcademicConfig(s2_api_key="test-api-key-123")
        client = S2Client(config=config)
        try:
            with patch.object(client._http_client, "get", return_value=mock_response):
                client.fetch_paper("2301.00001")

            # httpx.Client にヘッダーが設定されていることを確認
            # (Client 初期化時に headers として渡される)
            assert client._http_client.headers.get("x-api-key") == "test-api-key-123"
        finally:
            client.close()

    def test_正常系_APIキーなしの場合ヘッダーに含まれない(self) -> None:
        """API キーが None の場合 x-api-key ヘッダーが含まれないことを確認。"""
        sample_json = _sample_paper_json()
        mock_response = _make_response(status_code=200, json_data=sample_json)

        with patch.dict("os.environ", {}, clear=True):
            config = AcademicConfig(s2_api_key=None)
            client = S2Client(config=config)
            try:
                with patch.object(
                    client._http_client, "get", return_value=mock_response
                ):
                    client.fetch_paper("2301.00001")

                assert "x-api-key" not in client._http_client.headers
            finally:
                client.close()


class TestS2ClientFetchPapersBatch:
    """S2Client.fetch_papers_batch() のテスト."""

    def test_正常系_バッチ取得で複数論文を取得できる(self) -> None:
        """バッチ API で複数論文を取得できることを確認。"""
        batch_response = [
            _sample_paper_json("2301.00001"),
            _sample_paper_json("2301.00002"),
        ]
        mock_response = _make_response(status_code=200, json_data=batch_response)

        client = S2Client()
        try:
            with patch.object(client._http_client, "post", return_value=mock_response):
                results = client.fetch_papers_batch(["2301.00001", "2301.00002"])

            assert len(results) == 2
            assert results[0]["externalIds"]["ArXiv"] == "2301.00001"
            assert results[1]["externalIds"]["ArXiv"] == "2301.00002"
        finally:
            client.close()

    def test_正常系_500件超のバッチが自動分割される(self) -> None:
        """500件を超えるバッチリクエストが自動分割されることを確認。"""
        arxiv_ids = [f"2301.{i:05d}" for i in range(750)]

        # 2回のPOSTリクエストが発生するはず（500件 + 250件）
        batch_1 = [_sample_paper_json(f"2301.{i:05d}") for i in range(500)]
        batch_2 = [_sample_paper_json(f"2301.{i:05d}") for i in range(500, 750)]

        response_1 = _make_response(status_code=200, json_data=batch_1)
        response_2 = _make_response(status_code=200, json_data=batch_2)

        client = S2Client()
        try:
            with patch.object(
                client._http_client, "post", side_effect=[response_1, response_2]
            ) as mock_post:
                results = client.fetch_papers_batch(arxiv_ids)

            assert mock_post.call_count == 2
            assert len(results) == 750
        finally:
            client.close()

    def test_正常系_ちょうど500件はリクエスト1回(self) -> None:
        """ちょうど500件のバッチは1回のリクエストで処理されることを確認。"""
        arxiv_ids = [f"2301.{i:05d}" for i in range(500)]
        batch = [_sample_paper_json(f"2301.{i:05d}") for i in range(500)]
        mock_response = _make_response(status_code=200, json_data=batch)

        client = S2Client()
        try:
            with patch.object(
                client._http_client, "post", return_value=mock_response
            ) as mock_post:
                results = client.fetch_papers_batch(arxiv_ids)

            assert mock_post.call_count == 1
            assert len(results) == 500
        finally:
            client.close()

    def test_エッジケース_空リストで空結果を返す(self) -> None:
        """空のリストを渡した場合、空のリストが返ることを確認。"""
        client = S2Client()
        try:
            results = client.fetch_papers_batch([])
            assert results == []
        finally:
            client.close()

    def test_異常系_バッチ中に500エラーでRetryableError(self) -> None:
        """バッチリクエスト中に HTTP 500 で RetryableError が送出されることを確認。"""
        mock_response = _make_response(
            status_code=500, json_data={"error": "Internal Server Error"}
        )

        config = AcademicConfig(max_retries=1)
        client = S2Client(config=config)
        try:
            with (
                patch.object(client._http_client, "post", return_value=mock_response),
                pytest.raises(RetryableError),
            ):
                client.fetch_papers_batch(["2301.00001"])
        finally:
            client.close()


class TestS2ClientClose:
    """S2Client.close() のテスト."""

    def test_正常系_closeでhttpxクライアントがクローズされる(self) -> None:
        """close() で内部の httpx.Client が閉じられることを確認。"""
        client = S2Client()
        mock_close = MagicMock()
        client._http_client.close = mock_close

        client.close()

        mock_close.assert_called_once()

    def test_正常系_コンテキストマネージャで自動クローズされる(self) -> None:
        """with 文で S2Client を使用した場合、自動的に close されることを確認。"""
        with S2Client() as client:
            assert isinstance(client, S2Client)
            mock_close = MagicMock()
            client._http_client.close = mock_close

        mock_close.assert_called_once()


class TestS2ClientRateLimiter:
    """S2Client のレート制限テスト."""

    def test_正常系_RateLimiterがリクエスト前に呼ばれる(self) -> None:
        """fetch_paper 呼び出し時に RateLimiter.acquire() が呼ばれることを確認。"""
        sample_json = _sample_paper_json()
        mock_response = _make_response(status_code=200, json_data=sample_json)

        client = S2Client()
        try:
            mock_acquire = MagicMock()
            client._rate_limiter.acquire = mock_acquire

            with patch.object(client._http_client, "get", return_value=mock_response):
                client.fetch_paper("2301.00001")

            mock_acquire.assert_called_once()
        finally:
            client.close()

    def test_正常系_バッチリクエストでもRateLimiterが呼ばれる(self) -> None:
        """fetch_papers_batch 呼び出し時に RateLimiter.acquire() が呼ばれることを確認。"""
        batch_response = [_sample_paper_json("2301.00001")]
        mock_response = _make_response(status_code=200, json_data=batch_response)

        client = S2Client()
        try:
            mock_acquire = MagicMock()
            client._rate_limiter.acquire = mock_acquire

            with patch.object(client._http_client, "post", return_value=mock_response):
                client.fetch_papers_batch(["2301.00001"])

            mock_acquire.assert_called_once()
        finally:
            client.close()
