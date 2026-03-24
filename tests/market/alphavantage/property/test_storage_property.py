"""Property-based tests for the Alpha Vantage storage layer.

Uses Hypothesis to verify invariant properties:
- upsert idempotency: upserting the same data twice yields unchanged row count
- PK constraint: upserting with the same PK overwrites to latest data
- Annual/Quarterly mixed earnings roundtrip
- Finite float values survive roundtrip without becoming None

Each test creates its own temporary ``AlphaVantageStorage`` instance
inside the test body to avoid Hypothesis health-check issues with
function-scoped pytest fixtures.

See Also
--------
market.alphavantage.storage : Implementation under test.
market.alphavantage.models : Record dataclasses.
tests.market.alphavantage.property.test_parser_property : Similar pattern.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from market.alphavantage.models import (
    AnnualEarningsRecord,
    CompanyOverviewRecord,
    DailyPriceRecord,
    QuarterlyEarningsRecord,
)
from market.alphavantage.storage import AlphaVantageStorage

# =============================================================================
# Strategies
# =============================================================================

# Symbols: 1-5 uppercase ASCII letters
symbols = st.text(
    alphabet=st.characters(whitelist_categories=("Lu",)),
    min_size=1,
    max_size=5,
)

# Positive finite floats suitable for OHLCV price values
positive_prices = st.floats(
    min_value=0.01,
    max_value=1e9,
    allow_nan=False,
    allow_infinity=False,
)

# Optional float values (finite or None)
optional_floats = st.one_of(
    st.none(),
    st.floats(
        min_value=-1e15,
        max_value=1e15,
        allow_nan=False,
        allow_infinity=False,
    ),
)


# =============================================================================
# Helper: create temporary storage
# =============================================================================


_counter = 0


def _make_storage() -> AlphaVantageStorage:
    """Create a temporary AlphaVantageStorage backed by a unique temp file."""
    global _counter
    _counter += 1
    import os
    import tempfile

    tmp_dir = Path(tempfile.gettempdir())
    db_path = tmp_dir / f"av_prop_test_{os.getpid()}_{_counter}.db"
    return AlphaVantageStorage(db_path=db_path)


# =============================================================================
# Property tests for upsert idempotency
# =============================================================================


class TestUpsertIdempotency:
    """Upserting the same data twice does not change the row count."""

    @given(data=st.data())
    @settings(max_examples=30, deadline=5000)
    def test_プロパティ_daily_prices_upsertは冪等(
        self,
        data: st.DataObject,
    ) -> None:
        """Upserting the same DailyPriceRecord list twice yields same row count."""
        storage = _make_storage()
        n = data.draw(st.integers(min_value=1, max_value=5))
        records = [
            DailyPriceRecord(
                symbol="TEST",
                date=f"2026-01-{i + 1:02d}",
                open=data.draw(positive_prices),
                high=data.draw(positive_prices),
                low=data.draw(positive_prices),
                close=data.draw(positive_prices),
                adjusted_close=data.draw(optional_floats),
                volume=data.draw(st.integers(min_value=0, max_value=10**12)),
                fetched_at="2026-03-24T12:00:00",
            )
            for i in range(n)
        ]

        # First upsert
        count1 = storage.upsert_daily_prices(records)
        assert count1 == n

        # Second upsert (same data)
        count2 = storage.upsert_daily_prices(records)
        assert count2 == n

        # Row count should be n (not 2n)
        total = storage.get_row_count("av_daily_prices")
        assert total == n

    @given(data=st.data())
    @settings(max_examples=30, deadline=5000)
    def test_プロパティ_company_overview_upsertは冪等(
        self,
        data: st.DataObject,
    ) -> None:
        """Upserting the same CompanyOverviewRecord twice yields 1 row."""
        storage = _make_storage()
        sym = data.draw(symbols)
        pe = data.draw(optional_floats)
        record = CompanyOverviewRecord(
            symbol=sym,
            name="Test Corp",
            pe_ratio=pe,
            fetched_at="2026-03-24T12:00:00",
        )

        storage.upsert_company_overview(record)
        storage.upsert_company_overview(record)

        result = storage.get_company_overview(sym)
        assert result is not None
        assert result.symbol == sym
        assert result.pe_ratio == pe

    @given(data=st.data())
    @settings(max_examples=30, deadline=5000)
    def test_プロパティ_earnings_upsertは冪等(
        self,
        data: st.DataObject,
    ) -> None:
        """Upserting the same earnings records twice yields same row count."""
        storage = _make_storage()
        eps_val = data.draw(optional_floats)
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            AnnualEarningsRecord(
                symbol="TEST",
                fiscal_date_ending="2025-09-30",
                period_type="annual",
                reported_eps=eps_val,
                fetched_at="2026-03-24T12:00:00",
            ),
        ]

        count1 = storage.upsert_earnings(records)
        count2 = storage.upsert_earnings(records)
        assert count1 == 1
        assert count2 == 1

        total = storage.get_row_count("av_earnings")
        assert total == 1


# =============================================================================
# Property tests for PK constraint (overwrite semantics)
# =============================================================================


class TestPKOverwrite:
    """Upserting with the same PK overwrites to the latest data."""

    @given(
        price_v1=positive_prices,
        price_v2=positive_prices,
    )
    @settings(max_examples=30, deadline=5000)
    def test_プロパティ_同一PKでupsertすると最新データに上書き(
        self,
        price_v1: float,
        price_v2: float,
    ) -> None:
        """Upserting with same (symbol, date) PK overwrites to latest values."""
        storage = _make_storage()
        record_v1 = DailyPriceRecord(
            symbol="AAPL",
            date="2026-01-15",
            open=price_v1,
            high=price_v1 + 1,
            low=price_v1 - 1,
            close=price_v1,
            adjusted_close=price_v1,
            volume=1_000_000,
            fetched_at="2026-03-24T10:00:00",
        )
        record_v2 = DailyPriceRecord(
            symbol="AAPL",
            date="2026-01-15",
            open=price_v2,
            high=price_v2 + 1,
            low=price_v2 - 1,
            close=price_v2,
            adjusted_close=price_v2,
            volume=2_000_000,
            fetched_at="2026-03-24T12:00:00",
        )

        storage.upsert_daily_prices([record_v1])
        storage.upsert_daily_prices([record_v2])

        df = storage.get_daily_prices("AAPL")
        assert len(df) == 1
        assert df.iloc[0]["close"] == price_v2
        assert df.iloc[0]["volume"] == 2_000_000


# =============================================================================
# Property tests for Annual/Quarterly mixed earnings roundtrip
# =============================================================================


class TestEarningsMixedRoundtrip:
    """Annual and Quarterly earnings records can be upserted and retrieved."""

    @given(
        annual_eps=optional_floats,
        quarterly_eps=optional_floats,
        surprise=optional_floats,
    )
    @settings(max_examples=30, deadline=5000)
    def test_プロパティ_annual_quarterly混在のラウンドトリップ(
        self,
        annual_eps: float | None,
        quarterly_eps: float | None,
        surprise: float | None,
    ) -> None:
        """Mixed annual and quarterly earnings records persist correctly."""
        storage = _make_storage()
        records: list[AnnualEarningsRecord | QuarterlyEarningsRecord] = [
            AnnualEarningsRecord(
                symbol="AAPL",
                fiscal_date_ending="2025-09-30",
                period_type="annual",
                reported_eps=annual_eps,
                fetched_at="2026-03-24T12:00:00",
            ),
            QuarterlyEarningsRecord(
                symbol="AAPL",
                fiscal_date_ending="2025-12-31",
                period_type="quarterly",
                reported_date="2026-01-30",
                reported_eps=quarterly_eps,
                estimated_eps=quarterly_eps,
                surprise=surprise,
                surprise_percentage=None,
                fetched_at="2026-03-24T12:00:00",
            ),
        ]

        storage.upsert_earnings(records)

        # Retrieve all earnings
        df_all = storage.get_earnings("AAPL")
        assert len(df_all) == 2

        # Filter annual
        df_annual = storage.get_earnings("AAPL", period_type="annual")
        assert len(df_annual) == 1
        row_a = df_annual.iloc[0]
        assert row_a["period_type"] == "annual"
        # Annual records should not have reported_date set
        assert row_a["reported_date"] is None

        # Filter quarterly
        df_quarterly = storage.get_earnings("AAPL", period_type="quarterly")
        assert len(df_quarterly) == 1
        row_q = df_quarterly.iloc[0]
        assert row_q["period_type"] == "quarterly"
        assert row_q["reported_date"] == "2026-01-30"


# =============================================================================
# Property tests for float value preservation
# =============================================================================


class TestFloatPreservation:
    """Float values survive upsert -> get roundtrip correctly."""

    @given(
        finite_price=st.floats(
            min_value=0.01,
            max_value=1e9,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=20, deadline=5000)
    def test_プロパティ_有限floatはNoneにならず正常にupsertされる(
        self,
        finite_price: float,
    ) -> None:
        """Finite float values survive upsert and are retrievable as-is."""
        storage = _make_storage()
        record = DailyPriceRecord(
            symbol="AAPL",
            date="2026-01-15",
            open=finite_price,
            high=finite_price + 1.0,
            low=max(finite_price - 1.0, 0.01),
            close=finite_price,
            adjusted_close=finite_price,
            volume=1_000_000,
            fetched_at="2026-03-24T12:00:00",
        )

        storage.upsert_daily_prices([record])
        df = storage.get_daily_prices("AAPL")
        assert len(df) == 1
        assert df.iloc[0]["close"] == finite_price

    @given(
        eps_val=st.one_of(st.none(), optional_floats),
    )
    @settings(max_examples=20, deadline=5000)
    def test_プロパティ_optional_floatのNoneはNoneとして保持される(
        self,
        eps_val: float | None,
    ) -> None:
        """Optional float fields with None value are stored and retrieved as None."""
        storage = _make_storage()
        record = CompanyOverviewRecord(
            symbol="TEST",
            pe_ratio=eps_val,
            fetched_at="2026-03-24T12:00:00",
        )

        storage.upsert_company_overview(record)
        result = storage.get_company_overview("TEST")
        assert result is not None
        if eps_val is None:
            assert result.pe_ratio is None
        else:
            assert result.pe_ratio == eps_val
