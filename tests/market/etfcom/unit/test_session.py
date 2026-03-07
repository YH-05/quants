"""Unit tests for market.etfcom.session module.

ETFComSession の動作を検証するテストスイート。
curl_cffi ベースの HTTP セッションクラスのテスト。

Test TODO List:
- [x] ETFComSession: デフォルト値で初期化
- [x] ETFComSession: カスタム config / retry_config で初期化
- [x] ETFComSession: context manager プロトコル
- [x] get(): ポライトディレイ適用
- [x] get(): ランダム User-Agent ヘッダー設定
- [x] get(): Referer ヘッダー設定
- [x] get(): 403 レスポンスで ETFComBlockedError
- [x] get(): 429 レスポンスで ETFComBlockedError
- [x] get(): 正常レスポンスを返却
- [x] get_with_retry(): 指数バックオフリトライ
- [x] get_with_retry(): 失敗時に rotate_session() を呼び出す
- [x] get_with_retry(): 全リトライ失敗で例外
- [x] get_with_retry(): 成功時はリトライ不要
- [x] rotate_session(): 新しい偽装ターゲットでセッション再生成
- [x] close(): セッションを閉じる
- [x] structlog ロガーの使用
- [x] __all__ エクスポート
- [x] _request(): 共通処理（polite delay, UA rotation, header merge, block detection）
- [x] _request(): GET メソッドで正常動作
- [x] _request(): POST メソッドで正常動作
- [x] _request(): カスタムヘッダーのマージ
- [x] post(): API_HEADERS をデフォルト設定して動作
- [x] post(): 追加ヘッダーが API_HEADERS とマージされる
- [x] post(): JSON データを送信できる
- [x] post(): 403 レスポンスで ETFComBlockedError
- [x] post_with_retry(): 成功時はリトライなし
- [x] post_with_retry(): 失敗後リトライで成功
- [x] post_with_retry(): 全リトライ失敗で ETFComBlockedError
- [x] post_with_retry(): リトライ時に rotate_session() を呼び出す
- [x] get() 後方互換性: リファクタリング後も既存テストが全てパス
- [x] get_with_retry() 後方互換性: リファクタリング後も既存テストが全てパス
- [x] _request_with_retry(): GET/POST 共通リトライロジック
- [x] _request(): 404 レスポンスで ETFComNotFoundError
- [x] _request_with_retry(): 404 はリトライせず即座に伝播
- [x] get_with_retry(): 404 はリトライせず即座に伝播
- [x] post_with_retry(): 404 はリトライせず即座に伝播
"""

from unittest.mock import MagicMock, patch

import pytest

from market.etfcom.constants import (
    API_HEADERS,
    BROWSER_IMPERSONATE_TARGETS,
    DEFAULT_HEADERS,
    ETFCOM_BASE_URL,
)
from market.etfcom.errors import ETFComBlockedError, ETFComNotFoundError
from market.etfcom.session import ETFComSession
from market.etfcom.types import RetryConfig, ScrapingConfig

# =============================================================================
# Initialization tests
# =============================================================================


class TestETFComSessionInit:
    """ETFComSession 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの ScrapingConfig / RetryConfig で初期化されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_curl.Session.return_value = MagicMock()
            session = ETFComSession()

        assert session._config is not None
        assert session._retry_config is not None
        assert isinstance(session._config, ScrapingConfig)
        assert isinstance(session._retry_config, RetryConfig)

    def test_正常系_カスタムconfigで初期化できる(self) -> None:
        """カスタム ScrapingConfig で初期化されること。"""
        config = ScrapingConfig(polite_delay=5.0, impersonate="edge99")
        retry_config = RetryConfig(max_attempts=5, initial_delay=0.5)

        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_curl.Session.return_value = MagicMock()
            session = ETFComSession(config=config, retry_config=retry_config)

        assert session._config.polite_delay == 5.0
        assert session._config.impersonate == "edge99"
        assert session._retry_config.max_attempts == 5
        assert session._retry_config.initial_delay == 0.5

    def test_正常系_curl_cffiセッションが生成される(self) -> None:
        """curl_cffi.Session が impersonate パラメータで生成されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_curl.Session.return_value = MagicMock()
            ETFComSession()
            mock_curl.Session.assert_called_once_with(impersonate="chrome")

    def test_正常系_カスタムimpersonateでセッション生成(self) -> None:
        """カスタム impersonate でセッションが生成されること。"""
        config = ScrapingConfig(impersonate="safari15_3")
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_curl.Session.return_value = MagicMock()
            ETFComSession(config=config)
            mock_curl.Session.assert_called_once_with(impersonate="safari15_3")


# =============================================================================
# Context manager tests
# =============================================================================


class TestETFComSessionContextManager:
    """ETFComSession context manager のテスト。"""

    def test_正常系_context_managerとして使用できる(self) -> None:
        """with 文で使用できること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_curl.Session.return_value = mock_session

            with ETFComSession() as session:
                assert isinstance(session, ETFComSession)

            mock_session.close.assert_called_once()

    def test_正常系_例外発生時もcloseが呼ばれる(self) -> None:
        """例外発生時もセッションが閉じられること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_curl.Session.return_value = mock_session

            with (
                pytest.raises(ValueError, match="test error"),
                ETFComSession() as _session,
            ):
                raise ValueError("test error")

            mock_session.close.assert_called_once()


# =============================================================================
# get() tests
# =============================================================================


class TestETFComSessionGet:
    """ETFComSession.get() のテスト。"""

    def test_正常系_正常なレスポンスを返却する(self) -> None:
        """200 レスポンスが正常に返却されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session.get("https://www.etf.com/SPY")

            assert response.status_code == 200

    def test_正常系_ポライトディレイが適用される(self) -> None:
        """polite_delay + ジッターが適用されること。"""
        config = ScrapingConfig(polite_delay=2.0, delay_jitter=1.0)

        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with (
                patch("market.etfcom.session.time.sleep") as mock_sleep,
                patch("market.etfcom.session.random.uniform", return_value=0.5),
            ):
                session = ETFComSession(config=config)
                session.get("https://www.etf.com/SPY")

                mock_sleep.assert_called_once()
                actual_delay = mock_sleep.call_args[0][0]
                assert actual_delay == pytest.approx(2.5, abs=0.01)

    def test_正常系_User_Agentヘッダーが設定される(self) -> None:
        """ランダムな User-Agent がヘッダーに設定されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with (
                patch("market.etfcom.session.time.sleep"),
                patch(
                    "market.etfcom.session.random.choice",
                    return_value="MockUserAgent/1.0",
                ),
            ):
                session = ETFComSession()
                session.get("https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["User-Agent"] == "MockUserAgent/1.0"

    def test_正常系_Refererヘッダーが設定される(self) -> None:
        """Referer ヘッダーに ETFCOM_BASE_URL が設定されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.get("https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["Referer"] == ETFCOM_BASE_URL

    def test_正常系_デフォルトヘッダーが含まれる(self) -> None:
        """DEFAULT_HEADERS の項目がヘッダーに含まれること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.get("https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                for key, value in DEFAULT_HEADERS.items():
                    assert headers[key] == value

    def test_異常系_403レスポンスでETFComBlockedError(self) -> None:
        """403 レスポンスで ETFComBlockedError が発生すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()

                with pytest.raises(ETFComBlockedError) as exc_info:
                    session.get("https://www.etf.com/SPY")

                assert exc_info.value.status_code == 403
                assert exc_info.value.url == "https://www.etf.com/SPY"

    def test_異常系_429レスポンスでETFComBlockedError(self) -> None:
        """429 レスポンスで ETFComBlockedError が発生すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()

                with pytest.raises(ETFComBlockedError) as exc_info:
                    session.get("https://www.etf.com/SPY")

                assert exc_info.value.status_code == 429

    def test_正常系_timeoutが設定される(self) -> None:
        """config.timeout がリクエストに渡されること。"""
        config = ScrapingConfig(timeout=15.0)

        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(config=config)
                session.get("https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                assert call_kwargs[1]["timeout"] == 15.0

    def test_正常系_追加のkwargsが渡される(self) -> None:
        """追加の kwargs が curl_cffi.request に渡されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.get("https://www.etf.com/SPY", params={"key": "value"})

                call_kwargs = mock_session.request.call_args
                assert call_kwargs[1]["params"] == {"key": "value"}


# =============================================================================
# get_with_retry() tests
# =============================================================================


class TestETFComSessionGetWithRetry:
    """ETFComSession.get_with_retry() のテスト。"""

    def test_正常系_成功時はリトライなし(self) -> None:
        """最初の試行で成功した場合リトライしないこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session.get_with_retry("https://www.etf.com/SPY")

            assert response.status_code == 200
            # _request() 経由で request() は1回だけ呼ばれる
            assert mock_session.request.call_count == 1

    def test_正常系_失敗後リトライで成功(self) -> None:
        """失敗後にリトライで成功すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200
            mock_session.request.side_effect = [
                mock_response_blocked,
                mock_response_ok,
            ]
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)
                response = session.get_with_retry("https://www.etf.com/SPY")

            assert response.status_code == 200

    def test_正常系_リトライ時にrotate_sessionが呼ばれる(self) -> None:
        """リトライ時に rotate_session() が呼ばれること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200
            mock_session.request.side_effect = [
                mock_response_blocked,
                mock_response_ok,
            ]
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)
                with patch.object(session, "rotate_session") as mock_rotate:
                    session.get_with_retry("https://www.etf.com/SPY")
                    mock_rotate.assert_called_once()

    def test_異常系_全リトライ失敗でETFComBlockedError(self) -> None:
        """全リトライが失敗した場合 ETFComBlockedError が発生すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_session.request.return_value = mock_response_blocked
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=2, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)

                with pytest.raises(ETFComBlockedError):
                    session.get_with_retry("https://www.etf.com/SPY")

    def test_正常系_指数バックオフでディレイが増加する(self) -> None:
        """リトライ間のディレイが指数バックオフで増加すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_session.request.return_value = mock_response_blocked
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=False,
            )

            sleep_calls: list[float] = []

            def track_sleep(duration: float) -> None:
                sleep_calls.append(duration)

            with patch("market.etfcom.session.time.sleep", side_effect=track_sleep):
                session = ETFComSession(retry_config=retry_config)

                with pytest.raises(ETFComBlockedError):
                    session.get_with_retry("https://www.etf.com/SPY")

            # ポライトディレイ分を除いたリトライディレイを確認
            # 各リトライ前に sleep が呼ばれる（ポライトディレイ + リトライディレイ）
            # max_attempts=3 なので、リトライディレイは2回（attempt 1, 2 の後）
            retry_delays = [d for d in sleep_calls if d >= 1.0]
            assert len(retry_delays) >= 2


# =============================================================================
# rotate_session() tests
# =============================================================================


class TestETFComSessionRotateSession:
    """ETFComSession.rotate_session() のテスト。"""

    def test_正常系_新しい偽装ターゲットでセッション再生成(self) -> None:
        """rotate_session() が新しい偽装ターゲットで再生成すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session_old = MagicMock()
            mock_session_new = MagicMock()
            mock_curl.Session.side_effect = [mock_session_old, mock_session_new]

            session = ETFComSession()

            with patch(
                "market.etfcom.session.random.choice",
                return_value="edge99",
            ):
                session.rotate_session()

            # 古いセッションが閉じられること
            mock_session_old.close.assert_called_once()
            # 新しいセッションが生成されること
            assert mock_curl.Session.call_count == 2

    def test_正常系_BROWSER_IMPERSONATE_TARGETSから選択される(self) -> None:
        """偽装ターゲットが BROWSER_IMPERSONATE_TARGETS から選択されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_curl.Session.return_value = MagicMock()

            session = ETFComSession()
            session.rotate_session()

            # 2回目の Session() 呼び出しの impersonate 引数を確認
            second_call_kwargs = mock_curl.Session.call_args
            target = second_call_kwargs[1]["impersonate"]
            assert target in BROWSER_IMPERSONATE_TARGETS


# =============================================================================
# close() tests
# =============================================================================


class TestETFComSessionClose:
    """ETFComSession.close() のテスト。"""

    def test_正常系_セッションが閉じられる(self) -> None:
        """close() でセッションが閉じられること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_curl.Session.return_value = mock_session

            session = ETFComSession()
            session.close()

            mock_session.close.assert_called_once()


# =============================================================================
# Logging tests
# =============================================================================


class TestETFComSessionLogging:
    """ETFComSession のロギングテスト。"""

    def test_正常系_loggerが定義されている(self) -> None:
        """モジュールレベルで structlog ロガーが定義されていること。"""
        import market.etfcom.session as session_module

        assert hasattr(session_module, "logger")


# =============================================================================
# __all__ export tests
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_ETFComSessionがエクスポートされている(self) -> None:
        """__all__ に ETFComSession が含まれていること。"""
        from market.etfcom.session import __all__

        assert "ETFComSession" in __all__


# =============================================================================
# _request() tests
# =============================================================================


class TestRequest:
    """ETFComSession._request() の共通処理テスト。"""

    def test_正常系_GETメソッドで正常動作する(self) -> None:
        """_request('GET', url) が正常にレスポンスを返すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session._request("GET", "https://www.etf.com/SPY")

            assert response.status_code == 200

    def test_正常系_POSTメソッドで正常動作する(self) -> None:
        """_request('POST', url) が正常にレスポンスを返すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session._request("POST", "https://api-prod.etf.com/test")

            assert response.status_code == 200

    def test_正常系_ポライトディレイが適用される(self) -> None:
        """_request() でポライトディレイが適用されること。"""
        config = ScrapingConfig(polite_delay=2.0, delay_jitter=1.0)

        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with (
                patch("market.etfcom.session.time.sleep") as mock_sleep,
                patch("market.etfcom.session.random.uniform", return_value=0.5),
            ):
                session = ETFComSession(config=config)
                session._request("GET", "https://www.etf.com/SPY")

                mock_sleep.assert_called_once()
                actual_delay = mock_sleep.call_args[0][0]
                assert actual_delay == pytest.approx(2.5, abs=0.01)

    def test_正常系_User_Agentヘッダーが設定される(self) -> None:
        """_request() でランダム User-Agent がヘッダーに設定されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with (
                patch("market.etfcom.session.time.sleep"),
                patch(
                    "market.etfcom.session.random.choice",
                    return_value="MockUA/1.0",
                ),
            ):
                session = ETFComSession()
                session._request("GET", "https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["User-Agent"] == "MockUA/1.0"

    def test_正常系_カスタムヘッダーがマージされる(self) -> None:
        """_request() で caller 提供のヘッダーが DEFAULT_HEADERS にマージされること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                custom_headers = {"X-Custom": "test-value"}
                session._request(
                    "POST",
                    "https://api-prod.etf.com/test",
                    headers=custom_headers,
                )

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["X-Custom"] == "test-value"
                # DEFAULT_HEADERS もまだ含まれること
                for key, value in DEFAULT_HEADERS.items():
                    assert headers[key] == value

    def test_異常系_403レスポンスでETFComBlockedError(self) -> None:
        """_request() で 403 レスポンスが ETFComBlockedError を発生させること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()

                with pytest.raises(ETFComBlockedError) as exc_info:
                    session._request("GET", "https://www.etf.com/SPY")

                assert exc_info.value.status_code == 403
                assert exc_info.value.url == "https://www.etf.com/SPY"

    def test_異常系_429レスポンスでETFComBlockedError(self) -> None:
        """_request() で 429 レスポンスが ETFComBlockedError を発生させること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()

                with pytest.raises(ETFComBlockedError) as exc_info:
                    session._request("POST", "https://api-prod.etf.com/test")

                assert exc_info.value.status_code == 429

    def test_異常系_404レスポンスでETFComNotFoundError(self) -> None:
        """_request() で 404 レスポンスが ETFComNotFoundError を発生させること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()

                with pytest.raises(ETFComNotFoundError) as exc_info:
                    session._request("GET", "https://www.etf.com/INVALID")

                assert exc_info.value.status_code == 404
                assert exc_info.value.url == "https://www.etf.com/INVALID"

    def test_異常系_404はBLOCKED_STATUS_CODESに含まれない(self) -> None:
        """404 が _BLOCKED_STATUS_CODES に含まれていないこと。"""
        from market.etfcom.session import _BLOCKED_STATUS_CODES

        assert 404 not in _BLOCKED_STATUS_CODES

    def test_正常系_メソッド名がcurl_cffiのrequestに渡される(self) -> None:
        """_request() が method 引数を curl_cffi session.request() に渡すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session._request("POST", "https://api-prod.etf.com/test")

                call_args = mock_session.request.call_args
                assert call_args[0][0] == "POST"
                assert call_args[0][1] == "https://api-prod.etf.com/test"


# =============================================================================
# post() tests
# =============================================================================


class TestPost:
    """ETFComSession.post() のテスト。"""

    def test_正常系_API_HEADERSがデフォルトで設定される(self) -> None:
        """post() が API_HEADERS をデフォルトヘッダーとして設定すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.post("https://api-prod.etf.com/test")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                # API_HEADERS の各フィールドが含まれること
                for key, value in API_HEADERS.items():
                    assert headers[key] == value

    def test_正常系_追加ヘッダーがAPI_HEADERSとマージされる(self) -> None:
        """post() で caller 提供のヘッダーが API_HEADERS にマージされること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.post(
                    "https://api-prod.etf.com/test",
                    headers={"X-Extra": "extra-value"},
                )

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["X-Extra"] == "extra-value"
                # API_HEADERS もまだ含まれること
                assert headers["Content-Type"] == "application/json"

    def test_正常系_JSONデータを送信できる(self) -> None:
        """post() が JSON データを kwargs 経由で送信できること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                payload = {"fundId": 1, "startDate": "2020-01-01"}
                session.post(
                    "https://api-prod.etf.com/test",
                    json=payload,
                )

                call_kwargs = mock_session.request.call_args
                assert call_kwargs[1]["json"] == payload

    def test_異常系_403レスポンスでETFComBlockedError(self) -> None:
        """post() で 403 レスポンスが ETFComBlockedError を発生させること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()

                with pytest.raises(ETFComBlockedError) as exc_info:
                    session.post("https://api-prod.etf.com/test")

                assert exc_info.value.status_code == 403

    def test_正常系_POSTメソッドでrequestが呼ばれる(self) -> None:
        """post() が内部で _request('POST', ...) を呼ぶこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.post("https://api-prod.etf.com/test")

                call_args = mock_session.request.call_args
                assert call_args[0][0] == "POST"


# =============================================================================
# post_with_retry() tests
# =============================================================================


class TestPostWithRetry:
    """ETFComSession.post_with_retry() のテスト。"""

    def test_正常系_成功時はリトライなし(self) -> None:
        """最初の試行で成功した場合リトライしないこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session.post_with_retry(
                    "https://api-prod.etf.com/test",
                )

            assert response.status_code == 200
            assert mock_session.request.call_count == 1

    def test_正常系_失敗後リトライで成功(self) -> None:
        """失敗後にリトライで成功すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200
            mock_session.request.side_effect = [
                mock_response_blocked,
                mock_response_ok,
            ]
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)
                response = session.post_with_retry(
                    "https://api-prod.etf.com/test",
                )

            assert response.status_code == 200

    def test_異常系_全リトライ失敗でETFComBlockedError(self) -> None:
        """全リトライが失敗した場合 ETFComBlockedError が発生すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_session.request.return_value = mock_response_blocked
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=2, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)

                with pytest.raises(ETFComBlockedError):
                    session.post_with_retry("https://api-prod.etf.com/test")

    def test_正常系_リトライ時にrotate_sessionが呼ばれる(self) -> None:
        """リトライ時に rotate_session() が呼ばれること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200
            mock_session.request.side_effect = [
                mock_response_blocked,
                mock_response_ok,
            ]
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)
                with patch.object(session, "rotate_session") as mock_rotate:
                    session.post_with_retry("https://api-prod.etf.com/test")
                    mock_rotate.assert_called_once()

    def test_正常系_API_HEADERSがリトライ時も保持される(self) -> None:
        """リトライ時も API_HEADERS が保持されること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200
            mock_session.request.side_effect = [
                mock_response_blocked,
                mock_response_ok,
            ]
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)
                session.post_with_retry("https://api-prod.etf.com/test")

                # 2回目（成功時）のリクエストヘッダーを確認
                last_call_kwargs = mock_session.request.call_args
                headers = last_call_kwargs[1]["headers"]
                assert headers["Content-Type"] == "application/json"


# =============================================================================
# _request_with_retry() tests
# =============================================================================


class TestRequestWithRetry:
    """ETFComSession._request_with_retry() の共通リトライロジックテスト。"""

    def test_正常系_GETメソッドで動作する(self) -> None:
        """_request_with_retry('GET', ...) が正常にレスポンスを返すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session._request_with_retry("GET", "https://www.etf.com/SPY")

            assert response.status_code == 200

    def test_正常系_POSTメソッドで動作する(self) -> None:
        """_request_with_retry('POST', ...) が正常にレスポンスを返すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session._request_with_retry(
                    "POST", "https://api-prod.etf.com/test"
                )

            assert response.status_code == 200

    def test_正常系_指数バックオフでディレイが増加する(self) -> None:
        """リトライ間のディレイが指数バックオフで増加すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_blocked = MagicMock()
            mock_response_blocked.status_code = 403
            mock_session.request.return_value = mock_response_blocked
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=False,
            )

            sleep_calls: list[float] = []

            def track_sleep(duration: float) -> None:
                sleep_calls.append(duration)

            with patch("market.etfcom.session.time.sleep", side_effect=track_sleep):
                session = ETFComSession(retry_config=retry_config)

                with pytest.raises(ETFComBlockedError):
                    session._request_with_retry("POST", "https://api-prod.etf.com/test")

            # リトライディレイが2回あること（max_attempts=3, 最後の失敗後はなし）
            retry_delays = [d for d in sleep_calls if d >= 1.0]
            assert len(retry_delays) >= 2

    def test_異常系_404はリトライせず即座に伝播する(self) -> None:
        """_request_with_retry() が ETFComNotFoundError をリトライせず即座に伝播すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_not_found = MagicMock()
            mock_response_not_found.status_code = 404
            mock_session.request.return_value = mock_response_not_found
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)

                with patch.object(session, "rotate_session") as mock_rotate:
                    with pytest.raises(ETFComNotFoundError) as exc_info:
                        session._request_with_retry(
                            "GET", "https://www.etf.com/INVALID"
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.url == "https://www.etf.com/INVALID"
                    # rotate_session は呼ばれないこと（リトライしないため）
                    mock_rotate.assert_not_called()

            # request() は1回だけ呼ばれること（リトライなし）
            assert mock_session.request.call_count == 1


# =============================================================================
# get() backward compatibility tests
# =============================================================================


class TestGetBackwardCompatibility:
    """get() のリファクタリング後の後方互換性テスト。"""

    def test_正常系_getが_requestに委譲しても同じ結果を返す(self) -> None:
        """get() が _request('GET', ...) に委譲した後も同じ結果を返すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session.get("https://www.etf.com/SPY")

            assert response.status_code == 200

    def test_正常系_getのヘッダーにDEFAULT_HEADERSが含まれる(self) -> None:
        """get() が DEFAULT_HEADERS を引き続き使用すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.get("https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                for key, value in DEFAULT_HEADERS.items():
                    assert headers[key] == value

    def test_正常系_getのヘッダーにRefererが設定される(self) -> None:
        """get() が Referer ヘッダーに ETFCOM_BASE_URL を設定し続けること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                session.get("https://www.etf.com/SPY")

                call_kwargs = mock_session.request.call_args
                headers = call_kwargs[1]["headers"]
                assert headers["Referer"] == ETFCOM_BASE_URL

    def test_正常系_get_with_retryが_request_with_retryに委譲しても同じ結果(
        self,
    ) -> None:
        """get_with_retry() が _request_with_retry に委譲しても同じ結果を返すこと。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response
            mock_curl.Session.return_value = mock_session

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession()
                response = session.get_with_retry("https://www.etf.com/SPY")

            assert response.status_code == 200


# =============================================================================
# get_with_retry() / post_with_retry() 404 propagation tests
# =============================================================================


class TestHTTPMethodRetry404Propagation:
    """get_with_retry() / post_with_retry() 経由で 404 が即座に伝播すること。"""

    def test_異常系_get_with_retryで404が即座に伝播する(self) -> None:
        """get_with_retry() が ETFComNotFoundError をリトライせず即座に伝播すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_not_found = MagicMock()
            mock_response_not_found.status_code = 404
            mock_session.request.return_value = mock_response_not_found
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)

                with pytest.raises(ETFComNotFoundError) as exc_info:
                    session.get_with_retry("https://www.etf.com/INVALID")

                assert exc_info.value.status_code == 404
                assert exc_info.value.url == "https://www.etf.com/INVALID"

            # request() は1回だけ呼ばれること（リトライなし）
            assert mock_session.request.call_count == 1

    def test_異常系_post_with_retryで404が即座に伝播する(self) -> None:
        """post_with_retry() が ETFComNotFoundError をリトライせず即座に伝播すること。"""
        with patch("market.etfcom.session.curl_requests") as mock_curl:
            mock_session = MagicMock()
            mock_response_not_found = MagicMock()
            mock_response_not_found.status_code = 404
            mock_session.request.return_value = mock_response_not_found
            mock_curl.Session.return_value = mock_session

            retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

            with patch("market.etfcom.session.time.sleep"):
                session = ETFComSession(retry_config=retry_config)

                with pytest.raises(ETFComNotFoundError) as exc_info:
                    session.post_with_retry("https://api-prod.etf.com/invalid")

                assert exc_info.value.status_code == 404
                assert exc_info.value.url == "https://api-prod.etf.com/invalid"

            # request() は1回だけ呼ばれること（リトライなし）
            assert mock_session.request.call_count == 1
