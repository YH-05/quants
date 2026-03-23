"""Property-based tests for market.alphavantage.rate_limiter module.

Uses Hypothesis to verify invariant conditions of the dual-window
sliding rate limiter:
- acquire n times -> timestamp count equals n
- acquire return value is always non-negative
- available_minute is always in [0, requests_per_minute]
- available_hour is always in [0, requests_per_hour]
- available_minute + used_minute == requests_per_minute

Test TODO List:
- [x] acquire n times -> deque length equals n (within limits)
- [x] acquire return value is always non-negative float
- [x] available_minute is always in valid range
- [x] available_hour is always in valid range
- [x] available_minute + timestamps_in_minute == requests_per_minute
- [x] available_hour + timestamps_in_hour == requests_per_hour
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from market.alphavantage.rate_limiter import DualWindowRateLimiter

# =============================================================================
# Strategies
# =============================================================================

# Strategy for valid requests_per_minute values
minute_limits = st.integers(min_value=1, max_value=50)

# Strategy for valid requests_per_hour values
hour_limits = st.integers(min_value=1, max_value=200)

# Strategy for number of acquire calls (kept small for speed)
acquire_counts = st.integers(min_value=0, max_value=30)


# =============================================================================
# Property tests
# =============================================================================


class TestAcquireCountProperty:
    """Property tests for acquire call counting."""

    @given(
        per_minute=minute_limits,
        per_hour=hour_limits,
        n=acquire_counts,
    )
    @settings(max_examples=100)
    def test_プロパティ_n回acquireでタイムスタンプ数がn以下(
        self,
        per_minute: int,
        per_hour: int,
        n: int,
    ) -> None:
        """n 回 acquire 後のタイムスタンプ数は n 以下であること。

        制限到達で待機が発生する場合があるため「以下」で検証する。
        ただし制限内であれば正確に n になる。
        """
        # per_hour >= per_minute を保証
        per_hour = max(per_hour, per_minute)
        # n が制限を超えないようにする（ブロッキングを避ける）
        safe_n = min(n, per_minute, per_hour)

        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=per_hour,
        )
        for _ in range(safe_n):
            limiter.acquire()

        assert len(limiter._timestamps) == safe_n


class TestAcquireReturnValueProperty:
    """Property tests for acquire return value."""

    @given(
        per_minute=minute_limits,
        per_hour=hour_limits,
    )
    @settings(max_examples=100)
    def test_プロパティ_acquire返り値は常に非負float(
        self,
        per_minute: int,
        per_hour: int,
    ) -> None:
        """acquire() の返り値は常に非負の float であること。"""
        per_hour = max(per_hour, per_minute)
        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=per_hour,
        )
        waited = limiter.acquire()
        assert isinstance(waited, float)
        assert waited >= 0.0


class TestAvailableMinuteProperty:
    """Property tests for available_minute range."""

    @given(
        per_minute=minute_limits,
        per_hour=hour_limits,
        n=acquire_counts,
    )
    @settings(max_examples=100)
    def test_プロパティ_available_minuteは常に有効範囲内(
        self,
        per_minute: int,
        per_hour: int,
        n: int,
    ) -> None:
        """available_minute は常に [0, requests_per_minute] の範囲内であること。"""
        per_hour = max(per_hour, per_minute)
        safe_n = min(n, per_minute, per_hour)

        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=per_hour,
        )
        for _ in range(safe_n):
            limiter.acquire()

        assert 0 <= limiter.available_minute <= per_minute


class TestAvailableHourProperty:
    """Property tests for available_hour range."""

    @given(
        per_minute=minute_limits,
        per_hour=hour_limits,
        n=acquire_counts,
    )
    @settings(max_examples=100)
    def test_プロパティ_available_hourは常に有効範囲内(
        self,
        per_minute: int,
        per_hour: int,
        n: int,
    ) -> None:
        """available_hour は常に [0, requests_per_hour] の範囲内であること。"""
        per_hour = max(per_hour, per_minute)
        safe_n = min(n, per_minute, per_hour)

        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=per_hour,
        )
        for _ in range(safe_n):
            limiter.acquire()

        assert 0 <= limiter.available_hour <= per_hour


class TestAvailableConsistencyProperty:
    """Property tests for consistency between available and used counts."""

    @given(
        per_minute=minute_limits,
        per_hour=hour_limits,
        n=acquire_counts,
    )
    @settings(max_examples=100)
    def test_プロパティ_available_minuteと使用数の合計が制限数(
        self,
        per_minute: int,
        per_hour: int,
        n: int,
    ) -> None:
        """available_minute + 分ウィンドウ内のリクエスト数 == requests_per_minute。"""
        per_hour = max(per_hour, per_minute)
        safe_n = min(n, per_minute, per_hour)

        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=per_hour,
        )
        for _ in range(safe_n):
            limiter.acquire()

        # 全タイムスタンプは1分以内（テスト実行は瞬時）なので
        # available_minute + safe_n == per_minute
        assert limiter.available_minute + safe_n == per_minute

    @given(
        per_minute=minute_limits,
        per_hour=hour_limits,
        n=acquire_counts,
    )
    @settings(max_examples=100)
    def test_プロパティ_available_hourと使用数の合計が制限数(
        self,
        per_minute: int,
        per_hour: int,
        n: int,
    ) -> None:
        """available_hour + 時ウィンドウ内のリクエスト数 == requests_per_hour。"""
        per_hour = max(per_hour, per_minute)
        safe_n = min(n, per_minute, per_hour)

        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=per_hour,
        )
        for _ in range(safe_n):
            limiter.acquire()

        # 全タイムスタンプは1時間以内（テスト実行は瞬時）なので
        # available_hour + safe_n == per_hour
        assert limiter.available_hour + safe_n == per_hour
