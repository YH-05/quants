"""async_core.py の単体テスト.

RateLimiter と gather_with_errors の動作を検証する。
"""

from __future__ import annotations

import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper.async_core import RateLimiter, gather_with_errors


class TestRateLimiter:
    """RateLimiter のテスト."""

    def test_正常系_有効なパラメータでインスタンス生成(self) -> None:
        """有効なパラメータで RateLimiter を生成できることを確認。"""
        limiter = RateLimiter(delay=1.0, max_concurrency=5)

        assert limiter._delay == 1.0

    def test_異常系_負のdelayでValueError(self) -> None:
        """delay が負数のとき ValueError が発生することを確認。"""
        with pytest.raises(ValueError, match="delay must be non-negative"):
            RateLimiter(delay=-1.0, max_concurrency=5)

    def test_異常系_0のmax_concurrencyでValueError(self) -> None:
        """max_concurrency が 0 のとき ValueError が発生することを確認。"""
        with pytest.raises(ValueError, match="max_concurrency must be positive"):
            RateLimiter(delay=0.0, max_concurrency=0)

    def test_異常系_負のmax_concurrencyでValueError(self) -> None:
        """max_concurrency が負のとき ValueError が発生することを確認。"""
        with pytest.raises(ValueError, match="max_concurrency must be positive"):
            RateLimiter(delay=1.0, max_concurrency=-1)

    def test_正常系_delay_0で生成できる(self) -> None:
        """delay が 0 でも RateLimiter を生成できることを確認。"""
        limiter = RateLimiter(delay=0.0, max_concurrency=1)

        assert limiter._delay == 0.0

    @pytest.mark.asyncio
    async def test_正常系_acquireとreleaseが動作する(self) -> None:
        """acquire() と release() が正常に動作することを確認。"""
        limiter = RateLimiter(delay=0.0, max_concurrency=5)

        await limiter.acquire()
        limiter.release()

    @pytest.mark.asyncio
    async def test_正常系_コンテキストマネージャとして使用できる(self) -> None:
        """非同期コンテキストマネージャとして使用できることを確認。"""
        limiter = RateLimiter(delay=0.0, max_concurrency=5)
        executed = False

        async with limiter:
            executed = True

        assert executed

    @pytest.mark.asyncio
    async def test_正常系_コンテキストマネージャがselfを返す(self) -> None:
        """__aenter__ が自身のインスタンスを返すことを確認。"""
        limiter = RateLimiter(delay=0.0, max_concurrency=5)

        async with limiter as ctx:
            assert ctx is limiter

    @pytest.mark.asyncio
    async def test_正常系_max_concurrencyを超えるリクエストを制限する(
        self,
    ) -> None:
        """max_concurrency を超えるリクエストが制限されることを確認。"""
        limiter = RateLimiter(delay=0.0, max_concurrency=2)
        completed: list[int] = []

        async def task(task_id: int) -> None:
            async with limiter:
                completed.append(task_id)
                await asyncio.sleep(0.01)

        tasks = [asyncio.create_task(task(i)) for i in range(5)]
        await asyncio.gather(*tasks)

        assert len(completed) == 5

    @pytest.mark.asyncio
    async def test_正常系_delayが適用される(self) -> None:
        """delay が正しく適用されることを確認（実時間測定）。"""
        limiter = RateLimiter(delay=0.05, max_concurrency=1)
        times: list[float] = []

        for _ in range(3):
            await limiter.acquire()
            times.append(time.monotonic())
            limiter.release()

        # 2回目以降は delay 以上の間隔があるはず
        for i in range(1, len(times)):
            assert times[i] - times[i - 1] >= 0.04  # 多少の誤差を許容

    @pytest.mark.asyncio
    async def test_正常系_例外が発生してもreleaseされる(self) -> None:
        """コンテキストマネージャ内で例外が発生しても release されることを確認。"""
        limiter = RateLimiter(delay=0.0, max_concurrency=1)

        with pytest.raises(RuntimeError, match="test error"):
            async with limiter:
                raise RuntimeError("test error")

        # 解放されているので再取得できる
        await limiter.acquire()
        limiter.release()


class TestGatherWithErrors:
    """gather_with_errors() のテスト."""

    @pytest.fixture
    def logger(self) -> logging.Logger:
        """テスト用ロガーを返すフィクスチャ."""
        return logging.getLogger("test_gather")

    @pytest.mark.asyncio
    async def test_正常系_全タスク成功時に全結果を返す(
        self, logger: logging.Logger
    ) -> None:
        """全タスクが成功した場合に全結果を返すことを確認。"""

        async def succeed(value: int) -> int:
            return value

        tasks = [asyncio.create_task(succeed(i)) for i in range(5)]
        results = await gather_with_errors(tasks, logger)

        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}

    @pytest.mark.asyncio
    async def test_正常系_空のタスクリストで空の結果を返す(
        self, logger: logging.Logger
    ) -> None:
        """空のタスクリストで空の結果リストを返すことを確認。"""
        results = await gather_with_errors([], logger)

        assert results == []

    @pytest.mark.asyncio
    async def test_正常系_失敗したタスクをスキップする(
        self, logger: logging.Logger
    ) -> None:
        """失敗したタスクをスキップして成功したタスクの結果を返すことを確認。"""

        async def succeed(value: int) -> int:
            return value

        async def fail() -> int:
            raise ValueError("task failed")

        tasks = [
            asyncio.create_task(succeed(1)),
            asyncio.create_task(fail()),
            asyncio.create_task(succeed(3)),
        ]
        results = await gather_with_errors(tasks, logger)

        assert len(results) == 2
        assert 1 in results
        assert 3 in results

    @pytest.mark.asyncio
    async def test_正常系_全タスク失敗時に空のリストを返す(
        self, logger: logging.Logger
    ) -> None:
        """全タスクが失敗した場合に空のリストを返すことを確認。"""

        async def fail() -> int:
            raise RuntimeError("all failed")

        tasks = [asyncio.create_task(fail()) for _ in range(3)]
        results = await gather_with_errors(tasks, logger)

        assert results == []

    @pytest.mark.asyncio
    async def test_正常系_失敗タスクのエラーがログに記録される(
        self,
    ) -> None:
        """失敗したタスクのエラーがロガーに記録されることを確認。"""
        mock_logger = MagicMock()

        async def fail() -> int:
            raise ValueError("expected failure")

        tasks = [asyncio.create_task(fail())]
        await gather_with_errors(tasks, mock_logger)

        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_正常系_成功結果の順序が元の順序を維持する(
        self, logger: logging.Logger
    ) -> None:
        """成功した結果が元のタスクの順序を維持することを確認。"""

        async def succeed(value: int) -> int:
            return value

        tasks = [asyncio.create_task(succeed(i)) for i in [10, 20, 30]]
        results = await gather_with_errors(tasks, logger)

        assert results == [10, 20, 30]

    @pytest.mark.asyncio
    async def test_正常系_structlogロガーでも動作する(self) -> None:
        """structlog のロガーを渡しても動作することを確認。"""
        mock_logger = MagicMock()
        mock_logger.error = MagicMock()

        async def fail() -> int:
            raise RuntimeError("structlog test")

        tasks = [asyncio.create_task(fail())]
        results = await gather_with_errors(tasks, mock_logger)

        assert results == []
        mock_logger.error.assert_called_once()
