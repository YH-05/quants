"""Unit tests for market.edinet_api.session module.

EdinetApiSession の動作を検証するテストスイート。
httpx ベースの HTTP セッションクラスのテスト。

Test TODO List:
- [x] EdinetApiSession: デフォルト値で初期化
- [x] EdinetApiSession: カスタム config / retry_config で初期化
- [x] EdinetApiSession: httpx.Client が生成される
- [x] EdinetApiSession: context manager プロトコル
- [x] EdinetApiSession: 例外発生時も close が呼ばれる
- [x] get(): X-API-Key ヘッダー設定
- [x] get(): polite_delay（monotonic ベース間隔制御）
- [x] get(): params が httpx に渡される
- [x] get(): 429 レスポンスで EdinetApiRateLimitError
- [x] get(): 403 レスポンスで EdinetApiAPIError
- [x] get(): 5xx レスポンスで EdinetApiAPIError
- [x] get(): 正常レスポンスを返却
- [x] get(): SSRF防止 - 許可されたホストへのリクエストが成功する
- [x] get(): SSRF防止 - 不正なホストへのリクエストが ValueError で拒否される
- [x] get(): SSRF防止 - 不正なスキームが ValueError で拒否される
- [x] get_with_retry(): 成功時はリトライなし
- [x] get_with_retry(): 失敗後リトライで成功
- [x] get_with_retry(): 全リトライ失敗で例外
- [x] get_with_retry(): 4xxエラーはリトライしない
- [x] download(): バイナリコンテンツを返却
- [x] close(): セッションが閉じられる
- [x] __all__ エクスポート
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from market.edinet_api.constants import BASE_URL
from market.edinet_api.errors import EdinetApiAPIError, EdinetApiRateLimitError
from market.edinet_api.session import EdinetApiSession
from market.edinet_api.types import EdinetApiConfig, RetryConfig

# Test URL within allowed hosts
_TEST_URL = f"{BASE_URL}/documents.json"

# Download URL within allowed hosts
_TEST_DOWNLOAD_URL = "https://disclosure2dl.edinet-fsa.go.jp/api/v2/documents/S100ABCD"


# =============================================================================
# Initialization tests
# =============================================================================


class TestEdinetApiSessionInit:
    """EdinetApiSession 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの EdinetApiConfig / RetryConfig で初期化されること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = EdinetApiSession()

        assert session._config is not None
        assert session._retry_config is not None
        assert isinstance(session._config, EdinetApiConfig)
        assert isinstance(session._retry_config, RetryConfig)

    def test_正常系_カスタムconfigで初期化できる(self) -> None:
        """カスタム EdinetApiConfig で初期化されること。"""
        config = EdinetApiConfig(api_key="test-key", polite_delay=1.0, timeout=60.0)
        retry_config = RetryConfig(max_attempts=5, initial_delay=0.5)

        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = EdinetApiSession(config=config, retry_config=retry_config)

        assert session._config.api_key == "test-key"
        assert session._config.polite_delay == 1.0
        assert session._config.timeout == 60.0
        assert session._retry_config.max_attempts == 5

    def test_正常系_httpx_ClientがX_API_Keyヘッダーで生成される(self) -> None:
        """httpx.Client が X-API-Key ヘッダー付きで生成されること。"""
        config = EdinetApiConfig(api_key="my-api-key")

        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            EdinetApiSession(config=config)

            call_kwargs = mock_client_cls.call_args[1]
            assert call_kwargs["headers"]["X-API-Key"] == "my-api-key"
            assert call_kwargs["verify"] is True


# =============================================================================
# Context manager tests
# =============================================================================


class TestEdinetApiSessionContextManager:
    """EdinetApiSession context manager のテスト。"""

    def test_正常系_context_managerとして使用できる(self) -> None:
        """with 文で使用できること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            with EdinetApiSession() as session:
                assert isinstance(session, EdinetApiSession)

            mock_client.close.assert_called_once()

    def test_正常系_例外発生時もcloseが呼ばれる(self) -> None:
        """with ブロック内で例外が発生しても close が呼ばれること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            with pytest.raises(RuntimeError), EdinetApiSession() as _session:
                raise RuntimeError("test error")

            mock_client.close.assert_called_once()


# =============================================================================
# get() method tests
# =============================================================================


class TestEdinetApiSessionGet:
    """EdinetApiSession.get() のテスト。"""

    def test_正常系_正常レスポンスを返却(self) -> None:
        """200レスポンスが正しく返却されること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()
            response = session.get(_TEST_URL)

            assert response.status_code == 200

    def test_正常系_paramsがhttpxに渡される(self) -> None:
        """パラメータが httpx に渡されること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()
            params = {"date": "2025-01-15", "type": "2"}
            session.get(_TEST_URL, params=params)

            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["params"] == params

    def test_異常系_429レスポンスでEdinetApiRateLimitError(self) -> None:
        """429レスポンスで EdinetApiRateLimitError が発生すること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()

            with pytest.raises(EdinetApiRateLimitError) as exc_info:
                session.get(_TEST_URL)

            assert exc_info.value.retry_after == 60

    def test_異常系_403レスポンスでEdinetApiAPIError(self) -> None:
        """403レスポンスで EdinetApiAPIError が発生すること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()

            with pytest.raises(EdinetApiAPIError) as exc_info:
                session.get(_TEST_URL)

            assert exc_info.value.status_code == 403

    def test_異常系_500レスポンスでEdinetApiAPIError(self) -> None:
        """500レスポンスで EdinetApiAPIError が発生すること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()

            with pytest.raises(EdinetApiAPIError) as exc_info:
                session.get(_TEST_URL)

            assert exc_info.value.status_code == 500

    def test_異常系_SSRF防止_不正なホストでValueError(self) -> None:
        """不正なホストへのリクエストが ValueError で拒否されること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = EdinetApiSession()

            with pytest.raises(ValueError, match="not in allowed hosts"):
                session.get("https://evil.example.com/api")

    def test_異常系_SSRF防止_不正なスキームでValueError(self) -> None:
        """不正なスキームが ValueError で拒否されること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = EdinetApiSession()

            with pytest.raises(ValueError, match="scheme must be"):
                session.get("ftp://api.edinet-fsa.go.jp/api/v2/documents.json")


# =============================================================================
# get_with_retry() tests
# =============================================================================


class TestEdinetApiSessionGetWithRetry:
    """EdinetApiSession.get_with_retry() のテスト。"""

    def test_正常系_成功時はリトライなし(self) -> None:
        """初回成功時はリトライなしで結果を返すこと。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()
            response = session.get_with_retry(_TEST_URL)

            assert response.status_code == 200
            assert mock_client.get.call_count == 1

    @patch("market.edinet_api.session.time.sleep")
    def test_正常系_失敗後リトライで成功(self, mock_sleep: MagicMock) -> None:
        """1回失敗後にリトライで成功すること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            # First call: 429, second call: 200
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {}

            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200

            mock_client = MagicMock()
            mock_client.get.side_effect = [mock_response_429, mock_response_200]
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession(
                retry_config=RetryConfig(max_attempts=3),
            )
            response = session.get_with_retry(_TEST_URL)

            assert response.status_code == 200
            assert mock_client.get.call_count == 2

    @patch("market.edinet_api.session.time.sleep")
    def test_異常系_全リトライ失敗で例外(self, mock_sleep: MagicMock) -> None:
        """全リトライ失敗で最後の例外が発生すること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {}

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response_429
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession(
                retry_config=RetryConfig(max_attempts=2),
            )

            with pytest.raises(EdinetApiRateLimitError):
                session.get_with_retry(_TEST_URL)

            assert mock_client.get.call_count == 2

    def test_異常系_4xxエラーはリトライしない(self) -> None:
        """4xx（429以外）エラーはリトライせず即座に例外を投げること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response_400 = MagicMock()
            mock_response_400.status_code = 400
            mock_response_400.text = "Bad Request"

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response_400
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession(
                retry_config=RetryConfig(max_attempts=3),
            )

            with pytest.raises(EdinetApiAPIError) as exc_info:
                session.get_with_retry(_TEST_URL)

            assert exc_info.value.status_code == 400
            assert mock_client.get.call_count == 1


# =============================================================================
# download() tests
# =============================================================================


class TestEdinetApiSessionDownload:
    """EdinetApiSession.download() のテスト。"""

    def test_正常系_バイナリコンテンツを返却(self) -> None:
        """ストリーミングダウンロードでバイナリコンテンツが返却されること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]

            mock_client = MagicMock()
            mock_client.stream.return_value.__enter__ = MagicMock(
                return_value=mock_response
            )
            mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()
            content = session.download(_TEST_DOWNLOAD_URL)

            assert content == b"chunk1chunk2"

    def test_異常系_SSRF防止_不正なホストでValueError(self) -> None:
        """ダウンロードでも SSRF 防止が機能すること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = EdinetApiSession()

            with pytest.raises(ValueError, match="not in allowed hosts"):
                session.download("https://evil.example.com/document.zip")


# =============================================================================
# close() tests
# =============================================================================


class TestEdinetApiSessionClose:
    """EdinetApiSession.close() のテスト。"""

    def test_正常系_セッションが閉じられる(self) -> None:
        """close() で httpx.Client が閉じられること。"""
        with patch("market.edinet_api.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            session = EdinetApiSession()
            session.close()

            mock_client.close.assert_called_once()


# =============================================================================
# Module Exports
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_EdinetApiSessionがエクスポートされている(self) -> None:
        """__all__ に EdinetApiSession が含まれていること。"""
        from market.edinet_api import session

        assert hasattr(session, "__all__")
        assert "EdinetApiSession" in session.__all__
