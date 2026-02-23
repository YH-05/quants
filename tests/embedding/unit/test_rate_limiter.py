"""embedding.rate_limiter モジュールの単体テスト.

テストTODOリスト:
- [x] RateLimiter: デフォルト値で作成できること
- [x] RateLimiter: カスタム値で作成できること
- [x] RateLimiter: max_concurrent が 0 以下で ValueError
- [x] RateLimiter: delay_seconds が負で ValueError
- [x] RateLimiter: async context manager として使用できること
- [x] RateLimiter: 同時実行数を制御すること
- [x] RateLimiter: delay_seconds=0 で待機なしで動作すること
- [x] RateLimiter: 例外発生時もセマフォが解放されること
"""

import asyncio
import time

import pytest

from embedding.rate_limiter import RateLimiter


class TestRateLimiterInit:
    """RateLimiter 初期化のテスト."""

    def test_正常系_デフォルト値で作成できる(self) -> None:
        """デフォルト値で RateLimiter を作成できることを確認。"""
        limiter = RateLimiter()

        assert limiter.max_concurrent == 5
        assert limiter.delay_seconds == 1.0

    def test_正常系_カスタム値で作成できる(self) -> None:
        """カスタム値で RateLimiter を作成できることを確認。"""
        limiter = RateLimiter(max_concurrent=3, delay_seconds=0.5)

        assert limiter.max_concurrent == 3
        assert limiter.delay_seconds == 0.5

    def test_異常系_max_concurrentが0でValueError(self) -> None:
        """max_concurrent が 0 の場合 ValueError が発生することを確認。"""
        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            RateLimiter(max_concurrent=0)

    def test_異常系_max_concurrentが負でValueError(self) -> None:
        """max_concurrent が負の場合 ValueError が発生することを確認。"""
        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            RateLimiter(max_concurrent=-1)

    def test_異常系_delay_secondsが負でValueError(self) -> None:
        """delay_seconds が負の場合 ValueError が発生することを確認。"""
        with pytest.raises(ValueError, match="delay_seconds must be >= 0"):
            RateLimiter(delay_seconds=-0.1)

    def test_正常系_delay_secondsが0で作成できる(self) -> None:
        """delay_seconds が 0 で RateLimiter を作成できることを確認。"""
        limiter = RateLimiter(delay_seconds=0)
        assert limiter.delay_seconds == 0.0

    def test_正常系_max_concurrentが1で作成できる(self) -> None:
        """max_concurrent が 1 で RateLimiter を作成できることを確認。"""
        limiter = RateLimiter(max_concurrent=1)
        assert limiter.max_concurrent == 1


class TestRateLimiterContextManager:
    """RateLimiter async context manager のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_async_context_managerとして使用できる(self) -> None:
        """async context manager として使用できることを確認。"""
        limiter = RateLimiter(max_concurrent=2, delay_seconds=0)
        result = []

        async with limiter:
            result.append("inside")

        assert result == ["inside"]

    @pytest.mark.asyncio
    async def test_正常系_複数回使用できる(self) -> None:
        """複数回 context manager を使用できることを確認。"""
        limiter = RateLimiter(max_concurrent=2, delay_seconds=0)
        count = 0

        for _ in range(3):
            async with limiter:
                count += 1

        assert count == 3

    @pytest.mark.asyncio
    async def test_正常系_同時実行数を制御する(self) -> None:
        """max_concurrent が同時実行数を制御することを確認。"""
        max_concurrent = 2
        limiter = RateLimiter(max_concurrent=max_concurrent, delay_seconds=0)
        concurrent_count = 0
        max_seen = 0

        async def task() -> None:
            nonlocal concurrent_count, max_seen
            async with limiter:
                concurrent_count += 1
                max_seen = max(max_seen, concurrent_count)
                await asyncio.sleep(0.01)
                concurrent_count -= 1

        tasks = [asyncio.create_task(task()) for _ in range(5)]
        await asyncio.gather(*tasks)

        assert max_seen <= max_concurrent

    @pytest.mark.asyncio
    async def test_正常系_delay_seconds_0で待機なしで動作する(self) -> None:
        """delay_seconds が 0 の場合、待機なしで動作することを確認。"""
        limiter = RateLimiter(max_concurrent=5, delay_seconds=0)
        start = time.monotonic()

        async def quick_task() -> None:
            async with limiter:
                pass

        tasks = [asyncio.create_task(quick_task()) for _ in range(5)]
        await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start
        # 待機なしなので 0.5 秒以内に完了するはず
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_正常系_例外発生時もセマフォが解放される(self) -> None:
        """例外発生時もセマフォが解放されることを確認。"""
        limiter = RateLimiter(max_concurrent=1, delay_seconds=0)

        with pytest.raises(RuntimeError, match="test error"):
            async with limiter:
                raise RuntimeError("test error")

        # セマフォが解放されているので、次の操作が正常に実行できる
        result = []
        async with limiter:
            result.append("success after exception")

        assert result == ["success after exception"]

    @pytest.mark.asyncio
    async def test_正常系_全タスクが完了する(self) -> None:
        """全てのタスクが完了することを確認。"""
        limiter = RateLimiter(max_concurrent=3, delay_seconds=0)
        completed = []

        async def task(n: int) -> None:
            async with limiter:
                await asyncio.sleep(0)
                completed.append(n)

        tasks = [asyncio.create_task(task(i)) for i in range(10)]
        await asyncio.gather(*tasks)

        assert len(completed) == 10
        assert sorted(completed) == list(range(10))
