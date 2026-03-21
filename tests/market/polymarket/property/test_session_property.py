"""PolymarketSession のプロパティテスト。"""

from hypothesis import given, settings
from hypothesis import strategies as st

from market.polymarket.session import PolymarketSession
from market.polymarket.types import PolymarketConfig, RetryConfig


class TestBackoffProperty:
    """バックオフ遅延のプロパティテスト。"""

    @given(attempt=st.integers(min_value=0, max_value=8))
    @settings(max_examples=50)
    def test_プロパティ_バックオフ遅延は非負(self, attempt: int) -> None:
        config = PolymarketConfig()
        retry = RetryConfig()
        session = PolymarketSession(config=config, retry_config=retry)
        try:
            delay = session._calculate_backoff_delay(attempt)
            assert delay >= 0.0
        finally:
            session.close()
