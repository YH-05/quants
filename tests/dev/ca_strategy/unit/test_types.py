"""Tests for ca_strategy types module.

All Pydantic models must be immutable (frozen=True) and properly validated.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import BaseModel, ValidationError

from dev.ca_strategy.types import (
    AdjustmentFloat,
    AnalystCorrelation,
    AnalystScore,
    BenchmarkWeight,
    Claim,
    ClaimType,
    ConfidenceAdjustment,
    EvaluationResult,
    NonNegativeInt,
    PerformanceMetrics,
    PortfolioHolding,
    RuleEvaluation,
    ScoredClaim,
    SectorAllocation,
    StockScore,
    Transcript,
    TranscriptMetadata,
    TranscriptSection,
    TransparencyMetrics,
    UnitFloat,
    UniverseConfig,
    UniverseTicker,
)


# =============================================================================
# TranscriptSection
# =============================================================================
class TestTranscriptSection:
    """TranscriptSection model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        section = TranscriptSection(
            speaker="Tim Cook",
            role="CEO",
            section_type="prepared_remarks",
            content="We had a great quarter...",
        )
        assert section.speaker == "Tim Cook"
        assert section.role == "CEO"
        assert section.section_type == "prepared_remarks"
        assert section.content == "We had a great quarter..."

    def test_正常系_frozenモデルである(self) -> None:
        section = TranscriptSection(
            speaker="Tim Cook",
            role="CEO",
            section_type="prepared_remarks",
            content="content",
        )
        with pytest.raises(ValidationError):
            section.speaker = "other"

    def test_異常系_speakerが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="speaker"):
            TranscriptSection(
                speaker="",
                role="CEO",
                section_type="prepared_remarks",
                content="content",
            )

    def test_異常系_speakerが空白のみ文字列でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="speaker"):
            TranscriptSection(
                speaker="   ",
                role="CEO",
                section_type="prepared_remarks",
                content="content",
            )

    def test_異常系_contentが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="content"):
            TranscriptSection(
                speaker="Tim Cook",
                role="CEO",
                section_type="prepared_remarks",
                content="",
            )

    def test_正常系_roleがNoneでも作成できる(self) -> None:
        section = TranscriptSection(
            speaker="Operator",
            role=None,
            section_type="operator",
            content="Welcome to the call.",
        )
        assert section.role is None


# =============================================================================
# TranscriptMetadata
# =============================================================================
class TestTranscriptMetadata:
    """TranscriptMetadata model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
            is_truncated=False,
        )
        assert meta.ticker == "AAPL"
        assert meta.event_date == date(2024, 1, 25)
        assert meta.fiscal_quarter == "Q1 2024"
        assert meta.is_truncated is False

    def test_正常系_frozenモデルである(self) -> None:
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
            is_truncated=False,
        )
        with pytest.raises(ValidationError):
            meta.ticker = "MSFT"

    def test_異常系_tickerが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            TranscriptMetadata(
                ticker="",
                event_date=date(2024, 1, 25),
                fiscal_quarter="Q1 2024",
                is_truncated=False,
            )

    def test_異常系_fiscal_quarterが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="fiscal_quarter"):
            TranscriptMetadata(
                ticker="AAPL",
                event_date=date(2024, 1, 25),
                fiscal_quarter="",
                is_truncated=False,
            )

    def test_正常系_is_truncatedのデフォルトはFalse(self) -> None:
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
        )
        assert meta.is_truncated is False


# =============================================================================
# Transcript
# =============================================================================
class TestTranscript:
    """Transcript model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        section = TranscriptSection(
            speaker="Tim Cook",
            role="CEO",
            section_type="prepared_remarks",
            content="Great quarter.",
        )
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
            is_truncated=False,
        )
        transcript = Transcript(
            metadata=meta,
            sections=[section],
            raw_source="Full transcript text...",
        )
        assert transcript.metadata == meta
        assert len(transcript.sections) == 1
        assert transcript.raw_source == "Full transcript text..."

    def test_正常系_frozenモデルである(self) -> None:
        section = TranscriptSection(
            speaker="Tim Cook",
            role="CEO",
            section_type="prepared_remarks",
            content="content",
        )
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
        )
        transcript = Transcript(
            metadata=meta,
            sections=[section],
            raw_source="source",
        )
        with pytest.raises(ValidationError):
            transcript.raw_source = "other"

    def test_異常系_sectionsが空リストでValidationError(self) -> None:
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
        )
        with pytest.raises(ValidationError, match="sections"):
            Transcript(
                metadata=meta,
                sections=[],
                raw_source="source",
            )

    def test_正常系_raw_sourceがNoneでも作成できる(self) -> None:
        section = TranscriptSection(
            speaker="Tim Cook",
            role="CEO",
            section_type="prepared_remarks",
            content="content",
        )
        meta = TranscriptMetadata(
            ticker="AAPL",
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
        )
        transcript = Transcript(
            metadata=meta,
            sections=[section],
            raw_source=None,
        )
        assert transcript.raw_source is None


# =============================================================================
# ClaimType
# =============================================================================
class TestClaimType:
    """ClaimType literal type tests."""

    def test_正常系_competitive_advantageが有効(self) -> None:
        claim = Claim(
            id="c1",
            claim_type="competitive_advantage",
            claim="Strong brand",
            evidence="Revenue growth",
            rule_evaluation=RuleEvaluation(
                applied_rules=["rule01"],
                results={"rule01": True},
                confidence=0.8,
                adjustments=[],
            ),
        )
        assert claim.claim_type == "competitive_advantage"

    def test_正常系_cagr_connectionが有効(self) -> None:
        claim = Claim(
            id="c2",
            claim_type="cagr_connection",
            claim="Growth driver",
            evidence="Data shows",
            rule_evaluation=RuleEvaluation(
                applied_rules=["rule01"],
                results={"rule01": True},
                confidence=0.7,
                adjustments=[],
            ),
        )
        assert claim.claim_type == "cagr_connection"

    def test_正常系_factual_claimが有効(self) -> None:
        claim = Claim(
            id="c3",
            claim_type="factual_claim",
            claim="Revenue was $100B",
            evidence="10-K filing",
            rule_evaluation=RuleEvaluation(
                applied_rules=["rule01"],
                results={"rule01": True},
                confidence=0.9,
                adjustments=[],
            ),
        )
        assert claim.claim_type == "factual_claim"


# =============================================================================
# RuleEvaluation
# =============================================================================
class TestRuleEvaluation:
    """RuleEvaluation model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01", "rule02"],
            results={"rule01": True, "rule02": False},
            confidence=0.75,
            adjustments=[],
        )
        assert rule_eval.applied_rules == ["rule01", "rule02"]
        assert rule_eval.results == {"rule01": True, "rule02": False}
        assert rule_eval.confidence == 0.75
        assert rule_eval.adjustments == []

    def test_正常系_frozenモデルである(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        with pytest.raises(ValidationError):
            rule_eval.confidence = 0.5

    def test_異常系_confidenceが0未満でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="confidence"):
            RuleEvaluation(
                applied_rules=["rule01"],
                results={"rule01": True},
                confidence=-0.1,
                adjustments=[],
            )

    def test_異常系_confidenceが1を超えてValidationError(self) -> None:
        with pytest.raises(ValidationError, match="confidence"):
            RuleEvaluation(
                applied_rules=["rule01"],
                results={"rule01": True},
                confidence=1.1,
                adjustments=[],
            )

    def test_エッジケース_confidence境界値0と1が有効(self) -> None:
        rule_eval_0 = RuleEvaluation(
            applied_rules=[],
            results={},
            confidence=0.0,
            adjustments=[],
        )
        assert rule_eval_0.confidence == 0.0

        rule_eval_1 = RuleEvaluation(
            applied_rules=[],
            results={},
            confidence=1.0,
            adjustments=[],
        )
        assert rule_eval_1.confidence == 1.0


# =============================================================================
# Claim
# =============================================================================
class TestClaim:
    """Claim model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        claim = Claim(
            id="claim_001",
            claim_type="competitive_advantage",
            claim="Strong brand recognition",
            evidence="Market share data shows 35% dominance",
            rule_evaluation=rule_eval,
        )
        assert claim.id == "claim_001"
        assert claim.claim_type == "competitive_advantage"
        assert claim.claim == "Strong brand recognition"
        assert claim.evidence == "Market share data shows 35% dominance"
        assert claim.rule_evaluation == rule_eval

    def test_正常系_frozenモデルである(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        claim = Claim(
            id="c1",
            claim_type="competitive_advantage",
            claim="claim",
            evidence="evidence",
            rule_evaluation=rule_eval,
        )
        with pytest.raises(ValidationError):
            claim.claim = "other"

    def test_異常系_idが空文字でValidationError(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        with pytest.raises(ValidationError, match="id"):
            Claim(
                id="",
                claim_type="competitive_advantage",
                claim="claim",
                evidence="evidence",
                rule_evaluation=rule_eval,
            )

    def test_異常系_claimが空文字でValidationError(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        with pytest.raises(ValidationError, match="claim"):
            Claim(
                id="c1",
                claim_type="competitive_advantage",
                claim="",
                evidence="evidence",
                rule_evaluation=rule_eval,
            )


# =============================================================================
# ConfidenceAdjustment
# =============================================================================
class TestConfidenceAdjustment:
    """ConfidenceAdjustment model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        adj = ConfidenceAdjustment(
            source="pattern_I",
            adjustment=0.1,
            reasoning="Quantitative evidence supports claim",
        )
        assert adj.source == "pattern_I"
        assert adj.adjustment == 0.1
        assert adj.reasoning == "Quantitative evidence supports claim"

    def test_正常系_frozenモデルである(self) -> None:
        adj = ConfidenceAdjustment(
            source="pattern_I",
            adjustment=0.1,
            reasoning="reasoning",
        )
        with pytest.raises(ValidationError):
            adj.adjustment = 0.2

    def test_正常系_負のadjustmentも有効(self) -> None:
        adj = ConfidenceAdjustment(
            source="pattern_A",
            adjustment=-0.2,
            reasoning="Result as cause detected",
        )
        assert adj.adjustment == -0.2

    def test_異常系_adjustmentが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="adjustment"):
            ConfidenceAdjustment(
                source="pattern_A",
                adjustment=-1.1,
                reasoning="too much",
            )

        with pytest.raises(ValidationError, match="adjustment"):
            ConfidenceAdjustment(
                source="pattern_I",
                adjustment=1.1,
                reasoning="too much",
            )


# =============================================================================
# ScoredClaim
# =============================================================================
class TestScoredClaim:
    """ScoredClaim model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        adj = ConfidenceAdjustment(
            source="pattern_I",
            adjustment=0.1,
            reasoning="Good quantitative evidence",
        )
        scored = ScoredClaim(
            id="c1",
            claim_type="competitive_advantage",
            claim="Strong brand",
            evidence="Market data",
            rule_evaluation=rule_eval,
            final_confidence=0.9,
            adjustments=[adj],
        )
        assert scored.final_confidence == 0.9
        assert len(scored.adjustments) == 1
        assert scored.adjustments[0].source == "pattern_I"

    def test_正常系_frozenモデルである(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        scored = ScoredClaim(
            id="c1",
            claim_type="competitive_advantage",
            claim="claim",
            evidence="evidence",
            rule_evaluation=rule_eval,
            final_confidence=0.8,
            adjustments=[],
        )
        with pytest.raises(ValidationError):
            scored.final_confidence = 0.5

    def test_異常系_final_confidenceが範囲外でValidationError(self) -> None:
        rule_eval = RuleEvaluation(
            applied_rules=["rule01"],
            results={"rule01": True},
            confidence=0.8,
            adjustments=[],
        )
        with pytest.raises(ValidationError, match="final_confidence"):
            ScoredClaim(
                id="c1",
                claim_type="competitive_advantage",
                claim="claim",
                evidence="evidence",
                rule_evaluation=rule_eval,
                final_confidence=1.5,
                adjustments=[],
            )

        with pytest.raises(ValidationError, match="final_confidence"):
            ScoredClaim(
                id="c1",
                claim_type="competitive_advantage",
                claim="claim",
                evidence="evidence",
                rule_evaluation=rule_eval,
                final_confidence=-0.1,
                adjustments=[],
            )


# =============================================================================
# StockScore
# =============================================================================
class TestStockScore:
    """StockScore model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        score = StockScore(
            ticker="AAPL",
            aggregate_score=0.85,
            claim_count=5,
            structural_weight=0.7,
        )
        assert score.ticker == "AAPL"
        assert score.aggregate_score == 0.85
        assert score.claim_count == 5
        assert score.structural_weight == 0.7

    def test_正常系_frozenモデルである(self) -> None:
        score = StockScore(
            ticker="AAPL",
            aggregate_score=0.85,
            claim_count=5,
            structural_weight=0.7,
        )
        with pytest.raises(ValidationError):
            score.ticker = "MSFT"

    def test_異常系_tickerが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            StockScore(
                ticker="",
                aggregate_score=0.85,
                claim_count=5,
                structural_weight=0.7,
            )

    def test_異常系_aggregate_scoreが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="aggregate_score"):
            StockScore(
                ticker="AAPL",
                aggregate_score=-0.1,
                claim_count=5,
                structural_weight=0.7,
            )

        with pytest.raises(ValidationError, match="aggregate_score"):
            StockScore(
                ticker="AAPL",
                aggregate_score=1.1,
                claim_count=5,
                structural_weight=0.7,
            )

    def test_異常系_claim_countが負でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="claim_count"):
            StockScore(
                ticker="AAPL",
                aggregate_score=0.85,
                claim_count=-1,
                structural_weight=0.7,
            )

    def test_異常系_structural_weightが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="structural_weight"):
            StockScore(
                ticker="AAPL",
                aggregate_score=0.85,
                claim_count=5,
                structural_weight=-0.1,
            )

        with pytest.raises(ValidationError, match="structural_weight"):
            StockScore(
                ticker="AAPL",
                aggregate_score=0.85,
                claim_count=5,
                structural_weight=1.1,
            )


# =============================================================================
# PortfolioHolding
# =============================================================================
class TestPortfolioHolding:
    """PortfolioHolding model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        holding = PortfolioHolding(
            ticker="AAPL",
            weight=0.05,
            sector="Information Technology",
            score=0.85,
            rationale_summary="Strong competitive advantages in ecosystem lock-in",
        )
        assert holding.ticker == "AAPL"
        assert holding.weight == 0.05
        assert holding.sector == "Information Technology"
        assert holding.score == 0.85
        assert "ecosystem" in holding.rationale_summary

    def test_正常系_frozenモデルである(self) -> None:
        holding = PortfolioHolding(
            ticker="AAPL",
            weight=0.05,
            sector="Information Technology",
            score=0.85,
            rationale_summary="summary",
        )
        with pytest.raises(ValidationError):
            holding.weight = 0.1

    def test_異常系_tickerが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            PortfolioHolding(
                ticker="",
                weight=0.05,
                sector="Information Technology",
                score=0.85,
                rationale_summary="summary",
            )

    def test_異常系_weightが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="weight"):
            PortfolioHolding(
                ticker="AAPL",
                weight=-0.01,
                sector="Information Technology",
                score=0.85,
                rationale_summary="summary",
            )

        with pytest.raises(ValidationError, match="weight"):
            PortfolioHolding(
                ticker="AAPL",
                weight=1.1,
                sector="Information Technology",
                score=0.85,
                rationale_summary="summary",
            )

    def test_異常系_scoreが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="score"):
            PortfolioHolding(
                ticker="AAPL",
                weight=0.05,
                sector="Information Technology",
                score=-0.1,
                rationale_summary="summary",
            )

    def test_異常系_sectorが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="sector"):
            PortfolioHolding(
                ticker="AAPL",
                weight=0.05,
                sector="",
                score=0.85,
                rationale_summary="summary",
            )


# =============================================================================
# SectorAllocation
# =============================================================================
class TestSectorAllocation:
    """SectorAllocation model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        alloc = SectorAllocation(
            sector="Information Technology",
            benchmark_weight=0.19,
            actual_weight=0.22,
            stock_count=10,
        )
        assert alloc.sector == "Information Technology"
        assert alloc.benchmark_weight == 0.19
        assert alloc.actual_weight == 0.22
        assert alloc.stock_count == 10

    def test_正常系_frozenモデルである(self) -> None:
        alloc = SectorAllocation(
            sector="IT",
            benchmark_weight=0.19,
            actual_weight=0.22,
            stock_count=10,
        )
        with pytest.raises(ValidationError):
            alloc.stock_count = 20

    def test_異常系_sectorが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="sector"):
            SectorAllocation(
                sector="",
                benchmark_weight=0.19,
                actual_weight=0.22,
                stock_count=10,
            )

    def test_異常系_stock_countが負でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="stock_count"):
            SectorAllocation(
                sector="IT",
                benchmark_weight=0.19,
                actual_weight=0.22,
                stock_count=-1,
            )

    def test_異常系_weightが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="benchmark_weight"):
            SectorAllocation(
                sector="IT",
                benchmark_weight=-0.1,
                actual_weight=0.22,
                stock_count=10,
            )

        with pytest.raises(ValidationError, match="actual_weight"):
            SectorAllocation(
                sector="IT",
                benchmark_weight=0.19,
                actual_weight=1.1,
                stock_count=10,
            )


# =============================================================================
# UniverseTicker
# =============================================================================
class TestUniverseTicker:
    """UniverseTicker model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        ticker = UniverseTicker(
            ticker="AAPL",
            gics_sector="Information Technology",
        )
        assert ticker.ticker == "AAPL"
        assert ticker.gics_sector == "Information Technology"

    def test_異常系_tickerが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            UniverseTicker(
                ticker="",
                gics_sector="Information Technology",
            )

    def test_異常系_gics_sectorが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="gics_sector"):
            UniverseTicker(
                ticker="AAPL",
                gics_sector="",
            )

    def test_正常系_bloomberg_tickerなしで作成できる_後方互換(self) -> None:
        ticker = UniverseTicker(
            ticker="AAPL",
            gics_sector="Information Technology",
        )
        assert ticker.ticker == "AAPL"
        assert ticker.gics_sector == "Information Technology"
        assert ticker.bloomberg_ticker == ""

    def test_正常系_bloomberg_tickerありで作成できる(self) -> None:
        ticker = UniverseTicker(
            ticker="AAPL",
            gics_sector="Information Technology",
            bloomberg_ticker="AAPL US Equity",
        )
        assert ticker.ticker == "AAPL"
        assert ticker.gics_sector == "Information Technology"
        assert ticker.bloomberg_ticker == "AAPL US Equity"

    def test_正常系_bloomberg_tickerのデフォルト値が空文字列(self) -> None:
        ticker = UniverseTicker(
            ticker="MSFT",
            gics_sector="Information Technology",
        )
        assert ticker.bloomberg_ticker == ""

    def test_正常系_国際銘柄のbloomberg_ticker(self) -> None:
        ticker = UniverseTicker(
            ticker="ADN",
            gics_sector="Industrials",
            bloomberg_ticker="ADN LN Equity",
        )
        assert ticker.bloomberg_ticker == "ADN LN Equity"


# =============================================================================
# UniverseConfig
# =============================================================================
class TestUniverseConfig:
    """UniverseConfig model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        tickers = [
            UniverseTicker(ticker="AAPL", gics_sector="Information Technology"),
            UniverseTicker(ticker="MSFT", gics_sector="Information Technology"),
        ]
        config = UniverseConfig(tickers=tickers)
        assert len(config.tickers) == 2
        assert config.tickers[0].ticker == "AAPL"

    def test_正常系_frozenモデルである(self) -> None:
        tickers = [
            UniverseTicker(ticker="AAPL", gics_sector="Information Technology"),
        ]
        config = UniverseConfig(tickers=tickers)
        with pytest.raises(ValidationError):
            config.tickers = []

    def test_異常系_tickersが空リストでValidationError(self) -> None:
        with pytest.raises(ValidationError, match="tickers"):
            UniverseConfig(tickers=[])


# =============================================================================
# BenchmarkWeight
# =============================================================================
class TestBenchmarkWeight:
    """BenchmarkWeight model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        bw = BenchmarkWeight(
            sector="Information Technology",
            weight=0.19,
        )
        assert bw.sector == "Information Technology"
        assert bw.weight == 0.19

    def test_正常系_frozenモデルである(self) -> None:
        bw = BenchmarkWeight(
            sector="IT",
            weight=0.19,
        )
        with pytest.raises(ValidationError):
            bw.weight = 0.25

    def test_異常系_sectorが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="sector"):
            BenchmarkWeight(
                sector="",
                weight=0.19,
            )

    def test_異常系_weightが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="weight"):
            BenchmarkWeight(
                sector="IT",
                weight=-0.1,
            )

        with pytest.raises(ValidationError, match="weight"):
            BenchmarkWeight(
                sector="IT",
                weight=1.1,
            )

    def test_エッジケース_weight境界値0と1が有効(self) -> None:
        bw0 = BenchmarkWeight(sector="IT", weight=0.0)
        assert bw0.weight == 0.0

        bw1 = BenchmarkWeight(sector="IT", weight=1.0)
        assert bw1.weight == 1.0


# =============================================================================
# UnitFloat 境界値テスト
# =============================================================================
class _UnitModel(BaseModel):
    """UnitFloat テスト用ヘルパーモデル。"""

    v: UnitFloat


class TestUnitFloat:
    """UnitFloat 型エイリアスの境界値テスト（[0.0, 1.0]制約）。"""

    def test_正常系_0_0が有効(self) -> None:
        assert _UnitModel(v=0.0).v == 0.0

    def test_正常系_1_0が有効(self) -> None:
        assert _UnitModel(v=1.0).v == 1.0

    def test_正常系_中間値0_5が有効(self) -> None:
        assert _UnitModel(v=0.5).v == 0.5

    def test_異常系_マイナス0_001でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="v"):
            _UnitModel(v=-0.001)

    def test_異常系_1_001でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="v"):
            _UnitModel(v=1.001)


# =============================================================================
# AdjustmentFloat 境界値テスト
# =============================================================================
class _AdjustmentModel(BaseModel):
    """AdjustmentFloat テスト用ヘルパーモデル。"""

    v: AdjustmentFloat


class TestAdjustmentFloat:
    """AdjustmentFloat 型エイリアスの境界値テスト（[-1.0, 1.0]制約）。"""

    def test_正常系_マイナス1_0が有効(self) -> None:
        assert _AdjustmentModel(v=-1.0).v == -1.0

    def test_正常系_1_0が有効(self) -> None:
        assert _AdjustmentModel(v=1.0).v == 1.0

    def test_正常系_0_0が有効(self) -> None:
        assert _AdjustmentModel(v=0.0).v == 0.0

    def test_異常系_マイナス1_001でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="v"):
            _AdjustmentModel(v=-1.001)

    def test_異常系_1_001でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="v"):
            _AdjustmentModel(v=1.001)


# =============================================================================
# NonNegativeInt 境界値テスト
# =============================================================================
class _NonNegativeIntModel(BaseModel):
    """NonNegativeInt テスト用ヘルパーモデル。"""

    v: NonNegativeInt


class TestNonNegativeInt:
    """NonNegativeInt 型エイリアスの境界値テスト（>= 0制約）。"""

    def test_正常系_0が有効(self) -> None:
        assert _NonNegativeIntModel(v=0).v == 0

    def test_正常系_正の整数が有効(self) -> None:
        assert _NonNegativeIntModel(v=100).v == 100

    def test_異常系_マイナス1でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="v"):
            _NonNegativeIntModel(v=-1)


# =============================================================================
# TickerStr 境界値テスト
# =============================================================================
class TestTickerStr:
    """TranscriptMetadata.ticker (TickerStr) の形式バリデーションテスト。"""

    def _make_meta(self, ticker: str) -> TranscriptMetadata:
        return TranscriptMetadata(
            ticker=ticker,
            event_date=date(2024, 1, 25),
            fiscal_quarter="Q1 2024",
        )

    def test_正常系_大文字アルファベットが有効(self) -> None:
        meta = self._make_meta("AAPL")
        assert meta.ticker == "AAPL"

    def test_正常系_ドット付きティッカーが有効(self) -> None:
        meta = self._make_meta("BRK.A")
        assert meta.ticker == "BRK.A"

    def test_正常系_スラッシュ付きティッカーが有効(self) -> None:
        meta = self._make_meta("BRK/B")
        assert meta.ticker == "BRK/B"

    def test_正常系_数字を含むティッカーが有効(self) -> None:
        meta = self._make_meta("A1234")
        assert meta.ticker == "A1234"

    def test_異常系_小文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            self._make_meta("aapl")

    def test_異常系_10文字超でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            self._make_meta("TOOLONGTICKE")

    def test_異常系_空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            self._make_meta("")

    def test_異常系_特殊文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            self._make_meta("AAPL!")


# =============================================================================
# PerformanceMetrics
# =============================================================================
class TestPerformanceMetrics:
    """PerformanceMetrics model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        metrics = PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=-0.15,
            beta=0.95,
            information_ratio=0.45,
            cumulative_return=0.25,
        )
        assert metrics.sharpe_ratio == 1.2
        assert metrics.max_drawdown == -0.15
        assert metrics.beta == 0.95
        assert metrics.information_ratio == 0.45
        assert metrics.cumulative_return == 0.25

    def test_正常系_frozenモデルである(self) -> None:
        metrics = PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=-0.15,
            beta=0.95,
            information_ratio=0.45,
            cumulative_return=0.25,
        )
        with pytest.raises(ValidationError):
            metrics.sharpe_ratio = 0.5

    def test_正常系_max_drawdownが0_0でも有効(self) -> None:
        metrics = PerformanceMetrics(
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            beta=1.0,
            information_ratio=0.0,
            cumulative_return=0.0,
        )
        assert metrics.max_drawdown == 0.0

    def test_正常系_cumulative_returnは制約外の負値も有効(self) -> None:
        metrics = PerformanceMetrics(
            sharpe_ratio=-1.5,
            max_drawdown=-0.50,
            beta=1.2,
            information_ratio=-0.3,
            cumulative_return=-0.30,
        )
        assert metrics.cumulative_return == -0.30

    def test_正常系_sharpe_ratioは制約外の大きな値も有効(self) -> None:
        metrics = PerformanceMetrics(
            sharpe_ratio=5.0,
            max_drawdown=-0.05,
            beta=0.8,
            information_ratio=2.0,
            cumulative_return=2.5,
        )
        assert metrics.sharpe_ratio == 5.0

    def test_異常系_max_drawdownが正値でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="max_drawdown"):
            PerformanceMetrics(
                sharpe_ratio=1.2,
                max_drawdown=0.01,
                beta=0.95,
                information_ratio=0.45,
                cumulative_return=0.25,
            )


# =============================================================================
# AnalystCorrelation
# =============================================================================
class TestAnalystCorrelation:
    """AnalystCorrelation model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        corr = AnalystCorrelation(
            spearman_correlation=0.65,
            p_value=0.02,
            hit_rate=0.60,
            sample_size=50,
        )
        assert corr.spearman_correlation == 0.65
        assert corr.p_value == 0.02
        assert corr.hit_rate == 0.60
        assert corr.sample_size == 50

    def test_正常系_frozenモデルである(self) -> None:
        corr = AnalystCorrelation(
            spearman_correlation=0.65,
            p_value=0.02,
            hit_rate=0.60,
            sample_size=50,
        )
        with pytest.raises(ValidationError):
            corr.sample_size = 100

    def test_正常系_NoneフィールドでNullableが有効(self) -> None:
        corr = AnalystCorrelation(
            spearman_correlation=None,
            p_value=None,
            hit_rate=None,
            sample_size=0,
        )
        assert corr.spearman_correlation is None
        assert corr.p_value is None
        assert corr.hit_rate is None

    def test_正常系_spearman_correlationは負値も有効(self) -> None:
        corr = AnalystCorrelation(
            spearman_correlation=-0.4,
            p_value=0.10,
            hit_rate=0.20,
            sample_size=30,
        )
        assert corr.spearman_correlation == -0.4

    def test_正常系_p_value境界値0_0と1_0が有効(self) -> None:
        corr_0 = AnalystCorrelation(
            spearman_correlation=0.0,
            p_value=0.0,
            hit_rate=0.0,
            sample_size=10,
        )
        assert corr_0.p_value == 0.0

        corr_1 = AnalystCorrelation(
            spearman_correlation=0.0,
            p_value=1.0,
            hit_rate=1.0,
            sample_size=10,
        )
        assert corr_1.p_value == 1.0

    def test_異常系_p_valueが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="p_value"):
            AnalystCorrelation(
                spearman_correlation=0.5,
                p_value=1.1,
                hit_rate=0.5,
                sample_size=10,
            )

        with pytest.raises(ValidationError, match="p_value"):
            AnalystCorrelation(
                spearman_correlation=0.5,
                p_value=-0.01,
                hit_rate=0.5,
                sample_size=10,
            )

    def test_異常系_hit_rateが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="hit_rate"):
            AnalystCorrelation(
                spearman_correlation=0.5,
                p_value=0.05,
                hit_rate=1.1,
                sample_size=10,
            )


# =============================================================================
# TransparencyMetrics
# =============================================================================
class TestTransparencyMetrics:
    """TransparencyMetrics model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        metrics = TransparencyMetrics(
            mean_claim_count=4.5,
            mean_structural_weight=0.65,
            coverage_rate=0.90,
        )
        assert metrics.mean_claim_count == 4.5
        assert metrics.mean_structural_weight == 0.65
        assert metrics.coverage_rate == 0.90

    def test_正常系_frozenモデルである(self) -> None:
        metrics = TransparencyMetrics(
            mean_claim_count=4.5,
            mean_structural_weight=0.65,
            coverage_rate=0.90,
        )
        with pytest.raises(ValidationError):
            metrics.coverage_rate = 0.5

    def test_正常系_coverage_rate境界値0_0と1_0が有効(self) -> None:
        m0 = TransparencyMetrics(
            mean_claim_count=0.0,
            mean_structural_weight=0.0,
            coverage_rate=0.0,
        )
        assert m0.coverage_rate == 0.0

        m1 = TransparencyMetrics(
            mean_claim_count=10.0,
            mean_structural_weight=1.0,
            coverage_rate=1.0,
        )
        assert m1.coverage_rate == 1.0

    def test_正常系_mean_claim_countは制約外の大きな値も有効(self) -> None:
        metrics = TransparencyMetrics(
            mean_claim_count=100.0,
            mean_structural_weight=0.5,
            coverage_rate=1.0,
        )
        assert metrics.mean_claim_count == 100.0

    def test_異常系_coverage_rateが範囲外でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="coverage_rate"):
            TransparencyMetrics(
                mean_claim_count=4.5,
                mean_structural_weight=0.65,
                coverage_rate=1.1,
            )

        with pytest.raises(ValidationError, match="coverage_rate"):
            TransparencyMetrics(
                mean_claim_count=4.5,
                mean_structural_weight=0.65,
                coverage_rate=-0.01,
            )


# =============================================================================
# EvaluationResult
# =============================================================================
class TestEvaluationResult:
    """EvaluationResult model tests."""

    def _make_performance(self) -> PerformanceMetrics:
        return PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=-0.15,
            beta=0.95,
            information_ratio=0.45,
            cumulative_return=0.25,
        )

    def _make_correlation(self) -> AnalystCorrelation:
        return AnalystCorrelation(
            spearman_correlation=0.65,
            p_value=0.02,
            hit_rate=0.60,
            sample_size=50,
        )

    def _make_transparency(self) -> TransparencyMetrics:
        return TransparencyMetrics(
            mean_claim_count=4.5,
            mean_structural_weight=0.65,
            coverage_rate=0.90,
        )

    def test_正常系_有効なデータで作成できる(self) -> None:
        from datetime import date

        result = EvaluationResult(
            threshold=0.5,
            portfolio_size=30,
            performance=self._make_performance(),
            analyst_correlation=self._make_correlation(),
            transparency=self._make_transparency(),
            as_of_date=date(2025, 12, 31),
        )
        assert result.threshold == 0.5
        assert result.portfolio_size == 30
        assert result.as_of_date == date(2025, 12, 31)
        assert isinstance(result.performance, PerformanceMetrics)
        assert isinstance(result.analyst_correlation, AnalystCorrelation)
        assert isinstance(result.transparency, TransparencyMetrics)

    def test_正常系_frozenモデルである(self) -> None:
        from datetime import date

        result = EvaluationResult(
            threshold=0.5,
            portfolio_size=30,
            performance=self._make_performance(),
            analyst_correlation=self._make_correlation(),
            transparency=self._make_transparency(),
            as_of_date=date(2025, 12, 31),
        )
        with pytest.raises(ValidationError):
            result.threshold = 0.7

    def test_正常系_3軸メトリクスが統合されている(self) -> None:
        from datetime import date

        result = EvaluationResult(
            threshold=0.3,
            portfolio_size=15,
            performance=self._make_performance(),
            analyst_correlation=self._make_correlation(),
            transparency=self._make_transparency(),
            as_of_date=date(2025, 6, 30),
        )
        assert result.performance.sharpe_ratio == 1.2
        assert result.analyst_correlation.sample_size == 50
        assert result.transparency.coverage_rate == 0.90
        assert result.as_of_date == date(2025, 6, 30)

    def test_エッジケース_portfolio_sizeが0でも有効(self) -> None:
        from datetime import date

        result = EvaluationResult(
            threshold=0.9,
            portfolio_size=0,
            performance=self._make_performance(),
            analyst_correlation=AnalystCorrelation(
                spearman_correlation=None,
                p_value=None,
                hit_rate=None,
                sample_size=0,
            ),
            transparency=TransparencyMetrics(
                mean_claim_count=0.0,
                mean_structural_weight=0.0,
                coverage_rate=0.0,
            ),
            as_of_date=date(2025, 1, 1),
        )
        assert result.portfolio_size == 0


# =============================================================================
# AnalystScore
# =============================================================================
class TestAnalystScore:
    """AnalystScore model tests."""

    def test_正常系_有効なデータで作成できる(self) -> None:
        score = AnalystScore(
            ticker="AAPL",
            ky=3,
            ak=2,
        )
        assert score.ticker == "AAPL"
        assert score.ky == 3
        assert score.ak == 2

    def test_正常系_frozenモデルである(self) -> None:
        score = AnalystScore(
            ticker="AAPL",
            ky=3,
            ak=2,
        )
        with pytest.raises(ValidationError):
            score.ticker = "MSFT"

    def test_正常系_kyとakのデフォルトはNone(self) -> None:
        score = AnalystScore(ticker="MSFT")
        assert score.ky is None
        assert score.ak is None

    def test_正常系_kyのみ指定で作成できる(self) -> None:
        score = AnalystScore(ticker="GOOGL", ky=5)
        assert score.ky == 5
        assert score.ak is None

    def test_正常系_akのみ指定で作成できる(self) -> None:
        score = AnalystScore(ticker="AMZN", ak=1)
        assert score.ky is None
        assert score.ak == 1

    def test_異常系_tickerが空文字でValidationError(self) -> None:
        with pytest.raises(ValidationError, match="ticker"):
            AnalystScore(ticker="", ky=1, ak=2)

    def test_正常系_ky_akが負の整数でも有効(self) -> None:
        # AnalystScore does not constrain ky/ak to non-negative values
        score = AnalystScore(ticker="NVDA", ky=-1, ak=-2)
        assert score.ky == -1
        assert score.ak == -2
