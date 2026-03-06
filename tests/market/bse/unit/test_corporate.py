"""Unit tests for market.bse.collectors.corporate module.

CorporateCollector の動作を検証するテストスイート。
非 ABC の BSE CorporateCollector のテスト。

Test TODO List:
- [x] CorporateCollector: デフォルト値で初期化（session なし）
- [x] CorporateCollector: DI パターンで session 注入
- [x] _get_session(): 注入なし時に新規セッション生成（should_close=True）
- [x] _get_session(): 注入あり時に既存セッション返却（should_close=False）
- [x] get_company_info(): 企業情報を取得
- [x] get_company_info(): セッションを正しくクローズ
- [x] get_company_info(): API エラー時に例外伝播
- [x] get_financial_results(): 決算情報リストを取得
- [x] get_financial_results(): 空レスポンスで空リスト
- [x] get_financial_results(): セッションを正しくクローズ
- [x] get_announcements(): アナウンスリストを取得
- [x] get_announcements(): 空レスポンスで空リスト
- [x] get_announcements(): セッションを正しくクローズ
- [x] get_corporate_actions(): コーポレートアクションリストを取得
- [x] get_corporate_actions(): 空レスポンスで空リスト
- [x] get_corporate_actions(): セッションを正しくクローズ
- [x] search_scrip(): 検索結果リストを取得
- [x] search_scrip(): 空レスポンスで空リスト
- [x] search_scrip(): 非リストレスポンスで空リスト
- [x] Module exports: __all__ completeness

Parser tests:
- [x] parse_company_info(): 有効なレスポンス
- [x] parse_company_info(): 空 dict で BseParseError
- [x] parse_company_info(): 非 dict で BseParseError
- [x] parse_company_info(): 必須フィールド両方欠損で BseParseError
- [x] parse_financial_results(): 有効なレスポンス
- [x] parse_financial_results(): 空リストで空結果
- [x] parse_financial_results(): 非リストで BseParseError
- [x] parse_financial_results(): 非 dict 要素をスキップ
- [x] parse_announcements(): 有効なレスポンス
- [x] parse_announcements(): 空リストで空結果
- [x] parse_announcements(): 非リストで BseParseError
- [x] parse_corporate_actions(): 有効なレスポンス
- [x] parse_corporate_actions(): 空リストで空結果
- [x] parse_corporate_actions(): 非リストで BseParseError
"""

from unittest.mock import MagicMock, patch

import pytest

from market.bse.collectors.corporate import CorporateCollector
from market.bse.errors import BseAPIError, BseParseError
from market.bse.parsers import (
    parse_announcements,
    parse_company_info,
    parse_corporate_actions,
    parse_financial_results,
)
from market.bse.session import BseSession
from market.bse.types import Announcement, CorporateAction, FinancialResult

# =============================================================================
# Helper: create mock data
# =============================================================================


def _make_company_info_json(
    *,
    scrip_code: str = "500325",
    company_name: str = "RELIANCE INDUSTRIES LTD",
) -> dict:
    """Create a mock BSE API company info JSON response."""
    return {
        "scrip_cd": scrip_code,
        "compname": company_name,
        "ISIN_NUMBER": "INE002A01018",
        "Scrip_grp": "A",
        "INDUSTRY": "Refineries",
        "Mktcap": "1800000",
        "Facevalue": "10.00",
    }


def _make_financial_results_json(
    *,
    scrip_code: str = "500325",
    count: int = 2,
) -> list[dict]:
    """Create a mock BSE API financial results JSON response."""
    results = []
    for i in range(count):
        results.append(
            {
                "scrip_cd": scrip_code,
                "companyname": "RELIANCE INDUSTRIES LTD",
                "cons_prd_to": f"31-Mar-202{5 - i}",
                "cons_revenue": f"{250000 - i * 10000}",
                "cons_netpnl": f"{18500 - i * 1000}",
                "cons_eps": f"{27.35 - i * 2.0:.2f}",
            }
        )
    return results


def _make_announcements_json(
    *,
    scrip_code: str = "500325",
    count: int = 2,
) -> list[dict]:
    """Create a mock BSE API announcements JSON response."""
    subjects = ["Board Meeting Outcome", "Quarterly Results"]
    categories = ["Board Meeting", "Result"]
    return [
        {
            "SCRIP_CD": scrip_code,
            "SLONGNAME": "RELIANCE INDUSTRIES LTD",
            "HEADLINE": subjects[i % len(subjects)],
            "DT_TM": f"1{5 + i}-Jan-2025",
            "CATEGORYNAME": categories[i % len(categories)],
        }
        for i in range(count)
    ]


def _make_corporate_actions_json(
    *,
    scrip_code: str = "500325",
    count: int = 2,
) -> list[dict]:
    """Create a mock BSE API corporate actions JSON response."""
    purposes = ["Dividend - Rs 8 Per Share", "Bonus 1:1"]
    return [
        {
            "scrip_code": scrip_code,
            "comp_name": "RELIANCE INDUSTRIES LTD",
            "ex_dt": f"0{1 + i}-Feb-2025",
            "PURPOSE": purposes[i % len(purposes)],
            "Record_dt": f"0{3 + i}-Feb-2025",
        }
        for i in range(count)
    ]


def _make_scrip_search_json() -> list[dict]:
    """Create a mock BSE API scrip search JSON response."""
    return [
        {
            "scrip_cd": "500325",
            "scripname": "RELIANCE INDUSTRIES LTD",
        },
        {
            "scrip_cd": "500111",
            "scripname": "RELIANCE CAPITAL LTD",
        },
    ]


def _make_mock_session(
    *,
    response_json: list | dict | None = None,
) -> MagicMock:
    """Create a mock BseSession with pre-configured responses.

    Parameters
    ----------
    response_json : list | dict | None
        JSON response for get_with_retry().

    Returns
    -------
    MagicMock
        A mock BseSession instance.
    """
    mock_session = MagicMock(spec=BseSession)
    mock_response = MagicMock()
    mock_response.json.return_value = (
        response_json if response_json is not None else _make_company_info_json()
    )
    mock_response.status_code = 200
    mock_session.get_with_retry.return_value = mock_response
    return mock_session


# =============================================================================
# Parser tests: parse_company_info
# =============================================================================


class TestParseCompanyInfo:
    """parse_company_info のテスト。"""

    def test_正常系_有効なレスポンスをdictに変換できる(self) -> None:
        """有効なレスポンスが正しく dict に変換されること。"""
        raw = _make_company_info_json()
        info = parse_company_info(raw)

        assert info["scrip_code"] == "500325"
        assert info["company_name"] == "RELIANCE INDUSTRIES LTD"
        assert info["isin"] == "INE002A01018"
        assert info["scrip_group"] == "A"
        assert info["industry"] == "Refineries"
        assert info["market_cap"] == "1800000"
        assert info["face_value"] == "10.00"

    def test_正常系_代替キー名でも変換できる(self) -> None:
        """SCRIP_CD や COMPNAME 等の代替キーでも変換されること。"""
        raw = {
            "SCRIP_CD": "500180",
            "COMPNAME": "HDFC BANK LTD",
            "isin_number": "INE040A01034",
            "scrip_grp": "A",
            "industry": "Banks",
        }
        info = parse_company_info(raw)

        assert info["scrip_code"] == "500180"
        assert info["company_name"] == "HDFC BANK LTD"
        assert info["isin"] == "INE040A01034"

    def test_異常系_空dictでBseParseError(self) -> None:
        """空の dict で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Empty company info"):
            parse_company_info({})

    def test_異常系_非dictでBseParseError(self) -> None:
        """dict でない入力で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Expected dict"):
            parse_company_info([1, 2, 3])  # type: ignore[arg-type]

    def test_異常系_必須フィールド両方欠損でBseParseError(self) -> None:
        """scrip_code と company_name の両方が欠損で BseParseError。"""
        raw = {"INDUSTRY": "Refineries", "Mktcap": "1800000"}
        with pytest.raises(BseParseError, match="Missing both"):
            parse_company_info(raw)

    def test_正常系_scrip_codeのみでも変換できる(self) -> None:
        """scrip_code のみでも変換されること（company_name は None）。"""
        raw = {"scrip_cd": "500325"}
        info = parse_company_info(raw)

        assert info["scrip_code"] == "500325"
        assert info["company_name"] is None

    def test_エッジケース_空文字フィールドはNoneになる(self) -> None:
        """空文字フィールドは None として返されること。"""
        raw = {
            "scrip_cd": "500325",
            "compname": "RELIANCE",
            "ISIN_NUMBER": "",
            "Scrip_grp": "  ",
        }
        info = parse_company_info(raw)

        assert info["isin"] is None
        assert info["scrip_group"] is None


# =============================================================================
# Parser tests: parse_financial_results
# =============================================================================


class TestParseFinancialResults:
    """parse_financial_results のテスト。"""

    def test_正常系_有効なレスポンスをリストに変換できる(self) -> None:
        """有効なレスポンスが FinancialResult リストに変換されること。"""
        raw = _make_financial_results_json()
        results = parse_financial_results(raw)

        assert len(results) == 2
        assert isinstance(results[0], FinancialResult)
        assert results[0].scrip_code == "500325"
        assert results[0].period_ended == "31-Mar-2025"
        assert results[0].revenue == "250000"
        assert results[0].net_profit == "18500"
        assert results[0].eps == "27.35"

    def test_正常系_空リストで空結果(self) -> None:
        """空リストで空リストを返すこと。"""
        results = parse_financial_results([])
        assert results == []

    def test_異常系_非リストでBseParseError(self) -> None:
        """リストでない入力で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Expected list"):
            parse_financial_results({"key": "value"})  # type: ignore[arg-type]

    def test_エッジケース_非dict要素をスキップ(self) -> None:
        """非 dict 要素はスキップされること。"""
        raw = [
            _make_financial_results_json(count=1)[0],
            "not a dict",
            42,
        ]
        results = parse_financial_results(raw)

        assert len(results) == 1
        assert results[0].scrip_code == "500325"

    def test_正常系_代替キー名でも変換できる(self) -> None:
        """SCRIP_CD や COMPANYNAME 等の代替キーでも変換されること。"""
        raw = [
            {
                "SCRIP_CD": "500180",
                "COMPANYNAME": "HDFC BANK LTD",
                "CONS_PRD_TO": "31-Dec-2025",
                "CONS_REVENUE": "120000",
                "CONS_NETPNL": "9500",
                "CONS_EPS": "44.50",
            }
        ]
        results = parse_financial_results(raw)

        assert len(results) == 1
        assert results[0].scrip_code == "500180"
        assert results[0].scrip_name == "HDFC BANK LTD"


# =============================================================================
# Parser tests: parse_announcements
# =============================================================================


class TestParseAnnouncements:
    """parse_announcements のテスト。"""

    def test_正常系_有効なレスポンスをリストに変換できる(self) -> None:
        """有効なレスポンスが Announcement リストに変換されること。"""
        raw = _make_announcements_json()
        announcements = parse_announcements(raw)

        assert len(announcements) == 2
        assert isinstance(announcements[0], Announcement)
        assert announcements[0].scrip_code == "500325"
        assert announcements[0].subject == "Board Meeting Outcome"
        assert announcements[0].category == "Board Meeting"

    def test_正常系_空リストで空結果(self) -> None:
        """空リストで空リストを返すこと。"""
        announcements = parse_announcements([])
        assert announcements == []

    def test_異常系_非リストでBseParseError(self) -> None:
        """リストでない入力で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Expected list"):
            parse_announcements("not a list")  # type: ignore[arg-type]

    def test_エッジケース_非dict要素をスキップ(self) -> None:
        """非 dict 要素はスキップされること。"""
        raw = [
            _make_announcements_json(count=1)[0],
            "not a dict",
        ]
        announcements = parse_announcements(raw)

        assert len(announcements) == 1

    def test_正常系_代替キー名でも変換できる(self) -> None:
        """scrip_cd や headline 等の小文字キーでも変換されること。"""
        raw = [
            {
                "scrip_cd": "500180",
                "slongname": "HDFC BANK LTD",
                "headline": "AGM Notice",
                "dt_tm": "01-Mar-2025",
                "categoryname": "AGM/EGM",
            }
        ]
        announcements = parse_announcements(raw)

        assert len(announcements) == 1
        assert announcements[0].scrip_code == "500180"
        assert announcements[0].subject == "AGM Notice"


# =============================================================================
# Parser tests: parse_corporate_actions
# =============================================================================


class TestParseCorporateActions:
    """parse_corporate_actions のテスト。"""

    def test_正常系_有効なレスポンスをリストに変換できる(self) -> None:
        """有効なレスポンスが CorporateAction リストに変換されること。"""
        raw = _make_corporate_actions_json()
        actions = parse_corporate_actions(raw)

        assert len(actions) == 2
        assert isinstance(actions[0], CorporateAction)
        assert actions[0].scrip_code == "500325"
        assert actions[0].purpose == "Dividend - Rs 8 Per Share"
        assert actions[0].ex_date == "01-Feb-2025"
        assert actions[0].record_date == "03-Feb-2025"

    def test_正常系_空リストで空結果(self) -> None:
        """空リストで空リストを返すこと。"""
        actions = parse_corporate_actions([])
        assert actions == []

    def test_異常系_非リストでBseParseError(self) -> None:
        """リストでない入力で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Expected list"):
            parse_corporate_actions({"key": "value"})  # type: ignore[arg-type]

    def test_エッジケース_非dict要素をスキップ(self) -> None:
        """非 dict 要素はスキップされること。"""
        raw = [
            _make_corporate_actions_json(count=1)[0],
            None,
            42,
        ]
        actions = parse_corporate_actions(raw)

        assert len(actions) == 1

    def test_正常系_代替キー名でも変換できる(self) -> None:
        """SCRIP_CODE や EX_DT 等の大文字キーでも変換されること。"""
        raw = [
            {
                "SCRIP_CODE": "500180",
                "COMP_NAME": "HDFC BANK LTD",
                "EX_DT": "15-Mar-2025",
                "PURPOSE": "Stock Split",
                "RECORD_DT": "17-Mar-2025",
            }
        ]
        actions = parse_corporate_actions(raw)

        assert len(actions) == 1
        assert actions[0].scrip_code == "500180"
        assert actions[0].purpose == "Stock Split"


# =============================================================================
# CorporateCollector initialization tests
# =============================================================================


class TestCorporateCollectorInit:
    """CorporateCollector 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """session なしでデフォルト初期化されること。"""
        collector = CorporateCollector()

        assert collector._session_instance is None

    def test_正常系_DIパターンでsession注入できる(self) -> None:
        """DI パターンで BseSession を注入できること。"""
        mock_session = _make_mock_session()
        collector = CorporateCollector(session=mock_session)

        assert collector._session_instance is mock_session


# =============================================================================
# _get_session tests
# =============================================================================


class TestCorporateGetSession:
    """CorporateCollector._get_session() のテスト。"""

    def test_正常系_注入なし時に新規セッション生成(self) -> None:
        """session 未注入時に新規 BseSession を生成し should_close=True。"""
        collector = CorporateCollector()

        with patch("market.bse.collectors.corporate.BseSession") as mock_cls:
            mock_cls.return_value = MagicMock(spec=BseSession)
            _session, should_close = collector._get_session()

        assert should_close is True
        mock_cls.assert_called_once()

    def test_正常系_注入あり時に既存セッション返却(self) -> None:
        """session 注入時に既存セッションを返し should_close=False。"""
        mock_session = _make_mock_session()
        collector = CorporateCollector(session=mock_session)

        session, should_close = collector._get_session()

        assert session is mock_session
        assert should_close is False


# =============================================================================
# get_company_info tests
# =============================================================================


class TestGetCompanyInfo:
    """get_company_info() メソッドのテスト。"""

    def test_正常系_企業情報を取得できる(self) -> None:
        """scrip_code で API を呼び出し企業情報 dict を返すこと。"""
        mock_session = _make_mock_session(response_json=_make_company_info_json())
        collector = CorporateCollector(session=mock_session)

        info = collector.get_company_info("500325")

        assert isinstance(info, dict)
        assert info["scrip_code"] == "500325"
        assert info["company_name"] == "RELIANCE INDUSTRIES LTD"
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session(response_json=_make_company_info_json())
        collector = CorporateCollector()

        with patch(
            "market.bse.collectors.corporate.BseSession",
            return_value=mock_new_session,
        ):
            collector.get_company_info("500325")

        mock_new_session.close.assert_called_once()

    def test_正常系_注入セッションはクローズしない(self) -> None:
        """注入されたセッションはクローズされないこと。"""
        mock_session = _make_mock_session(response_json=_make_company_info_json())
        collector = CorporateCollector(session=mock_session)

        collector.get_company_info("500325")

        mock_session.close.assert_not_called()

    def test_異常系_APIエラー時に例外伝播(self) -> None:
        """API エラー時に BseAPIError が伝播すること。"""
        mock_session = MagicMock(spec=BseSession)
        mock_session.get_with_retry.side_effect = BseAPIError(
            "API returned HTTP 500",
            url="https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData",
            status_code=500,
            response_body='{"error": "Internal Server Error"}',
        )
        collector = CorporateCollector(session=mock_session)

        with pytest.raises(BseAPIError, match="HTTP 500"):
            collector.get_company_info("500325")


# =============================================================================
# get_financial_results tests
# =============================================================================


class TestGetFinancialResults:
    """get_financial_results() メソッドのテスト。"""

    def test_正常系_決算情報リストを取得できる(self) -> None:
        """scrip_code で API を呼び出し FinancialResult リストを返すこと。"""
        mock_session = _make_mock_session(response_json=_make_financial_results_json())
        collector = CorporateCollector(session=mock_session)

        results = collector.get_financial_results("500325")

        assert isinstance(results, list)
        assert len(results) == 2
        assert isinstance(results[0], FinancialResult)
        assert results[0].scrip_code == "500325"
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_空レスポンスで空リスト(self) -> None:
        """空の API レスポンスで空リストを返すこと。"""
        mock_session = _make_mock_session(response_json=[])
        collector = CorporateCollector(session=mock_session)

        results = collector.get_financial_results("500325")

        assert results == []

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session(
            response_json=_make_financial_results_json()
        )
        collector = CorporateCollector()

        with patch(
            "market.bse.collectors.corporate.BseSession",
            return_value=mock_new_session,
        ):
            collector.get_financial_results("500325")

        mock_new_session.close.assert_called_once()


# =============================================================================
# get_announcements tests
# =============================================================================


class TestGetAnnouncements:
    """get_announcements() メソッドのテスト。"""

    def test_正常系_アナウンスリストを取得できる(self) -> None:
        """scrip_code で API を呼び出し Announcement リストを返すこと。"""
        mock_session = _make_mock_session(response_json=_make_announcements_json())
        collector = CorporateCollector(session=mock_session)

        announcements = collector.get_announcements("500325")

        assert isinstance(announcements, list)
        assert len(announcements) == 2
        assert isinstance(announcements[0], Announcement)
        assert announcements[0].scrip_code == "500325"
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_空レスポンスで空リスト(self) -> None:
        """空の API レスポンスで空リストを返すこと。"""
        mock_session = _make_mock_session(response_json=[])
        collector = CorporateCollector(session=mock_session)

        announcements = collector.get_announcements("500325")

        assert announcements == []

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session(response_json=_make_announcements_json())
        collector = CorporateCollector()

        with patch(
            "market.bse.collectors.corporate.BseSession",
            return_value=mock_new_session,
        ):
            collector.get_announcements("500325")

        mock_new_session.close.assert_called_once()


# =============================================================================
# get_corporate_actions tests
# =============================================================================


class TestGetCorporateActions:
    """get_corporate_actions() メソッドのテスト。"""

    def test_正常系_コーポレートアクションリストを取得できる(self) -> None:
        """scrip_code で API を呼び出し CorporateAction リストを返すこと。"""
        mock_session = _make_mock_session(response_json=_make_corporate_actions_json())
        collector = CorporateCollector(session=mock_session)

        actions = collector.get_corporate_actions("500325")

        assert isinstance(actions, list)
        assert len(actions) == 2
        assert isinstance(actions[0], CorporateAction)
        assert actions[0].scrip_code == "500325"
        assert actions[0].purpose == "Dividend - Rs 8 Per Share"
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_空レスポンスで空リスト(self) -> None:
        """空の API レスポンスで空リストを返すこと。"""
        mock_session = _make_mock_session(response_json=[])
        collector = CorporateCollector(session=mock_session)

        actions = collector.get_corporate_actions("500325")

        assert actions == []

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session(
            response_json=_make_corporate_actions_json()
        )
        collector = CorporateCollector()

        with patch(
            "market.bse.collectors.corporate.BseSession",
            return_value=mock_new_session,
        ):
            collector.get_corporate_actions("500325")

        mock_new_session.close.assert_called_once()


# =============================================================================
# search_scrip tests
# =============================================================================


class TestSearchScrip:
    """search_scrip() メソッドのテスト。"""

    def test_正常系_検索結果リストを取得できる(self) -> None:
        """クエリで API を呼び出し結果リストを返すこと。"""
        mock_session = _make_mock_session(response_json=_make_scrip_search_json())
        collector = CorporateCollector(session=mock_session)

        results = collector.search_scrip("RELIANCE")

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["scrip_code"] == "500325"
        assert results[0]["scrip_name"] == "RELIANCE INDUSTRIES LTD"
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_空レスポンスで空リスト(self) -> None:
        """空の API レスポンスで空リストを返すこと。"""
        mock_session = _make_mock_session(response_json=[])
        collector = CorporateCollector(session=mock_session)

        results = collector.search_scrip("NONEXISTENT")

        assert results == []

    def test_エッジケース_非リストレスポンスで空リスト(self) -> None:
        """リストでない API レスポンスで空リストを返すこと。"""
        mock_session = _make_mock_session(response_json={"error": "unexpected"})
        collector = CorporateCollector(session=mock_session)

        results = collector.search_scrip("TEST")

        assert results == []

    def test_正常系_セッションを正しくクローズ(self) -> None:
        """注入なし時に作成したセッションがクローズされること。"""
        mock_new_session = _make_mock_session(response_json=_make_scrip_search_json())
        collector = CorporateCollector()

        with patch(
            "market.bse.collectors.corporate.BseSession",
            return_value=mock_new_session,
        ):
            collector.search_scrip("RELIANCE")

        mock_new_session.close.assert_called_once()


# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Module exports のテスト。"""

    def test_正常系_collector_allが定義されている(self) -> None:
        """collectors.corporate.__all__ が CorporateCollector を含むこと。"""
        from market.bse.collectors.corporate import __all__

        assert "CorporateCollector" in __all__

    def test_正常系_parsers_allが新パーサーを含む(self) -> None:
        """parsers.__all__ が新しいパーサー関数を含むこと。"""
        from market.bse.parsers import __all__ as parsers_all

        expected_new = {
            "parse_company_info",
            "parse_financial_results",
            "parse_announcements",
            "parse_corporate_actions",
        }
        assert expected_new.issubset(set(parsers_all))

    def test_正常系_bse_initが全エクスポートを含む(self) -> None:
        """market.bse.__init__ が CorporateCollector と新パーサーを含むこと。"""
        from market.bse import __all__ as bse_all

        assert "CorporateCollector" in bse_all
        assert "parse_company_info" in bse_all
        assert "parse_financial_results" in bse_all
        assert "parse_announcements" in bse_all
        assert "parse_corporate_actions" in bse_all
