"""PolymarketStorage の upsert 冪等性プロパティテスト。

Hypothesis を使用して、ランダムデータでの upsert 冪等性と
例外安全性を検証する。同じデータを2回 upsert しても
レコード数が変わらないことを保証する。

各テストメソッドは独立した一時ディレクトリに SQLite DB を作成し、
Hypothesis の example 間でデータが蓄積しないようにする。

See Also
--------
tests.market.polymarket.unit.test_storage : Unit tests for storage.
tests.market.polymarket.property.test_session_property : Session property tests.
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from market.polymarket.models import (
    PolymarketEvent,
    PolymarketMarket,
    PricePoint,
    TradeRecord,
)
from market.polymarket.storage import PolymarketStorage
from market.polymarket.storage_constants import (
    TABLE_EVENTS,
    TABLE_LEADERBOARD_SNAPSHOTS,
    TABLE_MARKETS,
    TABLE_OI_SNAPSHOTS,
    TABLE_PRICE_HISTORY,
    TABLE_TOKENS,
    TABLE_TRADES,
)
from market.polymarket.types import PriceInterval

# ============================================================================
# Hypothesis strategies
# ============================================================================

# Safe text strategy: printable ASCII without NUL bytes
_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=50,
)

_safe_id = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"), blacklist_characters="\x00"
    ),
    min_size=1,
    max_size=30,
)

_price_st = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)

_token_dict_st = st.fixed_dictionaries(
    {
        "token_id": _safe_id,
        "outcome": st.sampled_from(["Yes", "No"]),
        "price": _price_st,
    }
)

_market_st = st.builds(
    PolymarketMarket,
    condition_id=_safe_id,
    question=_safe_text,
    tokens=st.lists(_token_dict_st, min_size=0, max_size=3),
    description=st.just("test"),
    active=st.just(True),
    closed=st.just(False),
    volume=st.floats(
        min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
    ),
    liquidity=st.floats(
        min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
    ),
)

_event_st = st.builds(
    PolymarketEvent,
    id=_safe_id,
    title=_safe_text,
    slug=_safe_id,
    markets=st.lists(_market_st, min_size=0, max_size=2),
    description=st.just("test"),
    active=st.just(True),
    closed=st.just(False),
    volume=st.floats(
        min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
    ),
    liquidity=st.floats(
        min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
    ),
)

_price_point_st = st.builds(
    PricePoint,
    t=st.integers(min_value=1_000_000_000, max_value=2_000_000_000),
    p=_price_st,
)

_trade_st = st.builds(
    TradeRecord,
    id=_safe_id,
    market=_safe_id,
    asset_id=_safe_id,
    price=_price_st,
    size=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    side=st.sampled_from(["BUY", "SELL", None]),
    timestamp=st.none(),
)

_interval_st = st.sampled_from(list(PriceInterval))

FETCHED_AT = "2026-03-23T00:00:00Z"


# ============================================================================
# Helper
# ============================================================================


def _fresh_storage() -> PolymarketStorage:
    """Create a fresh PolymarketStorage in a unique temp directory."""
    tmp_dir = tempfile.mkdtemp()
    return PolymarketStorage(db_path=Path(tmp_dir) / "prop_test.db")


# ============================================================================
# Property tests: upsert idempotency
# ============================================================================


class TestUpsertEventsIdempotent:
    """upsert_events の冪等性プロパティテスト。"""

    @given(event=_event_st)
    @settings(max_examples=30)
    def test_プロパティ_同一イベントを2回upsertしてもレコード数は変わらない(
        self,
        event: PolymarketEvent,
    ) -> None:
        """Upserting the same event twice should not increase the event count."""
        storage = _fresh_storage()
        storage.upsert_events([event], fetched_at=FETCHED_AT)
        stats_after_first = storage.get_stats()

        storage.upsert_events([event], fetched_at=FETCHED_AT)
        stats_after_second = storage.get_stats()

        assert stats_after_second[TABLE_EVENTS] == stats_after_first[TABLE_EVENTS]

    @given(event=_event_st)
    @settings(max_examples=30)
    def test_プロパティ_ランダムイベントのupsertで例外が発生しない(
        self,
        event: PolymarketEvent,
    ) -> None:
        """Random event data should not cause exceptions during upsert."""
        storage = _fresh_storage()
        storage.upsert_events([event], fetched_at=FETCHED_AT)


class TestUpsertMarketsIdempotent:
    """upsert_markets の冪等性プロパティテスト。"""

    @given(market=_market_st)
    @settings(max_examples=30)
    def test_プロパティ_同一マーケットを2回upsertしてもレコード数は変わらない(
        self,
        market: PolymarketMarket,
    ) -> None:
        """Upserting the same market twice should not increase the market count."""
        storage = _fresh_storage()
        storage.upsert_markets([market], fetched_at=FETCHED_AT)
        stats_after_first = storage.get_stats()

        storage.upsert_markets([market], fetched_at=FETCHED_AT)
        stats_after_second = storage.get_stats()

        assert stats_after_second[TABLE_MARKETS] == stats_after_first[TABLE_MARKETS]
        assert stats_after_second[TABLE_TOKENS] == stats_after_first[TABLE_TOKENS]

    @given(market=_market_st)
    @settings(max_examples=30)
    def test_プロパティ_ランダムマーケットのupsertで例外が発生しない(
        self,
        market: PolymarketMarket,
    ) -> None:
        """Random market data should not cause exceptions during upsert."""
        storage = _fresh_storage()
        storage.upsert_markets([market], fetched_at=FETCHED_AT)


class TestUpsertPriceHistoryIdempotent:
    """upsert_price_history の冪等性プロパティテスト。"""

    @given(
        token_id=_safe_id,
        prices=st.lists(_price_point_st, min_size=1, max_size=10),
        interval=_interval_st,
    )
    @settings(max_examples=30)
    def test_プロパティ_同一価格履歴を2回upsertしてもレコード数は変わらない(
        self,
        token_id: str,
        prices: list[PricePoint],
        interval: PriceInterval,
    ) -> None:
        """Upserting the same price data twice should not increase the count."""
        storage = _fresh_storage()
        storage.upsert_price_history(token_id, prices, interval, fetched_at=FETCHED_AT)
        stats_after_first = storage.get_stats()

        storage.upsert_price_history(token_id, prices, interval, fetched_at=FETCHED_AT)
        stats_after_second = storage.get_stats()

        assert (
            stats_after_second[TABLE_PRICE_HISTORY]
            == stats_after_first[TABLE_PRICE_HISTORY]
        )

    @given(
        token_id=_safe_id,
        prices=st.lists(_price_point_st, min_size=0, max_size=10),
        interval=_interval_st,
    )
    @settings(max_examples=30)
    def test_プロパティ_ランダム価格履歴のupsertで例外が発生しない(
        self,
        token_id: str,
        prices: list[PricePoint],
        interval: PriceInterval,
    ) -> None:
        """Random price history data should not cause exceptions during upsert."""
        storage = _fresh_storage()
        storage.upsert_price_history(token_id, prices, interval, fetched_at=FETCHED_AT)


class TestUpsertTradesIdempotent:
    """upsert_trades の冪等性プロパティテスト。"""

    @given(trade=_trade_st)
    @settings(max_examples=30)
    def test_プロパティ_同一トレードを2回upsertしてもレコード数は変わらない(
        self,
        trade: TradeRecord,
    ) -> None:
        """Upserting the same trade twice should not increase the trade count."""
        storage = _fresh_storage()
        storage.upsert_trades([trade], fetched_at=FETCHED_AT)
        stats_after_first = storage.get_stats()

        storage.upsert_trades([trade], fetched_at=FETCHED_AT)
        stats_after_second = storage.get_stats()

        assert stats_after_second[TABLE_TRADES] == stats_after_first[TABLE_TRADES]

    @given(trade=_trade_st)
    @settings(max_examples=30)
    def test_プロパティ_ランダムトレードのupsertで例外が発生しない(
        self,
        trade: TradeRecord,
    ) -> None:
        """Random trade data should not cause exceptions during upsert."""
        storage = _fresh_storage()
        storage.upsert_trades([trade], fetched_at=FETCHED_AT)


class TestSnapshotIdempotent:
    """スナップショット系 insert の冪等性プロパティテスト。"""

    @given(
        condition_id=_safe_id,
        data=st.dictionaries(
            keys=_safe_text,
            values=st.one_of(
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                _safe_text,
            ),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=30)
    def test_プロパティ_同一OIスナップショットを2回insertしてもレコード数は変わらない(
        self,
        condition_id: str,
        data: dict,
    ) -> None:
        """Inserting the same OI snapshot twice should not increase the count."""
        storage = _fresh_storage()
        storage.insert_oi_snapshot(condition_id, data, fetched_at=FETCHED_AT)
        stats_after_first = storage.get_stats()

        storage.insert_oi_snapshot(condition_id, data, fetched_at=FETCHED_AT)
        stats_after_second = storage.get_stats()

        assert (
            stats_after_second[TABLE_OI_SNAPSHOTS]
            == stats_after_first[TABLE_OI_SNAPSHOTS]
        )

    @given(
        entries=st.lists(
            st.dictionaries(
                keys=_safe_text,
                values=st.one_of(
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    _safe_text,
                ),
                min_size=0,
                max_size=3,
            ),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=30)
    def test_プロパティ_同一リーダーボードスナップショットを2回insertしてもレコード数は変わらない(
        self,
        entries: list[dict],
    ) -> None:
        """Inserting the same leaderboard snapshot twice should not increase count."""
        storage = _fresh_storage()
        storage.insert_leaderboard_snapshot(entries, fetched_at=FETCHED_AT)
        stats_after_first = storage.get_stats()

        storage.insert_leaderboard_snapshot(entries, fetched_at=FETCHED_AT)
        stats_after_second = storage.get_stats()

        assert (
            stats_after_second[TABLE_LEADERBOARD_SNAPSHOTS]
            == stats_after_first[TABLE_LEADERBOARD_SNAPSHOTS]
        )


class TestUpsertPreservesAllElements:
    """upsert 後のデータ整合性プロパティテスト。"""

    @given(
        events=st.lists(_event_st, min_size=1, max_size=3),
    )
    @settings(max_examples=20)
    def test_プロパティ_upsert後のイベント増分はユニークID数以下(
        self,
        events: list[PolymarketEvent],
    ) -> None:
        """The number of new event rows added is at most the unique event IDs count."""
        storage = _fresh_storage()
        storage.upsert_events(events, fetched_at=FETCHED_AT)

        unique_event_ids = {e.id for e in events}
        stats_after = storage.get_stats()
        assert stats_after[TABLE_EVENTS] <= len(unique_event_ids)

    @given(
        markets=st.lists(_market_st, min_size=1, max_size=5),
    )
    @settings(max_examples=20)
    def test_プロパティ_upsert後のマーケット増分はユニークcondition_id数以下(
        self,
        markets: list[PolymarketMarket],
    ) -> None:
        """The number of new market rows added is at most the unique condition_ids count."""
        storage = _fresh_storage()
        storage.upsert_markets(markets, fetched_at=FETCHED_AT)

        unique_condition_ids = {m.condition_id for m in markets}
        stats_after = storage.get_stats()
        assert stats_after[TABLE_MARKETS] <= len(unique_condition_ids)
