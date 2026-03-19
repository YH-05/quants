"""Unit tests for market.asean_common.errors module.

ASEAN共通エラークラスのテストスイート。
4つのエラークラス（AseanError, AseanStorageError, AseanScreenerError,
AseanLookupError）の動作を検証する。

Test TODO List:
- [x] AseanError: base exception with message attribute
- [x] AseanStorageError: storage operation error
- [x] AseanScreenerError: screener operation error
- [x] AseanLookupError: ticker lookup error
- [x] Exception hierarchy validation
- [x] Common usage patterns (try-except, raise, cause chaining)
- [x] __all__ exports
"""

import pytest

from market.asean_common.errors import (
    AseanError,
    AseanLookupError,
    AseanScreenerError,
    AseanStorageError,
)

# =============================================================================
# AseanError (base exception)
# =============================================================================


class TestAseanError:
    """AseanError 基底例外クラスのテスト。"""

    def test_正常系_メッセージで初期化できる(self) -> None:
        """AseanError がメッセージで初期化されること。"""
        error = AseanError("ASEAN operation failed")

        assert error.message == "ASEAN operation failed"
        assert str(error) == "ASEAN operation failed"

    def test_正常系_Exceptionを直接継承している(self) -> None:
        """AseanError が Exception を直接継承していること。"""
        assert issubclass(AseanError, Exception)
        assert Exception in AseanError.__bases__

    def test_正常系_raiseで例外として使用可能(self) -> None:
        """raise で例外として使用できること。"""
        with pytest.raises(AseanError, match="test error"):
            raise AseanError("test error")

    def test_正常系_message属性にアクセスできる(self) -> None:
        """message 属性が正しく設定されること。"""
        error = AseanError("some error message")

        assert hasattr(error, "message")
        assert error.message == "some error message"


# =============================================================================
# AseanStorageError
# =============================================================================


class TestAseanStorageError:
    """AseanStorageError (ストレージエラー) のテスト。"""

    def test_正常系_メッセージで初期化(self) -> None:
        """AseanStorageError がメッセージで初期化されること。"""
        error = AseanStorageError("Failed to write to DuckDB")

        assert error.message == "Failed to write to DuckDB"
        assert str(error) == "Failed to write to DuckDB"

    def test_正常系_AseanErrorを継承している(self) -> None:
        """AseanStorageError が AseanError を継承していること。"""
        assert issubclass(AseanStorageError, AseanError)

        error = AseanStorageError("storage error")
        assert isinstance(error, AseanError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = AseanStorageError("DuckDB connection failed")

        assert "DuckDB connection failed" in str(error)

    def test_正常系_AseanErrorでキャッチできる(self) -> None:
        """AseanError でキャッチできること。"""
        with pytest.raises(AseanError):
            raise AseanStorageError("storage error")


# =============================================================================
# AseanScreenerError
# =============================================================================


class TestAseanScreenerError:
    """AseanScreenerError (スクリーナーエラー) のテスト。"""

    def test_正常系_メッセージで初期化(self) -> None:
        """AseanScreenerError がメッセージで初期化されること。"""
        error = AseanScreenerError("Screener query failed")

        assert error.message == "Screener query failed"
        assert str(error) == "Screener query failed"

    def test_正常系_AseanErrorを継承している(self) -> None:
        """AseanScreenerError が AseanError を継承していること。"""
        assert issubclass(AseanScreenerError, AseanError)

        error = AseanScreenerError("screener error")
        assert isinstance(error, AseanError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = AseanScreenerError("TradingView screener timeout")

        assert "TradingView screener timeout" in str(error)

    def test_正常系_AseanErrorでキャッチできる(self) -> None:
        """AseanError でキャッチできること。"""
        with pytest.raises(AseanError):
            raise AseanScreenerError("screener error")


# =============================================================================
# AseanLookupError
# =============================================================================


class TestAseanLookupError:
    """AseanLookupError (ルックアップエラー) のテスト。"""

    def test_正常系_メッセージで初期化(self) -> None:
        """AseanLookupError がメッセージで初期化されること。"""
        error = AseanLookupError("Ticker not found: 1155.KL")

        assert error.message == "Ticker not found: 1155.KL"
        assert str(error) == "Ticker not found: 1155.KL"

    def test_正常系_AseanErrorを継承している(self) -> None:
        """AseanLookupError が AseanError を継承していること。"""
        assert issubclass(AseanLookupError, AseanError)

        error = AseanLookupError("lookup error")
        assert isinstance(error, AseanError)
        assert isinstance(error, Exception)

    def test_正常系_strでメッセージが表示される(self) -> None:
        """str() でエラーメッセージが表示されること。"""
        error = AseanLookupError("Ticker D05 not found in SGX")

        assert "Ticker D05 not found in SGX" in str(error)

    def test_正常系_AseanErrorでキャッチできる(self) -> None:
        """AseanError でキャッチできること。"""
        with pytest.raises(AseanError):
            raise AseanLookupError("lookup error")


# =============================================================================
# Exception Hierarchy
# =============================================================================


class TestExceptionHierarchy:
    """例外クラスの継承階層テスト。"""

    def test_正常系_全サブクラスがAseanErrorを継承(self) -> None:
        """全サブクラスが AseanError を継承していること。"""
        assert issubclass(AseanStorageError, AseanError)
        assert issubclass(AseanScreenerError, AseanError)
        assert issubclass(AseanLookupError, AseanError)

    def test_正常系_AseanErrorがExceptionを直接継承(self) -> None:
        """AseanError が Exception を直接継承していること。"""
        assert issubclass(AseanError, Exception)
        assert Exception in AseanError.__bases__

    def test_正常系_サブクラスはExceptionのインスタンスである(self) -> None:
        """サブクラスのインスタンスが Exception のインスタンスであること。"""
        storage_err = AseanStorageError("test")
        assert isinstance(storage_err, Exception)

        screener_err = AseanScreenerError("test")
        assert isinstance(screener_err, Exception)

        lookup_err = AseanLookupError("test")
        assert isinstance(lookup_err, Exception)


# =============================================================================
# Usage Patterns
# =============================================================================


class TestExceptionUsagePatterns:
    """例外クラスの使用パターンテスト。"""

    def test_正常系_try_exceptで適切にキャッチできる(self) -> None:
        """try-except で適切にキャッチできること。"""

        def lookup_ticker(ticker: str) -> None:
            raise AseanLookupError(f"Ticker not found: {ticker}")

        with pytest.raises(AseanLookupError) as exc_info:
            lookup_ticker("INVALID")

        assert "INVALID" in exc_info.value.message

        with pytest.raises(AseanError):
            lookup_ticker("INVALID")

    def test_正常系_原因チェーンが機能する(self) -> None:
        """例外の from チェーンが正しく機能すること。"""
        original = OSError("Disk full")

        try:
            raise AseanStorageError("Failed to write ticker data") from original
        except AseanStorageError as e:
            assert e.__cause__ is original
            assert isinstance(e.__cause__, OSError)

    def test_正常系_各サブクラスが独立してキャッチできる(self) -> None:
        """各サブクラスが独立してキャッチできること。"""
        with pytest.raises(AseanStorageError):
            raise AseanStorageError("storage")

        with pytest.raises(AseanScreenerError):
            raise AseanScreenerError("screener")

        with pytest.raises(AseanLookupError):
            raise AseanLookupError("lookup")


# =============================================================================
# Module Exports
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_全クラスがエクスポートされている(self) -> None:
        """__all__ に全4クラスが含まれていること。"""
        from market.asean_common import errors

        assert hasattr(errors, "__all__")
        expected = {
            "AseanError",
            "AseanStorageError",
            "AseanScreenerError",
            "AseanLookupError",
        }
        assert set(errors.__all__) == expected
