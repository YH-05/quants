"""Unit tests for market.bse.collectors.index (IndexCollector).

Tests cover:
- IndexCollector initialization and session injection
- list_indices() static method
- fetch() ABC interface with index_name resolution
- validate() required column checks
- fetch_historical() API interaction with mocked session
- Error handling for invalid inputs and API failures
"""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.bse.collectors.index import IndexCollector
from market.bse.errors import BseParseError
from market.bse.session import BseSession
from market.bse.types import IndexName

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_INDEX_DATA: list[dict[str, Any]] = [
    {
        "I_open": "73800.50",
        "I_high": "74200.00",
        "I_low": "73500.25",
        "I_close": "74100.75",
        "I_pe": "22.50",
        "I_pb": "3.10",
        "I_yield": "1.25",
        "Tdate": "2026-03-05T00:00:00",
    },
    {
        "I_open": "74100.00",
        "I_high": "74500.00",
        "I_low": "73900.00",
        "I_close": "74350.25",
        "I_pe": "22.55",
        "I_pb": "3.12",
        "I_yield": "1.24",
        "Tdate": "2026-03-06T00:00:00",
    },
]


@pytest.fixture()
def mock_session() -> MagicMock:
    """Create a mock BseSession that returns sample index data."""
    session = MagicMock(spec=BseSession)
    response = MagicMock()
    response.json.return_value = _SAMPLE_INDEX_DATA
    session.get_with_retry.return_value = response
    return session


@pytest.fixture()
def collector(mock_session: MagicMock) -> IndexCollector:
    """IndexCollector with injected mock session."""
    return IndexCollector(session=mock_session)


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestIndexCollectorInit:
    """Tests for IndexCollector initialization."""

    def test_正常系_デフォルト初期化でセッションがNone(self) -> None:
        collector = IndexCollector()
        assert collector._session_instance is None

    def test_正常系_セッション注入で保持される(self, mock_session: MagicMock) -> None:
        collector = IndexCollector(session=mock_session)
        assert collector._session_instance is mock_session

    def test_正常系_get_sessionでセッション注入時はクローズ不要(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        session, should_close = collector._get_session()
        assert session is mock_session
        assert should_close is False

    def test_正常系_get_sessionで未注入時は新規作成(self) -> None:
        collector = IndexCollector()
        session, should_close = collector._get_session()
        assert isinstance(session, BseSession)
        assert should_close is True
        session.close()


# ---------------------------------------------------------------------------
# list_indices tests
# ---------------------------------------------------------------------------


class TestListIndices:
    """Tests for IndexCollector.list_indices()."""

    def test_正常系_全インデックスが返される(self) -> None:
        indices = IndexCollector.list_indices()
        assert "SENSEX" in indices
        assert "BANKEX" in indices
        assert "BSE 100" in indices

    def test_正常系_ソート済みリストが返される(self) -> None:
        indices = IndexCollector.list_indices()
        assert indices == sorted(indices)

    def test_正常系_IndexName全メンバーが含まれる(self) -> None:
        indices = IndexCollector.list_indices()
        for member in IndexName:
            assert member.value in indices

    def test_正常系_リスト長がIndexNameメンバー数と一致(self) -> None:
        indices = IndexCollector.list_indices()
        assert len(indices) == len(IndexName)


# ---------------------------------------------------------------------------
# fetch (ABC interface) tests
# ---------------------------------------------------------------------------


class TestFetch:
    """Tests for IndexCollector.fetch() ABC interface."""

    def test_異常系_index_name未指定でValueError(
        self, collector: IndexCollector
    ) -> None:
        with pytest.raises(ValueError, match="index_name is required"):
            collector.fetch()

    def test_異常系_不正なindex_nameでValueError(
        self, collector: IndexCollector
    ) -> None:
        with pytest.raises(ValueError, match="Unknown index name"):
            collector.fetch(index_name="INVALID_INDEX")

    def test_正常系_文字列index_nameでデータ取得(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        df = collector.fetch(index_name="SENSEX")
        assert not df.empty
        assert "close" in df.columns
        mock_session.get_with_retry.assert_called_once()

    def test_正常系_日付範囲指定でデータ取得(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        df = collector.fetch(
            index_name="SENSEX",
            start="2026-01-01",
            end="2026-03-06",
        )
        assert not df.empty

        # Verify the params passed to the session
        call_args = mock_session.get_with_retry.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["fmdt"] == "01/01/2026"
        assert params["todt"] == "06/03/2026"


# ---------------------------------------------------------------------------
# validate tests
# ---------------------------------------------------------------------------


class TestValidate:
    """Tests for IndexCollector.validate()."""

    def test_正常系_有効なDataFrameでTrue(self, collector: IndexCollector) -> None:
        df = pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-03-05")],
                "close": [74100.75],
            }
        )
        assert collector.validate(df) is True

    def test_異常系_空のDataFrameでFalse(self, collector: IndexCollector) -> None:
        assert collector.validate(pd.DataFrame()) is False

    def test_異常系_dateカラム欠落でFalse(self, collector: IndexCollector) -> None:
        df = pd.DataFrame({"close": [74100.75]})
        assert collector.validate(df) is False

    def test_異常系_closeカラム欠落でFalse(self, collector: IndexCollector) -> None:
        df = pd.DataFrame({"date": [pd.Timestamp("2026-03-05")]})
        assert collector.validate(df) is False


# ---------------------------------------------------------------------------
# fetch_historical tests
# ---------------------------------------------------------------------------


class TestFetchHistorical:
    """Tests for IndexCollector.fetch_historical()."""

    def test_正常系_SENSEXデータ取得(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        df = collector.fetch_historical(IndexName.SENSEX)
        assert not df.empty
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "date" in df.columns

    def test_正常系_日付範囲が正しくフォーマットされる(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        start = datetime.date(2026, 1, 15)
        end = datetime.date(2026, 3, 5)
        collector.fetch_historical(IndexName.SENSEX, start=start, end=end)

        call_args = mock_session.get_with_retry.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["index"] == "SENSEX"
        assert params["fmdt"] == "15/01/2026"
        assert params["todt"] == "05/03/2026"

    def test_正常系_デフォルト日付範囲は1年間(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        with patch("market.bse.collectors.index.datetime") as mock_dt:
            mock_dt.date.today.return_value = datetime.date(2026, 3, 6)
            mock_dt.timedelta = datetime.timedelta
            mock_dt.date.fromisoformat = datetime.date.fromisoformat

            collector.fetch_historical(IndexName.SENSEX)

            call_args = mock_session.get_with_retry.call_args
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            assert params["todt"] == "06/03/2026"
            assert params["fmdt"] == "06/03/2025"

    def test_正常系_数値カラムがクリーニングされる(
        self, collector: IndexCollector
    ) -> None:
        df = collector.fetch_historical(IndexName.SENSEX)
        # close should be cleaned to float
        assert df["close"].iloc[0] == 74100.75
        assert df["open"].iloc[0] == 73800.5

    def test_正常系_dateカラムがdatetimeに変換される(
        self, collector: IndexCollector
    ) -> None:
        df = collector.fetch_historical(IndexName.SENSEX)
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_正常系_BANKEXデータ取得(
        self, collector: IndexCollector, mock_session: MagicMock
    ) -> None:
        df = collector.fetch_historical(IndexName.BANKEX)
        assert not df.empty

        call_args = mock_session.get_with_retry.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["index"] == "BANKEX"

    def test_異常系_空レスポンスで空DataFrame(self, mock_session: MagicMock) -> None:
        response = MagicMock()
        response.json.return_value = []
        mock_session.get_with_retry.return_value = response

        collector = IndexCollector(session=mock_session)
        df = collector.fetch_historical(IndexName.SENSEX)
        assert df.empty

    def test_異常系_非リストレスポンスでBseParseError(
        self, mock_session: MagicMock
    ) -> None:
        response = MagicMock()
        response.json.return_value = {"error": "not found"}
        mock_session.get_with_retry.return_value = response

        collector = IndexCollector(session=mock_session)
        with pytest.raises(BseParseError, match="Expected list"):
            collector.fetch_historical(IndexName.SENSEX)

    def test_正常系_セッションクローズがcalledされる(self) -> None:
        """Session created internally is closed after use."""
        mock_session = MagicMock(spec=BseSession)
        response = MagicMock()
        response.json.return_value = _SAMPLE_INDEX_DATA
        mock_session.get_with_retry.return_value = response

        with patch.object(
            IndexCollector, "_get_session", return_value=(mock_session, True)
        ):
            collector = IndexCollector()
            collector.fetch_historical(IndexName.SENSEX)

        mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# parse_index_data tests
# ---------------------------------------------------------------------------


class TestParseIndexData:
    """Tests for parse_index_data (used internally by IndexCollector)."""

    def test_正常系_サンプルデータがパースされる(self) -> None:
        from market.bse.parsers import parse_index_data

        df = parse_index_data(_SAMPLE_INDEX_DATA)
        assert len(df) == 2
        assert "open" in df.columns
        assert "close" in df.columns
        assert "date" in df.columns

    def test_異常系_リスト以外でBseParseError(self) -> None:
        from market.bse.parsers import parse_index_data

        with pytest.raises(BseParseError, match="Expected list"):
            parse_index_data({"not": "a list"})  # type: ignore[arg-type]

    def test_異常系_空リストでBseParseError(self) -> None:
        from market.bse.parsers import parse_index_data

        with pytest.raises(BseParseError, match="Empty index data"):
            parse_index_data([])

    def test_正常系_TDateキーもdateにマッピング(self) -> None:
        from market.bse.parsers import parse_index_data

        data = [
            {
                "I_open": "100.00",
                "I_close": "105.00",
                "TDate": "2026-01-01T00:00:00",
            }
        ]
        df = parse_index_data(data)
        assert "date" in df.columns

    def test_正常系_peとpbカラムがクリーニングされる(self) -> None:
        from market.bse.parsers import parse_index_data

        df = parse_index_data(_SAMPLE_INDEX_DATA)
        assert df["pe"].iloc[0] == 22.5
        assert df["pb"].iloc[0] == 3.1


# ---------------------------------------------------------------------------
# DataCollector ABC compliance
# ---------------------------------------------------------------------------


class TestDataCollectorCompliance:
    """Verify IndexCollector satisfies the DataCollector ABC contract."""

    def test_正常系_nameプロパティがクラス名を返す(
        self, collector: IndexCollector
    ) -> None:
        assert collector.name == "IndexCollector"

    def test_正常系_collectメソッドがfetchとvalidateを統合(
        self, collector: IndexCollector
    ) -> None:
        df = collector.collect(index_name="SENSEX")
        assert not df.empty
        assert "close" in df.columns
