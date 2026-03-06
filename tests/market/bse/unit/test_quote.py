"""Unit tests for market.bse.collectors.quote module.

QuoteCollector の動作を検証するテストスイート。
DataCollector ABC を継承した BSE QuoteCollector のテスト。

Test TODO List:
- [x] QuoteCollector: デフォルト値で初期化（session なし）
- [x] QuoteCollector: DI パターンで session 注入
- [x] _get_session(): 注入なし時に新規セッション生成（should_close=True）
- [x] _get_session(): 注入あり時に既存セッション返却（should_close=False）
- [x] fetch(): scrip_code で単一銘柄取得
- [x] fetch(): scrip_code 未指定で ValueError
- [x] fetch(): API エラー時に例外を伝播
- [x] validate(): 有効な DataFrame で True
- [x] validate(): 空 DataFrame で False
- [x] validate(): 必須カラム不足で False
- [x] fetch_quote(): 単一銘柄のクオートを取得
- [x] fetch_quote(): セッションを正しくクローズ
- [x] fetch_historical(): 履歴データを取得
- [x] fetch_historical(): 空レスポンスで BseParseError
- [x] Module exports: __all__ completeness
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.bse.collectors.quote import QuoteCollector
from market.bse.errors import BseAPIError, BseParseError
from market.bse.session import BseSession
from market.bse.types import ScripQuote

# =============================================================================
# Helper: create mock session and response
# =============================================================================


def _make_quote_json(
    *,
    scrip_code: str = "500325",
    scrip_name: str = "RELIANCE INDUSTRIES LTD",
) -> dict:
    """Create a mock BSE API quote JSON response."""
    return {
        "ScripCode": scrip_code,
        "ScripName": scrip_name,
        "ScripGroup": "A",
        "Open": "2450.00",
        "High": "2480.50",
        "Low": "2440.00",
        "Close": "2470.25",
        "last": "2469.90",
        "PrevClose": "2445.00",
        "No_Trades": "125000",
        "No_of_Shrs": "5000000",
        "Net_Turnov": "12345678900",
    }


def _make_historical_csv_response() -> str:
    """Create a mock BSE historical CSV response."""
    return (
        "ScripCode,ScripName,Open,High,Low,Close\n"
        "500325,RELIANCE INDUSTRIES LTD,2450.00,2480.50,2440.00,2470.25\n"
        "500325,RELIANCE INDUSTRIES LTD,2470.25,2490.00,2460.00,2485.50\n"
    )


def _make_mock_session(
    *,
    response_json: dict | None = None,
    response_text: str | None = None,
) -> MagicMock:
    """Create a mock BseSession with pre-configured responses.

    Parameters
    ----------
    response_json : dict | None
        JSON response for get_with_retry(). Uses default quote if None.
    response_text : str | None
        Text response for get_with_retry(). Uses default CSV if None.

    Returns
    -------
    MagicMock
        A mock BseSession instance.
    """
    mock_session = MagicMock(spec=BseSession)
    mock_response = MagicMock()
    mock_response.json.return_value = response_json or _make_quote_json()
    mock_response.text = (
        response_text if response_text is not None else _make_historical_csv_response()
    )
    mock_response.status_code = 200
    mock_session.get_with_retry.return_value = mock_response
    return mock_session


# =============================================================================
# Initialization tests
# =============================================================================


class TestQuoteCollectorInit:
    """QuoteCollector 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """session なしでデフォルト初期化されること。"""
        collector = QuoteCollector()

        assert collector._session_instance is None
        assert collector.name == "QuoteCollector"

    def test_正常系_DIパターンでsession注入できる(self) -> None:
        """DI パターンで BseSession を注入できること。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        assert collector._session_instance is mock_session


# =============================================================================
# _get_session tests
# =============================================================================


class TestGetSession:
    """_get_session() ヘルパーのテスト。"""

    def test_正常系_注入なし時に新規セッション生成(self) -> None:
        """session 未注入時に新規 BseSession を生成し should_close=True。"""
        collector = QuoteCollector()

        with patch("market.bse.collectors.quote.BseSession") as mock_cls:
            mock_cls.return_value = MagicMock(spec=BseSession)
            _session, should_close = collector._get_session()

        assert should_close is True
        mock_cls.assert_called_once()

    def test_正常系_注入あり時に既存セッション返却(self) -> None:
        """session 注入時に既存セッションを返し should_close=False。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        session, should_close = collector._get_session()

        assert session is mock_session
        assert should_close is False


# =============================================================================
# fetch tests
# =============================================================================


class TestFetch:
    """fetch() メソッドのテスト。"""

    def test_正常系_scripCodeで単一銘柄取得(self) -> None:
        """scrip_code を指定して API を呼び出し DataFrame を返すこと。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        df = collector.fetch(scrip_code="500325")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "scrip_code" in df.columns
        assert "scrip_name" in df.columns
        assert df["scrip_code"].iloc[0] == "500325"
        mock_session.get_with_retry.assert_called_once()

    def test_異常系_scripCode未指定でValueError(self) -> None:
        """scrip_code を指定しない場合に ValueError が発生すること。"""
        collector = QuoteCollector()

        with pytest.raises(ValueError, match="scrip_code is required"):
            collector.fetch()

    def test_異常系_APIエラー時に例外伝播(self) -> None:
        """API エラー時に BseAPIError が伝播すること。"""
        mock_session = MagicMock(spec=BseSession)
        mock_session.get_with_retry.side_effect = BseAPIError(
            "API returned HTTP 500",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        collector = QuoteCollector(session=mock_session)

        with pytest.raises(BseAPIError, match="HTTP 500"):
            collector.fetch(scrip_code="500325")


# =============================================================================
# validate tests
# =============================================================================


class TestValidate:
    """validate() メソッドのテスト。"""

    def test_正常系_有効なDataFrameでTrue(self) -> None:
        """scrip_code と scrip_name を含む非空 DataFrame で True を返すこと。"""
        collector = QuoteCollector()
        df = pd.DataFrame(
            {
                "scrip_code": ["500325", "500180"],
                "scrip_name": ["RELIANCE", "HDFC BANK"],
            }
        )

        assert collector.validate(df) is True

    def test_異常系_空DataFrameでFalse(self) -> None:
        """空の DataFrame で False を返すこと。"""
        collector = QuoteCollector()
        df = pd.DataFrame()

        assert collector.validate(df) is False

    def test_異常系_必須カラム不足でFalse(self) -> None:
        """scrip_code カラムがない場合に False を返すこと。"""
        collector = QuoteCollector()
        df = pd.DataFrame({"other_col": ["value1"]})

        assert collector.validate(df) is False


# =============================================================================
# fetch_quote tests
# =============================================================================


class TestFetchQuote:
    """fetch_quote() メソッドのテスト。"""

    def test_正常系_単一銘柄のクオートを取得(self) -> None:
        """scrip_code で API を呼び出し ScripQuote を返すこと。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        quote = collector.fetch_quote("500325")

        assert isinstance(quote, ScripQuote)
        assert quote.scrip_code == "500325"
        assert quote.scrip_name == "RELIANCE INDUSTRIES LTD"
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session()
        collector = QuoteCollector()

        with patch(
            "market.bse.collectors.quote.BseSession",
            return_value=mock_new_session,
        ):
            collector.fetch_quote("500325")

        mock_new_session.close.assert_called_once()

    def test_正常系_注入セッションはクローズしない(self) -> None:
        """注入されたセッションはクローズされないこと。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        collector.fetch_quote("500325")

        mock_session.close.assert_not_called()

    def test_正常系_正しいパラメータでAPIを呼び出す(self) -> None:
        """正しいエンドポイントとパラメータで API を呼び出すこと。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        collector.fetch_quote("500325")

        call_args = mock_session.get_with_retry.call_args
        url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
        params = call_args.kwargs.get("params") or (
            call_args[1].get("params") if len(call_args) > 1 else None
        )

        assert "getScripHeaderData" in url
        assert params is not None
        assert params["scripcode"] == "500325"


# =============================================================================
# fetch_historical tests
# =============================================================================


class TestFetchHistorical:
    """fetch_historical() メソッドのテスト。"""

    def test_正常系_履歴データを取得(self) -> None:
        """scrip_code で履歴データを取得し DataFrame を返すこと。"""
        mock_session = _make_mock_session()
        collector = QuoteCollector(session=mock_session)

        df = collector.fetch_historical("500325")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        mock_session.get_with_retry.assert_called_once()

    def test_異常系_空レスポンスでBseParseError(self) -> None:
        """空の履歴データレスポンスで BseParseError が発生すること。"""
        mock_session = _make_mock_session(response_text="")
        collector = QuoteCollector(session=mock_session)

        with pytest.raises(BseParseError, match="Empty"):
            collector.fetch_historical("500325")

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session()
        collector = QuoteCollector()

        with patch(
            "market.bse.collectors.quote.BseSession",
            return_value=mock_new_session,
        ):
            collector.fetch_historical("500325")

        mock_new_session.close.assert_called_once()


# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Module exports のテスト。"""

    def test_正常系_allが定義されている(self) -> None:
        """__all__ が QuoteCollector を含むこと。"""
        from market.bse.collectors.quote import __all__

        assert "QuoteCollector" in __all__
