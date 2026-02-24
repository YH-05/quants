"""Tests for ca_strategy pit module (Point-in-Time management).

Validates PoiT (Point-in-Time) management functions that prevent
survivorship bias and look-ahead bias by enforcing cutoff_date filtering.
"""

from __future__ import annotations

from datetime import date

import pytest

from dev.ca_strategy.pit import (
    CUTOFF_DATE,
    EVALUATION_END_DATE,
    PORTFOLIO_DATE,
    filter_by_pit,
    get_pit_prompt_context,
    validate_pit_compliance,
)
from dev.ca_strategy.types import (
    Transcript,
    TranscriptMetadata,
    TranscriptSection,
)


def _make_transcript(ticker: str, event_date: date) -> Transcript:
    """Helper to create a Transcript with minimal valid data."""
    section = TranscriptSection(
        speaker="CEO",
        role="CEO",
        section_type="prepared_remarks",
        content="Great quarter results.",
    )
    metadata = TranscriptMetadata(
        ticker=ticker,
        event_date=event_date,
        fiscal_quarter="Q1 2015",
    )
    return Transcript(
        metadata=metadata,
        sections=[section],
        raw_source=None,
    )


# =============================================================================
# CUTOFF_DATE constant
# =============================================================================
class TestCutoffDate:
    """CUTOFF_DATE constant tests."""

    def test_正常系_CUTOFF_DATEが2015年9月30日である(self) -> None:
        assert date(2015, 9, 30) == CUTOFF_DATE

    def test_正常系_CUTOFF_DATEがdate型である(self) -> None:
        assert isinstance(CUTOFF_DATE, date)


# =============================================================================
# PORTFOLIO_DATE constant
# =============================================================================
class TestPortfolioDate:
    """PORTFOLIO_DATE constant tests."""

    def test_正常系_PORTFOLIO_DATEが2015年12月31日である(self) -> None:
        assert date(2015, 12, 31) == PORTFOLIO_DATE

    def test_正常系_PORTFOLIO_DATEがdate型である(self) -> None:
        assert isinstance(PORTFOLIO_DATE, date)


# =============================================================================
# EVALUATION_END_DATE constant
# =============================================================================
class TestEvaluationEndDate:
    """EVALUATION_END_DATE constant tests."""

    def test_正常系_EVALUATION_END_DATEが2026年2月28日である(self) -> None:
        assert date(2026, 2, 28) == EVALUATION_END_DATE

    def test_正常系_EVALUATION_END_DATEがdate型である(self) -> None:
        assert isinstance(EVALUATION_END_DATE, date)


# =============================================================================
# Date ordering
# =============================================================================
class TestDateOrdering:
    """Date constant ordering tests."""

    def test_正常系_CUTOFF_DATEがPORTFOLIO_DATEより前(self) -> None:
        assert CUTOFF_DATE < PORTFOLIO_DATE

    def test_正常系_PORTFOLIO_DATEがEVALUATION_END_DATEより前(self) -> None:
        assert PORTFOLIO_DATE < EVALUATION_END_DATE

    def test_正常系_3定数の順序が成立する(self) -> None:
        assert CUTOFF_DATE < PORTFOLIO_DATE < EVALUATION_END_DATE


# =============================================================================
# filter_by_pit
# =============================================================================
class TestFilterByPit:
    """filter_by_pit function tests."""

    def test_正常系_cutoff_date以前のトランスクリプトのみ返す(self) -> None:
        cutoff = date(2015, 9, 30)
        t_before = _make_transcript("AAPL", date(2015, 6, 15))
        t_on = _make_transcript("MSFT", date(2015, 9, 30))
        t_after = _make_transcript("GOOG", date(2015, 10, 1))

        result = filter_by_pit([t_before, t_on, t_after], cutoff)

        assert len(result) == 2
        tickers = [t.metadata.ticker for t in result]
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert "GOOG" not in tickers

    def test_正常系_全てcutoff_date以前なら全て返す(self) -> None:
        cutoff = date(2015, 9, 30)
        transcripts = [
            _make_transcript("AAPL", date(2015, 1, 1)),
            _make_transcript("MSFT", date(2015, 6, 15)),
        ]

        result = filter_by_pit(transcripts, cutoff)

        assert len(result) == 2

    def test_正常系_全てcutoff_date後なら空リスト(self) -> None:
        cutoff = date(2015, 9, 30)
        transcripts = [
            _make_transcript("AAPL", date(2015, 10, 1)),
            _make_transcript("MSFT", date(2016, 1, 1)),
        ]

        result = filter_by_pit(transcripts, cutoff)

        assert result == []

    def test_エッジケース_空リストで空結果(self) -> None:
        cutoff = date(2015, 9, 30)

        result = filter_by_pit([], cutoff)

        assert result == []

    def test_正常系_デフォルトcutoff_dateを使用(self) -> None:
        t_before = _make_transcript("AAPL", date(2015, 6, 15))
        t_after = _make_transcript("GOOG", date(2025, 1, 1))

        result = filter_by_pit([t_before, t_after])

        assert len(result) == 1
        assert result[0].metadata.ticker == "AAPL"

    def test_正常系_元のリストを変更しない(self) -> None:
        cutoff = date(2015, 9, 30)
        original = [
            _make_transcript("AAPL", date(2015, 6, 15)),
            _make_transcript("GOOG", date(2015, 10, 1)),
        ]
        original_len = len(original)

        filter_by_pit(original, cutoff)

        assert len(original) == original_len


# =============================================================================
# get_pit_prompt_context
# =============================================================================
class TestGetPitPromptContext:
    """get_pit_prompt_context function tests."""

    def test_正常系_cutoff_dateを含む文字列を返す(self) -> None:
        cutoff = date(2015, 9, 30)

        result = get_pit_prompt_context(cutoff)

        assert "2015-09-30" in result

    def test_正常系_デフォルトcutoff_dateを使用(self) -> None:
        result = get_pit_prompt_context()

        assert "2015-09-30" in result

    def test_正常系_返り値がstr型(self) -> None:
        result = get_pit_prompt_context(date(2015, 9, 30))

        assert isinstance(result, str)

    def test_正常系_時間制約に関する指示を含む(self) -> None:
        result = get_pit_prompt_context(date(2015, 9, 30))

        # Must contain temporal constraint instructions
        assert len(result) > 50  # non-trivial content

    def test_正常系_異なる日付で異なる出力(self) -> None:
        result1 = get_pit_prompt_context(date(2015, 9, 30))
        result2 = get_pit_prompt_context(date(2020, 12, 31))

        assert result1 != result2
        assert "2015-09-30" in result1
        assert "2020-12-31" in result2


# =============================================================================
# validate_pit_compliance
# =============================================================================
class TestValidatePitCompliance:
    """validate_pit_compliance function tests."""

    def test_正常系_全てcutoff_date以前なら真(self) -> None:
        cutoff = date(2015, 9, 30)
        transcripts = [
            _make_transcript("AAPL", date(2015, 6, 15)),
            _make_transcript("MSFT", date(2015, 9, 30)),
        ]

        assert validate_pit_compliance(transcripts, cutoff) is True

    def test_異常系_cutoff_date後のデータがあれば偽(self) -> None:
        cutoff = date(2015, 9, 30)
        transcripts = [
            _make_transcript("AAPL", date(2015, 6, 15)),
            _make_transcript("GOOG", date(2015, 10, 1)),
        ]

        assert validate_pit_compliance(transcripts, cutoff) is False

    def test_エッジケース_空リストなら真(self) -> None:
        cutoff = date(2015, 9, 30)

        assert validate_pit_compliance([], cutoff) is True

    def test_正常系_デフォルトcutoff_dateを使用(self) -> None:
        transcripts = [
            _make_transcript("AAPL", date(2015, 6, 15)),
        ]

        assert validate_pit_compliance(transcripts) is True

    def test_異常系_境界値_cutoff_date翌日は違反(self) -> None:
        cutoff = date(2015, 9, 30)
        transcripts = [
            _make_transcript("AAPL", date(2015, 10, 1)),
        ]

        assert validate_pit_compliance(transcripts, cutoff) is False
