"""Unit tests for BhavcopyCollector and parse_bhavcopy_csv.

Tests cover:
- parse_bhavcopy_csv: CSV parsing, column renaming, numeric cleaning
- BhavcopyCollector: URL building, equity/derivative fetch, date range
- DataCollector ABC compliance
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.bse.collectors.bhavcopy import BhavcopyCollector
from market.bse.errors import BseParseError
from market.bse.parsers import parse_bhavcopy_csv
from market.bse.types import BhavcopyType

# ---------------------------------------------------------------------------
# Sample CSV data
# ---------------------------------------------------------------------------

_EQUITY_BHAVCOPY_CSV: str = (
    "SC_CODE,SC_NAME,SC_GROUP,SC_TYPE,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,"
    "NO_TRADES,NO_OF_SHRS,NET_TURNOV,TDCLOINDI,ISIN_CODE,TRADING_DATE\n"
    "500325,RELIANCE INDUSTRIES LT,A,Q,2450.00,2480.50,2440.00,2470.25,"
    "2469.90,2445.00,125000,5000000,12345678900,,INE002A01018,20260305\n"
    "500180,HDFC BANK LTD,A,Q,1650.00,1670.50,1640.00,1660.25,"
    "1659.90,1645.00,98000,3500000,5800000000,,INE040A01034,20260305\n"
)

_DERIVATIVE_BHAVCOPY_CSV: str = (
    "SC_CODE,SC_NAME,SC_GROUP,SC_TYPE,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,"
    "NO_TRADES,NO_OF_SHRS,NET_TURNOV,TDCLOINDI,ISIN_CODE,TRADING_DATE\n"
    "800100,SENSEX FUT MAR26,F,XX,74500.00,74800.00,74200.00,74600.00,"
    "74550.00,74400.00,5000,250000,18650000000,,INE999Z01001,20260305\n"
)


# ===========================================================================
# parse_bhavcopy_csv tests
# ===========================================================================


class TestParseBhavcopyCSV:
    """Tests for parse_bhavcopy_csv function."""

    def test_正常系_equity_bhavcopyをパースできる(self) -> None:
        df = parse_bhavcopy_csv(_EQUITY_BHAVCOPY_CSV)

        assert len(df) == 2
        assert "scrip_code" in df.columns
        assert "scrip_name" in df.columns
        assert "open" in df.columns
        assert "close" in df.columns
        assert "trading_date" in df.columns

    def test_正常系_数値カラムがクリーニングされる(self) -> None:
        df = parse_bhavcopy_csv(_EQUITY_BHAVCOPY_CSV)

        # Price columns should be float
        assert df["open"].iloc[0] == pytest.approx(2450.0)
        assert df["close"].iloc[0] == pytest.approx(2470.25)

    def test_正常系_文字列カラムの空白が除去される(self) -> None:
        csv_with_spaces = (
            "SC_CODE, SC_NAME ,SC_GROUP,SC_TYPE,OPEN,HIGH,LOW,CLOSE,LAST,"
            "PREVCLOSE,NO_TRADES,NO_OF_SHRS,NET_TURNOV,TDCLOINDI,ISIN_CODE,"
            "TRADING_DATE\n"
            "500325, RELIANCE ,A,Q,2450.00,2480.50,2440.00,2470.25,"
            "2469.90,2445.00,125000,5000000,12345678900,,INE002A01018,20260305\n"
        )
        df = parse_bhavcopy_csv(csv_with_spaces)
        assert df["scrip_name"].iloc[0] == "RELIANCE"

    def test_正常系_bytes入力を受け付ける(self) -> None:
        df = parse_bhavcopy_csv(_EQUITY_BHAVCOPY_CSV.encode("utf-8"))
        assert len(df) == 2

    def test_正常系_utf8_bom付きbytes入力を受け付ける(self) -> None:
        content = b"\xef\xbb\xbf" + _EQUITY_BHAVCOPY_CSV.encode("utf-8")
        df = parse_bhavcopy_csv(content)
        assert len(df) == 2

    def test_異常系_空文字列でBseParseError(self) -> None:
        with pytest.raises(BseParseError, match="Empty"):
            parse_bhavcopy_csv("")

    def test_異常系_空bytesでBseParseError(self) -> None:
        with pytest.raises(BseParseError, match="Empty"):
            parse_bhavcopy_csv(b"")

    def test_エッジケース_ヘッダーのみでデータなし(self) -> None:
        header_only = (
            "SC_CODE,SC_NAME,SC_GROUP,SC_TYPE,OPEN,HIGH,LOW,CLOSE,LAST,"
            "PREVCLOSE,NO_TRADES,NO_OF_SHRS,NET_TURNOV,TDCLOINDI,ISIN_CODE,"
            "TRADING_DATE\n"
        )
        df = parse_bhavcopy_csv(header_only)
        assert df.empty

    def test_正常系_カラム名がsnake_caseにマッピングされる(self) -> None:
        df = parse_bhavcopy_csv(_EQUITY_BHAVCOPY_CSV)
        expected_columns = {
            "scrip_code",
            "scrip_name",
            "scrip_group",
            "scrip_type",
            "open",
            "high",
            "low",
            "close",
            "last",
            "prev_close",
            "num_trades",
            "num_shares",
            "net_turnover",
            "tdcloindi",
            "isin_code",
            "trading_date",
        }
        assert expected_columns.issubset(set(df.columns))


# ===========================================================================
# BhavcopyCollector._build_url tests
# ===========================================================================


class TestBhavcopyCollectorBuildUrl:
    """Tests for BhavcopyCollector._build_url method."""

    def test_正常系_equity_url構築(self) -> None:
        collector = BhavcopyCollector()
        date = datetime.date(2026, 3, 5)
        url = collector._build_url(date, BhavcopyType.EQUITY)

        assert "BhavCopy_BSE_CM_0_0_0_20260305_F_0000.CSV" in url
        assert "www.bseindia.com" in url

    def test_正常系_derivatives_url構築(self) -> None:
        collector = BhavcopyCollector()
        date = datetime.date(2026, 3, 5)
        url = collector._build_url(date, BhavcopyType.DERIVATIVES)

        assert "20260305" in url
        assert "www.bseindia.com" in url

    def test_正常系_日付フォーマットYYYYMMDD(self) -> None:
        collector = BhavcopyCollector()
        date = datetime.date(2026, 1, 9)
        url = collector._build_url(date, BhavcopyType.EQUITY)

        assert "20260109" in url


# ===========================================================================
# BhavcopyCollector.fetch_equity / fetch_derivative tests
# ===========================================================================


class TestBhavcopyCollectorFetchEquity:
    """Tests for BhavcopyCollector.fetch_equity method."""

    def test_正常系_equity_bhavcopyを取得できる(self) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.content = _EQUITY_BHAVCOPY_CSV.encode("utf-8")
        mock_session.download.return_value = mock_response.content

        collector = BhavcopyCollector(session=mock_session)
        date = datetime.date(2026, 3, 5)
        df = collector.fetch_equity(date)

        assert len(df) == 2
        assert "scrip_code" in df.columns
        mock_session.download.assert_called_once()

    def test_正常系_derivative_bhavcopyを取得できる(self) -> None:
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.content = _DERIVATIVE_BHAVCOPY_CSV.encode("utf-8")
        mock_session.download.return_value = mock_response.content

        collector = BhavcopyCollector(session=mock_session)
        date = datetime.date(2026, 3, 5)
        df = collector.fetch_derivative(date)

        assert len(df) == 1
        mock_session.download.assert_called_once()


# ===========================================================================
# BhavcopyCollector.fetch_date_range tests
# ===========================================================================


class TestBhavcopyCollectorFetchDateRange:
    """Tests for BhavcopyCollector.fetch_date_range method."""

    def test_正常系_日付範囲で複数日分を取得(self) -> None:
        mock_session = MagicMock()
        mock_session.download.return_value = _EQUITY_BHAVCOPY_CSV.encode("utf-8")

        collector = BhavcopyCollector(session=mock_session)
        start = datetime.date(2026, 3, 3)
        end = datetime.date(2026, 3, 5)
        df = collector.fetch_date_range(start, end)

        # 3 days: 3, 4, 5
        assert mock_session.download.call_count == 3
        # Each day returns 2 rows
        assert len(df) == 6

    def test_正常系_単一日でも動作する(self) -> None:
        mock_session = MagicMock()
        mock_session.download.return_value = _EQUITY_BHAVCOPY_CSV.encode("utf-8")

        collector = BhavcopyCollector(session=mock_session)
        date = datetime.date(2026, 3, 5)
        df = collector.fetch_date_range(date, date)

        assert mock_session.download.call_count == 1
        assert len(df) == 2

    def test_異常系_開始日が終了日より後でValueError(self) -> None:
        collector = BhavcopyCollector()
        with pytest.raises(ValueError, match="start.*end"):
            collector.fetch_date_range(
                datetime.date(2026, 3, 6),
                datetime.date(2026, 3, 5),
            )

    def test_正常系_一部の日がエラーでもスキップして継続(self) -> None:
        mock_session = MagicMock()

        # First call succeeds, second call raises (holiday), third succeeds
        mock_session.download.side_effect = [
            _EQUITY_BHAVCOPY_CSV.encode("utf-8"),
            Exception("404 Not Found"),
            _EQUITY_BHAVCOPY_CSV.encode("utf-8"),
        ]

        collector = BhavcopyCollector(session=mock_session)
        start = datetime.date(2026, 3, 3)
        end = datetime.date(2026, 3, 5)
        df = collector.fetch_date_range(start, end)

        # 2 successful days x 2 rows each
        assert len(df) == 4

    def test_エッジケース_全日失敗で空DataFrameを返す(self) -> None:
        mock_session = MagicMock()

        # All days fail
        mock_session.download.side_effect = [
            Exception("404 Not Found"),
            Exception("500 Server Error"),
            Exception("Timeout"),
        ]

        collector = BhavcopyCollector(session=mock_session)
        start = datetime.date(2026, 3, 3)
        end = datetime.date(2026, 3, 5)
        df = collector.fetch_date_range(start, end)

        assert df.empty


# ===========================================================================
# DataCollector ABC compliance tests
# ===========================================================================


class TestBhavcopyCollectorABCCompliance:
    """Tests for DataCollector ABC interface compliance."""

    def test_正常系_fetchメソッドが実装されている(self) -> None:
        collector = BhavcopyCollector()
        assert hasattr(collector, "fetch")
        assert callable(collector.fetch)

    def test_正常系_validateメソッドが実装されている(self) -> None:
        collector = BhavcopyCollector()
        assert hasattr(collector, "validate")
        assert callable(collector.validate)

    def test_正常系_nameプロパティが正しい(self) -> None:
        collector = BhavcopyCollector()
        assert collector.name == "BhavcopyCollector"

    def test_正常系_validateが有効なDataFrameでTrue(self) -> None:
        collector = BhavcopyCollector()
        df = pd.DataFrame(
            {
                "scrip_code": ["500325"],
                "scrip_name": ["RELIANCE"],
                "trading_date": ["20260305"],
            }
        )
        assert collector.validate(df) is True

    def test_正常系_validateが空DataFrameでFalse(self) -> None:
        collector = BhavcopyCollector()
        assert collector.validate(pd.DataFrame()) is False

    def test_正常系_validateが必須カラム欠落でFalse(self) -> None:
        collector = BhavcopyCollector()
        df = pd.DataFrame({"some_column": [1]})
        assert collector.validate(df) is False

    def test_正常系_fetchがdateパラメータで動作(self) -> None:
        mock_session = MagicMock()
        mock_session.download.return_value = _EQUITY_BHAVCOPY_CSV.encode("utf-8")

        collector = BhavcopyCollector(session=mock_session)
        df = collector.fetch(date="2026-03-05")

        assert len(df) == 2

    def test_異常系_fetchにdateなしでValueError(self) -> None:
        collector = BhavcopyCollector()
        with pytest.raises(ValueError, match="date"):
            collector.fetch()

    def test_正常系_DI_sessionが注入できる(self) -> None:
        mock_session = MagicMock()
        collector = BhavcopyCollector(session=mock_session)
        session, should_close = collector._get_session()

        assert session is mock_session
        assert should_close is False

    def test_正常系_session未注入で新規作成(self) -> None:
        collector = BhavcopyCollector()
        with patch("market.bse.collectors._base.BseSession") as mock_cls:
            session, should_close = collector._get_session()

            mock_cls.assert_called_once()
            assert should_close is True
