"""Unit tests for BloombergFetcher._process_* methods.

Tests each response-processing helper in isolation using mock BLPAPI Element
factories defined in conftest.py. Real Bloomberg connections are never made.

Test TODO List:
- [x] _process_historical_response: normal / security error / empty data / session None
- [x] _process_reference_response: normal / security error / empty data / session None
- [x] _process_id_conversion: normal / security error / empty / session None
- [x] _process_news_response: normal / empty / session None
- [x] _process_index_members: normal / security error / empty / session None
- [x] _process_field_info: normal / empty / session None
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tests.market.unit.bloomberg.conftest import (
    _make_error_element,
    make_mock_element,
    make_mock_event,
    make_mock_field_data,
    make_mock_historical_field_data_array,
    make_mock_historical_security_data,
    make_mock_message,
    make_mock_security_data,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fetcher() -> "BloombergFetcher":  # type: ignore[name-defined]
    from market.bloomberg.fetcher import BloombergFetcher

    return BloombergFetcher()


# ---------------------------------------------------------------------------
# _process_historical_response
# ---------------------------------------------------------------------------


class TestProcessHistoricalResponse:
    """Tests for BloombergFetcher._process_historical_response()."""

    def test_正常系_ヒストリカルレスポンスからDataFrameを生成(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """正常なヒストリカルレスポンスから DataFrame が生成されること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        dates = ["2024-01-02", "2024-01-03", "2024-01-04"]
        fields = ["PX_LAST", "PX_VOLUME"]
        values = [[150.0, 1_000_000], [151.0, 1_100_000], [152.0, 1_200_000]]

        fda = make_mock_historical_field_data_array(dates, fields, values)
        sd = make_mock_historical_security_data("AAPL US Equity", fda)
        msg = make_mock_message(has_security_data=True, security_data=sd)
        event = make_mock_event(blpapi.Event.RESPONSE, [msg])

        session = mock_blpapi_session_factory([event])  # type: ignore[operator]
        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=fields,
        )

        result = fetcher._process_historical_response(
            "AAPL US Equity", options, session
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "PX_LAST" in result.columns
        assert "PX_VOLUME" in result.columns

    def test_正常系_日付とフィールド値が正しく取得できる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """日付カラムとフィールド値が正確に設定されること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        dates = ["2024-01-02"]
        fields = ["PX_LAST"]
        values = [[175.5]]

        fda = make_mock_historical_field_data_array(dates, fields, values)
        sd = make_mock_historical_security_data("AAPL US Equity", fda)
        msg = make_mock_message(has_security_data=True, security_data=sd)
        event = make_mock_event(blpapi.Event.RESPONSE, [msg])

        session = mock_blpapi_session_factory([event])  # type: ignore[operator]
        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=fields,
        )

        result = fetcher._process_historical_response(
            "AAPL US Equity", options, session
        )

        assert len(result) == 1
        assert result["PX_LAST"].iloc[0] == 175.5

    def test_異常系_セキュリティエラーでBloombergDataErrorが発生(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """securityError が含まれる場合 BloombergDataError が発生すること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions
        from market.errors import BloombergDataError

        fda = MagicMock()
        sd = make_mock_historical_security_data(
            "INVALID US Equity",
            fda,
            has_error=True,
            error_message="Unknown security: INVALID US Equity",
        )
        msg = make_mock_message(has_security_data=True, security_data=sd)
        event = make_mock_event(blpapi.Event.RESPONSE, [msg])

        session = mock_blpapi_session_factory([event])  # type: ignore[operator]
        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["INVALID US Equity"],
            fields=["PX_LAST"],
        )

        with pytest.raises(BloombergDataError):
            fetcher._process_historical_response("INVALID US Equity", options, session)

    def test_異常系_responseErrorでBloombergDataErrorが発生(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """responseError が含まれる場合 BloombergDataError が発生すること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions
        from market.errors import BloombergDataError

        msg = make_mock_message(
            has_security_data=False,
            has_response_error=True,
            error_message="Service unavailable",
        )
        event = make_mock_event(blpapi.Event.RESPONSE, [msg])

        session = mock_blpapi_session_factory([event])  # type: ignore[operator]
        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        with pytest.raises(BloombergDataError):
            fetcher._process_historical_response("AAPL US Equity", options, session)

    def test_エッジケース_securityDataなしメッセージで空DataFrame(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """securityData を含まないメッセージは空 DataFrame を返すこと。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        msg = make_mock_message(has_security_data=False)
        event = make_mock_event(blpapi.Event.RESPONSE, [msg])

        session = mock_blpapi_session_factory([event])  # type: ignore[operator]
        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        result = fetcher._process_historical_response(
            "AAPL US Equity", options, session
        )

        assert result.empty

    def test_エッジケース_sessionがNoneで空DataFrameを返す(self) -> None:
        """session が None の場合は空 DataFrame を返すこと（後方互換性）。"""
        from market.bloomberg.types import BloombergFetchOptions

        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        result = fetcher._process_historical_response("AAPL US Equity", options, None)

        assert result.empty

    def test_エッジケース_タイムアウトで空DataFrame(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """タイムアウト発生時に空 DataFrame を返すこと。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        # Factory will return TIMEOUT event when events list is empty
        session = mock_blpapi_session_factory([])  # type: ignore[operator]
        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        result = fetcher._process_historical_response(
            "AAPL US Equity", options, session
        )

        assert result.empty


# ---------------------------------------------------------------------------
# _process_reference_response
# ---------------------------------------------------------------------------


class TestProcessReferenceResponse:
    """Tests for BloombergFetcher._process_reference_response()."""

    def test_正常系_参照データレスポンスからDataFrameを生成(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """正常な参照データレスポンスから DataFrame が生成されること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        fd = make_mock_field_data(
            {
                "NAME": "Apple Inc",
                "GICS_SECTOR_NAME": "Information Technology",
                "CRNCY": "USD",
            }
        )
        sd = make_mock_security_data("AAPL US Equity", fd)
        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.hasElement.return_value = True
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["NAME", "GICS_SECTOR_NAME", "CRNCY"],
        )

        result = fetcher._process_reference_response("AAPL US Equity", options, session)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert "NAME" in result.columns

    def test_正常系_フィールド値が正しく取得できる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """参照データのフィールド値が正確に設定されること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        fd = make_mock_field_data({"NAME": "Apple Inc"})
        sd = make_mock_security_data("AAPL US Equity", fd)
        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.hasElement.return_value = True
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["NAME"],
        )

        result = fetcher._process_reference_response("AAPL US Equity", options, session)

        assert result["NAME"].iloc[0] == "Apple Inc"

    def test_異常系_セキュリティエラーでBloombergDataErrorが発生(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """securityError が含まれる場合 BloombergDataError が発生すること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions
        from market.errors import BloombergDataError

        fd = make_mock_field_data({})
        sd = make_mock_security_data(
            "INVALID US Equity",
            fd,
            has_error=True,
            error_message="Unknown security",
        )
        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.hasElement.return_value = True
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["INVALID US Equity"],
            fields=["NAME"],
        )

        with pytest.raises(BloombergDataError):
            fetcher._process_reference_response("INVALID US Equity", options, session)

    def test_エッジケース_sessionがNoneで空DataFrameを返す(self) -> None:
        """session が None の場合は空 DataFrame を返すこと。"""
        from market.bloomberg.types import BloombergFetchOptions

        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["NAME"],
        )

        result = fetcher._process_reference_response("AAPL US Equity", options, None)

        assert result.empty

    def test_エッジケース_データなしで空DataFrameを返す(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """空のレスポンスで空 DataFrame を返すこと。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import BloombergFetchOptions

        sd_array = MagicMock()
        sd_array.values.return_value = iter([])

        msg = MagicMock()
        msg.hasElement.return_value = True
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["NAME"],
        )

        result = fetcher._process_reference_response("AAPL US Equity", options, session)

        assert result.empty


# ---------------------------------------------------------------------------
# _process_id_conversion
# ---------------------------------------------------------------------------


class TestProcessIdConversion:
    """Tests for BloombergFetcher._process_id_conversion()."""

    def test_正常系_ISINからBloombergTickerへ変換できる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """ISIN から Bloomberg Ticker への変換が正しく行われること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import IDType

        ticker_elem = make_mock_element("AAPL US Equity")
        ticker_elem.isNull.return_value = False

        fd = MagicMock()
        fd.hasElement.side_effect = lambda name: name == "PARSEKYABLE_DES"
        fd.getElement.return_value = ticker_elem

        sd = MagicMock()
        sd.getElement.side_effect = lambda name: (
            make_mock_element("/isin/US0378331005") if name == "security" else fd
        )
        sd.hasElement.return_value = False

        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_id_conversion(
            ["US0378331005"],
            IDType.ISIN,
            IDType.TICKER,
            session,
        )

        assert "US0378331005" in result
        assert result["US0378331005"] == "AAPL US Equity"

    def test_正常系_複数識別子の変換ができる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """複数の ISIN を一括変換できること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import IDType

        def _build_sd(isin: str, ticker: str) -> MagicMock:
            ticker_elem = make_mock_element(ticker)
            ticker_elem.isNull.return_value = False

            fd = MagicMock()
            fd.hasElement.side_effect = lambda name: name == "PARSEKYABLE_DES"
            fd.getElement.return_value = ticker_elem

            sd = MagicMock()
            sd.getElement.side_effect = lambda name, _isin=isin, _fd=fd: (
                make_mock_element(f"/isin/{_isin}") if name == "security" else _fd
            )
            sd.hasElement.return_value = False
            return sd

        sd1 = _build_sd("US0378331005", "AAPL US Equity")
        sd2 = _build_sd("US02079K3059", "GOOGL US Equity")

        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd1, sd2])

        msg = MagicMock()
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_id_conversion(
            ["US0378331005", "US02079K3059"],
            IDType.ISIN,
            IDType.TICKER,
            session,
        )

        assert len(result) == 2
        assert result["US0378331005"] == "AAPL US Equity"
        assert result["US02079K3059"] == "GOOGL US Equity"

    def test_エッジケース_セキュリティエラー時は該当識別子がスキップされる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """securityError が発生した識別子はスキップされ、他の識別子は変換されること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import IDType

        # Valid identifier
        ticker_elem = make_mock_element("AAPL US Equity")
        ticker_elem.isNull.return_value = False

        fd_valid = MagicMock()
        fd_valid.hasElement.side_effect = lambda name: name == "PARSEKYABLE_DES"
        fd_valid.getElement.return_value = ticker_elem

        sd_valid = MagicMock()
        sd_valid.getElement.side_effect = lambda name, _fd=fd_valid: (
            make_mock_element("/isin/US0378331005") if name == "security" else _fd
        )
        sd_valid.hasElement.return_value = False

        # Invalid identifier with securityError
        sd_invalid = MagicMock()
        sd_invalid.getElement.side_effect = lambda name: (
            make_mock_element("/isin/INVALID999")
            if name == "security"
            else _make_error_element("Unknown security")
        )
        sd_invalid.hasElement.side_effect = lambda name: name == "securityError"

        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd_valid, sd_invalid])

        msg = MagicMock()
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_id_conversion(
            ["US0378331005", "INVALID999"],
            IDType.ISIN,
            IDType.TICKER,
            session,
        )

        assert "US0378331005" in result
        assert "INVALID999" not in result

    def test_エッジケース_sessionがNoneで空dictを返す(self) -> None:
        """session が None の場合は空辞書を返すこと。"""
        from market.bloomberg.types import IDType

        fetcher = _make_fetcher()
        result = fetcher._process_id_conversion(
            ["US0378331005"],
            IDType.ISIN,
            IDType.TICKER,
            None,
        )

        assert result == {}

    def test_エッジケース_識別子リストが空で空dictを返す(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """空の識別子リストを渡した場合、空辞書が返ること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import IDType

        sd_array = MagicMock()
        sd_array.values.return_value = iter([])

        msg = MagicMock()
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_id_conversion(
            [],
            IDType.ISIN,
            IDType.TICKER,
            session,
        )

        assert result == {}


# ---------------------------------------------------------------------------
# _process_news_response
# ---------------------------------------------------------------------------


class TestProcessNewsResponse:
    """Tests for BloombergFetcher._process_news_response()."""

    def _make_headline_element(
        self,
        story_id: str,
        headline_text: str,
        story_dt: datetime,
        source: str | None = None,
    ) -> MagicMock:
        """Create a mock newsHeadlines element."""
        elem = MagicMock()
        elem.getElementAsString.side_effect = lambda name: (
            story_id if name == "storyId" else headline_text
        )
        elem.getElementAsDatetime.side_effect = lambda name: story_dt
        elem.hasElement.side_effect = (
            lambda name: name == "sources" and source is not None
        )

        sources_elem = MagicMock()
        sources_elem.numValues.return_value = 1 if source else 0
        sources_elem.getValueAsString.return_value = source or ""
        elem.getElement.side_effect = (
            lambda name: sources_elem if name == "sources" else MagicMock()
        )
        return elem

    def test_正常系_ニュースレスポンスからNewsStoryリストを生成(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """正常なニュースレスポンスから NewsStory リストが生成されること。"""
        import blpapi  # type: ignore[import-not-found]

        headline1 = self._make_headline_element(
            "BBG001",
            "Apple Reports Earnings",
            datetime(2024, 1, 15, 9, 30),
            "Bloomberg News",
        )
        headline2 = self._make_headline_element(
            "BBG002",
            "Tech Stocks Rally",
            datetime(2024, 1, 16, 14, 0),
        )

        news_headlines = MagicMock()
        news_headlines.values.return_value = iter([headline1, headline2])

        msg = MagicMock()
        msg.hasElement.side_effect = lambda name: name == "newsHeadlines"
        msg.getElement.return_value = news_headlines

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_news_response(
            "AAPL US Equity",
            "2024-01-01",
            "2024-01-31",
            session,
        )

        assert len(result) == 2

    def test_正常系_story_idとheadlineが正しく取得できる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """story_id と headline が正確に取得されること。"""
        import blpapi  # type: ignore[import-not-found]

        headline = self._make_headline_element(
            "BBG12345",
            "Apple Beats Q4 Estimates",
            datetime(2024, 1, 15, 9, 30),
        )

        news_headlines = MagicMock()
        news_headlines.values.return_value = iter([headline])

        msg = MagicMock()
        msg.hasElement.side_effect = lambda name: name == "newsHeadlines"
        msg.getElement.return_value = news_headlines

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_news_response(
            "AAPL US Equity",
            None,
            None,
            session,
        )

        assert len(result) == 1
        assert result[0].story_id == "BBG12345"
        assert result[0].headline == "Apple Beats Q4 Estimates"

    def test_正常系_結果が日時昇順にソートされている(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """返却される NewsStory リストが日時昇順にソートされていること。"""
        import blpapi  # type: ignore[import-not-found]

        # Story 2 is newer — insert in reverse order to verify sorting
        headline1 = self._make_headline_element(
            "BBG002",
            "Later Story",
            datetime(2024, 1, 16, 10, 0),
        )
        headline2 = self._make_headline_element(
            "BBG001",
            "Earlier Story",
            datetime(2024, 1, 15, 8, 0),
        )

        news_headlines = MagicMock()
        news_headlines.values.return_value = iter([headline1, headline2])

        msg = MagicMock()
        msg.hasElement.side_effect = lambda name: name == "newsHeadlines"
        msg.getElement.return_value = news_headlines

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_news_response(
            "AAPL US Equity",
            None,
            None,
            session,
        )

        assert result[0].story_id == "BBG001"
        assert result[1].story_id == "BBG002"

    def test_エッジケース_ニュースなしで空リストを返す(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """newsHeadlines が含まれないメッセージの場合は空リストを返すこと。"""
        import blpapi  # type: ignore[import-not-found]

        msg = MagicMock()
        msg.hasElement.return_value = False

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_news_response(
            "AAPL US Equity",
            None,
            None,
            session,
        )

        assert result == []

    def test_エッジケース_sessionがNoneで空リストを返す(self) -> None:
        """session が None の場合は空リストを返すこと。"""
        fetcher = _make_fetcher()
        result = fetcher._process_news_response("AAPL US Equity", None, None, None)

        assert result == []


# ---------------------------------------------------------------------------
# _process_index_members
# ---------------------------------------------------------------------------


class TestProcessIndexMembers:
    """Tests for BloombergFetcher._process_index_members()."""

    def _make_member_element(self, ticker: str) -> MagicMock:
        """Create a mock member element."""
        elem = MagicMock()
        elem.hasElement.side_effect = (
            lambda name: name == "Member Ticker and Exchange Code"
        )
        elem.getElementAsString.return_value = ticker
        return elem

    def test_正常系_インデックス構成銘柄を取得できる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """インデックス構成銘柄のリストが正しく返されること。"""
        import blpapi  # type: ignore[import-not-found]

        tickers = ["AAPL US Equity", "MSFT US Equity", "GOOGL US Equity"]
        member_elems = [self._make_member_element(t) for t in tickers]

        members_element = MagicMock()
        members_element.numValues.return_value = len(tickers)
        members_element.getValueAsElement.side_effect = lambda i: member_elems[i]

        fd = MagicMock()
        fd.hasElement.side_effect = lambda name: name == "INDX_MEMBERS"
        fd.getElement.return_value = members_element

        sd = MagicMock()
        sd.hasElement.return_value = False
        sd.getElement.side_effect = lambda name: (
            make_mock_element("SPX Index") if name == "security" else fd
        )

        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.hasElement.return_value = False
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_index_members("SPX Index", session)

        assert len(result) == 3
        assert "AAPL US Equity" in result
        assert "MSFT US Equity" in result

    def test_異常系_インデックスエラーでBloombergDataErrorが発生(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """securityError が含まれる場合 BloombergDataError が発生すること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.errors import BloombergDataError

        fd = make_mock_field_data({})
        sd = make_mock_security_data(
            "INVALID Index",
            fd,
            has_error=True,
            error_message="Unknown index",
        )
        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.hasElement.return_value = False
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()

        with pytest.raises(BloombergDataError):
            fetcher._process_index_members("INVALID Index", session)

    def test_異常系_responseErrorでBloombergDataErrorが発生(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """responseError が含まれる場合 BloombergDataError が発生すること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.errors import BloombergDataError

        msg = MagicMock()
        msg.hasElement.side_effect = lambda name: name == "responseError"
        msg.getElement.return_value = _make_error_element("Service unavailable")

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()

        with pytest.raises(BloombergDataError):
            fetcher._process_index_members("SPX Index", session)

    def test_エッジケース_INDX_MEMBERSフィールドなしで空リスト(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """INDX_MEMBERS フィールドがない場合は空リストを返すこと。"""
        import blpapi  # type: ignore[import-not-found]

        fd = MagicMock()
        fd.hasElement.return_value = False

        sd = MagicMock()
        sd.hasElement.return_value = False
        sd.getElement.side_effect = lambda name: (
            make_mock_element("SPX Index") if name == "security" else fd
        )

        sd_array = MagicMock()
        sd_array.values.return_value = iter([sd])

        msg = MagicMock()
        msg.hasElement.return_value = False
        msg.getElement.return_value = sd_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_index_members("SPX Index", session)

        assert result == []

    def test_エッジケース_sessionがNoneで空リストを返す(self) -> None:
        """session が None の場合は空リストを返すこと。"""
        fetcher = _make_fetcher()
        result = fetcher._process_index_members("SPX Index", None)

        assert result == []


# ---------------------------------------------------------------------------
# _process_field_info
# ---------------------------------------------------------------------------


class TestProcessFieldInfo:
    """Tests for BloombergFetcher._process_field_info()."""

    def test_正常系_フィールドメタデータが取得できる(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """正常なレスポンスからフィールドメタデータが取得されること。"""
        import blpapi  # type: ignore[import-not-found]

        from market.bloomberg.types import FieldInfo

        field_elem = MagicMock()
        field_elem.hasElement.return_value = True
        field_elem.getElementAsString.side_effect = lambda name: {
            "mnemonic": "PX_LAST",
            "description": "Last Price",
            "datatype": "Double",
        }.get(name, "")

        field_data_array = MagicMock()
        field_data_array.numValues.return_value = 1
        field_data_array.getValueAsElement.return_value = field_elem

        msg = MagicMock()
        msg.hasElement.side_effect = lambda name: name == "fieldData"
        msg.getElement.return_value = field_data_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_field_info("PX_LAST", session)

        assert isinstance(result, FieldInfo)
        assert result.field_id == "PX_LAST"
        assert result.field_name == "PX_LAST"
        assert result.description == "Last Price"
        assert result.data_type == "Double"

    def test_正常系_複数フィールド情報が正しく設定されている(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """mnemonic・description・datatype が正確に FieldInfo に設定されること。"""
        import blpapi  # type: ignore[import-not-found]

        field_elem = MagicMock()
        field_elem.hasElement.return_value = True
        field_elem.getElementAsString.side_effect = lambda name: {
            "mnemonic": "PE_RATIO",
            "description": "Price-to-Earnings Ratio",
            "datatype": "Double",
        }.get(name, "")

        field_data_array = MagicMock()
        field_data_array.numValues.return_value = 1
        field_data_array.getValueAsElement.return_value = field_elem

        msg = MagicMock()
        msg.hasElement.side_effect = lambda name: name == "fieldData"
        msg.getElement.return_value = field_data_array

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_field_info("PE_RATIO", session)

        assert result.field_name == "PE_RATIO"
        assert result.description == "Price-to-Earnings Ratio"

    def test_エッジケース_fieldDataなしで空FieldInfoを返す(
        self,
        mock_blpapi_session_factory: object,
    ) -> None:
        """fieldData を含まないレスポンスで空の FieldInfo を返すこと。"""
        import blpapi  # type: ignore[import-not-found]

        msg = MagicMock()
        msg.hasElement.return_value = False

        event = make_mock_event(blpapi.Event.RESPONSE, [msg])
        session = mock_blpapi_session_factory([event])  # type: ignore[operator]

        fetcher = _make_fetcher()
        result = fetcher._process_field_info("PX_LAST", session)

        assert result.field_id == "PX_LAST"
        assert result.field_name == ""
        assert result.description == ""
        assert result.data_type == ""

    def test_エッジケース_sessionがNoneで空FieldInfoを返す(self) -> None:
        """session が None の場合は空の FieldInfo を返すこと。"""
        from market.bloomberg.types import FieldInfo

        fetcher = _make_fetcher()
        result = fetcher._process_field_info("PX_LAST", None)

        assert isinstance(result, FieldInfo)
        assert result.field_id == "PX_LAST"
        assert result.field_name == ""
        assert result.description == ""
        assert result.data_type == ""
