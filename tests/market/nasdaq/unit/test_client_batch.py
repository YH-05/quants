"""Unit tests for NasdaqClient.fetch_for_symbols() batch helper.

Tests cover:
- Normal: multiple symbols successfully fetched
- Normal: empty symbol list returns empty dict
- Error: non-existent method name raises AttributeError
- Normal: partial failure (some symbols fail, others succeed)
- Normal: kwargs are forwarded to the underlying method

Test TODO List:
- [x] test_正常系_複数シンボルで一括取得成功
- [x] test_正常系_空リストで空辞書を返す
- [x] test_異常系_存在しないメソッド名でAttributeError
- [x] test_正常系_部分失敗時にエラーログを出力して継続
- [x] test_正常系_追加キーワード引数が転送される

See Also
--------
market.nasdaq.client : NasdaqClient.fetch_for_symbols implementation.
tests.market.nasdaq.conftest : Shared fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from market.nasdaq.client_types import NasdaqFetchOptions, ShortInterestRecord

if TYPE_CHECKING:
    from market.nasdaq.client import NasdaqClient


class TestFetchForSymbolsNormal:
    """Tests for fetch_for_symbols() normal operation."""

    def test_正常系_複数シンボルで一括取得成功(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Multiple symbols are fetched successfully and returned as a dict."""
        mock_records_aapl = [
            ShortInterestRecord(
                settlement_date="03/15/2026", short_interest="15,000,000"
            )
        ]
        mock_records_msft = [
            ShortInterestRecord(
                settlement_date="03/15/2026", short_interest="10,000,000"
            )
        ]

        with patch.object(
            nasdaq_client,
            "get_short_interest",
            side_effect=[mock_records_aapl, mock_records_msft],
        ):
            results = nasdaq_client.fetch_for_symbols(
                ["AAPL", "MSFT"],
                "get_short_interest",
            )

        assert len(results) == 2
        assert results["AAPL"] == mock_records_aapl
        assert results["MSFT"] == mock_records_msft

    def test_正常系_空リストで空辞書を返す(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Empty symbol list returns an empty dict without errors."""
        results = nasdaq_client.fetch_for_symbols([], "get_short_interest")

        assert results == {}
        assert isinstance(results, dict)

    def test_正常系_追加キーワード引数が転送される(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Additional kwargs are forwarded to the endpoint method."""
        options = NasdaqFetchOptions(force_refresh=True)
        mock_method = MagicMock(return_value=[])

        with patch.object(nasdaq_client, "get_short_interest", mock_method):
            nasdaq_client.fetch_for_symbols(
                ["AAPL"],
                "get_short_interest",
                options=options,
            )

        mock_method.assert_called_once_with("AAPL", options=options)

    def test_正常系_単一シンボルで辞書に1件返す(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Single symbol returns a dict with one entry."""
        mock_records = [ShortInterestRecord(settlement_date="03/15/2026")]

        with patch.object(
            nasdaq_client,
            "get_short_interest",
            return_value=mock_records,
        ):
            results = nasdaq_client.fetch_for_symbols(
                ["AAPL"],
                "get_short_interest",
            )

        assert len(results) == 1
        assert results["AAPL"] == mock_records


class TestFetchForSymbolsError:
    """Tests for fetch_for_symbols() error handling."""

    def test_異常系_存在しないメソッド名でAttributeError(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Non-existent method name raises AttributeError."""
        with pytest.raises(AttributeError):
            nasdaq_client.fetch_for_symbols(
                ["AAPL"],
                "get_nonexistent_data",
            )

    def test_正常系_部分失敗時にエラーログを出力して継続(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Partial failure: failed symbols are logged and skipped."""
        mock_records = [
            ShortInterestRecord(
                settlement_date="03/15/2026", short_interest="15,000,000"
            )
        ]

        def side_effect(symbol: str, **kwargs: Any) -> list[ShortInterestRecord]:
            if symbol == "INVALID":
                raise ValueError("API error for INVALID")
            return mock_records

        with patch.object(
            nasdaq_client,
            "get_short_interest",
            side_effect=side_effect,
        ):
            results = nasdaq_client.fetch_for_symbols(
                ["AAPL", "INVALID", "MSFT"],
                "get_short_interest",
            )

        # AAPL and MSFT succeed, INVALID is skipped
        assert len(results) == 2
        assert "AAPL" in results
        assert "MSFT" in results
        assert "INVALID" not in results

    def test_正常系_全シンボル失敗時に空辞書を返す(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """All symbols fail: returns empty dict."""
        with patch.object(
            nasdaq_client,
            "get_short_interest",
            side_effect=ValueError("API error"),
        ):
            results = nasdaq_client.fetch_for_symbols(
                ["BAD1", "BAD2"],
                "get_short_interest",
            )

        assert results == {}


class TestFetchForSymbolsCallOrder:
    """Tests for fetch_for_symbols() call sequencing."""

    def test_正常系_シンボルが順番に処理される(
        self,
        nasdaq_client: NasdaqClient,
    ) -> None:
        """Symbols are processed in order."""
        call_order: list[str] = []

        def side_effect(symbol: str, **kwargs: Any) -> list[Any]:
            call_order.append(symbol)
            return []

        with patch.object(
            nasdaq_client,
            "get_short_interest",
            side_effect=side_effect,
        ):
            nasdaq_client.fetch_for_symbols(
                ["AAPL", "MSFT", "GOOGL"],
                "get_short_interest",
            )

        assert call_order == ["AAPL", "MSFT", "GOOGL"]
