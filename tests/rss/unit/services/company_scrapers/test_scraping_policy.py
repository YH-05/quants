"""Unit tests for ScrapingPolicy (UA rotation, rate limiting, 429 retry).

Tests cover:
- UA rotation with previous-UA avoidance
- Domain-based rate limiting with asyncio.Lock mutual exclusion
- 429 retry with Retry-After header + exponential backoff (2->4->8s)
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rss.services.company_scrapers.scraping_policy import (
    DEFAULT_USER_AGENTS,
    ScrapingPolicy,
)

# ---------------------------------------------------------------------------
# UA Rotation
# ---------------------------------------------------------------------------


class TestUARotation:
    """Tests for User-Agent rotation with previous-UA avoidance."""

    def test_正常系_デフォルトUAリストが7種ある(self) -> None:
        assert len(DEFAULT_USER_AGENTS) == 7

    def test_正常系_デフォルトUAリストにChrome_Firefox_Edge_Safariが含まれる(
        self,
    ) -> None:
        ua_text = " ".join(DEFAULT_USER_AGENTS)
        assert "Chrome" in ua_text
        assert "Firefox" in ua_text
        assert "Edg" in ua_text
        assert "Safari" in ua_text

    def test_正常系_get_user_agentがUA文字列を返す(self) -> None:
        policy = ScrapingPolicy()
        ua = policy.get_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 0

    def test_正常系_連続呼び出しで直前UAと異なるUAを返す(self) -> None:
        policy = ScrapingPolicy()
        previous = policy.get_user_agent()
        for _ in range(20):
            current = policy.get_user_agent()
            assert current != previous, (
                f"UA should differ from previous: got {current!r} twice in a row"
            )
            previous = current

    def test_正常系_カスタムUAリストを指定できる(self) -> None:
        custom_uas = ["UA-A", "UA-B", "UA-C"]
        policy = ScrapingPolicy(user_agents=custom_uas)
        ua = policy.get_user_agent()
        assert ua in custom_uas

    def test_異常系_UAリストが1件の場合でもエラーにならない(self) -> None:
        policy = ScrapingPolicy(user_agents=["OnlyOne"])
        ua = policy.get_user_agent()
        assert ua == "OnlyOne"

    def test_異常系_空のUAリストでValueError(self) -> None:
        with pytest.raises(ValueError, match="user_agents must not be empty"):
            ScrapingPolicy(user_agents=[])

    def test_正常系_全UAが使われる(self) -> None:
        custom_uas = ["UA-1", "UA-2", "UA-3"]
        policy = ScrapingPolicy(user_agents=custom_uas)
        seen: set[str] = set()
        for _ in range(100):
            seen.add(policy.get_user_agent())
        assert seen == set(custom_uas)


# ---------------------------------------------------------------------------
# Domain Rate Limiting
# ---------------------------------------------------------------------------


class TestDomainRateLimiting:
    """Tests for domain-based rate limiting with asyncio.Lock."""

    @pytest.mark.asyncio
    async def test_正常系_異なるドメインで独立したロックが使われる(self) -> None:
        policy = ScrapingPolicy(
            domain_rate_limits={"a.com": 0.0, "b.com": 0.0},
        )
        # Both should acquire without blocking
        async with policy.domain_lock("a.com"):
            pass
        async with policy.domain_lock("b.com"):
            pass

    @pytest.mark.asyncio
    async def test_正常系_同一ドメインで排他制御される(self) -> None:
        policy = ScrapingPolicy(
            domain_rate_limits={"example.com": 0.0},
        )
        order: list[str] = []

        async def task(name: str) -> None:
            async with policy.domain_lock("example.com"):
                order.append(f"{name}_start")
                await asyncio.sleep(0.05)
                order.append(f"{name}_end")

        await asyncio.gather(task("A"), task("B"))
        # One must complete before the other starts
        assert order[0].endswith("_start")
        assert order[1].endswith("_end")
        assert order[2].endswith("_start")
        assert order[3].endswith("_end")

    @pytest.mark.asyncio
    async def test_正常系_デフォルトレートリミットが適用される(self) -> None:
        default_limit = 0.1
        policy = ScrapingPolicy(default_rate_limit=default_limit)
        start = time.monotonic()
        await policy.wait_for_domain("unknown-domain.com")
        await policy.wait_for_domain("unknown-domain.com")
        elapsed = time.monotonic() - start
        # Second call should wait at least default_limit seconds
        assert elapsed >= default_limit * 0.9  # Allow 10% tolerance

    @pytest.mark.asyncio
    async def test_正常系_ドメイン別レートリミットが適用される(self) -> None:
        policy = ScrapingPolicy(
            domain_rate_limits={"slow.com": 0.15},
            default_rate_limit=0.0,
        )
        start = time.monotonic()
        await policy.wait_for_domain("slow.com")
        await policy.wait_for_domain("slow.com")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15 * 0.9

    @pytest.mark.asyncio
    async def test_正常系_初回リクエストは待機なし(self) -> None:
        policy = ScrapingPolicy(default_rate_limit=1.0)
        start = time.monotonic()
        await policy.wait_for_domain("first-time.com")
        elapsed = time.monotonic() - start
        # First request should not wait
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_正常系_異なるドメインは独立してレートリミットされる(self) -> None:
        policy = ScrapingPolicy(default_rate_limit=0.2)
        await policy.wait_for_domain("a.com")
        await policy.wait_for_domain("b.com")
        # b.com is first request, should not wait
        start = time.monotonic()
        await policy.wait_for_domain("b.com")
        elapsed_b = time.monotonic() - start
        assert elapsed_b >= 0.2 * 0.9


# ---------------------------------------------------------------------------
# 429 Retry
# ---------------------------------------------------------------------------


class TestRetry429:
    """Tests for 429 retry with Retry-After + exponential backoff."""

    @pytest.mark.asyncio
    async def test_正常系_成功レスポンスでリトライなし(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        request_fn = AsyncMock(return_value=mock_response)
        policy = ScrapingPolicy()

        result = await policy.execute_with_retry(request_fn, "https://example.com/page")
        assert result == mock_response
        assert request_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_正常系_429後にリトライで成功(self) -> None:
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}

        request_fn = AsyncMock(side_effect=[response_429, response_200])
        policy = ScrapingPolicy(base_backoff=0.01)

        result = await policy.execute_with_retry(request_fn, "https://example.com/page")
        assert result.status_code == 200
        assert request_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_正常系_Retry_Afterヘッダが尊重される(self) -> None:
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {"Retry-After": "0.05"}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}

        request_fn = AsyncMock(side_effect=[response_429, response_200])
        policy = ScrapingPolicy(base_backoff=0.01)

        start = time.monotonic()
        result = await policy.execute_with_retry(request_fn, "https://example.com/page")
        elapsed = time.monotonic() - start

        assert result.status_code == 200
        assert elapsed >= 0.04  # Allow tolerance

    @pytest.mark.asyncio
    async def test_正常系_指数バックオフが適用される(self) -> None:
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}

        # 3 failures then success
        request_fn = AsyncMock(
            side_effect=[response_429, response_429, response_429, response_200],
        )
        policy = ScrapingPolicy(base_backoff=0.01, max_retries=3)

        start = time.monotonic()
        result = await policy.execute_with_retry(request_fn, "https://example.com/page")
        elapsed = time.monotonic() - start

        assert result.status_code == 200
        assert request_fn.call_count == 4
        # Backoff: 0.01 + 0.02 + 0.04 = 0.07
        assert elapsed >= 0.06  # Allow tolerance

    @pytest.mark.asyncio
    async def test_異常系_最大リトライ回数超過でRateLimitError(self) -> None:
        from rss.services.company_scrapers.types import RateLimitError

        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {}

        request_fn = AsyncMock(return_value=response_429)
        policy = ScrapingPolicy(base_backoff=0.01, max_retries=3)

        with pytest.raises(RateLimitError, match=r"Max retries.*exceeded"):
            await policy.execute_with_retry(request_fn, "https://example.com/page")

        # Initial + 3 retries = 4 calls
        assert request_fn.call_count == 4

    @pytest.mark.asyncio
    async def test_正常系_デフォルトmax_retriesが3(self) -> None:
        policy = ScrapingPolicy()
        assert policy.max_retries == 3

    @pytest.mark.asyncio
    async def test_正常系_デフォルトbase_backoffが2秒(self) -> None:
        policy = ScrapingPolicy()
        assert policy.base_backoff == 2.0

    @pytest.mark.asyncio
    async def test_正常系_Retry_Afterが整数文字列でもパースされる(self) -> None:
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {"Retry-After": "1"}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}

        request_fn = AsyncMock(side_effect=[response_429, response_200])
        policy = ScrapingPolicy(base_backoff=0.01)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await policy.execute_with_retry(request_fn, "https://example.com/page")
            # Should use Retry-After value (1.0) not base_backoff
            mock_sleep.assert_called_once()
            actual_sleep = mock_sleep.call_args[0][0]
            assert actual_sleep == pytest.approx(1.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_正常系_非429エラーステータスはリトライしない(self) -> None:
        response_500 = MagicMock()
        response_500.status_code = 500
        response_500.headers = {}

        request_fn = AsyncMock(return_value=response_500)
        policy = ScrapingPolicy(base_backoff=0.01)

        result = await policy.execute_with_retry(request_fn, "https://example.com/page")
        assert result.status_code == 500
        assert request_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_正常系_urlからドメインが抽出される(self) -> None:
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {}

        request_fn = AsyncMock(return_value=response_429)
        policy = ScrapingPolicy(base_backoff=0.01, max_retries=0)

        from rss.services.company_scrapers.types import RateLimitError

        with pytest.raises(RateLimitError) as exc_info:
            await policy.execute_with_retry(
                request_fn,
                "https://api.example.com/v1/data",
            )
        assert exc_info.value.domain == "api.example.com"
        assert exc_info.value.url == "https://api.example.com/v1/data"


# ---------------------------------------------------------------------------
# Integration / Combined behavior
# ---------------------------------------------------------------------------


class TestScrapingPolicyIntegration:
    """Tests for combined ScrapingPolicy behavior."""

    def test_正常系_デフォルトパラメータで初期化できる(self) -> None:
        policy = ScrapingPolicy()
        assert policy.max_retries == 3
        assert policy.base_backoff == 2.0
        assert len(policy.user_agents) == 7

    def test_正常系_全パラメータを指定して初期化できる(self) -> None:
        policy = ScrapingPolicy(
            user_agents=["UA1", "UA2"],
            domain_rate_limits={"a.com": 1.0},
            default_rate_limit=0.5,
            max_retries=5,
            base_backoff=1.0,
        )
        assert len(policy.user_agents) == 2
        assert policy.max_retries == 5
        assert policy.base_backoff == 1.0

    @pytest.mark.asyncio
    async def test_正常系_wait_for_domainとdomain_lockが連携する(self) -> None:
        policy = ScrapingPolicy(
            domain_rate_limits={"example.com": 0.0},
        )
        async with policy.domain_lock("example.com"):
            await policy.wait_for_domain("example.com")
        # Should complete without error

    @pytest.mark.asyncio
    async def test_正常系_Retry_Afterヘッダの不正値はフォールバック(self) -> None:
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {"Retry-After": "invalid"}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}

        request_fn = AsyncMock(side_effect=[response_429, response_200])
        policy = ScrapingPolicy(base_backoff=0.01)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await policy.execute_with_retry(
                request_fn, "https://example.com/page"
            )
            assert result.status_code == 200
            # Should fall back to base_backoff
            mock_sleep.assert_called_once()
            actual_sleep = mock_sleep.call_args[0][0]
            assert actual_sleep == pytest.approx(0.01, abs=0.005)
