"""Tests for market.polymarket.errors module."""

import pytest

from market.polymarket.errors import (
    PolymarketAPIError,
    PolymarketError,
    PolymarketNotFoundError,
    PolymarketRateLimitError,
    PolymarketValidationError,
)


class TestPolymarketError:
    """Tests for PolymarketError base exception."""

    def test_正常系_Exceptionを継承(self) -> None:
        assert issubclass(PolymarketError, Exception)

    def test_正常系_メッセージが設定される(self) -> None:
        error = PolymarketError("test error")
        assert error.message == "test error"

    def test_正常系_strで取得可能(self) -> None:
        error = PolymarketError("test error")
        assert str(error) == "test error"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(PolymarketError, match="test error"):
            raise PolymarketError("test error")


class TestPolymarketAPIError:
    """Tests for PolymarketAPIError."""

    def test_正常系_PolymarketErrorを継承(self) -> None:
        assert issubclass(PolymarketAPIError, PolymarketError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = PolymarketAPIError(
            message="API error",
            url="https://gamma-api.polymarket.com/markets",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        assert error.message == "API error"
        assert error.url == "https://gamma-api.polymarket.com/markets"
        assert error.status_code == 500
        assert error.response_body == '{"error": "Internal Server Error"}'

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(PolymarketAPIError):
            raise PolymarketAPIError(
                message="Server error",
                url="https://clob.polymarket.com/order-book",
                status_code=503,
                response_body="Service Unavailable",
            )

    def test_正常系_PolymarketErrorでキャッチ可能(self) -> None:
        with pytest.raises(PolymarketError):
            raise PolymarketAPIError(
                message="Error",
                url="https://data-api.polymarket.com/timeseries",
                status_code=400,
                response_body="Bad Request",
            )


class TestPolymarketRateLimitError:
    """Tests for PolymarketRateLimitError."""

    def test_正常系_PolymarketAPIErrorを継承(self) -> None:
        assert issubclass(PolymarketRateLimitError, PolymarketAPIError)

    def test_正常系_PolymarketErrorのサブクラス(self) -> None:
        assert issubclass(PolymarketRateLimitError, PolymarketError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = PolymarketRateLimitError(
            message="Rate limit exceeded",
            url="https://gamma-api.polymarket.com/markets",
            retry_after=60,
        )
        assert error.message == "Rate limit exceeded"
        assert error.url == "https://gamma-api.polymarket.com/markets"
        assert error.retry_after == 60

    def test_正常系_retry_afterがNone(self) -> None:
        error = PolymarketRateLimitError(
            message="Rate limit",
            url=None,
            retry_after=None,
        )
        assert error.url is None
        assert error.retry_after is None

    def test_正常系_PolymarketAPIErrorでキャッチ可能(self) -> None:
        with pytest.raises(PolymarketAPIError):
            raise PolymarketRateLimitError(
                message="429 Too Many Requests",
                url="https://clob.polymarket.com/prices",
                retry_after=30,
            )

    def test_正常系_PolymarketErrorでキャッチ可能(self) -> None:
        with pytest.raises(PolymarketError):
            raise PolymarketRateLimitError(
                message="429 Too Many Requests",
                url="https://clob.polymarket.com/prices",
                retry_after=30,
            )


class TestPolymarketValidationError:
    """Tests for PolymarketValidationError."""

    def test_正常系_PolymarketErrorを継承(self) -> None:
        assert issubclass(PolymarketValidationError, PolymarketError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = PolymarketValidationError(
            message="Invalid condition ID",
            field="condition_id",
            value="",
        )
        assert error.message == "Invalid condition ID"
        assert error.field == "condition_id"
        assert error.value == ""

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(PolymarketValidationError):
            raise PolymarketValidationError(
                message="Invalid",
                field="token_id",
                value=-1,
            )


class TestPolymarketNotFoundError:
    """Tests for PolymarketNotFoundError."""

    def test_正常系_PolymarketErrorを継承(self) -> None:
        assert issubclass(PolymarketNotFoundError, PolymarketError)

    def test_正常系_属性が正しく設定される(self) -> None:
        error = PolymarketNotFoundError(
            message="Market not found",
            resource_type="market",
            resource_id="0x1234567890abcdef",
        )
        assert error.message == "Market not found"
        assert error.resource_type == "market"
        assert error.resource_id == "0x1234567890abcdef"

    def test_正常系_raiseできる(self) -> None:
        with pytest.raises(PolymarketNotFoundError, match="Market not found"):
            raise PolymarketNotFoundError(
                message="Market not found",
                resource_type="market",
                resource_id="unknown-id",
            )

    def test_正常系_PolymarketErrorでキャッチ可能(self) -> None:
        with pytest.raises(PolymarketError):
            raise PolymarketNotFoundError(
                message="Event not found",
                resource_type="event",
                resource_id="nonexistent",
            )


class TestErrorHierarchy:
    """Tests for the complete error hierarchy."""

    def test_正常系_全エラーがPolymarketErrorのサブクラス(self) -> None:
        subclasses = [
            PolymarketAPIError,
            PolymarketRateLimitError,
            PolymarketValidationError,
            PolymarketNotFoundError,
        ]
        for cls in subclasses:
            assert issubclass(cls, PolymarketError), (
                f"{cls.__name__} is not a subclass of PolymarketError"
            )

    def test_正常系_全エラーがExceptionのサブクラス(self) -> None:
        subclasses = [
            PolymarketError,
            PolymarketAPIError,
            PolymarketRateLimitError,
            PolymarketValidationError,
            PolymarketNotFoundError,
        ]
        for cls in subclasses:
            assert issubclass(cls, Exception), (
                f"{cls.__name__} is not a subclass of Exception"
            )

    def test_正常系_RateLimitErrorはAPIErrorのサブクラス(self) -> None:
        assert issubclass(PolymarketRateLimitError, PolymarketAPIError), (
            "PolymarketRateLimitError is not a subclass of PolymarketAPIError"
        )

    def test_正常系_親クラスキャッチで全子クラスをキャッチ(self) -> None:
        """Verify parent class catch catches all child exceptions."""
        exceptions = [
            PolymarketAPIError(
                message="API error",
                url="https://gamma-api.polymarket.com/markets",
                status_code=500,
                response_body="error",
            ),
            PolymarketRateLimitError(
                message="Rate limit",
                url="https://clob.polymarket.com/prices",
                retry_after=60,
            ),
            PolymarketValidationError(
                message="Invalid",
                field="condition_id",
                value="",
            ),
            PolymarketNotFoundError(
                message="Not found",
                resource_type="market",
                resource_id="unknown",
            ),
        ]
        for exc in exceptions:
            with pytest.raises(PolymarketError):
                raise exc
