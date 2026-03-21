"""Property-based tests for market.polymarket.types module.

Uses Hypothesis to test boundary conditions and invariants
of PolymarketConfig and RetryConfig dataclasses.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from market.polymarket.types import PolymarketConfig, RetryConfig


class TestPolymarketConfigProperty:
    """Property-based tests for PolymarketConfig."""

    @given(
        timeout=st.floats(min_value=1.0, max_value=300.0, allow_nan=False),
        rate_limit=st.floats(min_value=0.001, max_value=1000.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_プロパティ_有効範囲内のtimeoutとrate_limitで生成成功(
        self,
        timeout: float,
        rate_limit: float,
    ) -> None:
        config = PolymarketConfig(timeout=timeout, rate_limit_per_second=rate_limit)
        assert config.timeout == timeout
        assert config.rate_limit_per_second == rate_limit

    @given(
        timeout=st.floats(max_value=0.99, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_プロパティ_timeoutが下限未満でValueError(
        self,
        timeout: float,
    ) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            PolymarketConfig(timeout=timeout)

    @given(
        timeout=st.floats(
            min_value=300.01, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=20)
    def test_プロパティ_timeoutが上限超過でValueError(
        self,
        timeout: float,
    ) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            PolymarketConfig(timeout=timeout)

    @given(
        rate_limit=st.floats(max_value=0.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_プロパティ_rate_limitが0以下でValueError(
        self,
        rate_limit: float,
    ) -> None:
        with pytest.raises(ValueError, match="rate_limit_per_second must be positive"):
            PolymarketConfig(rate_limit_per_second=rate_limit)

    @given(
        timeout=st.floats(min_value=1.0, max_value=300.0, allow_nan=False),
    )
    @settings(max_examples=20)
    def test_プロパティ_frozen属性は変更不可(
        self,
        timeout: float,
    ) -> None:
        config = PolymarketConfig(timeout=timeout)
        with pytest.raises(AttributeError):
            config.timeout = timeout + 1.0  # type: ignore[misc]


class TestRetryConfigProperty:
    """Property-based tests for RetryConfig."""

    @given(
        max_attempts=st.integers(min_value=1, max_value=10),
        base_wait=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
        max_wait=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_プロパティ_有効範囲内のパラメータで生成成功(
        self,
        max_attempts: int,
        base_wait: float,
        max_wait: float,
    ) -> None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_wait=base_wait,
            max_wait=max_wait,
        )
        assert config.max_attempts == max_attempts
        assert config.base_wait == base_wait
        assert config.max_wait == max_wait

    @given(
        max_attempts=st.integers(max_value=0),
    )
    @settings(max_examples=20)
    def test_プロパティ_max_attemptsが下限未満でValueError(
        self,
        max_attempts: int,
    ) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=max_attempts)

    @given(
        max_attempts=st.integers(min_value=11, max_value=100),
    )
    @settings(max_examples=20)
    def test_プロパティ_max_attemptsが上限超過でValueError(
        self,
        max_attempts: int,
    ) -> None:
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=max_attempts)

    @given(
        base_wait=st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_プロパティ_base_waitが負数でValueError(
        self,
        base_wait: float,
    ) -> None:
        with pytest.raises(ValueError, match="base_wait must be non-negative"):
            RetryConfig(base_wait=base_wait)

    @given(
        max_wait=st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_プロパティ_max_waitが負数でValueError(
        self,
        max_wait: float,
    ) -> None:
        with pytest.raises(ValueError, match="max_wait must be non-negative"):
            RetryConfig(max_wait=max_wait)
