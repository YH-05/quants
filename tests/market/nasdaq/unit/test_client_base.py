"""Unit tests for NasdaqClient base functionality.

Tests cover:
- Dependency injection (session + cache)
- ``_fetch_and_parse`` DRY helper (cache hit, cache miss, force refresh)
- ``unwrap_envelope`` (success, rCode != 200, missing structure)
- ``_validate_symbol`` (valid symbols, invalid symbols)
- ``_build_referer`` (with symbol, without symbol)
- Context manager (``__enter__`` / ``__exit__``)

See Also
--------
market.nasdaq.client : NasdaqClient implementation.
market.nasdaq.client_parsers : ``unwrap_envelope`` implementation.
tests.market.nasdaq.conftest : Shared fixtures.
tests.market.alphavantage.unit.test_client : Reference test patterns.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from market.nasdaq.client import NasdaqClient
from market.nasdaq.client_parsers import unwrap_envelope
from market.nasdaq.client_types import NasdaqFetchOptions
from market.nasdaq.errors import NasdaqAPIError, NasdaqParseError

# =============================================================================
# Dependency Injection Tests
# =============================================================================


class TestNasdaqClientDI:
    """Tests for NasdaqClient dependency injection."""

    def test_正常系_セッションとキャッシュをDIで受け取る(
        self,
        mock_nasdaq_session: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """NasdaqClient accepts session and cache via constructor."""
        client = NasdaqClient(session=mock_nasdaq_session, cache=mock_cache)

        assert client._session is mock_nasdaq_session
        assert client._cache is mock_cache
        assert client._owns_session is False

    def test_正常系_セッション未指定時にデフォルトセッションを作成(
        self,
        mock_cache: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """NasdaqClient creates a default session when none is provided."""
        mock_session_cls = MagicMock()
        monkeypatch.setattr("market.nasdaq.client.NasdaqSession", mock_session_cls)
        client = NasdaqClient(cache=mock_cache)

        mock_session_cls.assert_called_once()
        assert client._owns_session is True

    def test_正常系_キャッシュ未指定時にデフォルトキャッシュを作成(
        self,
        mock_nasdaq_session: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """NasdaqClient creates a default cache when none is provided."""
        mock_get_cache = MagicMock()
        monkeypatch.setattr("market.nasdaq.client.get_nasdaq_cache", mock_get_cache)
        client = NasdaqClient(session=mock_nasdaq_session)

        mock_get_cache.assert_called_once()
        assert client._cache is mock_get_cache.return_value


# =============================================================================
# _fetch_and_parse Tests
# =============================================================================


class TestFetchAndParse:
    """Tests for NasdaqClient._fetch_and_parse DRY helper."""

    def test_正常系_キャッシュヒット時にAPIを呼ばない(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
    ) -> None:
        """When cache has data, API is not called."""
        cached_data = {"symbol": "AAPL", "price": 227.63}
        mock_cache.get.return_value = cached_data

        parser = MagicMock()
        result = nasdaq_client._fetch_and_parse(
            url="https://api.nasdaq.com/api/quote/AAPL/info",
            cache_key="test_key",
            parser=parser,
            ttl=3600,
        )

        assert result == cached_data
        mock_cache.get.assert_called_once_with("test_key")
        mock_nasdaq_session.get_with_retry.assert_not_called()
        parser.assert_not_called()

    def test_正常系_キャッシュミス時にAPIを呼びパース結果をキャッシュ(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
        sample_envelope_response: dict[str, object],
    ) -> None:
        """When cache misses, fetches from API, parses, and caches result."""
        mock_cache.get.return_value = None

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = sample_envelope_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        parsed_result = {"symbol": "AAPL", "exchange": "NASDAQ-GS"}
        parser = MagicMock(return_value=parsed_result)

        result = nasdaq_client._fetch_and_parse(
            url="https://api.nasdaq.com/api/quote/AAPL/info",
            cache_key="test_key",
            parser=parser,
            ttl=3600,
        )

        assert result == parsed_result
        mock_cache.get.assert_called_once_with("test_key")
        mock_nasdaq_session.get_with_retry.assert_called_once()
        parser.assert_called_once()
        mock_cache.set.assert_called_once_with("test_key", parsed_result, ttl=3600)

    def test_正常系_force_refresh時にキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
        sample_envelope_response: dict[str, object],
    ) -> None:
        """When force_refresh=True, cache is bypassed."""
        # Even if cache has data, it should be ignored
        mock_cache.get.return_value = {"old": "data"}

        mock_response = MagicMock()
        mock_response.json.return_value = sample_envelope_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        parsed_result = {"symbol": "AAPL", "fresh": True}
        parser = MagicMock(return_value=parsed_result)

        options = NasdaqFetchOptions(force_refresh=True)
        result = nasdaq_client._fetch_and_parse(
            url="https://api.nasdaq.com/api/quote/AAPL/info",
            cache_key="test_key",
            parser=parser,
            ttl=3600,
            options=options,
        )

        assert result == parsed_result
        # cache.get should NOT be called when force_refresh=True
        mock_cache.get.assert_not_called()
        mock_nasdaq_session.get_with_retry.assert_called_once()

    def test_正常系_use_cache_false時にキャッシュを無視(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
        sample_envelope_response: dict[str, object],
    ) -> None:
        """When use_cache=False, cache is not checked."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_envelope_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        parsed_result = {"symbol": "AAPL"}
        parser = MagicMock(return_value=parsed_result)

        options = NasdaqFetchOptions(use_cache=False)
        result = nasdaq_client._fetch_and_parse(
            url="https://api.nasdaq.com/api/quote/AAPL/info",
            cache_key="test_key",
            parser=parser,
            ttl=3600,
            options=options,
        )

        assert result == parsed_result
        mock_cache.get.assert_not_called()

    def test_正常系_paramsをAPIリクエストに渡す(
        self,
        nasdaq_client: NasdaqClient,
        mock_cache: MagicMock,
        mock_nasdaq_session: MagicMock,
        sample_envelope_response: dict[str, object],
    ) -> None:
        """Query parameters are forwarded to the API request."""
        mock_cache.get.return_value = None

        mock_response = MagicMock()
        mock_response.json.return_value = sample_envelope_response
        mock_nasdaq_session.get_with_retry.return_value = mock_response

        parser = MagicMock(return_value={})

        nasdaq_client._fetch_and_parse(
            url="https://api.nasdaq.com/api/calendar/earnings",
            cache_key="test_key",
            parser=parser,
            ttl=86400,
            params={"date": "2026-03-24"},
        )

        mock_nasdaq_session.get_with_retry.assert_called_once_with(
            "https://api.nasdaq.com/api/calendar/earnings",
            params={"date": "2026-03-24"},
        )


# =============================================================================
# unwrap_envelope Tests
# =============================================================================


class TestUnwrapEnvelope:
    """Tests for unwrap_envelope helper."""

    def test_正常系_rCode200でdataを返す(
        self,
        sample_envelope_response: dict[str, object],
    ) -> None:
        """Returns data dict when rCode is 200."""
        result = unwrap_envelope(
            sample_envelope_response,
            "https://api.nasdaq.com/api/quote/AAPL/info",
        )

        assert isinstance(result, dict)
        assert result["symbol"] == "AAPL"
        assert "summaryData" in result

    def test_異常系_rCode400でNasdaqAPIError(self) -> None:
        """Raises NasdaqAPIError when rCode is not 200."""
        raw: dict[str, Any] = {
            "data": None,
            "message": "Bad Request",
            "status": {"rCode": 400, "bCodeMessage": "Invalid symbol"},
        }

        with pytest.raises(NasdaqAPIError) as exc_info:
            unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/BAD/info")

        assert exc_info.value.status_code == 400
        assert "rCode 400" in str(exc_info.value)

    def test_異常系_rCode403でNasdaqAPIError(self) -> None:
        """Raises NasdaqAPIError when rCode is 403."""
        raw: dict[str, Any] = {
            "data": None,
            "message": "Forbidden",
            "status": {"rCode": 403, "bCodeMessage": None},
        }

        with pytest.raises(NasdaqAPIError) as exc_info:
            unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/AAPL/info")

        assert exc_info.value.status_code == 403

    def test_異常系_status欠落でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when status key is missing."""
        raw: dict[str, Any] = {"data": {"symbol": "AAPL"}}

        with pytest.raises(NasdaqParseError) as exc_info:
            unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/AAPL/info")

        assert exc_info.value.field == "status"

    def test_異常系_data欠落でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when data key is None with rCode=200."""
        raw: dict[str, Any] = {
            "data": None,
            "status": {"rCode": 200},
        }

        with pytest.raises(NasdaqParseError) as exc_info:
            unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/AAPL/info")

        assert exc_info.value.field == "data"

    def test_異常系_dataがdict以外でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when data is not a dict."""
        raw: dict[str, Any] = {
            "data": "not a dict",
            "status": {"rCode": 200},
        }

        with pytest.raises(NasdaqParseError) as exc_info:
            unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/AAPL/info")

        assert exc_info.value.field == "data"

    def test_異常系_statusがdict以外でNasdaqParseError(self) -> None:
        """Raises NasdaqParseError when status is not a dict."""
        raw: dict[str, Any] = {
            "data": {"symbol": "AAPL"},
            "status": "not a dict",
        }

        with pytest.raises(NasdaqParseError) as exc_info:
            unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/AAPL/info")

        assert exc_info.value.field == "status"


# =============================================================================
# _validate_symbol Tests
# =============================================================================


class TestValidateSymbol:
    """Tests for NasdaqClient._validate_symbol."""

    @pytest.mark.parametrize(
        ("symbol", "expected"),
        [
            ("AAPL", "AAPL"),
            ("MSFT", "MSFT"),
            ("GOOGL", "GOOGL"),
            ("BRK.B", "BRK.B"),
            ("BF-B", "BF-B"),
            ("T", "T"),
            ("X", "X"),
        ],
        ids=["AAPL", "MSFT", "GOOGL", "BRK.B", "BF-B", "single-T", "single-X"],
    )
    def test_正常系_有効なシンボルで正規化された文字列を返す(
        self, symbol: str, expected: str
    ) -> None:
        """Valid symbols return the normalized (uppercased) string."""
        result = NasdaqClient._validate_symbol(symbol)
        assert result == expected

    def test_正常系_小文字入力を大文字に正規化する(self) -> None:
        """Lowercase symbol is uppercased."""
        result = NasdaqClient._validate_symbol("aapl")
        assert result == "AAPL"

    def test_正常系_前後空白を除去して正規化する(self) -> None:
        """Leading/trailing whitespace is stripped and symbol is uppercased."""
        result = NasdaqClient._validate_symbol("  AAPL  ")
        assert result == "AAPL"

    def test_異常系_空文字列でValueError(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            NasdaqClient._validate_symbol("")

    def test_異常系_空白のみでValueError(self) -> None:
        """Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            NasdaqClient._validate_symbol("   ")

    def test_異常系_11文字以上でValueError(self) -> None:
        """Symbol longer than 10 characters raises ValueError."""
        with pytest.raises(ValueError, match="1-10 characters"):
            NasdaqClient._validate_symbol("A" * 11)

    @pytest.mark.parametrize(
        "symbol",
        ["AA@PL", "MS FT", "GO!GL", "AAPL$"],
        ids=["at-sign", "space", "exclamation", "dollar"],
    )
    def test_異常系_不正文字を含むシンボルでValueError(self, symbol: str) -> None:
        """Symbol with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            NasdaqClient._validate_symbol(symbol)


# =============================================================================
# _build_referer Tests
# =============================================================================


class TestBuildReferer:
    """Tests for NasdaqClient._build_referer."""

    def test_正常系_シンボル指定時に銘柄ページURLを返す(self) -> None:
        """Returns symbol-specific URL when symbol is provided."""
        result = NasdaqClient._build_referer("AAPL")
        assert result == "https://www.nasdaq.com/market-activity/stocks/aapl"

    def test_正常系_大文字シンボルが小文字に変換される(self) -> None:
        """Symbol is lowercased in the URL."""
        result = NasdaqClient._build_referer("GOOGL")
        assert result == "https://www.nasdaq.com/market-activity/stocks/googl"

    def test_正常系_シンボル未指定時にマーケット活動ページURLを返す(self) -> None:
        """Returns generic market activity URL when no symbol."""
        result = NasdaqClient._build_referer()
        assert result == "https://www.nasdaq.com/market-activity"

    def test_正常系_None指定時にマーケット活動ページURLを返す(self) -> None:
        """Returns generic market activity URL when symbol is None."""
        result = NasdaqClient._build_referer(None)
        assert result == "https://www.nasdaq.com/market-activity"


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Tests for NasdaqClient context manager support."""

    def test_正常系_withブロックでクライアントを返す(
        self,
        mock_nasdaq_session: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Context manager returns the client instance."""
        with NasdaqClient(session=mock_nasdaq_session, cache=mock_cache) as client:
            assert isinstance(client, NasdaqClient)

    def test_正常系_withブロック終了時にクローズされる(
        self,
        mock_cache: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Session is closed when exiting the context manager (owned session)."""
        mock_session_cls = MagicMock()
        mock_session_instance = MagicMock()
        mock_session_cls.return_value = mock_session_instance
        monkeypatch.setattr("market.nasdaq.client.NasdaqSession", mock_session_cls)

        with NasdaqClient(cache=mock_cache):
            pass

        mock_session_instance.close.assert_called_once()

    def test_正常系_注入セッションはクローズしない(
        self,
        mock_nasdaq_session: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Injected session is NOT closed when client is closed."""
        with NasdaqClient(session=mock_nasdaq_session, cache=mock_cache):
            pass

        mock_nasdaq_session.close.assert_not_called()


# =============================================================================
# NasdaqFetchOptions Tests
# =============================================================================


class TestNasdaqFetchOptions:
    """Tests for NasdaqFetchOptions dataclass."""

    def test_正常系_デフォルト値(self) -> None:
        """Default values are use_cache=True, force_refresh=False."""
        options = NasdaqFetchOptions()
        assert options.use_cache is True
        assert options.force_refresh is False

    def test_正常系_frozen_dataclass(self) -> None:
        """NasdaqFetchOptions is immutable (frozen)."""
        options = NasdaqFetchOptions()
        with pytest.raises(AttributeError):
            options.use_cache = False

    def test_正常系_カスタム値(self) -> None:
        """Custom values are accepted."""
        options = NasdaqFetchOptions(use_cache=False, force_refresh=True)
        assert options.use_cache is False
        assert options.force_refresh is True


# =============================================================================
# _validate_date Tests
# =============================================================================


class TestValidateDate:
    """Tests for NasdaqClient._validate_date."""

    def test_正常系_YYYY_MM_DD形式を受け付ける(self) -> None:
        """Valid YYYY-MM-DD date string is accepted."""
        result = NasdaqClient._validate_date("2026-01-30")
        assert result == "2026-01-30"

    def test_正常系_前後空白を除去する(self) -> None:
        """Leading/trailing whitespace is stripped."""
        result = NasdaqClient._validate_date("  2026-01-30  ")
        assert result == "2026-01-30"

    def test_異常系_不正なフォーマットでValueError(self) -> None:
        """Slash-separated date raises ValueError."""
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            NasdaqClient._validate_date("2026/01/30")

    def test_異常系_年月のみでValueError(self) -> None:
        """Year-month only string raises ValueError."""
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            NasdaqClient._validate_date("2026-01")


# =============================================================================
# _validate_year_month Tests
# =============================================================================


class TestValidateYearMonth:
    """Tests for NasdaqClient._validate_year_month."""

    def test_正常系_YYYY_MM形式を受け付ける(self) -> None:
        """Valid YYYY-MM year-month string is accepted."""
        result = NasdaqClient._validate_year_month("2026-03")
        assert result == "2026-03"

    def test_正常系_前後空白を除去する(self) -> None:
        """Leading/trailing whitespace is stripped."""
        result = NasdaqClient._validate_year_month("  2026-03  ")
        assert result == "2026-03"

    def test_異常系_日付付きでValueError(self) -> None:
        """Full date string raises ValueError."""
        with pytest.raises(ValueError, match="YYYY-MM"):
            NasdaqClient._validate_year_month("2026-03-01")

    def test_異常系_不正なフォーマットでValueError(self) -> None:
        """Non-numeric format raises ValueError."""
        with pytest.raises(ValueError, match="YYYY-MM"):
            NasdaqClient._validate_year_month("March 2026")
