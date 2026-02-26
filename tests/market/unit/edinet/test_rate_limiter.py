"""Tests for market.edinet.rate_limiter module.

Verifies that DailyRateLimiter correctly manages daily API call counting,
JSON persistence, date-based reset, and safety margin calculations
as specified in Issue #3672.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from market.edinet.rate_limiter import DailyRateLimiter

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    """Provide a temporary path for the rate limit state file.

    Returns
    -------
    Path
        Path to a temporary ``_rate_limit.json`` file.
    """
    return tmp_path / "_rate_limit.json"


@pytest.fixture
def limiter(state_path: Path) -> DailyRateLimiter:
    """Create a DailyRateLimiter with default settings.

    Returns
    -------
    DailyRateLimiter
        Limiter with daily_limit=1000, safe_margin=50.
    """
    return DailyRateLimiter(state_path=state_path)


@pytest.fixture
def small_limiter(state_path: Path) -> DailyRateLimiter:
    """Create a DailyRateLimiter with a small limit for edge case testing.

    Returns
    -------
    DailyRateLimiter
        Limiter with daily_limit=5, safe_margin=1.
    """
    return DailyRateLimiter(
        state_path=state_path,
        daily_limit=5,
        safe_margin=1,
    )


# ---------------------------------------------------------------------------
# TestDailyRateLimiterInit
# ---------------------------------------------------------------------------


class TestDailyRateLimiterInit:
    """DailyRateLimiter の初期化テスト。"""

    def test_正常系_デフォルト値で初期化できること(self, state_path: Path) -> None:
        limiter = DailyRateLimiter(state_path=state_path)
        assert limiter.daily_limit == 1000
        assert limiter.safe_margin == 50

    def test_正常系_カスタム値で初期化できること(self, state_path: Path) -> None:
        limiter = DailyRateLimiter(
            state_path=state_path,
            daily_limit=500,
            safe_margin=25,
        )
        assert limiter.daily_limit == 500
        assert limiter.safe_margin == 25

    def test_正常系_既存の状態ファイルから復元できること(
        self, state_path: Path
    ) -> None:
        today = date.today().isoformat()
        state_path.write_text(
            json.dumps({"date": today, "calls": 42}),
            encoding="utf-8",
        )
        limiter = DailyRateLimiter(state_path=state_path)
        assert limiter.get_remaining() == 1000 - 50 - 42

    def test_正常系_状態ファイルが存在しない場合カウント0で初期化されること(
        self, state_path: Path
    ) -> None:
        assert not state_path.exists()
        limiter = DailyRateLimiter(state_path=state_path)
        assert limiter.get_remaining() == 1000 - 50


# ---------------------------------------------------------------------------
# TestRecordCall
# ---------------------------------------------------------------------------


class TestRecordCall:
    """record_call() のテスト。"""

    def test_正常系_カウントが1増加すること(self, limiter: DailyRateLimiter) -> None:
        initial = limiter.get_remaining()
        limiter.record_call()
        assert limiter.get_remaining() == initial - 1

    def test_正常系_複数回呼び出しで正しくカウントされること(
        self, limiter: DailyRateLimiter
    ) -> None:
        for _ in range(5):
            limiter.record_call()
        assert limiter.get_remaining() == 1000 - 50 - 5

    def test_正常系_flush後にJSONファイルに書き込まれること(
        self, limiter: DailyRateLimiter, state_path: Path
    ) -> None:
        limiter.record_call()
        limiter.flush()
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["calls"] == 1
        assert data["date"] == date.today().isoformat()

    def test_正常系_flush後にJSONファイルのカウントが更新されること(
        self, limiter: DailyRateLimiter, state_path: Path
    ) -> None:
        limiter.record_call()
        limiter.record_call()
        limiter.record_call()
        limiter.flush()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["calls"] == 3


# ---------------------------------------------------------------------------
# TestGetRemaining
# ---------------------------------------------------------------------------


class TestGetRemaining:
    """get_remaining() のテスト。"""

    def test_正常系_初期状態でdaily_limitマイナスsafe_marginを返すこと(
        self, limiter: DailyRateLimiter
    ) -> None:
        assert limiter.get_remaining() == 950

    def test_正常系_コール後に正しい残数を返すこと(
        self, limiter: DailyRateLimiter
    ) -> None:
        for _ in range(10):
            limiter.record_call()
        assert limiter.get_remaining() == 940

    def test_正常系_カスタムlimitとmarginで正しく計算されること(
        self, state_path: Path
    ) -> None:
        limiter = DailyRateLimiter(
            state_path=state_path,
            daily_limit=100,
            safe_margin=10,
        )
        assert limiter.get_remaining() == 90

    def test_エッジケース_全コール消費後に0を返すこと(
        self, small_limiter: DailyRateLimiter
    ) -> None:
        # small_limiter: daily_limit=5, safe_margin=1 -> effective=4
        for _ in range(4):
            small_limiter.record_call()
        assert small_limiter.get_remaining() == 0

    def test_エッジケース_超過時に負の値を返さず0を返すこと(
        self, small_limiter: DailyRateLimiter
    ) -> None:
        # Record more calls than effective limit
        for _ in range(10):
            small_limiter.record_call()
        assert small_limiter.get_remaining() == 0


# ---------------------------------------------------------------------------
# TestIsAllowed
# ---------------------------------------------------------------------------


class TestIsAllowed:
    """is_allowed() のテスト。"""

    def test_正常系_残数がある場合Trueを返すこと(
        self, limiter: DailyRateLimiter
    ) -> None:
        assert limiter.is_allowed() is True

    def test_正常系_残数が0の場合Falseを返すこと(
        self, small_limiter: DailyRateLimiter
    ) -> None:
        # small_limiter: effective=4
        for _ in range(4):
            small_limiter.record_call()
        assert small_limiter.is_allowed() is False

    def test_正常系_残数が1の場合Trueを返すこと(
        self, small_limiter: DailyRateLimiter
    ) -> None:
        # small_limiter: effective=4, consume 3
        for _ in range(3):
            small_limiter.record_call()
        assert small_limiter.is_allowed() is True


# ---------------------------------------------------------------------------
# TestResetIfNewDay
# ---------------------------------------------------------------------------


class TestResetIfNewDay:
    """reset_if_new_day() のテスト。"""

    def test_正常系_日付変更でカウンターがリセットされること(
        self, limiter: DailyRateLimiter, state_path: Path
    ) -> None:
        # Record some calls
        for _ in range(10):
            limiter.record_call()
        assert limiter.get_remaining() == 940

        # Write state with yesterday's date
        state_path.write_text(
            json.dumps({"date": "2020-01-01", "calls": 10}),
            encoding="utf-8",
        )

        # Reload and reset
        limiter2 = DailyRateLimiter(state_path=state_path)
        limiter2.reset_if_new_day()
        assert limiter2.get_remaining() == 950

    def test_正常系_同日ではリセットされないこと(
        self, limiter: DailyRateLimiter
    ) -> None:
        for _ in range(10):
            limiter.record_call()
        limiter.reset_if_new_day()
        assert limiter.get_remaining() == 940

    def test_正常系_日付変更後にJSONファイルが更新されること(
        self, state_path: Path
    ) -> None:
        # Write state with yesterday's date
        state_path.write_text(
            json.dumps({"date": "2020-01-01", "calls": 500}),
            encoding="utf-8",
        )
        limiter = DailyRateLimiter(state_path=state_path)
        limiter.reset_if_new_day()

        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["date"] == date.today().isoformat()
        assert data["calls"] == 0

    def test_正常系_リセット後にis_allowedがTrueを返すこと(
        self, state_path: Path
    ) -> None:
        # Exhaust all calls with yesterday's date
        state_path.write_text(
            json.dumps({"date": "2020-01-01", "calls": 1000}),
            encoding="utf-8",
        )
        limiter = DailyRateLimiter(state_path=state_path)
        limiter.reset_if_new_day()
        assert limiter.is_allowed() is True


# ---------------------------------------------------------------------------
# TestPersistence
# ---------------------------------------------------------------------------


class TestPersistence:
    """永続化のテスト。"""

    def test_正常系_新しいインスタンスで状態が復元されること(
        self, state_path: Path
    ) -> None:
        limiter1 = DailyRateLimiter(state_path=state_path)
        for _ in range(15):
            limiter1.record_call()
        limiter1.flush()

        # Create a new instance from the same state file
        limiter2 = DailyRateLimiter(state_path=state_path)
        assert limiter2.get_remaining() == 1000 - 50 - 15

    def test_正常系_JSONスキーマが正しいこと(
        self, limiter: DailyRateLimiter, state_path: Path
    ) -> None:
        limiter.record_call()
        limiter.flush()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"date", "calls"}
        assert isinstance(data["date"], str)
        assert isinstance(data["calls"], int)

    def test_エッジケース_壊れたJSONファイルで新規初期化されること(
        self, state_path: Path
    ) -> None:
        state_path.write_text("not valid json{{{", encoding="utf-8")
        limiter = DailyRateLimiter(state_path=state_path)
        assert limiter.get_remaining() == 950

    def test_エッジケース_空のJSONファイルで新規初期化されること(
        self, state_path: Path
    ) -> None:
        state_path.write_text("", encoding="utf-8")
        limiter = DailyRateLimiter(state_path=state_path)
        assert limiter.get_remaining() == 950

    def test_エッジケース_不完全なJSONスキーマで新規初期化されること(
        self, state_path: Path
    ) -> None:
        state_path.write_text(
            json.dumps({"date": "2026-01-01"}),  # "calls" missing
            encoding="utf-8",
        )
        limiter = DailyRateLimiter(state_path=state_path)
        assert limiter.get_remaining() == 950


# ---------------------------------------------------------------------------
# TestModuleExports
# ---------------------------------------------------------------------------


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_DailyRateLimiterがエクスポートされていること(self) -> None:
        import market.edinet.rate_limiter as mod

        assert "DailyRateLimiter" in mod.__all__
