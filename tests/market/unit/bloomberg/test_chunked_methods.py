"""Unit tests for BloombergFetcher chunked methods.

Tests for:
- get_financial_data_chunked: chunk_size splitting + retry logic
- get_earnings_dates: ReferenceDataRequest + EXPECTED_REPORT_DT
- convert_identifiers_with_date: date-qualified identifier conversion
- update_historical_data: DataFrame-return-only incremental update
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from market.bloomberg.fetcher import BloombergFetcher
    from market.bloomberg.types import (
        BloombergDataResult,
        BloombergFetchOptions,
        EarningsInfo,
        IdentifierConversionResult,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref_response_event(
    securities_fields: list[dict[str, Any]],
    event_type: int,
) -> MagicMock:
    """Build a mock BLPAPI event for ReferenceDataResponse."""
    rows = []
    for item in securities_fields:
        security = item["security"]
        fields = {k: v for k, v in item.items() if k != "security"}
        fd = MagicMock()
        fd.hasElement.side_effect = lambda n, _f=fields: n in _f
        fd.getElement.side_effect = lambda n, _f=fields: _make_val_element(_f.get(n))

        sd = MagicMock()
        sd.hasElement.side_effect = lambda n: n == "fieldData"
        sd.getElement.side_effect = lambda n, _sec=security, _fd=fd: (
            _make_val_element(_sec) if n == "security" else _fd
        )
        rows.append(sd)

    sd_array = MagicMock()
    sd_array.values.return_value = iter(rows)

    msg = MagicMock()
    msg.hasElement.side_effect = lambda n: n == "securityData"
    msg.getElement.return_value = sd_array

    event = MagicMock()
    event.eventType.return_value = event_type
    event.__iter__ = MagicMock(return_value=iter([msg]))
    return event


def _make_val_element(value: Any) -> MagicMock:
    elem = MagicMock()
    elem.getValue.return_value = value
    elem.getElementAsString.return_value = str(value) if value is not None else ""
    elem.isNull.return_value = value is None
    return elem


# ---------------------------------------------------------------------------
# get_financial_data_chunked
# ---------------------------------------------------------------------------


class TestGetFinancialDataChunked:
    """Tests for BloombergFetcher.get_financial_data_chunked."""

    def test_正常系_チャンク分割で複数リクエストを送信する(self) -> None:
        """chunk_size=2、証券5件 → 3回のget_financial_data呼び出し."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergDataResult, BloombergFetchOptions

        fetcher = BloombergFetcher()
        securities = [
            "AAPL US Equity",
            "MSFT US Equity",
            "GOOGL US Equity",
            "AMZN US Equity",
            "NVDA US Equity",
        ]
        options = BloombergFetchOptions(
            securities=securities,
            fields=["IS_EPS"],
        )

        call_count = 0
        captured_chunks: list[list[str]] = []

        def mock_get_financial_data(
            chunk_options: BloombergFetchOptions,
        ) -> list[BloombergDataResult]:
            nonlocal call_count
            call_count += 1
            captured_chunks.append(list(chunk_options.securities))
            return [
                BloombergDataResult(
                    security=sec,
                    data=pd.DataFrame({"security": [sec], "IS_EPS": [1.0]}),
                    source=fetcher.source,
                    fetched_at=datetime.now(),
                )
                for sec in chunk_options.securities
            ]

        with patch.object(
            fetcher, "get_financial_data", side_effect=mock_get_financial_data
        ):
            results = fetcher.get_financial_data_chunked(options, chunk_size=2)

        assert call_count == 3  # ceil(5/2) = 3
        assert captured_chunks[0] == ["AAPL US Equity", "MSFT US Equity"]
        assert captured_chunks[1] == ["GOOGL US Equity", "AMZN US Equity"]
        assert captured_chunks[2] == ["NVDA US Equity"]
        assert len(results) == 5

    def test_正常系_デフォルトchunk_size50が使用される(self) -> None:
        """デフォルトのchunk_sizeが50であること."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergFetchOptions

        fetcher = BloombergFetcher()
        securities = [f"TICKER{i:02d} US Equity" for i in range(60)]
        options = BloombergFetchOptions(securities=securities, fields=["IS_EPS"])

        call_count = 0

        def mock_get_financial_data(chunk_options: BloombergFetchOptions) -> list:
            nonlocal call_count
            call_count += 1
            return []

        with patch.object(
            fetcher, "get_financial_data", side_effect=mock_get_financial_data
        ):
            fetcher.get_financial_data_chunked(options)  # No chunk_size → default 50

        assert call_count == 2  # ceil(60/50) = 2

    def test_正常系_リトライ後に成功する(self) -> None:
        """1回失敗後に2回目で成功するチャンクのリトライ動作."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergDataResult, BloombergFetchOptions
        from market.errors import BloombergDataError

        fetcher = BloombergFetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["IS_EPS"],
        )

        attempt = 0

        def mock_get_financial_data(
            chunk_options: BloombergFetchOptions,
        ) -> list[BloombergDataResult]:
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise BloombergDataError("Transient error", security="AAPL US Equity")
            return [
                BloombergDataResult(
                    security="AAPL US Equity",
                    data=pd.DataFrame({"IS_EPS": [6.5]}),
                    source=fetcher.source,
                    fetched_at=datetime.now(),
                )
            ]

        with (
            patch.object(
                fetcher, "get_financial_data", side_effect=mock_get_financial_data
            ),
            patch("time.sleep"),
        ):
            results = fetcher.get_financial_data_chunked(options, chunk_size=50)

        assert attempt == 2
        assert len(results) == 1

    def test_異常系_最大リトライ超過でエラー(self) -> None:
        """max_retries回失敗し続けるとBloombergDataErrorを発生させる."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergFetchOptions
        from market.errors import BloombergDataError

        fetcher = BloombergFetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["IS_EPS"],
        )

        def mock_get_financial_data(chunk_options: BloombergFetchOptions) -> list:
            raise BloombergDataError("Persistent error", security="AAPL US Equity")

        with (
            patch.object(
                fetcher, "get_financial_data", side_effect=mock_get_financial_data
            ),
            patch("time.sleep"),
            pytest.raises(BloombergDataError),
        ):
            fetcher.get_financial_data_chunked(options, chunk_size=50)

    def test_異常系_chunk_sizeが0以下でValueError(self) -> None:
        """chunk_size <= 0 のときValueErrorを発生させる."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergFetchOptions

        fetcher = BloombergFetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["IS_EPS"],
        )

        with pytest.raises(ValueError, match="chunk_size must be positive"):
            fetcher.get_financial_data_chunked(options, chunk_size=0)

    def test_異常系_chunk_sizeが負数でValueError(self) -> None:
        """chunk_size < 0 のときValueErrorを発生させる."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergFetchOptions

        fetcher = BloombergFetcher()
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["IS_EPS"],
        )

        with pytest.raises(ValueError, match="chunk_size must be positive"):
            fetcher.get_financial_data_chunked(options, chunk_size=-1)


# ---------------------------------------------------------------------------
# get_earnings_dates
# ---------------------------------------------------------------------------


class TestGetEarningsDates:
    """Tests for BloombergFetcher.get_earnings_dates."""

    def test_正常系_EarningsInfoオブジェクトが返される(self) -> None:
        """_process_reference_responseの結果からEarningsInfoリストが組み立てられること."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import EarningsInfo

        fetcher = BloombergFetcher()
        securities = ["AAPL US Equity"]

        ref_df = pd.DataFrame({"EXPECTED_REPORT_DT": ["2024-10-31"]})

        mock_session = MagicMock()
        with (
            patch.object(fetcher, "_create_session", return_value=mock_session),
            patch.object(fetcher, "_open_service"),
            patch.object(fetcher, "_process_reference_response", return_value=ref_df),
        ):
            results = fetcher.get_earnings_dates(
                securities=securities,
                start_date="2024-10-01",
                end_date="2024-12-31",
            )

        assert len(results) == 1
        assert isinstance(results[0], EarningsInfo)
        assert results[0].security == "AAPL US Equity"
        assert results[0].expected_report_dt == date(2024, 10, 31)

    def test_エッジケース_空の証券リストで空結果(self) -> None:
        """証券リストが空なら空のリストを返す."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()

        results = fetcher.get_earnings_dates(
            securities=[],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        assert results == []

    def test_正常系_メソッドが存在する(self) -> None:
        """get_earnings_datesメソッドがBloombergFetcherに存在すること."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        assert hasattr(fetcher, "get_earnings_dates")
        assert callable(fetcher.get_earnings_dates)


# ---------------------------------------------------------------------------
# convert_identifiers_with_date
# ---------------------------------------------------------------------------


class TestConvertIdentifiersWithDate:
    """Tests for BloombergFetcher.convert_identifiers_with_date."""

    def test_正常系_日付指定で識別子変換できる(self) -> None:
        """_process_id_conversionの結果からIdentifierConversionResultリストが組み立てられること."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import IdentifierConversionResult, IDType

        fetcher = BloombergFetcher()
        securities = ["AAPL US Equity"]
        ref_date = date(2024, 1, 15)

        # _process_id_conversion は {security: converted_id} の dict を返す
        converted_map = {"AAPL US Equity": "US0378331005"}

        mock_session = MagicMock()
        with (
            patch.object(fetcher, "_create_session", return_value=mock_session),
            patch.object(fetcher, "_open_service"),
            patch.object(fetcher, "_process_id_conversion", return_value=converted_map),
        ):
            results = fetcher.convert_identifiers_with_date(
                securities=securities,
                from_type=IDType.TICKER,
                to_type=IDType.ISIN,
                date=ref_date,
            )

        assert len(results) == 1
        assert isinstance(results[0], IdentifierConversionResult)
        assert results[0].original == "AAPL US Equity"
        assert results[0].converted == "US0378331005"
        assert results[0].status == "success"
        assert results[0].date == ref_date

    def test_正常系_変換失敗銘柄はfailedステータス(self) -> None:
        """_process_id_conversionで変換できない識別子はstatus='failed'として返される."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import IdentifierConversionResult, IDType

        fetcher = BloombergFetcher()

        # 変換できなかった場合は dict に含まれない
        converted_map: dict[str, str] = {}

        mock_session = MagicMock()
        with (
            patch.object(fetcher, "_create_session", return_value=mock_session),
            patch.object(fetcher, "_open_service"),
            patch.object(fetcher, "_process_id_conversion", return_value=converted_map),
        ):
            results = fetcher.convert_identifiers_with_date(
                securities=["INVALID US Equity"],
                from_type=IDType.TICKER,
                to_type=IDType.ISIN,
                date=date(2024, 1, 15),
            )

        assert len(results) == 1
        assert isinstance(results[0], IdentifierConversionResult)
        assert results[0].status == "failed"
        assert results[0].original == "INVALID US Equity"
        assert results[0].converted == ""

    def test_エッジケース_空リストで空結果(self) -> None:
        """空の証券リストは空のリストを返す."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import IDType

        fetcher = BloombergFetcher()

        results = fetcher.convert_identifiers_with_date(
            securities=[],
            from_type=IDType.TICKER,
            to_type=IDType.ISIN,
            date=date(2024, 1, 15),
        )

        assert results == []

    def test_正常系_メソッドが存在する(self) -> None:
        """convert_identifiers_with_dateメソッドがBloombergFetcherに存在すること."""
        from market.bloomberg.fetcher import BloombergFetcher

        fetcher = BloombergFetcher()
        assert hasattr(fetcher, "convert_identifiers_with_date")
        assert callable(fetcher.convert_identifiers_with_date)


# ---------------------------------------------------------------------------
# update_historical_data
# ---------------------------------------------------------------------------


class TestUpdateHistoricalData:
    """Tests for BloombergFetcher.update_historical_data."""

    def test_正常系_DataFrameを返す(self, tmp_path: "Path") -> None:
        """update_historical_dataがpd.DataFrameを返すこと."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergDataResult, BloombergFetchOptions

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        incremental_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-02-01", "2024-02-02"]),
                "security": ["AAPL US Equity", "AAPL US Equity"],
                "PX_LAST": [185.0, 186.0],
            }
        )

        with (
            patch.object(
                fetcher, "get_latest_date_from_db", return_value=datetime(2024, 1, 31)
            ),
            patch.object(
                fetcher,
                "get_historical_data",
                return_value=[
                    BloombergDataResult(
                        security="AAPL US Equity",
                        data=incremental_df,
                        source=fetcher.source,
                        fetched_at=datetime.now(),
                    )
                ],
            ),
        ):
            result = fetcher.update_historical_data(
                options=options,
                db_path=db_path,
                table_name="prices",
                date_column="date",
            )

        assert isinstance(result, pd.DataFrame)

    def test_正常系_DB保存ロジックを含まない(self, tmp_path: "Path") -> None:
        """update_historical_dataはDBへの書き込みを行わずDataFrameのみ返す."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergDataResult, BloombergFetchOptions

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        with (
            patch.object(fetcher, "get_latest_date_from_db", return_value=None),
            patch.object(
                fetcher,
                "get_historical_data",
                return_value=[
                    BloombergDataResult(
                        security="AAPL US Equity",
                        data=pd.DataFrame(
                            {"date": [datetime(2024, 1, 1)], "PX_LAST": [150.0]}
                        ),
                        source=fetcher.source,
                        fetched_at=datetime.now(),
                    )
                ],
            ),
            patch.object(fetcher, "store_to_database") as mock_store,
        ):
            result = fetcher.update_historical_data(
                options=options,
                db_path=db_path,
                table_name="prices",
                date_column="date",
            )

        # store_to_database should NOT be called inside update_historical_data
        mock_store.assert_not_called()
        assert isinstance(result, pd.DataFrame)

    def test_正常系_最新日以降のデータのみ取得する(self, tmp_path: "Path") -> None:
        """get_latest_date_from_dbで取得した日付以降のデータのみ要求する."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergDataResult, BloombergFetchOptions

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        latest_date = datetime(2024, 1, 15)
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        captured_options: list[BloombergFetchOptions] = []

        def mock_get_historical(
            opt: BloombergFetchOptions,
        ) -> list[BloombergDataResult]:
            captured_options.append(opt)
            return [
                BloombergDataResult(
                    security="AAPL US Equity",
                    data=pd.DataFrame(),
                    source=fetcher.source,
                    fetched_at=datetime.now(),
                )
            ]

        with (
            patch.object(fetcher, "get_latest_date_from_db", return_value=latest_date),
            patch.object(
                fetcher, "get_historical_data", side_effect=mock_get_historical
            ),
        ):
            fetcher.update_historical_data(
                options=options,
                db_path=db_path,
                table_name="prices",
                date_column="date",
            )

        # The start_date of the request should be at or after the latest_date in DB
        assert len(captured_options) == 1
        called_start = captured_options[0].start_date
        assert called_start is not None, "start_date should have been set"
        # start_date should be at or after latest_date
        if isinstance(called_start, str):
            called_dt: datetime = datetime.strptime(called_start, "%Y-%m-%d")
        else:
            called_dt = called_start  # datetime instance
        assert called_dt >= latest_date

    def test_エッジケース_DBが空の場合全期間取得(self, tmp_path: "Path") -> None:
        """get_latest_date_from_dbがNoneを返す場合、元のstart_dateから取得する."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergDataResult, BloombergFetchOptions

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        original_start = "2024-01-01"
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
            start_date=original_start,
            end_date="2024-12-31",
        )

        captured_options: list[BloombergFetchOptions] = []

        def mock_get_historical(opt: BloombergFetchOptions) -> list:
            captured_options.append(opt)
            return []

        with (
            patch.object(fetcher, "get_latest_date_from_db", return_value=None),
            patch.object(
                fetcher, "get_historical_data", side_effect=mock_get_historical
            ),
        ):
            fetcher.update_historical_data(
                options=options,
                db_path=db_path,
                table_name="prices",
                date_column="date",
            )

        assert captured_options[0].start_date == original_start

    def test_エッジケース_増分データなしで空DataFrameを返す(
        self, tmp_path: "Path"
    ) -> None:
        """新規データが0件のとき空DataFrameを返す."""
        from market.bloomberg.fetcher import BloombergFetcher
        from market.bloomberg.types import BloombergFetchOptions

        fetcher = BloombergFetcher()
        db_path = str(tmp_path / "test.duckdb")
        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        with (
            patch.object(fetcher, "get_latest_date_from_db", return_value=None),
            patch.object(fetcher, "get_historical_data", return_value=[]),
        ):
            result = fetcher.update_historical_data(
                options=options,
                db_path=db_path,
                table_name="prices",
                date_column="date",
            )

        assert isinstance(result, pd.DataFrame)
        assert result.empty
