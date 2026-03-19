"""Unit tests for pandera schema validation in AseanTickerStorage.

Tests cover:
- TICKER_DF_SCHEMA definition: column types, nullable constraints
- upsert_tickers: validation is called before store_df
- Schema violation: raises SchemaError on invalid data
- Valid data: passes validation without error
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pandas as pd
import pandera
import pandera.pandas
import pytest

from market.asean_common.constants import (
    YFINANCE_SUFFIX_MAP,
    AseanMarket,
)
from market.asean_common.types import TickerRecord

if TYPE_CHECKING:
    from database.db.duckdb_client import DuckDBClient


# ============================================================================
# Test: TICKER_DF_SCHEMA definition
# ============================================================================


class TestTickerDfSchema:
    """Tests for TICKER_DF_SCHEMA pandera DataFrameSchema."""

    def test_正常系_スキーマがDataFrameSchemaインスタンスである(self) -> None:
        """TICKER_DF_SCHEMAがpandera DataFrameSchemaインスタンスであること."""
        from market.asean_common.storage import TICKER_DF_SCHEMA

        assert isinstance(TICKER_DF_SCHEMA, pandera.pandas.DataFrameSchema)

    def test_正常系_必須カラムが定義されている(self) -> None:
        """TICKER_DF_SCHEMAに必須カラムが全て定義されていること."""
        from market.asean_common.storage import TICKER_DF_SCHEMA

        expected_columns = {
            "ticker",
            "name",
            "market",
            "yfinance_suffix",
            "yfinance_ticker",
            "sector",
            "industry",
            "market_cap",
            "currency",
            "is_active",
        }
        assert set(TICKER_DF_SCHEMA.columns.keys()) == expected_columns

    def test_正常系_NOT_NULLカラムがnullable_falseである(self) -> None:
        """ticker, name, market等のNOT NULLカラムがnullable=Falseであること."""
        from market.asean_common.storage import TICKER_DF_SCHEMA

        not_null_columns = [
            "ticker",
            "name",
            "market",
            "yfinance_suffix",
            "yfinance_ticker",
            "is_active",
        ]
        for col_name in not_null_columns:
            col = TICKER_DF_SCHEMA.columns[col_name]
            assert col.nullable is False, f"Column '{col_name}' should be non-nullable"

    def test_正常系_NULLABLEカラムがnullable_trueである(self) -> None:
        """sector, industry, market_cap, currencyがnullable=Trueであること."""
        from market.asean_common.storage import TICKER_DF_SCHEMA

        nullable_columns = ["sector", "industry", "market_cap", "currency"]
        for col_name in nullable_columns:
            col = TICKER_DF_SCHEMA.columns[col_name]
            assert col.nullable is True, f"Column '{col_name}' should be nullable"


# ============================================================================
# Test: upsert_tickers schema validation
# ============================================================================


class TestUpsertTickersSchemaValidation:
    """Tests for schema validation in upsert_tickers method."""

    def test_正常系_有効なTickerRecordリストでバリデーション成功(
        self,
        duckdb_client: DuckDBClient,
        sample_tickers: list[TickerRecord],
    ) -> None:
        """有効なTickerRecordリストがスキーマ検証を通過すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        # Should not raise any exception
        count = storage.upsert_tickers(sample_tickers)
        assert count == 3

    def test_正常系_Noneフィールド含むデータでバリデーション成功(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """オプショナルフィールドがNoneのデータがスキーマ検証を通過すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)
        ticker = TickerRecord(
            ticker="TEST",
            name="Test Company",
            market=AseanMarket.IDX,
            yfinance_suffix=YFINANCE_SUFFIX_MAP[AseanMarket.IDX],
        )
        count = storage.upsert_tickers([ticker])
        assert count == 1

    def test_異常系_market_capに文字列が入るとSchemaError(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """market_capに文字列が混入した場合にSchemaErrorが発生すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)

        # Build a DataFrame directly with invalid data to simulate
        # dataclasses.asdict() producing unexpected values
        invalid_df = pd.DataFrame(
            [
                {
                    "ticker": "BAD",
                    "name": "Bad Company",
                    "market": "SGX",
                    "yfinance_suffix": ".SI",
                    "yfinance_ticker": "BAD.SI",
                    "sector": None,
                    "industry": None,
                    "market_cap": "not_a_number",
                    "currency": None,
                    "is_active": True,
                }
            ]
        )

        # Patch _build_ticker_df to return our invalid DataFrame
        with (
            patch.object(
                storage,
                "_build_ticker_df",
                return_value=invalid_df,
            ),
            pytest.raises(pandera.errors.SchemaError),
        ):
            storage.upsert_tickers(
                [
                    TickerRecord(
                        ticker="BAD",
                        name="Bad Company",
                        market=AseanMarket.SGX,
                        yfinance_suffix=".SI",
                    )
                ]
            )

    def test_異常系_ticker列がNullだとSchemaError(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """ticker列にNullが含まれる場合にSchemaErrorが発生すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)

        invalid_df = pd.DataFrame(
            [
                {
                    "ticker": None,
                    "name": "Bad Company",
                    "market": "SGX",
                    "yfinance_suffix": ".SI",
                    "yfinance_ticker": "None.SI",
                    "sector": None,
                    "industry": None,
                    "market_cap": None,
                    "currency": None,
                    "is_active": True,
                }
            ]
        )

        with (
            patch.object(
                storage,
                "_build_ticker_df",
                return_value=invalid_df,
            ),
            pytest.raises(pandera.errors.SchemaError),
        ):
            storage.upsert_tickers(
                [
                    TickerRecord(
                        ticker="PLACEHOLDER",
                        name="Bad Company",
                        market=AseanMarket.SGX,
                        yfinance_suffix=".SI",
                    )
                ]
            )

    def test_異常系_name列がNullだとSchemaError(
        self,
        duckdb_client: DuckDBClient,
    ) -> None:
        """name列にNullが含まれる場合にSchemaErrorが発生すること."""
        from market.asean_common.storage import AseanTickerStorage

        storage = AseanTickerStorage(client=duckdb_client)

        invalid_df = pd.DataFrame(
            [
                {
                    "ticker": "BAD",
                    "name": None,
                    "market": "SGX",
                    "yfinance_suffix": ".SI",
                    "yfinance_ticker": "BAD.SI",
                    "sector": None,
                    "industry": None,
                    "market_cap": None,
                    "currency": None,
                    "is_active": True,
                }
            ]
        )

        with (
            patch.object(
                storage,
                "_build_ticker_df",
                return_value=invalid_df,
            ),
            pytest.raises(pandera.errors.SchemaError),
        ):
            storage.upsert_tickers(
                [
                    TickerRecord(
                        ticker="BAD",
                        name="Bad Company",
                        market=AseanMarket.SGX,
                        yfinance_suffix=".SI",
                    )
                ]
            )
