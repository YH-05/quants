"""Unit tests for market.bse.session module.

BseSession の動作を検証するテストスイート。
httpx ベースの HTTP セッションクラスのテスト。

Test TODO List:
- [x] BseSession: デフォルト値で初期化
- [x] BseSession: カスタム config / retry_config で初期化
- [x] BseSession: httpx.Client が生成される
- [x] BseSession: context manager プロトコル
- [x] BseSession: 例外発生時も close が呼ばれる
- [x] get(): polite_delay（monotonic ベース間隔制御）
- [x] get(): ランダム User-Agent ヘッダー設定
- [x] get(): デフォルトヘッダーが含まれる
- [x] get(): params が httpx に渡される
- [x] get(): 429 レスポンスで BseRateLimitError
- [x] get(): 403 レスポンスで BseAPIError
- [x] get(): 5xx レスポンスで BseAPIError
- [x] get(): 正常レスポンスを返却
- [x] get(): timeout が設定される
- [x] get(): SSRF防止 - 許可されたホストへのリクエストが成功する
- [x] get(): SSRF防止 - 不正なホストへのリクエストが ValueError で拒否される
- [x] get(): SSRF防止 - ホストなしURLが ValueError で拒否される
- [x] get_with_retry(): 成功時はリトライなし
- [x] get_with_retry(): 失敗後リトライで成功
- [x] get_with_retry(): 全リトライ失敗で BseRateLimitError
- [x] get_with_retry(): 指数バックオフでディレイが増加する
- [x] get_with_retry(): max_delay 上限でクリップされる
- [x] download(): バイナリコンテンツを返却
- [x] download(): 失敗時に BseAPIError
- [x] close(): セッションが閉じられる
- [x] structlog ロガーの使用
- [x] __all__ エクスポート
"""

from unittest.mock import MagicMock, patch

import pytest

from market.bse.constants import ALLOWED_HOSTS, BASE_URL, DEFAULT_HEADERS
from market.bse.errors import BseAPIError, BseRateLimitError
from market.bse.session import BseSession
from market.bse.types import BseConfig, RetryConfig

# Test URL within allowed hosts
_TEST_URL = f"{BASE_URL}/getScripHeaderData"


# =============================================================================
# Initialization tests
# =============================================================================


class TestBseSessionInit:
    """BseSession 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの BseConfig / RetryConfig で初期化されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = BseSession()

        assert session._config is not None
        assert session._retry_config is not None
        assert isinstance(session._config, BseConfig)
        assert isinstance(session._retry_config, RetryConfig)

    def test_正常系_カスタムconfigで初期化できる(self) -> None:
        """カスタム BseConfig で初期化されること。"""
        config = BseConfig(polite_delay=0.5, timeout=60.0)
        retry_config = RetryConfig(max_attempts=5, initial_delay=0.5)

        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            session = BseSession(config=config, retry_config=retry_config)

        assert session._config.polite_delay == 0.5
        assert session._config.timeout == 60.0
        assert session._retry_config.max_attempts == 5
        assert session._retry_config.initial_delay == 0.5

    def test_正常系_httpx_Clientが生成される(self) -> None:
        """httpx.Client がタイムアウト付きで生成されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            BseSession()
            mock_client_cls.assert_called_once()


# =============================================================================
# Context manager tests
# =============================================================================


class TestBseSessionContextManager:
    """BseSession context manager のテスト。"""

    def test_正常系_context_managerとして使用できる(self) -> None:
        """with 文で使用できること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            with BseSession() as session:
                assert isinstance(session, BseSession)

            mock_client.close.assert_called_once()

    def test_正常系_例外発生時もcloseが呼ばれる(self) -> None:
        """例外発生時もセッションが閉じられること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            with (
                pytest.raises(ValueError, match="test error"),
                BseSession() as _session,
            ):
                raise ValueError("test error")

            mock_client.close.assert_called_once()


# =============================================================================
# get() tests
# =============================================================================


class TestBseSessionGet:
    """BseSession.get() のテスト。"""

    def test_正常系_正常なレスポンスを返却する(
        self, mock_httpx_response_200: MagicMock
    ) -> None:
        """200 レスポンスが正常に返却されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_httpx_response_200
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()
                response = session.get(_TEST_URL)

            assert response.status_code == 200

    def test_正常系_polite_delayがmonotonic制御で適用される(self) -> None:
        """polite_delay が time.monotonic() ベースで適用されること。"""
        config = BseConfig(polite_delay=2.0, delay_jitter=0.0)

        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep") as mock_sleep,
                patch(
                    "market.bse.session.time.monotonic",
                    side_effect=[100.0, 100.0, 100.5, 100.5],
                ),
                patch("market.bse.session.random.uniform", return_value=0.0),
            ):
                session = BseSession(config=config)
                # First request: no delay (no previous request)
                session.get(_TEST_URL)
                # Second request: should wait remaining polite_delay
                session.get(_TEST_URL)

                # Second call should sleep for remaining delay (2.0 - 0.5 = 1.5)
                assert mock_sleep.call_count >= 1
                # Find the polite delay sleep call (should be 1.5s)
                delay_calls = [
                    c[0][0] for c in mock_sleep.call_args_list if c[0][0] > 1.0
                ]
                assert len(delay_calls) >= 1
                assert delay_calls[0] == pytest.approx(1.5, abs=0.01)

    def test_正常系_polite_delay経過済みでsleepスキップ(self) -> None:
        """十分な時間が経過していれば sleep がスキップされること。"""
        config = BseConfig(polite_delay=0.1, delay_jitter=0.0)

        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep") as mock_sleep,
                patch(
                    "market.bse.session.time.monotonic",
                    side_effect=[100.0, 100.0, 101.0, 101.0],
                ),
                patch("market.bse.session.random.uniform", return_value=0.0),
            ):
                session = BseSession(config=config)
                session.get(_TEST_URL)
                session.get(_TEST_URL)

                # Elapsed 1.0s > polite_delay 0.1s → no sleep needed
                polite_sleeps = [
                    c[0][0] for c in mock_sleep.call_args_list if c[0][0] > 0
                ]
                assert len(polite_sleeps) == 0

    def test_正常系_User_Agentヘッダーが設定される(self) -> None:
        """ランダムな User-Agent がヘッダーに設定されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
                patch(
                    "market.bse.session.random.choice",
                    return_value="MockUserAgent/1.0",
                ),
            ):
                session = BseSession()
                session.get(_TEST_URL)

                call_kwargs = mock_client.get.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["User-Agent"] == "MockUserAgent/1.0"

    def test_正常系_デフォルトヘッダーが含まれる(self) -> None:
        """DEFAULT_HEADERS の項目（User-Agent以外）がヘッダーに含まれること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()
                session.get(_TEST_URL)

                call_kwargs = mock_client.get.call_args
                headers = call_kwargs[1]["headers"]
                for key, value in DEFAULT_HEADERS.items():
                    if key == "User-Agent":
                        assert "User-Agent" in headers
                    else:
                        assert headers[key] == value

    def test_正常系_paramsがhttpxに渡される(self) -> None:
        """params が httpx.Client.get に渡されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()
                session.get(
                    _TEST_URL,
                    params={"scripcode": "500325"},
                )

                call_kwargs = mock_client.get.call_args
                assert call_kwargs[1]["params"] == {"scripcode": "500325"}

    def test_正常系_timeoutが設定される(self) -> None:
        """config.timeout がリクエストに渡されること。"""
        config = BseConfig(timeout=15.0)

        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession(config=config)
                session.get(_TEST_URL)

                call_kwargs = mock_client.get.call_args
                assert call_kwargs[1]["timeout"] == 15.0

    def test_異常系_429レスポンスでBseRateLimitError(
        self, mock_httpx_response_429: MagicMock
    ) -> None:
        """429 レスポンスで BseRateLimitError が発生すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_httpx_response_429
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()

                with pytest.raises(BseRateLimitError) as exc_info:
                    session.get(_TEST_URL)

                assert exc_info.value.url == _TEST_URL

    def test_異常系_403レスポンスでBseAPIError(
        self, mock_httpx_response_403: MagicMock
    ) -> None:
        """403 レスポンスで BseAPIError が発生すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_httpx_response_403
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()

                with pytest.raises(BseAPIError) as exc_info:
                    session.get(_TEST_URL)

                assert exc_info.value.status_code == 403

    def test_異常系_5xxレスポンスでBseAPIError(
        self, mock_httpx_response_500: MagicMock
    ) -> None:
        """500 レスポンスで BseAPIError が発生すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_httpx_response_500
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()

                with pytest.raises(BseAPIError) as exc_info:
                    session.get(_TEST_URL)

                assert exc_info.value.status_code == 500


# =============================================================================
# URL whitelist validation tests
# =============================================================================


class TestBseSessionURLWhitelist:
    """BseSession URL ホワイトリスト検証のテスト。"""

    def test_正常系_許可されたホストへのリクエストが成功する(self) -> None:
        """ALLOWED_HOSTS に含まれるホストへのリクエストが成功すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()
                response = session.get(_TEST_URL)

            assert response.status_code == 200

    def test_異常系_不正なホストへのリクエストがValueErrorで拒否される(self) -> None:
        """ALLOWED_HOSTS に含まれないホストが ValueError で拒否されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()

            session = BseSession()

            with pytest.raises(ValueError, match="not in allowed hosts"):
                session.get("https://evil.example.com/api/data")

    def test_異常系_ホストなしURLがValueErrorで拒否される(self) -> None:
        """ホストが空の URL が ValueError で拒否されること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()

            session = BseSession()

            with pytest.raises(ValueError, match="URL scheme must be"):
                session.get("/relative/path/only")

    def test_正常系_ALLOWED_HOSTSにapi_bseindia_comが含まれる(self) -> None:
        """ALLOWED_HOSTS に api.bseindia.com が含まれていること。"""
        assert "api.bseindia.com" in ALLOWED_HOSTS

    def test_正常系_ALLOWED_HOSTSがfrozensetである(self) -> None:
        """ALLOWED_HOSTS が frozenset であること。"""
        assert isinstance(ALLOWED_HOSTS, frozenset)


# =============================================================================
# get_with_retry() tests
# =============================================================================


class TestBseSessionGetWithRetry:
    """BseSession.get_with_retry() のテスト。"""

    def test_正常系_成功時はリトライなし(self) -> None:
        """最初の試行で成功した場合リトライしないこと。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()
                response = session.get_with_retry(_TEST_URL)

            assert response.status_code == 200
            assert mock_client.get.call_count == 1

    def test_正常系_失敗後リトライで成功(self) -> None:
        """失敗後にリトライで成功すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.text = "Too Many Requests"
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200
            mock_client.get.side_effect = [
                mock_response_429,
                mock_response_ok,
            ]
            mock_client_cls.return_value = mock_client

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession(retry_config=retry_config)
                response = session.get_with_retry(_TEST_URL)

            assert response.status_code == 200

    def test_異常系_全リトライ失敗でBseRateLimitError(self) -> None:
        """全リトライが失敗した場合 BseRateLimitError が発生すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.text = "Too Many Requests"
            mock_client.get.return_value = mock_response_429
            mock_client_cls.return_value = mock_client

            retry_config = RetryConfig(max_attempts=2, initial_delay=0.01)

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession(retry_config=retry_config)

                with pytest.raises(BseRateLimitError):
                    session.get_with_retry(_TEST_URL)

    def test_正常系_指数バックオフでディレイが増加する(self) -> None:
        """リトライ間のディレイが指数バックオフで増加すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.text = "Too Many Requests"
            mock_client.get.return_value = mock_response_429
            mock_client_cls.return_value = mock_client

            retry_config = RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=False,
            )

            sleep_calls: list[float] = []

            def track_sleep(duration: float) -> None:
                sleep_calls.append(duration)

            with patch("market.bse.session.time") as mock_time:
                mock_time.monotonic.return_value = 0.0
                mock_time.sleep.side_effect = track_sleep

                session = BseSession(retry_config=retry_config)

                with pytest.raises(BseRateLimitError):
                    session.get_with_retry(_TEST_URL)

            # Should have backoff delays >= 1.0
            retry_delays = [d for d in sleep_calls if d >= 1.0]
            assert len(retry_delays) >= 2

    def test_正常系_max_delay上限でクリップされる(self) -> None:
        """max_delay が指数バックオフの上限としてクリップされること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.text = "Too Many Requests"
            mock_client.get.return_value = mock_response_429
            mock_client_cls.return_value = mock_client

            retry_config = RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                max_delay=5.0,
                exponential_base=10.0,
                jitter=False,
            )

            sleep_calls: list[float] = []

            def track_sleep(duration: float) -> None:
                sleep_calls.append(duration)

            with patch("market.bse.session.time") as mock_time:
                mock_time.monotonic.return_value = 0.0
                mock_time.sleep.side_effect = track_sleep

                session = BseSession(retry_config=retry_config)

                with pytest.raises(BseRateLimitError):
                    session.get_with_retry(_TEST_URL)

            retry_delays = [d for d in sleep_calls if d >= 1.0]
            assert len(retry_delays) >= 2
            for delay in retry_delays:
                assert delay <= 5.0 + 0.01


# =============================================================================
# download() tests
# =============================================================================


class TestBseSessionDownload:
    """BseSession.download() のテスト。"""

    def test_正常系_バイナリコンテンツを返却する(self) -> None:
        """download() がバイナリコンテンツを返却すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"csv,data\n1,2\n"
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()
                content = session.download(_TEST_URL)

            assert content == b"csv,data\n1,2\n"

    def test_異常系_ダウンロード失敗でBseAPIError(self) -> None:
        """download() 失敗時に BseAPIError が発生すること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with (
                patch("market.bse.session.time.sleep"),
                patch("market.bse.session.time.monotonic", return_value=0.0),
            ):
                session = BseSession()

                with pytest.raises(BseAPIError):
                    session.download(_TEST_URL)


# =============================================================================
# close() tests
# =============================================================================


class TestBseSessionClose:
    """BseSession.close() のテスト。"""

    def test_正常系_セッションが閉じられる(self) -> None:
        """close() でセッションが閉じられること。"""
        with patch("market.bse.session.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            session = BseSession()
            session.close()

            mock_client.close.assert_called_once()


# =============================================================================
# Logging tests
# =============================================================================


class TestBseSessionLogging:
    """BseSession のロギングテスト。"""

    def test_正常系_loggerが定義されている(self) -> None:
        """モジュールレベルで structlog ロガーが定義されていること。"""
        import market.bse.session as session_module

        assert hasattr(session_module, "logger")


# =============================================================================
# __all__ export tests
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_BseSessionがエクスポートされている(self) -> None:
        """__all__ に BseSession が含まれていること。"""
        from market.bse.session import __all__

        assert "BseSession" in __all__
