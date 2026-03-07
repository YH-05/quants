"""Unit tests for market.etfcom.browser module.

ETFComBrowserMixin の動作を検証するテストスイート。
Playwright ベースのブラウザ操作 Mixin クラスのテスト。

Test TODO List:
- [x] ETFComBrowserMixin: デフォルト値で初期化
- [x] ETFComBrowserMixin: カスタム config / retry_config で初期化
- [x] ETFComBrowserMixin: async context manager プロトコル
- [x] _ensure_browser(): ブラウザ起動
- [x] _ensure_browser(): 既にブラウザ起動済みの場合はスキップ
- [x] _create_stealth_context(): viewport / UA / locale / timezone 設定
- [x] _create_stealth_context(): STEALTH_INIT_SCRIPT 注入
- [x] _navigate(): URL へのナビゲーションとポライトディレイ
- [x] _navigate(): タイムアウト時に ETFComTimeoutError
- [x] _navigate(): 404 レスポンスで ETFComNotFoundError
- [x] _navigate(): TargetClosedError で ETFComNotFoundError
- [x] _navigate(): 200 レスポンスでページを返す（回帰テスト）
- [x] _get_page_html(): ページ HTML を取得
- [x] _get_page_html_with_retry(): リトライ + バックオフ
- [x] _get_page_html_with_retry(): 全リトライ失敗で例外
- [x] _accept_cookies(): クッキー同意ボタンクリック
- [x] _accept_cookies(): ボタンが見つからない場合はスキップ
- [x] _wait_for_content_loaded(): セレクタ待機
- [x] _click_display_100(): Display 100 オプションクリック
- [x] close(): ブラウザ・コンテキスト・playwright を閉じる
- [x] close(): 未初期化でも安全に呼べる
- [x] Playwright 未インストール時に ImportError
- [x] structlog ロガーの使用
- [x] __all__ エクスポート
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from market.etfcom.constants import (
    COOKIE_CONSENT_SELECTOR,
    DISPLAY_100_SELECTOR,
    STEALTH_INIT_SCRIPT,
    STEALTH_VIEWPORT,
)
from market.etfcom.errors import ETFComNotFoundError, ETFComTimeoutError
from market.etfcom.types import RetryConfig, ScrapingConfig

# =============================================================================
# Helper: Create a mixin instance with mocked playwright
# =============================================================================


def _make_mock_playwright() -> tuple[MagicMock, MagicMock, MagicMock, AsyncMock]:
    """Create mocked Playwright objects.

    Returns
    -------
    tuple
        (mock_async_playwright, mock_pw_instance, mock_browser, mock_page)
    """
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body>test</body></html>")
    mock_page.goto = AsyncMock()
    mock_page.close = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.query_selector = AsyncMock(return_value=None)

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    mock_context.add_init_script = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw_instance = AsyncMock()
    mock_pw_instance.chromium = MagicMock()
    mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw_instance.stop = AsyncMock()

    mock_pw_context_manager = AsyncMock()
    mock_pw_context_manager.start = AsyncMock(return_value=mock_pw_instance)

    mock_async_playwright = MagicMock(return_value=mock_pw_context_manager)

    return mock_async_playwright, mock_pw_instance, mock_browser, mock_page


# =============================================================================
# Initialization tests
# =============================================================================


class TestETFComBrowserMixinInit:
    """ETFComBrowserMixin 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの ScrapingConfig / RetryConfig で初期化されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mixin = ETFComBrowserMixin()
        assert mixin._config is not None
        assert mixin._retry_config is not None
        assert isinstance(mixin._config, ScrapingConfig)
        assert isinstance(mixin._retry_config, RetryConfig)

    def test_正常系_カスタムconfigで初期化できる(self) -> None:
        """カスタム ScrapingConfig / RetryConfig で初期化されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        config = ScrapingConfig(polite_delay=5.0, headless=False)
        retry_config = RetryConfig(max_attempts=5, initial_delay=0.5)
        mixin = ETFComBrowserMixin(config=config, retry_config=retry_config)

        assert mixin._config.polite_delay == 5.0
        assert mixin._config.headless is False
        assert mixin._retry_config.max_attempts == 5
        assert mixin._retry_config.initial_delay == 0.5

    def test_正常系_ブラウザ関連属性がNoneで初期化される(self) -> None:
        """ブラウザ関連属性が None で初期化されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mixin = ETFComBrowserMixin()
        assert mixin._playwright is None
        assert mixin._browser is None
        assert mixin._context is None


# =============================================================================
# Async context manager tests
# =============================================================================


class TestETFComBrowserMixinContextManager:
    """ETFComBrowserMixin async context manager のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_async_context_managerとして使用できる(self) -> None:
        """async with 文で使用できること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, _mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        with patch(
            "market.etfcom.browser._get_async_playwright",
            return_value=mock_async_playwright(),
        ):
            async with ETFComBrowserMixin() as mixin:
                assert isinstance(mixin, ETFComBrowserMixin)

    @pytest.mark.asyncio
    async def test_正常系_例外発生時もcloseが呼ばれる(self) -> None:
        """例外発生時もリソースが解放されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, _mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            pytest.raises(ValueError, match="test error"),
        ):
            async with ETFComBrowserMixin() as mixin:
                # Ensure browser is initialized
                await mixin._ensure_browser()
                raise ValueError("test error")


# =============================================================================
# _ensure_browser() tests
# =============================================================================


class TestEnsureBrowser:
    """_ensure_browser() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_ブラウザが起動される(self) -> None:
        """Playwright ブラウザが headless モードで起動されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, mock_pw, _mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        with patch(
            "market.etfcom.browser._get_async_playwright",
            return_value=mock_async_playwright(),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()

            assert mixin._browser is not None
            assert mixin._playwright is not None
            mock_pw.chromium.launch.assert_awaited_once_with(headless=True)

    @pytest.mark.asyncio
    async def test_正常系_既にブラウザ起動済みの場合スキップ(self) -> None:
        """ブラウザが既に起動している場合は再起動しないこと。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, mock_pw, _mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        with patch(
            "market.etfcom.browser._get_async_playwright",
            return_value=mock_async_playwright(),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            await mixin._ensure_browser()  # 2回目

            # launch は1回だけ呼ばれる
            mock_pw.chromium.launch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_正常系_headless_falseで起動できる(self) -> None:
        """headless=False でブラウザが起動されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, mock_pw, _mock_browser, _mock_page = (
            _make_mock_playwright()
        )
        config = ScrapingConfig(headless=False)

        with patch(
            "market.etfcom.browser._get_async_playwright",
            return_value=mock_async_playwright(),
        ):
            mixin = ETFComBrowserMixin(config=config)
            await mixin._ensure_browser()

            mock_pw.chromium.launch.assert_awaited_once_with(headless=False)


# =============================================================================
# _create_stealth_context() tests
# =============================================================================


class TestCreateStealthContext:
    """_create_stealth_context() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_viewport_UA_locale_timezoneが設定される(self) -> None:
        """stealth context に viewport, UA, locale, timezone が設定されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        with patch(
            "market.etfcom.browser._get_async_playwright",
            return_value=mock_async_playwright(),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            _context = await mixin._create_stealth_context()

            # new_context が呼ばれたことを確認
            call_kwargs = mock_browser.new_context.call_args[1]
            assert call_kwargs["viewport"] == STEALTH_VIEWPORT
            assert "user_agent" in call_kwargs
            assert call_kwargs["locale"] == "en-US"
            assert call_kwargs["timezone_id"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_正常系_STEALTH_INIT_SCRIPTが注入される(self) -> None:
        """STEALTH_INIT_SCRIPT が context に注入されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        mock_context = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with patch(
            "market.etfcom.browser._get_async_playwright",
            return_value=mock_async_playwright(),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            await mixin._create_stealth_context()

            mock_context.add_init_script.assert_awaited_once_with(STEALTH_INIT_SCRIPT)


# =============================================================================
# _navigate() tests
# =============================================================================


class TestNavigate:
    """_navigate() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_URLへナビゲーションできる(self) -> None:
        """指定URLへナビゲーションし Page を返すこと。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            page = await mixin._navigate("https://www.etf.com/SPY")

            assert page is mock_page
            mock_page.goto.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_正常系_ポライトディレイが適用される(self) -> None:
        """ナビゲーション前にポライトディレイが適用されること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        config = ScrapingConfig(polite_delay=2.0, delay_jitter=0.0)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch(
                "market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep,
        ):
            mixin = ETFComBrowserMixin(config=config)
            await mixin._ensure_browser()
            await mixin._navigate("https://www.etf.com/SPY")

            mock_sleep.assert_awaited_once()
            actual_delay = mock_sleep.call_args[0][0]
            assert actual_delay >= 2.0

    @pytest.mark.asyncio
    async def test_異常系_タイムアウト時にETFComTimeoutError(self) -> None:
        """ナビゲーションタイムアウト時に ETFComTimeoutError が発生すること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )
        mock_page.goto = AsyncMock(side_effect=asyncio.TimeoutError("timeout"))

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()

            with pytest.raises(ETFComTimeoutError) as exc_info:
                await mixin._navigate("https://www.etf.com/SPY")

            assert exc_info.value.url == "https://www.etf.com/SPY"

    @pytest.mark.asyncio
    async def test_異常系_404レスポンスでETFComNotFoundError(self) -> None:
        """HTTP 404 レスポンス時に ETFComNotFoundError が発生すること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )

        # Configure goto to return a response with status 404
        mock_response = MagicMock()
        mock_response.status = 404
        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()

            with pytest.raises(ETFComNotFoundError) as exc_info:
                await mixin._navigate("https://www.etf.com/INVALID")

            assert exc_info.value.url == "https://www.etf.com/INVALID"
            assert exc_info.value.status_code == 404
            mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_異常系_TargetClosedErrorでETFComNotFoundError(self) -> None:
        """TargetClosedError 発生時に ETFComNotFoundError でラップされること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )

        # Create a TargetClosedError-like exception
        target_closed_error = type("TargetClosedError", (Exception,), {})()
        mock_page.goto = AsyncMock(side_effect=target_closed_error)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()

            with pytest.raises(ETFComNotFoundError) as exc_info:
                await mixin._navigate("https://www.etf.com/INVALID")

            assert exc_info.value.url == "https://www.etf.com/INVALID"
            mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_正常系_200レスポンスでページを返す(self) -> None:
        """HTTP 200 レスポンス時にページオブジェクトが返されること（回帰テスト）。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )

        # Configure goto to return a response with status 200
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            page = await mixin._navigate("https://www.etf.com/SPY")

            assert page is mock_page
            mock_page.close.assert_not_awaited()


# =============================================================================
# _get_page_html() tests
# =============================================================================


class TestGetPageHtml:
    """_get_page_html() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_ページHTMLを取得できる(self) -> None:
        """指定URLのページ HTML コンテンツを取得できること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )
        mock_page.content = AsyncMock(return_value="<html><body>ETF Data</body></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            html = await mixin._get_page_html("https://www.etf.com/SPY")

            assert "ETF Data" in html
            mock_page.close.assert_awaited_once()


# =============================================================================
# _get_page_html_with_retry() tests
# =============================================================================


class TestGetPageHtmlWithRetry:
    """_get_page_html_with_retry() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_成功時はリトライなし(self) -> None:
        """最初の試行で成功した場合リトライしないこと。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )
        mock_page.content = AsyncMock(return_value="<html><body>success</body></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            html = await mixin._get_page_html_with_retry("https://www.etf.com/SPY")

            assert "success" in html

    @pytest.mark.asyncio
    async def test_正常系_失敗後リトライで成功(self) -> None:
        """初回失敗後にリトライで成功すること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )

        # First call raises timeout, second call succeeds
        call_count = 0

        async def mock_goto(*args: Any, **kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("timeout")

        mock_page.goto = AsyncMock(side_effect=mock_goto)
        mock_page.content = AsyncMock(return_value="<html><body>success</body></html>")

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin(retry_config=retry_config)
            await mixin._ensure_browser()
            html = await mixin._get_page_html_with_retry("https://www.etf.com/SPY")

            assert "success" in html

    @pytest.mark.asyncio
    async def test_異常系_全リトライ失敗で例外(self) -> None:
        """全リトライが失敗した場合 ETFComTimeoutError が発生すること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, mock_page = (
            _make_mock_playwright()
        )
        mock_page.goto = AsyncMock(side_effect=asyncio.TimeoutError("timeout"))

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        retry_config = RetryConfig(max_attempts=2, initial_delay=0.01)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin(retry_config=retry_config)
            await mixin._ensure_browser()

            with pytest.raises(ETFComTimeoutError):
                await mixin._get_page_html_with_retry("https://www.etf.com/SPY")


# =============================================================================
# _accept_cookies() tests
# =============================================================================


class TestAcceptCookies:
    """_accept_cookies() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_クッキー同意ボタンをクリックする(self) -> None:
        """クッキー同意ボタンが存在する場合クリックすること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_page = AsyncMock()
        mock_button = AsyncMock()
        mock_button.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_button)

        mixin = ETFComBrowserMixin()
        await mixin._accept_cookies(mock_page)

        mock_page.query_selector.assert_awaited_once_with(COOKIE_CONSENT_SELECTOR)
        mock_button.click.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_正常系_ボタンが見つからない場合はスキップ(self) -> None:
        """クッキー同意ボタンが存在しない場合はスキップすること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mixin = ETFComBrowserMixin()
        # Should not raise
        await mixin._accept_cookies(mock_page)

        mock_page.query_selector.assert_awaited_once_with(COOKIE_CONSENT_SELECTOR)

    @pytest.mark.asyncio
    async def test_正常系_例外発生時もエラーにならない(self) -> None:
        """クッキー同意処理で例外が発生しても握りつぶすこと。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(side_effect=Exception("click failed"))

        mixin = ETFComBrowserMixin()
        # Should not raise
        await mixin._accept_cookies(mock_page)


# =============================================================================
# _wait_for_content_loaded() tests
# =============================================================================


class TestWaitForContentLoaded:
    """_wait_for_content_loaded() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_セレクタを待機する(self) -> None:
        """指定セレクタの要素が表示されるまで待機すること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        mixin = ETFComBrowserMixin()
        await mixin._wait_for_content_loaded(mock_page, "[data-testid='summary-data']")

        mock_page.wait_for_selector.assert_awaited_once()
        call_args = mock_page.wait_for_selector.call_args
        assert call_args[0][0] == "[data-testid='summary-data']"


# =============================================================================
# _click_display_100() tests
# =============================================================================


class TestClickDisplay100:
    """_click_display_100() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_Display100オプションをクリックする(self) -> None:
        """Display 100 オプション要素をクリックすること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        mixin = ETFComBrowserMixin()
        await mixin._click_display_100(mock_page)

        mock_page.query_selector.assert_awaited_once_with(DISPLAY_100_SELECTOR)
        mock_element.click.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_正常系_要素が見つからない場合はスキップ(self) -> None:
        """Display 100 要素が見つからない場合はスキップすること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        mixin = ETFComBrowserMixin()
        # Should not raise
        await mixin._click_display_100(mock_page)


# =============================================================================
# close() tests
# =============================================================================


class TestClose:
    """close() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_リソースが全て解放される(self) -> None:
        """close() でブラウザ・コンテキスト・playwright が閉じられること。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mock_async_playwright, _mock_pw, mock_browser, _mock_page = (
            _make_mock_playwright()
        )

        mock_context = AsyncMock()
        mock_context.close = AsyncMock()
        mock_context.add_init_script = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        with (
            patch(
                "market.etfcom.browser._get_async_playwright",
                return_value=mock_async_playwright(),
            ),
            patch("market.etfcom.browser.asyncio.sleep", new_callable=AsyncMock),
        ):
            mixin = ETFComBrowserMixin()
            await mixin._ensure_browser()
            # Create a stealth context to test context cleanup
            await mixin._create_stealth_context()
            await mixin.close()

            assert mixin._browser is None
            assert mixin._context is None
            assert mixin._playwright is None

    @pytest.mark.asyncio
    async def test_正常系_未初期化でも安全に呼べる(self) -> None:
        """未初期化状態で close() を呼んでもエラーにならないこと。"""
        from market.etfcom.browser import ETFComBrowserMixin

        mixin = ETFComBrowserMixin()
        # Should not raise
        await mixin.close()


# =============================================================================
# Playwright optional import tests
# =============================================================================


class TestPlaywrightOptionalImport:
    """Playwright optional import のテスト。"""

    def test_異常系_Playwright未インストール時にImportError(self) -> None:
        """Playwright 未インストール時に分かりやすいエラーメッセージが出ること。"""
        from market.etfcom.browser import _get_async_playwright

        with (
            patch.dict(
                "sys.modules",
                {"playwright": None, "playwright.async_api": None},
            ),
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'playwright'"),
            ),
            pytest.raises(ImportError, match="playwright"),
        ):
            _get_async_playwright()


# =============================================================================
# Logging tests
# =============================================================================


class TestLogging:
    """ロギングのテスト。"""

    def test_正常系_loggerが定義されている(self) -> None:
        """モジュールレベルで structlog ロガーが定義されていること。"""
        import market.etfcom.browser as browser_module

        assert hasattr(browser_module, "logger")


# =============================================================================
# __all__ export tests
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_ETFComBrowserMixinがエクスポートされている(self) -> None:
        """__all__ に ETFComBrowserMixin が含まれていること。"""
        from market.etfcom.browser import __all__

        assert "ETFComBrowserMixin" in __all__
