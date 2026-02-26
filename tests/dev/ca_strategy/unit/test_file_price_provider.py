"""Tests for FilePriceProvider.

FilePriceProvider reads daily close prices from Parquet/CSV files.
It supports two modes:

1. **Per-ticker mode** (directory): File naming convention:
   ``{TICKER}.parquet`` or ``{TICKER}.csv``. Each file must have a
   ``DatetimeIndex`` and a ``close`` column.

2. **Single-file mode** (file): A single Parquet/CSV file where
   columns are ticker symbols and rows are dates with close prices.

Key behaviors:
- Reads Parquet files preferentially over CSV (per-ticker mode)
- Filters data by start/end date range
- Skips missing tickers with a warning log
- Raises FileNotFoundError if data_path does not exist
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from dev.ca_strategy.price_provider import FilePriceProvider, PriceDataProvider


class TestFilePriceProvider:
    """FilePriceProvider per-ticker mode unit tests."""

    def test_正常系_Parquetファイルから読み取り(self, tmp_path: object) -> None:
        """Parquet file with close column should be read correctly."""
        data_dir = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0]}, index=idx)
        df.to_parquet(data_dir / "AAPL.parquet")  # type: ignore[operator]

        provider = FilePriceProvider(data_dir)
        result = provider.fetch(
            tickers=["AAPL"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "AAPL" in result
        assert len(result["AAPL"]) == 4
        assert result["AAPL"].iloc[0] == 100.0
        assert result["AAPL"].iloc[-1] == 103.0

    def test_正常系_CSVファイルから読み取り(self, tmp_path: object) -> None:
        """CSV file with close column should be read correctly."""
        data_dir = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame({"close": [200.0, 201.0, 202.0, 203.0]}, index=idx)
        df.to_csv(data_dir / "MSFT.csv")  # type: ignore[operator]

        provider = FilePriceProvider(data_dir)
        result = provider.fetch(
            tickers=["MSFT"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "MSFT" in result
        assert len(result["MSFT"]) == 4
        assert result["MSFT"].iloc[0] == 200.0

    def test_正常系_日付フィルタリング(self, tmp_path: object) -> None:
        """Data outside start/end range should be excluded."""
        data_dir = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-31", freq="B")
        df = pd.DataFrame({"close": range(len(idx))}, index=idx)
        df.to_parquet(data_dir / "AAPL.parquet")  # type: ignore[operator]

        provider = FilePriceProvider(data_dir)
        result = provider.fetch(
            tickers=["AAPL"],
            start=date(2024, 1, 10),
            end=date(2024, 1, 15),
        )

        assert "AAPL" in result
        series = result["AAPL"]
        # All dates should be within range
        for dt in series.index:
            d = dt.date() if hasattr(dt, "date") else dt
            assert date(2024, 1, 10) <= d <= date(2024, 1, 15)

    def test_正常系_存在しないティッカーはスキップ(self, tmp_path: object) -> None:
        """Tickers without files should be silently skipped."""
        data_dir = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0]}, index=idx)
        df.to_parquet(data_dir / "AAPL.parquet")  # type: ignore[operator]

        provider = FilePriceProvider(data_dir)
        result = provider.fetch(
            tickers=["AAPL", "NONEXISTENT"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "AAPL" in result
        assert "NONEXISTENT" not in result

    def test_正常系_Parquet優先_両方ある場合(self, tmp_path: object) -> None:
        """When both Parquet and CSV exist, Parquet should be preferred."""
        data_dir = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")

        # Parquet has different values than CSV
        df_parquet = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0]}, index=idx)
        df_csv = pd.DataFrame({"close": [999.0, 999.0, 999.0, 999.0]}, index=idx)
        df_parquet.to_parquet(data_dir / "AAPL.parquet")  # type: ignore[operator]
        df_csv.to_csv(data_dir / "AAPL.csv")  # type: ignore[operator]

        provider = FilePriceProvider(data_dir)
        result = provider.fetch(
            tickers=["AAPL"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "AAPL" in result
        # Should have Parquet values, not CSV values
        assert result["AAPL"].iloc[0] == 100.0

    def test_異常系_data_pathが存在しない場合FileNotFoundError(self) -> None:
        """Non-existent data_path should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            FilePriceProvider("/nonexistent/path/to/data")

    def test_エッジケース_空のティッカーリスト(self, tmp_path: object) -> None:
        """Empty tickers list should return empty dict."""
        data_dir = tmp_path  # type: ignore[assignment]
        provider = FilePriceProvider(data_dir)
        result = provider.fetch(
            tickers=[],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )
        assert result == {}

    def test_正常系_PriceDataProviderProtocolを満たす(self, tmp_path: object) -> None:
        """FilePriceProvider should satisfy the PriceDataProvider Protocol."""
        data_dir = tmp_path  # type: ignore[assignment]
        provider = FilePriceProvider(data_dir)
        assert isinstance(provider, PriceDataProvider)


class TestFilePriceProviderSingleFile:
    """Single-file mode unit tests."""

    def test_正常系_Parquet単一ファイルから複数ティッカー読み取り(
        self, tmp_path: object
    ) -> None:
        """Single Parquet file with multiple tickers as columns."""
        tmp = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame(
            {
                "AAPL": [100.0, 101.0, 102.0, 103.0],
                "MSFT": [200.0, 201.0, 202.0, 203.0],
            },
            index=idx,
        )
        file_path = tmp / "prices.parquet"
        df.to_parquet(file_path)

        provider = FilePriceProvider(file_path)
        result = provider.fetch(
            tickers=["AAPL", "MSFT"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "AAPL" in result
        assert "MSFT" in result
        assert len(result["AAPL"]) == 4
        assert result["AAPL"].iloc[0] == 100.0
        assert result["MSFT"].iloc[0] == 200.0

    def test_正常系_CSV単一ファイルから読み取り(self, tmp_path: object) -> None:
        """Single CSV file with tickers as columns."""
        tmp = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame(
            {"AAPL": [100.0, 101.0, 102.0, 103.0]},
            index=idx,
        )
        file_path = tmp / "prices.csv"
        df.to_csv(file_path)

        provider = FilePriceProvider(file_path)
        result = provider.fetch(
            tickers=["AAPL"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "AAPL" in result
        assert len(result["AAPL"]) == 4

    def test_正常系_単一ファイルで存在しないティッカーはスキップ(
        self, tmp_path: object
    ) -> None:
        """Tickers not in columns should be skipped."""
        tmp = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0, 103.0]}, index=idx)
        file_path = tmp / "prices.parquet"
        df.to_parquet(file_path)

        provider = FilePriceProvider(file_path)
        result = provider.fetch(
            tickers=["AAPL", "NONEXISTENT"],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )

        assert "AAPL" in result
        assert "NONEXISTENT" not in result

    def test_正常系_単一ファイルで日付フィルタリング(self, tmp_path: object) -> None:
        """Date filtering should work in single-file mode."""
        tmp = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-31", freq="B")
        df = pd.DataFrame({"AAPL": range(len(idx))}, index=idx)
        file_path = tmp / "prices.parquet"
        df.to_parquet(file_path)

        provider = FilePriceProvider(file_path)
        result = provider.fetch(
            tickers=["AAPL"],
            start=date(2024, 1, 10),
            end=date(2024, 1, 15),
        )

        assert "AAPL" in result
        for dt in result["AAPL"].index:
            d = dt.date() if hasattr(dt, "date") else dt
            assert date(2024, 1, 10) <= d <= date(2024, 1, 15)

    def test_正常系_PriceDataProviderProtocolを満たす_単一ファイル(
        self, tmp_path: object
    ) -> None:
        """Single-file mode should also satisfy PriceDataProvider Protocol."""
        tmp = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0, 103.0]}, index=idx)
        file_path = tmp / "prices.parquet"
        df.to_parquet(file_path)

        provider = FilePriceProvider(file_path)
        assert isinstance(provider, PriceDataProvider)

    def test_エッジケース_単一ファイルで空のティッカーリスト(
        self, tmp_path: object
    ) -> None:
        """Empty tickers list should return empty dict in single-file mode."""
        tmp = tmp_path  # type: ignore[assignment]
        idx = pd.date_range("2024-01-02", "2024-01-05", freq="B")
        df = pd.DataFrame({"AAPL": [100.0, 101.0, 102.0, 103.0]}, index=idx)
        file_path = tmp / "prices.parquet"
        df.to_parquet(file_path)

        provider = FilePriceProvider(file_path)
        result = provider.fetch(
            tickers=[],
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
        )
        assert result == {}
