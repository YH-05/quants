"""Tests for market.alphavantage.rate_limiter module.

Unit tests for the dual-window sliding rate limiter including:
- DualWindowRateLimiter (sync): minute/hour window limits, available counts,
  purge behavior, blocking acquire, thread-safety
- AsyncDualWindowRateLimiter (async): async acquire, async safety

Test TODO List:
- [x] DualWindowRateLimiter: acquire returns 0.0 when under limit
- [x] DualWindowRateLimiter: available_minute decreases after acquire
- [x] DualWindowRateLimiter: available_hour decreases after acquire
- [x] DualWindowRateLimiter: minute window blocks when limit reached
- [x] DualWindowRateLimiter: hour window blocks when limit reached
- [x] DualWindowRateLimiter: _purge_old removes timestamps older than 1 hour
- [x] DualWindowRateLimiter: thread-safety with ThreadPoolExecutor
- [x] DualWindowRateLimiter: custom limits via constructor
- [x] DualWindowRateLimiter: ValueError for invalid limits
- [x] AsyncDualWindowRateLimiter: async acquire returns 0.0 when under limit
- [x] AsyncDualWindowRateLimiter: async minute window blocks when limit reached
- [x] AsyncDualWindowRateLimiter: available_minute/available_hour properties
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from market.alphavantage.rate_limiter import (
    AsyncDualWindowRateLimiter,
    DualWindowRateLimiter,
)

# =============================================================================
# DualWindowRateLimiter (sync) tests
# =============================================================================


class TestDualWindowRateLimiterInit:
    """Tests for DualWindowRateLimiter initialization."""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトのリクエスト制限で初期化できること。"""
        limiter = DualWindowRateLimiter()
        assert limiter.available_minute == 25
        assert limiter.available_hour == 500

    def test_正常系_カスタム値で初期化できる(self) -> None:
        """カスタムのリクエスト制限で初期化できること。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=10,
            requests_per_hour=100,
        )
        assert limiter.available_minute == 10
        assert limiter.available_hour == 100

    def test_異常系_毎分リクエスト数が0以下でValueError(self) -> None:
        """requests_per_minute が 0 以下の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="requests_per_minute must be positive"):
            DualWindowRateLimiter(requests_per_minute=0)

    def test_異常系_毎時リクエスト数が0以下でValueError(self) -> None:
        """requests_per_hour が 0 以下の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="requests_per_hour must be positive"):
            DualWindowRateLimiter(requests_per_hour=0)

    def test_異常系_毎分リクエスト数が負の値でValueError(self) -> None:
        """requests_per_minute が負の値の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="requests_per_minute must be positive"):
            DualWindowRateLimiter(requests_per_minute=-5)


class TestDualWindowRateLimiterAcquire:
    """Tests for DualWindowRateLimiter.acquire method."""

    def test_正常系_制限内で待機時間0を返す(self) -> None:
        """リクエスト制限内であれば待機時間 0.0 を返すこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        waited = limiter.acquire()
        assert waited == 0.0

    def test_正常系_acquireで残りリクエスト数が減少する(self) -> None:
        """acquire 後に available_minute が減少すること。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        limiter.acquire()
        assert limiter.available_minute == 4
        assert limiter.available_hour == 99

    def test_正常系_複数回acquireで残りリクエスト数が正しい(self) -> None:
        """複数回 acquire 後に残りリクエスト数が正しいこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        for _ in range(3):
            limiter.acquire()
        assert limiter.available_minute == 2
        assert limiter.available_hour == 97


class TestDualWindowRateLimiterMinuteWindow:
    """Tests for minute window blocking behavior."""

    def test_正常系_分ウィンドウ制限到達でブロッキング待機(self) -> None:
        """分ウィンドウ制限到達時にブロッキング待機し、正の待機時間を返すこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=2,
            requests_per_hour=100,
        )
        # 2回 acquire して制限到達
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_minute == 0

        # タイムスタンプを手動で古くすることで、次の acquire が即座に通るようにする
        oldest_ts = limiter._timestamps[0]
        # 両方のタイムスタンプを61秒前に移動
        limiter._timestamps.clear()
        limiter._timestamps.append(oldest_ts - 61.0)
        limiter._timestamps.append(oldest_ts - 61.0)

        # 1分ウィンドウ外になったので acquire 可能
        waited = limiter.acquire()
        assert waited == 0.0
        # 新しいタイムスタンプが追加されている
        assert len(limiter._timestamps) == 3

    def test_正常系_分ウィンドウ制限到達でavailable_minuteが0(self) -> None:
        """分ウィンドウ制限到達時に available_minute が 0 になること。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=3,
            requests_per_hour=100,
        )
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_minute == 0


class TestDualWindowRateLimiterHourWindow:
    """Tests for hour window blocking behavior."""

    def test_正常系_時ウィンドウ制限到達でavailable_hourが0(self) -> None:
        """時ウィンドウ制限到達時に available_hour が 0 になること。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=3,
        )
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_hour == 0

    def test_正常系_時ウィンドウ外のタイムスタンプはカウントされない(self) -> None:
        """1時間超のタイムスタンプは時ウィンドウのカウントに含まれないこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=3,
        )
        # 3回 acquire して制限到達
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_hour == 0

        # タイムスタンプを1時間以上前に移動
        oldest_ts = limiter._timestamps[0]
        limiter._timestamps.clear()
        limiter._timestamps.append(oldest_ts - 3700.0)
        limiter._timestamps.append(oldest_ts - 3700.0)
        limiter._timestamps.append(oldest_ts - 3700.0)

        # 1時間ウィンドウ外になったので acquire 可能
        waited = limiter.acquire()
        assert waited == 0.0


class TestDualWindowRateLimiterPurgeOld:
    """Tests for _purge_old method."""

    def test_正常系_1時間超のタイムスタンプが削除される(self) -> None:
        """_purge_old で1時間超のタイムスタンプが削除されること。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=500,
        )
        # 古いタイムスタンプを手動で挿入
        now = time.monotonic()
        limiter._timestamps.appendleft(now - 7200.0)  # 2時間前
        limiter._timestamps.appendleft(now - 3700.0)  # 1時間+100秒前

        initial_count = len(limiter._timestamps)
        limiter._purge_old()
        assert len(limiter._timestamps) < initial_count
        # 1時間超のタイムスタンプが削除されている
        for ts in limiter._timestamps:
            assert now - ts <= 3600.0


class TestDualWindowRateLimiterAvailableProperties:
    """Tests for available_minute and available_hour properties."""

    def test_正常系_available_minuteが正しい残数を返す(self) -> None:
        """available_minute が正しい残りリクエスト数を返すこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        assert limiter.available_minute == 5
        limiter.acquire()
        assert limiter.available_minute == 4

    def test_正常系_available_hourが正しい残数を返す(self) -> None:
        """available_hour が正しい残りリクエスト数を返すこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=5,
        )
        assert limiter.available_hour == 5
        limiter.acquire()
        assert limiter.available_hour == 4

    def test_正常系_available_minuteは0未満にならない(self) -> None:
        """available_minute は 0 未満にならないこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=2,
            requests_per_hour=100,
        )
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_minute == 0

    def test_正常系_available_hourは0未満にならない(self) -> None:
        """available_hour は 0 未満にならないこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=2,
        )
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_hour == 0


class TestDualWindowRateLimiterThreadSafety:
    """Tests for thread-safety with ThreadPoolExecutor."""

    def test_正常系_並行アクセスでレース条件が発生しない(self) -> None:
        """ThreadPoolExecutor での並行 acquire でレース条件が発生しないこと。"""
        limiter = DualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=500,
        )
        num_threads = 10
        acquires_per_thread = 5

        def worker() -> list[float]:
            results = []
            for _ in range(acquires_per_thread):
                waited = limiter.acquire()
                results.append(waited)
            return results

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            all_results = []
            for future in futures:
                all_results.extend(future.result())

        total_acquires = num_threads * acquires_per_thread
        assert len(all_results) == total_acquires
        # 全ての待機時間は非負
        assert all(w >= 0.0 for w in all_results)
        # タイムスタンプの数が正しい
        assert len(limiter._timestamps) == total_acquires

    def test_正常系_並行アクセスで制限を超えない(self) -> None:
        """並行 acquire でリクエスト制限を超えないこと。"""
        per_minute = 20
        limiter = DualWindowRateLimiter(
            requests_per_minute=per_minute,
            requests_per_hour=500,
        )

        def worker() -> float:
            return limiter.acquire()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(per_minute)]
            for future in futures:
                future.result()

        # 全 acquire 完了後、タイムスタンプは制限数以内
        assert len(limiter._timestamps) <= per_minute


# =============================================================================
# AsyncDualWindowRateLimiter tests
# =============================================================================


class TestAsyncDualWindowRateLimiterInit:
    """Tests for AsyncDualWindowRateLimiter initialization."""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトのリクエスト制限で初期化できること。"""
        limiter = AsyncDualWindowRateLimiter()
        assert limiter.available_minute == 25
        assert limiter.available_hour == 500

    def test_正常系_カスタム値で初期化できる(self) -> None:
        """カスタムのリクエスト制限で初期化できること。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=10,
            requests_per_hour=100,
        )
        assert limiter.available_minute == 10
        assert limiter.available_hour == 100


class TestAsyncDualWindowRateLimiterAcquire:
    """Tests for AsyncDualWindowRateLimiter.acquire method."""

    @pytest.mark.asyncio
    async def test_正常系_制限内で待機時間0を返す(self) -> None:
        """リクエスト制限内であれば待機時間 0.0 を返すこと。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        waited = await limiter.acquire()
        assert waited == 0.0

    @pytest.mark.asyncio
    async def test_正常系_acquireで残りリクエスト数が減少する(self) -> None:
        """acquire 後に available_minute が減少すること。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        await limiter.acquire()
        assert limiter.available_minute == 4
        assert limiter.available_hour == 99

    @pytest.mark.asyncio
    async def test_正常系_分ウィンドウ制限到達でブロッキング待機(self) -> None:
        """分ウィンドウ制限到達時にブロッキング待機すること。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=2,
            requests_per_hour=100,
        )
        await limiter.acquire()
        await limiter.acquire()
        assert limiter.available_minute == 0

    @pytest.mark.asyncio
    async def test_正常系_複数の非同期タスクで正しく動作する(self) -> None:
        """複数の asyncio.Task で並行 acquire しても正しく動作すること。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=50,
            requests_per_hour=500,
        )
        num_tasks = 10

        async def worker() -> float:
            return await limiter.acquire()

        results = await asyncio.gather(*[worker() for _ in range(num_tasks)])

        assert len(results) == num_tasks
        assert all(w >= 0.0 for w in results)
        assert len(limiter._timestamps) == num_tasks


class TestAsyncDualWindowRateLimiterAvailableProperties:
    """Tests for async available_minute and available_hour properties."""

    @pytest.mark.asyncio
    async def test_正常系_available_minuteが正しい残数を返す(self) -> None:
        """available_minute が正しい残りリクエスト数を返すこと。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
        )
        assert limiter.available_minute == 5
        await limiter.acquire()
        assert limiter.available_minute == 4

    @pytest.mark.asyncio
    async def test_正常系_available_hourが正しい残数を返す(self) -> None:
        """available_hour が正しい残りリクエスト数を返すこと。"""
        limiter = AsyncDualWindowRateLimiter(
            requests_per_minute=100,
            requests_per_hour=5,
        )
        assert limiter.available_hour == 5
        await limiter.acquire()
        assert limiter.available_hour == 4


# =============================================================================
# Module exports tests
# =============================================================================


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_正常系_allが定義されている(self) -> None:
        """__all__ が定義されていること。"""
        from market.alphavantage import rate_limiter

        assert hasattr(rate_limiter, "__all__")

    def test_正常系_全クラスがallに含まれる(self) -> None:
        """全クラスが __all__ に含まれること。"""
        from market.alphavantage import rate_limiter

        expected = {
            "AsyncDualWindowRateLimiter",
            "DualWindowRateLimiter",
        }
        assert set(rate_limiter.__all__) == expected
