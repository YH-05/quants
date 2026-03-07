"""Unit tests for market.etfcom.errors module.

ETF.com エラークラスのテストスイート。
7つのエラークラス（ETFComError, ETFComScrapingError,
ETFComTimeoutError, ETFComHTTPError, ETFComBlockedError,
ETFComNotFoundError, ETFComAPIError）の動作を検証する。

Test TODO List:
- [x] ETFComError: base exception with message attribute
- [x] ETFComScrapingError: HTML parse failure with url, selector
- [x] ETFComTimeoutError: timeout with url, timeout_seconds
- [x] ETFComHTTPError: HTTP status code error with url, status_code
- [x] ETFComBlockedError: bot blocking with url, status_code
- [x] ETFComNotFoundError: HTTP 404 not found with url, status_code
- [x] ETFComAPIError: REST API error with url, status_code, response_body, ticker, fund_id
- [x] Exception hierarchy validation
- [x] Common usage patterns (try-except, raise, cause chaining)
"""

import pytest

from market.etfcom.errors import (
    ETFComAPIError,
    ETFComBlockedError,
    ETFComError,
    ETFComHTTPError,
    ETFComNotFoundError,
    ETFComScrapingError,
    ETFComTimeoutError,
)

# =============================================================================
# ETFComError (base exception)
# =============================================================================


class TestETFComError:
    """ETFComError 基底例外クラスのテスト。"""

    def test_正常系_メッセージで初期化できる(self) -> None:
        """ETFComError がメッセージで初期化されること。"""
        error = ETFComError("ETF.com operation failed")

        assert error.message == "ETF.com operation failed"
        assert str(error) == "ETF.com operation failed"

    def test_正常系_Exceptionを直接継承している(self) -> None:
        """ETFComError が Exception を直接継承していること。"""
        assert issubclass(ETFComError, Exception)
        # ETFComError の直接の基底クラスに Exception が含まれること
        assert Exception in ETFComError.__bases__

    def test_正常系_raiseで例外として使用可能(self) -> None:
        """raise で例外として使用できること。"""
        with pytest.raises(ETFComError, match="test error"):
            raise ETFComError("test error")

    def test_正常系_message属性にアクセスできる(self) -> None:
        """message 属性が正しく設定されること。"""
        error = ETFComError("some error message")

        assert hasattr(error, "message")
        assert error.message == "some error message"


# =============================================================================
# ETFComScrapingError
# =============================================================================


class TestETFComScrapingError:
    """ETFComScrapingError (HTMLパース失敗) のテスト。"""

    def test_正常系_基本的な初期化(self) -> None:
        """ETFComScrapingError が基本パラメータで初期化されること。"""
        error = ETFComScrapingError(
            "Failed to parse ETF profile page",
            url="https://www.etf.com/SPY",
            selector="[data-testid='summary-data']",
        )

        assert error.message == "Failed to parse ETF profile page"
        assert error.url == "https://www.etf.com/SPY"
        assert error.selector == "[data-testid='summary-data']"

    def test_正常系_ETFComErrorを継承している(self) -> None:
        """ETFComScrapingError が ETFComError を継承していること。"""
        assert issubclass(ETFComScrapingError, ETFComError)

        error = ETFComScrapingError(
            "parse error",
            url="https://www.etf.com/VOO",
            selector="div.summary",
        )
        assert isinstance(error, ETFComError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = ETFComScrapingError(
            "Element not found",
            url="https://www.etf.com/QQQ",
            selector="table.flows",
        )

        assert "Element not found" in str(error)

    def test_正常系_ETFComErrorでキャッチできる(self) -> None:
        """ETFComError でキャッチできること。"""
        with pytest.raises(ETFComError):
            raise ETFComScrapingError(
                "scraping failed",
                url="https://www.etf.com/IVV",
                selector="div.data",
            )

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること。"""
        error = ETFComScrapingError(
            "parse error",
            url=None,
            selector=None,
        )

        assert error.url is None
        assert error.selector is None


# =============================================================================
# ETFComTimeoutError
# =============================================================================


class TestETFComTimeoutError:
    """ETFComTimeoutError (タイムアウト) のテスト。"""

    def test_正常系_基本的な初期化(self) -> None:
        """ETFComTimeoutError が基本パラメータで初期化されること。"""
        error = ETFComTimeoutError(
            "Page load timed out",
            url="https://www.etf.com/SPY",
            timeout_seconds=30.0,
        )

        assert error.message == "Page load timed out"
        assert error.url == "https://www.etf.com/SPY"
        assert error.timeout_seconds == 30.0

    def test_正常系_ETFComErrorを継承している(self) -> None:
        """ETFComTimeoutError が ETFComError を継承していること。"""
        assert issubclass(ETFComTimeoutError, ETFComError)

        error = ETFComTimeoutError(
            "timeout",
            url="https://www.etf.com/VOO",
            timeout_seconds=60.0,
        )
        assert isinstance(error, ETFComError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = ETFComTimeoutError(
            "Navigation timed out after 30s",
            url="https://www.etf.com/QQQ",
            timeout_seconds=30.0,
        )

        assert "Navigation timed out after 30s" in str(error)

    def test_正常系_ETFComErrorでキャッチできる(self) -> None:
        """ETFComError でキャッチできること。"""
        with pytest.raises(ETFComError):
            raise ETFComTimeoutError(
                "timeout",
                url="https://www.etf.com/IVV",
                timeout_seconds=30.0,
            )

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること。"""
        error = ETFComTimeoutError(
            "timeout",
            url=None,
            timeout_seconds=30.0,
        )

        assert error.url is None
        assert error.timeout_seconds == 30.0


# =============================================================================
# ETFComHTTPError
# =============================================================================


class TestETFComHTTPError:
    """ETFComHTTPError (HTTPステータスコードエラー基底) のテスト。"""

    def test_正常系_基本的な初期化(self) -> None:
        """ETFComHTTPError が基本パラメータで初期化されること。"""
        error = ETFComHTTPError(
            "HTTP error occurred",
            url="https://www.etf.com/SPY",
            status_code=500,
        )

        assert error.message == "HTTP error occurred"
        assert error.url == "https://www.etf.com/SPY"
        assert error.status_code == 500

    def test_正常系_ETFComErrorを継承している(self) -> None:
        """ETFComHTTPError が ETFComError を継承していること。"""
        assert issubclass(ETFComHTTPError, ETFComError)

        error = ETFComHTTPError(
            "http error",
            url="https://www.etf.com/VOO",
            status_code=403,
        )
        assert isinstance(error, ETFComError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = ETFComHTTPError(
            "Server error",
            url="https://www.etf.com/SPY",
            status_code=500,
        )

        assert "Server error" in str(error)

    def test_正常系_ETFComErrorでキャッチできる(self) -> None:
        """ETFComError でキャッチできること。"""
        with pytest.raises(ETFComError):
            raise ETFComHTTPError(
                "http error",
                url="https://www.etf.com/IVV",
                status_code=500,
            )

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること。"""
        error = ETFComHTTPError(
            "http error",
            url=None,
            status_code=500,
        )

        assert error.url is None
        assert error.status_code == 500


# =============================================================================
# ETFComBlockedError
# =============================================================================


class TestETFComBlockedError:
    """ETFComBlockedError (ボットブロック検出) のテスト。"""

    def test_正常系_基本的な初期化(self) -> None:
        """ETFComBlockedError が基本パラメータで初期化されること。"""
        error = ETFComBlockedError(
            "Bot detected: HTTP 403",
            url="https://www.etf.com/SPY",
            status_code=403,
        )

        assert error.message == "Bot detected: HTTP 403"
        assert error.url == "https://www.etf.com/SPY"
        assert error.status_code == 403

    def test_正常系_ETFComErrorを継承している(self) -> None:
        """ETFComBlockedError が ETFComError を継承していること。"""
        assert issubclass(ETFComBlockedError, ETFComError)

        error = ETFComBlockedError(
            "blocked",
            url="https://www.etf.com/VOO",
            status_code=429,
        )
        assert isinstance(error, ETFComError)
        assert isinstance(error, Exception)

    def test_正常系_HTTP429でも初期化可能(self) -> None:
        """HTTP 429 (Rate Limit) でも初期化できること。"""
        error = ETFComBlockedError(
            "Rate limited",
            url="https://www.etf.com/QQQ",
            status_code=429,
        )

        assert error.status_code == 429

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = ETFComBlockedError(
            "Access denied",
            url="https://www.etf.com/SPY",
            status_code=403,
        )

        assert "Access denied" in str(error)

    def test_正常系_ETFComErrorでキャッチできる(self) -> None:
        """ETFComError でキャッチできること。"""
        with pytest.raises(ETFComError):
            raise ETFComBlockedError(
                "blocked",
                url="https://www.etf.com/IVV",
                status_code=403,
            )

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること。"""
        error = ETFComBlockedError(
            "blocked",
            url=None,
            status_code=403,
        )

        assert error.url is None
        assert error.status_code == 403


# =============================================================================
# ETFComNotFoundError
# =============================================================================


class TestETFComNotFoundError:
    """ETFComNotFoundError (HTTP 404) のテスト。"""

    def test_正常系_基本的な初期化(self) -> None:
        """ETFComNotFoundError が基本パラメータで初期化されること。"""
        error = ETFComNotFoundError(
            "ETF not found: HTTP 404",
            url="https://www.etf.com/INVALID",
        )

        assert error.message == "ETF not found: HTTP 404"
        assert error.url == "https://www.etf.com/INVALID"
        assert error.status_code == 404

    def test_正常系_ETFComErrorを継承している(self) -> None:
        """ETFComNotFoundError が ETFComError を継承していること。"""
        assert issubclass(ETFComNotFoundError, ETFComError)

        error = ETFComNotFoundError(
            "not found",
            url="https://www.etf.com/INVALID",
        )
        assert isinstance(error, ETFComError)
        assert isinstance(error, Exception)

    def test_正常系_デフォルトstatus_codeが404(self) -> None:
        """デフォルトの status_code が 404 であること。"""
        error = ETFComNotFoundError(
            "not found",
            url="https://www.etf.com/INVALID",
        )

        assert error.status_code == 404

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = ETFComNotFoundError(
            "Page not found",
            url="https://www.etf.com/INVALID",
        )

        assert "Page not found" in str(error)

    def test_正常系_ETFComErrorでキャッチできる(self) -> None:
        """ETFComError でキャッチできること。"""
        with pytest.raises(ETFComError):
            raise ETFComNotFoundError(
                "not found",
                url="https://www.etf.com/INVALID",
            )

    def test_正常系_url属性がNoneでも初期化可能(self) -> None:
        """url が None でも初期化できること。"""
        error = ETFComNotFoundError(
            "not found",
            url=None,
        )

        assert error.url is None
        assert error.status_code == 404


# =============================================================================
# ETFComAPIError
# =============================================================================


class TestETFComAPIError:
    """ETFComAPIError (REST APIエラー) のテスト。"""

    def test_正常系_全パラメータで初期化(self) -> None:
        """ETFComAPIError が全パラメータで初期化されること。"""
        error = ETFComAPIError(
            "API returned HTTP 403",
            url="https://api-prod.etf.com/private/apps/fundflows/fund-flows-query",
            status_code=403,
            response_body='{"error": "Forbidden"}',
            ticker="SPY",
            fund_id=1,
        )

        assert error.message == "API returned HTTP 403"
        assert (
            error.url
            == "https://api-prod.etf.com/private/apps/fundflows/fund-flows-query"
        )
        assert error.status_code == 403
        assert error.response_body == '{"error": "Forbidden"}'
        assert error.ticker == "SPY"
        assert error.fund_id == 1

    def test_正常系_ETFComErrorを継承している(self) -> None:
        """ETFComAPIError が ETFComError を継承していること。"""
        assert issubclass(ETFComAPIError, ETFComError)

        error = ETFComAPIError("api error")
        assert isinstance(error, ETFComError)
        assert isinstance(error, Exception)

    def test_正常系_デフォルト値でNoneが設定される(self) -> None:
        """ETFComAPIError のオプションパラメータがデフォルトで None であること。"""
        error = ETFComAPIError("api error")

        assert error.message == "api error"
        assert error.url is None
        assert error.status_code is None
        assert error.response_body is None
        assert error.ticker is None
        assert error.fund_id is None

    def test_正常系_ETFComErrorでキャッチできる(self) -> None:
        """ETFComError でキャッチできること。"""
        with pytest.raises(ETFComError):
            raise ETFComAPIError(
                "API error",
                url="https://api-prod.etf.com/test",
                status_code=500,
            )

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = ETFComAPIError(
            "API returned HTTP 500",
            url="https://api-prod.etf.com/test",
            status_code=500,
        )

        assert "API returned HTTP 500" in str(error)

    def test_正常系_部分的なパラメータで初期化可能(self) -> None:
        """ETFComAPIError が一部のオプションパラメータのみで初期化できること。"""
        error = ETFComAPIError(
            "Ticker resolution failed",
            url="https://api-prod.etf.com/private/apps/fundflows/tickers",
            status_code=429,
            ticker="SPY",
        )

        assert error.url is not None
        assert error.status_code == 429
        assert error.response_body is None
        assert error.ticker == "SPY"
        assert error.fund_id is None


# =============================================================================
# Exception Hierarchy
# =============================================================================


class TestExceptionHierarchy:
    """例外クラスの継承階層テスト。"""

    def test_正常系_全サブクラスがETFComErrorを継承(self) -> None:
        """全サブクラスが ETFComError を継承していること。"""
        assert issubclass(ETFComScrapingError, ETFComError)
        assert issubclass(ETFComTimeoutError, ETFComError)
        assert issubclass(ETFComHTTPError, ETFComError)
        assert issubclass(ETFComBlockedError, ETFComError)
        assert issubclass(ETFComNotFoundError, ETFComError)
        assert issubclass(ETFComAPIError, ETFComError)

    def test_正常系_ETFComHTTPErrorがETFComErrorを継承(self) -> None:
        """ETFComHTTPError が ETFComError を継承していること。"""
        assert issubclass(ETFComHTTPError, ETFComError)
        assert ETFComError in ETFComHTTPError.__bases__

    def test_正常系_ETFComBlockedErrorがETFComHTTPErrorを継承(self) -> None:
        """ETFComBlockedError が ETFComHTTPError を継承していること。"""
        assert issubclass(ETFComBlockedError, ETFComHTTPError)
        assert ETFComHTTPError in ETFComBlockedError.__bases__

    def test_正常系_ETFComNotFoundErrorがETFComHTTPErrorを継承(self) -> None:
        """ETFComNotFoundError が ETFComHTTPError を継承していること。"""
        assert issubclass(ETFComNotFoundError, ETFComHTTPError)
        assert ETFComHTTPError in ETFComNotFoundError.__bases__

    def test_正常系_ETFComErrorがExceptionを直接継承(self) -> None:
        """ETFComError が Exception を直接継承していること。"""
        assert issubclass(ETFComError, Exception)
        assert Exception in ETFComError.__bases__

    def test_正常系_サブクラスはExceptionのインスタンスである(self) -> None:
        """サブクラスのインスタンスが Exception のインスタンスであること。"""
        scraping_err = ETFComScrapingError(
            "test",
            url="https://www.etf.com/SPY",
            selector="div",
        )
        assert isinstance(scraping_err, Exception)

        timeout_err = ETFComTimeoutError(
            "test",
            url="https://www.etf.com/SPY",
            timeout_seconds=30.0,
        )
        assert isinstance(timeout_err, Exception)

        blocked_err = ETFComBlockedError(
            "test",
            url="https://www.etf.com/SPY",
            status_code=403,
        )
        assert isinstance(blocked_err, Exception)

        not_found_err = ETFComNotFoundError(
            "test",
            url="https://www.etf.com/INVALID",
        )
        assert isinstance(not_found_err, Exception)

        api_err = ETFComAPIError(
            "test",
            url="https://api-prod.etf.com/test",
            status_code=500,
        )
        assert isinstance(api_err, Exception)


# =============================================================================
# Usage Patterns
# =============================================================================


class TestExceptionUsagePatterns:
    """例外クラスの使用パターンテスト。"""

    def test_正常系_try_exceptで適切にキャッチできる(self) -> None:
        """try-except で適切にキャッチできること。"""

        def scrape_etf(ticker: str) -> None:
            raise ETFComScrapingError(
                f"Failed to parse {ticker} page",
                url=f"https://www.etf.com/{ticker}",
                selector="[data-testid='summary-data']",
            )

        # 具体的な例外でキャッチ
        with pytest.raises(ETFComScrapingError) as exc_info:
            scrape_etf("SPY")

        assert exc_info.value.url == "https://www.etf.com/SPY"

        # 基底例外でキャッチ
        with pytest.raises(ETFComError):
            scrape_etf("SPY")

    def test_正常系_原因チェーンが機能する(self) -> None:
        """例外の from チェーンが正しく機能すること。"""
        original = TimeoutError("Connection timed out")

        try:
            raise ETFComTimeoutError(
                "Page load failed",
                url="https://www.etf.com/SPY",
                timeout_seconds=30.0,
            ) from original
        except ETFComTimeoutError as e:
            assert e.__cause__ is original
            assert isinstance(e.__cause__, TimeoutError)


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_全クラスがエクスポートされている(self) -> None:
        """__all__ に全7クラスが含まれていること。"""
        from market.etfcom import errors

        assert hasattr(errors, "__all__")
        expected = {
            "ETFComAPIError",
            "ETFComBlockedError",
            "ETFComError",
            "ETFComHTTPError",
            "ETFComNotFoundError",
            "ETFComScrapingError",
            "ETFComTimeoutError",
        }
        assert set(errors.__all__) == expected
