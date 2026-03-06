"""Unit tests for market.edinet_api.client module.

EdinetApiClient の動作を検証するテストスイート。

Test TODO List:
- [x] EdinetApiClient: デフォルト値で初期化（環境変数から読み込み）
- [x] EdinetApiClient: カスタム config で初期化
- [x] EdinetApiClient: context manager プロトコル
- [x] search_documents(): 正常系 - ドキュメントリスト返却
- [x] search_documents(): 正常系 - doc_type フィルタ適用
- [x] search_documents(): 異常系 - 無効な日付形式で EdinetApiValidationError
- [x] search_documents(): 異常系 - 空の日付で EdinetApiValidationError
- [x] download_document(): 正常系 - バイナリコンテンツ返却
- [x] download_document(): 正常系 - フォーマット指定（xbrl/pdf/csv/english）
- [x] download_document(): 異常系 - 空の doc_id で EdinetApiValidationError
- [x] download_document(): 異常系 - 無効なフォーマットで EdinetApiValidationError
- [x] _validate_date(): 日付検証の正常系・異常系
- [x] __all__ エクスポート
"""

from unittest.mock import MagicMock, patch

import pytest

from market.edinet_api.client import EdinetApiClient
from market.edinet_api.errors import EdinetApiValidationError
from market.edinet_api.types import (
    DisclosureDocument,
    DocumentType,
    EdinetApiConfig,
)

# =============================================================================
# Initialization tests
# =============================================================================


class TestEdinetApiClientInit:
    """EdinetApiClient 初期化のテスト。"""

    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_カスタムconfigで初期化できる(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """カスタム EdinetApiConfig で初期化されること。"""
        mock_httpx_client.return_value = MagicMock()
        config = EdinetApiConfig(api_key="test-key", timeout=60.0)
        client = EdinetApiClient(config=config)

        assert client._config.api_key == "test-key"
        assert client._config.timeout == 60.0

    @patch.dict("os.environ", {"EDINET_FSA_API_KEY": "env-api-key"})
    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_環境変数からAPIキーを読み込む(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """config=None の場合、環境変数から API キーを読み込むこと。"""
        mock_httpx_client.return_value = MagicMock()
        client = EdinetApiClient()

        assert client._config.api_key == "env-api-key"


# =============================================================================
# Context manager tests
# =============================================================================


class TestEdinetApiClientContextManager:
    """EdinetApiClient context manager のテスト。"""

    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_context_managerとして使用できる(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """with 文で使用できること。"""
        mock_httpx_client.return_value = MagicMock()
        config = EdinetApiConfig(api_key="test-key")

        with EdinetApiClient(config=config) as client:
            assert isinstance(client, EdinetApiClient)


# =============================================================================
# search_documents() tests
# =============================================================================


class TestSearchDocuments:
    """EdinetApiClient.search_documents() のテスト。"""

    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_ドキュメントリスト返却(self, mock_httpx_client: MagicMock) -> None:
        """正常なレスポンスからドキュメントリストが返却されること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "docID": "S100ABCD",
                    "edinetCode": "E00001",
                    "filerName": "テスト株式会社",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2025-01-15 09:30",
                    "docTypeCode": "120",
                    "secCode": "72010",
                    "JCN": "1234567890123",
                },
                {
                    "docID": "S100EFGH",
                    "edinetCode": "E00002",
                    "filerName": "サンプル株式会社",
                    "docDescription": "四半期報告書",
                    "submitDateTime": "2025-01-15 10:00",
                    "docTypeCode": "140",
                    "secCode": "33010",
                    "JCN": "9876543210123",
                },
            ]
        }

        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_response
        mock_httpx_client.return_value = mock_http_client

        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)
        docs = client.search_documents("2025-01-15")

        assert len(docs) == 2
        assert isinstance(docs[0], DisclosureDocument)
        assert docs[0].doc_id == "S100ABCD"
        assert docs[0].filer_name == "テスト株式会社"
        assert docs[1].doc_id == "S100EFGH"

    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_doc_typeフィルタ適用(self, mock_httpx_client: MagicMock) -> None:
        """doc_type フィルタが適用されること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "docID": "S100ABCD",
                    "edinetCode": "E00001",
                    "filerName": "テスト株式会社",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2025-01-15 09:30",
                },
                {
                    "docID": "S100EFGH",
                    "edinetCode": "E00002",
                    "filerName": "サンプル株式会社",
                    "docDescription": "四半期報告書",
                    "submitDateTime": "2025-01-15 10:00",
                },
            ]
        }

        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_response
        mock_httpx_client.return_value = mock_http_client

        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)
        docs = client.search_documents(
            "2025-01-15",
            doc_type=DocumentType.ANNUAL_REPORT,
        )

        assert len(docs) == 1
        assert docs[0].doc_id == "S100ABCD"
        assert "有価証券報告書" in docs[0].doc_description

    @patch("market.edinet_api.session.httpx.Client")
    def test_異常系_無効な日付形式でEdinetApiValidationError(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """無効な日付形式で EdinetApiValidationError が発生すること。"""
        mock_httpx_client.return_value = MagicMock()
        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)

        with pytest.raises(EdinetApiValidationError, match="Invalid date format"):
            client.search_documents("2025/01/15")

    @patch("market.edinet_api.session.httpx.Client")
    def test_異常系_空の日付でEdinetApiValidationError(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """空の日付で EdinetApiValidationError が発生すること。"""
        mock_httpx_client.return_value = MagicMock()
        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)

        with pytest.raises(EdinetApiValidationError, match="must not be empty"):
            client.search_documents("")


# =============================================================================
# download_document() tests
# =============================================================================


class TestDownloadDocument:
    """EdinetApiClient.download_document() のテスト。"""

    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_バイナリコンテンツ返却(self, mock_httpx_client: MagicMock) -> None:
        """ストリーミングダウンロードでバイナリコンテンツが返却されること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes.return_value = [b"zip-content"]

        mock_http_client = MagicMock()
        mock_http_client.stream.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_http_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_http_client

        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)
        content = client.download_document("S100ABCD", format="xbrl")

        assert content == b"zip-content"

    @patch("market.edinet_api.session.httpx.Client")
    def test_異常系_空のdoc_idでEdinetApiValidationError(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """空の doc_id で EdinetApiValidationError が発生すること。"""
        mock_httpx_client.return_value = MagicMock()
        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)

        with pytest.raises(EdinetApiValidationError, match="must not be empty"):
            client.download_document("", format="xbrl")

    @patch("market.edinet_api.session.httpx.Client")
    def test_異常系_無効なフォーマットでEdinetApiValidationError(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """無効なフォーマットで EdinetApiValidationError が発生すること。"""
        mock_httpx_client.return_value = MagicMock()
        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)

        with pytest.raises(EdinetApiValidationError, match="Invalid format"):
            client.download_document("S100ABCD", format="invalid")

    @patch("market.edinet_api.session.httpx.Client")
    def test_正常系_全フォーマットが有効(self, mock_httpx_client: MagicMock) -> None:
        """xbrl/pdf/csv/english の全フォーマットが有効であること。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes.return_value = [b"content"]

        mock_http_client = MagicMock()
        mock_http_client.stream.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_http_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_http_client

        config = EdinetApiConfig(api_key="test-key")
        client = EdinetApiClient(config=config)

        for fmt in ("xbrl", "pdf", "csv", "english"):
            content = client.download_document("S100ABCD", format=fmt)
            assert content == b"content"


# =============================================================================
# _validate_date() tests
# =============================================================================


class TestValidateDate:
    """EdinetApiClient._validate_date() のテスト。"""

    def test_正常系_有効な日付(self) -> None:
        """有効な日付がエラーなしで検証されること。"""
        EdinetApiClient._validate_date("2025-01-15")
        EdinetApiClient._validate_date("2025-12-31")
        EdinetApiClient._validate_date("2000-01-01")

    def test_異常系_空文字列(self) -> None:
        """空文字列で EdinetApiValidationError が発生すること。"""
        with pytest.raises(EdinetApiValidationError, match="must not be empty"):
            EdinetApiClient._validate_date("")

    def test_異常系_不正な区切り文字(self) -> None:
        """不正な区切り文字で EdinetApiValidationError が発生すること。"""
        with pytest.raises(EdinetApiValidationError, match="Invalid date format"):
            EdinetApiClient._validate_date("2025/01/15")

    def test_異常系_数値以外の値(self) -> None:
        """数値以外の値で EdinetApiValidationError が発生すること。"""
        with pytest.raises(EdinetApiValidationError, match="numeric values"):
            EdinetApiClient._validate_date("abcd-ef-gh")

    def test_異常系_年が範囲外(self) -> None:
        """年が範囲外で EdinetApiValidationError が発生すること。"""
        with pytest.raises(EdinetApiValidationError, match="Year.*out of range"):
            EdinetApiClient._validate_date("1999-01-15")

    def test_異常系_月が範囲外(self) -> None:
        """月が範囲外で EdinetApiValidationError が発生すること。"""
        with pytest.raises(EdinetApiValidationError, match="Month.*out of range"):
            EdinetApiClient._validate_date("2025-13-15")

    def test_異常系_日が範囲外(self) -> None:
        """日が範囲外で EdinetApiValidationError が発生すること。"""
        with pytest.raises(EdinetApiValidationError, match="Day.*out of range"):
            EdinetApiClient._validate_date("2025-01-32")


# =============================================================================
# Module Exports
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_EdinetApiClientがエクスポートされている(self) -> None:
        """__all__ に EdinetApiClient が含まれていること。"""
        from market.edinet_api import client

        assert hasattr(client, "__all__")
        assert "EdinetApiClient" in client.__all__
