"""Pydantic v2 data models for the CA Strategy package.

Defines all shared types used across the ca_strategy pipeline:
- Transcript models (input to Phase 1)
- Claim / ScoredClaim models (Phase 1 & 2 outputs)
- StockScore / PortfolioHolding models (Phase 3 & 4 outputs)
- Configuration models (UniverseConfig, BenchmarkWeight)

All models are immutable (frozen=True) with field validators.
"""

from __future__ import annotations

import re
from datetime import date  # noqa: TC003 - required at runtime by Pydantic
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Reusable non-empty string validator (DRY-002)
# ---------------------------------------------------------------------------
def _validate_non_empty_str(v: str) -> str:
    """Validate that a string is non-empty after stripping whitespace."""
    if not v or not v.strip():
        msg = "value must be non-empty string"
        raise ValueError(msg)
    return v


NonEmptyStr = Annotated[str, AfterValidator(_validate_non_empty_str)]


def _validate_unit_range(v: float) -> float:
    """Validate that a float is in [0.0, 1.0]."""
    if not 0.0 <= v <= 1.0:
        msg = f"value must be between 0.0 and 1.0, got {v}"
        raise ValueError(msg)
    return v


UnitFloat = Annotated[float, AfterValidator(_validate_unit_range)]
"""Float constrained to [0.0, 1.0]. Used for scores, weights, and confidences."""


def _validate_non_negative_int(v: int) -> int:
    """Validate that an int is >= 0."""
    if v < 0:
        msg = f"value must be >= 0, got {v}"
        raise ValueError(msg)
    return v


NonNegativeInt = Annotated[int, AfterValidator(_validate_non_negative_int)]
"""Int constrained to >= 0. Used for counts."""


def _validate_non_positive_float(v: float) -> float:
    """Validate that a float is <= 0.0."""
    if v > 0.0:
        msg = f"value must be <= 0.0, got {v}"
        raise ValueError(msg)
    return v


NonPositiveFloat = Annotated[float, AfterValidator(_validate_non_positive_float)]
"""Float constrained to <= 0.0. Used for max_drawdown (always negative or zero)."""


def _validate_adjustment_range(v: float) -> float:
    """Validate that a float is in [-1.0, 1.0]."""
    if not -1.0 <= v <= 1.0:
        msg = f"adjustment must be between -1.0 and 1.0, got {v}"
        raise ValueError(msg)
    return v


AdjustmentFloat = Annotated[float, AfterValidator(_validate_adjustment_range)]
"""Float constrained to [-1.0, 1.0]. Used for confidence adjustments."""


_SAFE_TICKER_RE: re.Pattern[str] = re.compile(r"^[A-Z0-9./]{1,10}$")


def _validate_ticker(v: str) -> str:
    """Validate ticker symbol format: uppercase alphanumeric with . or / allowed."""
    if not _SAFE_TICKER_RE.match(v):
        msg = f"Invalid ticker format: {v!r}. Must match ^[A-Z0-9./]{{1,10}}$"
        raise ValueError(msg)
    return v


TickerStr = Annotated[str, AfterValidator(_validate_ticker)]
"""Ticker symbol constrained to uppercase alphanumeric with . or / (1-10 chars)."""

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
type ClaimType = Literal["competitive_advantage", "cagr_connection", "factual_claim"]

type PowerType = Literal[
    "scale_economies",
    "network_economies",
    "counter_positioning",
    "switching_costs",
    "branding",
    "cornered_resource",
    "process_power",
]
"""Hamilton Helmer's 7 Powers classification for competitive advantages."""


# ===========================================================================
# Transcript models
# ===========================================================================
class TranscriptSection(BaseModel):
    """A single section of an earnings call transcript.

    Parameters
    ----------
    speaker : str
        Name of the speaker (e.g. "Tim Cook").
    role : str | None
        Role of the speaker (e.g. "CEO", "CFO").  None for operator.
    section_type : str
        Type of section (e.g. "prepared_remarks", "q_and_a", "operator").
    content : str
        Text content of this section.
    """

    model_config = ConfigDict(frozen=True)

    speaker: NonEmptyStr
    role: str | None
    section_type: str
    content: NonEmptyStr


class TranscriptMetadata(BaseModel):
    """Metadata for an earnings call transcript.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g. "AAPL").
    event_date : date
        Date of the earnings call.
    fiscal_quarter : str
        Fiscal quarter label (e.g. "Q1 2024").
    is_truncated : bool
        Whether the transcript was truncated due to length limits.
    """

    model_config = ConfigDict(frozen=True)

    ticker: TickerStr
    event_date: date
    fiscal_quarter: NonEmptyStr
    is_truncated: bool = False


class Transcript(BaseModel):
    """Complete earnings call transcript.

    Parameters
    ----------
    metadata : TranscriptMetadata
        Metadata about the transcript (ticker, date, quarter).
    sections : list[TranscriptSection]
        Ordered list of transcript sections.  Must not be empty.
    raw_source : str | None
        Original raw transcript text, if available.
    """

    model_config = ConfigDict(frozen=True)

    metadata: TranscriptMetadata
    sections: list[TranscriptSection]
    raw_source: str | None = None

    @field_validator("sections")
    @classmethod
    def _sections_non_empty(cls, v: list[TranscriptSection]) -> list[TranscriptSection]:
        """Validate that sections list contains at least one entry."""
        if not v:
            msg = "sections must contain at least one section"
            raise ValueError(msg)
        return v


# ===========================================================================
# Phase 1 structured extraction models (7 Powers)
# ===========================================================================
class PowerClassification(BaseModel):
    """7 Powers classification for a competitive advantage claim.

    Parameters
    ----------
    power_type : PowerType
        Which of the 7 Powers this claim maps to.
    benefit : str
        The specific benefit this Power provides (e.g. cost advantage, premium pricing).
    barrier : str
        The structural barrier preventing competitor imitation.
    """

    model_config = ConfigDict(frozen=True)

    power_type: PowerType
    benefit: NonEmptyStr
    barrier: NonEmptyStr


class EvidenceSource(BaseModel):
    """Source location and context for a claim within the transcript.

    Parameters
    ----------
    speaker : str
        Name of the speaker who made the statement.
    role : str | None
        Role of the speaker (e.g. "CEO", "CFO").
    section_type : str
        Transcript section type (e.g. "prepared_remarks", "q_and_a").
    quarter : str
        Fiscal quarter of the transcript (e.g. "Q1 2015").
    quote : str
        Direct quote or paraphrase from the transcript.
    """

    model_config = ConfigDict(frozen=True)

    speaker: NonEmptyStr
    role: str | None
    section_type: NonEmptyStr
    quarter: NonEmptyStr
    quote: NonEmptyStr


# ===========================================================================
# Phase 1 output models
# ===========================================================================
class RuleEvaluation(BaseModel):
    """Result of applying KB1 rules to a claim.

    Parameters
    ----------
    applied_rules : list[str]
        List of rule identifiers that were applied.
    results : dict[str, bool]
        Mapping of rule ID to pass/fail result.
    confidence : float
        Confidence score between 0.0 and 1.0.
    adjustments : list[str]
        List of adjustment descriptions applied.
    """

    model_config = ConfigDict(frozen=True)

    applied_rules: list[str]
    results: dict[str, bool]
    confidence: UnitFloat
    adjustments: list[str]


class Claim(BaseModel):
    """A claim extracted from a transcript with rule evaluation.

    Parameters
    ----------
    id : str
        Unique identifier for the claim.
    claim_type : ClaimType
        Type of claim: competitive_advantage, cagr_connection, or factual_claim.
    claim : str
        The claim text.
    evidence : str
        Supporting evidence for the claim.
    rule_evaluation : RuleEvaluation
        Results of applying KB1 rules.
    power_classification : PowerClassification | None
        7 Powers classification (Phase 1 structured extraction).
        None for claims extracted without 7 Powers framework.
    evidence_sources : list[EvidenceSource]
        Transcript source locations for this claim.
    """

    model_config = ConfigDict(frozen=True)

    id: NonEmptyStr
    claim_type: ClaimType
    claim: NonEmptyStr
    evidence: str
    rule_evaluation: RuleEvaluation
    power_classification: PowerClassification | None = None
    evidence_sources: list[EvidenceSource] = Field(default_factory=list)


# ===========================================================================
# Phase 2 structured evaluation models
# ===========================================================================
class GatekeeperResult(BaseModel):
    """Result of gatekeeper rule checks (immediate rejection/downgrade).

    Parameters
    ----------
    rule9_factual_error : bool
        True if a factual error was detected (-> confidence 10%).
    rule3_industry_common : bool
        True if the claimed advantage is industry-common (-> confidence <= 30%).
    triggered : bool
        True if any gatekeeper rule was triggered.
    override_confidence : float | None
        If triggered, the overridden confidence value (0.0-1.0).
        None if no gatekeeper was triggered.
    """

    model_config = ConfigDict(frozen=True)

    rule9_factual_error: bool = False
    rule3_industry_common: bool = False
    triggered: bool = False
    override_confidence: UnitFloat | None = None


class KB1RuleApplication(BaseModel):
    """Result of applying a single KB1-T rule to a claim.

    Parameters
    ----------
    rule_id : str
        Rule identifier (e.g. "rule_1_t", "rule_6_t").
    result : bool
        Whether the rule passed (True) or failed (False).
    reasoning : str
        Explanation for the rule evaluation result.
    """

    model_config = ConfigDict(frozen=True)

    rule_id: NonEmptyStr
    result: bool
    reasoning: str


class KB2PatternMatch(BaseModel):
    """Result of matching a claim against a KB2-T pattern.

    Parameters
    ----------
    pattern_id : str
        Pattern identifier (e.g. "pattern_A", "pattern_I").
    matched : bool
        Whether the pattern was matched.
    adjustment : float
        Confidence adjustment value (-0.3 to +0.3).
    reasoning : str
        Explanation for the pattern match result.
    """

    model_config = ConfigDict(frozen=True)

    pattern_id: NonEmptyStr
    matched: bool
    adjustment: AdjustmentFloat
    reasoning: str


# ===========================================================================
# Phase 2 output models
# ===========================================================================
class ConfidenceAdjustment(BaseModel):
    """A confidence adjustment applied during Phase 2 scoring.

    Parameters
    ----------
    source : str
        Source of the adjustment (e.g. "pattern_I", "pattern_A").
    adjustment : float
        Adjustment value between -1.0 and 1.0.
    reasoning : str
        Explanation for the adjustment.
    """

    model_config = ConfigDict(frozen=True)

    source: str
    adjustment: AdjustmentFloat
    reasoning: str


class ScoredClaim(BaseModel):
    """A claim with final confidence score after Phase 2 adjustments.

    Extends Claim fields with scoring information.

    Parameters
    ----------
    id : str
        Unique identifier for the claim.
    claim_type : ClaimType
        Type of claim.
    claim : str
        The claim text.
    evidence : str
        Supporting evidence.
    rule_evaluation : RuleEvaluation
        Results of applying KB1 rules.
    final_confidence : float
        Final confidence score between 0.0 and 1.0 after adjustments.
    adjustments : list[ConfidenceAdjustment]
        List of adjustments applied.
    power_classification : PowerClassification | None
        7 Powers classification carried from Phase 1.
    evidence_sources : list[EvidenceSource]
        Transcript source locations carried from Phase 1.
    gatekeeper : GatekeeperResult | None
        Gatekeeper rule check results (Phase 2 structured evaluation).
    kb1_evaluations : list[KB1RuleApplication]
        Individual KB1-T rule application results.
    kb2_patterns : list[KB2PatternMatch]
        KB2-T pattern matching results.
    overall_reasoning : str
        Overall reasoning for the final confidence score.
    """

    model_config = ConfigDict(frozen=True)

    id: NonEmptyStr
    claim_type: ClaimType
    claim: NonEmptyStr
    evidence: str
    rule_evaluation: RuleEvaluation
    final_confidence: UnitFloat
    adjustments: list[ConfidenceAdjustment]
    power_classification: PowerClassification | None = None
    evidence_sources: list[EvidenceSource] = Field(default_factory=list)
    gatekeeper: GatekeeperResult | None = None
    kb1_evaluations: list[KB1RuleApplication] = Field(default_factory=list)
    kb2_patterns: list[KB2PatternMatch] = Field(default_factory=list)
    overall_reasoning: str = ""


# ===========================================================================
# Score / Portfolio models
# ===========================================================================
class StockScore(BaseModel):
    """Aggregate score for a single stock.

    Parameters
    ----------
    ticker : str
        Ticker symbol.
    aggregate_score : float
        Aggregate score between 0.0 and 1.0.
    claim_count : int
        Number of claims contributing to the score.  Must be >= 0.
    structural_weight : float
        Weight of structural (competitive advantage) claims, 0.0-1.0.
    """

    model_config = ConfigDict(frozen=True)

    ticker: NonEmptyStr
    aggregate_score: UnitFloat
    claim_count: NonNegativeInt
    structural_weight: UnitFloat


class PortfolioHolding(BaseModel):
    """A single holding in the constructed portfolio.

    Parameters
    ----------
    ticker : str
        Ticker symbol.
    weight : float
        Portfolio weight, 0.0-1.0.
    sector : str
        GICS sector name.
    score : float
        Stock score, 0.0-1.0.
    rationale_summary : str
        Brief rationale for inclusion.
    """

    model_config = ConfigDict(frozen=True)

    ticker: NonEmptyStr
    weight: UnitFloat
    sector: NonEmptyStr
    score: UnitFloat
    rationale_summary: str


class SectorAllocation(BaseModel):
    """Sector-level allocation in the portfolio.

    Parameters
    ----------
    sector : str
        GICS sector name.
    benchmark_weight : float
        Benchmark sector weight, 0.0-1.0.
    actual_weight : float
        Actual portfolio sector weight, 0.0-1.0.
    stock_count : int
        Number of stocks from this sector in the portfolio.  Must be >= 0.
    """

    model_config = ConfigDict(frozen=True)

    sector: NonEmptyStr
    benchmark_weight: UnitFloat
    actual_weight: UnitFloat
    stock_count: NonNegativeInt


class PortfolioResult(BaseModel):
    """Complete portfolio construction result.

    Parameters
    ----------
    holdings : list[PortfolioHolding]
        List of portfolio holdings with weights.
    sector_allocations : list[SectorAllocation]
        Sector-level allocations.
    as_of_date : date
        As-of date for the portfolio.
    """

    model_config = ConfigDict(frozen=True)

    holdings: list[PortfolioHolding]
    sector_allocations: list[SectorAllocation]
    as_of_date: date


# ===========================================================================
# Configuration models
# ===========================================================================
class UniverseTicker(BaseModel):
    """A ticker entry in the investment universe.

    Parameters
    ----------
    ticker : str
        Ticker symbol.
    gics_sector : str
        GICS sector classification.
    bloomberg_ticker : str
        Bloomberg ticker identifier including exchange code
        (e.g. ``"AAPL US Equity"``).  Defaults to ``""`` for
        backward compatibility with existing universe files.
    """

    model_config = ConfigDict(frozen=True)

    ticker: NonEmptyStr
    gics_sector: NonEmptyStr
    bloomberg_ticker: str = ""


class UniverseConfig(BaseModel):
    """Investment universe configuration.

    Parameters
    ----------
    tickers : list[UniverseTicker]
        List of tickers in the universe.  Must not be empty.
    """

    model_config = ConfigDict(frozen=True)

    tickers: list[UniverseTicker]

    @field_validator("tickers")
    @classmethod
    def _tickers_non_empty(cls, v: list[UniverseTicker]) -> list[UniverseTicker]:
        """Validate that tickers list contains at least one entry."""
        if not v:
            msg = "tickers must contain at least one ticker"
            raise ValueError(msg)
        return v


class BenchmarkWeight(BaseModel):
    """Benchmark sector weight.

    Parameters
    ----------
    sector : str
        GICS sector name.
    weight : float
        Sector weight in the benchmark, 0.0-1.0.
    """

    model_config = ConfigDict(frozen=True)

    sector: NonEmptyStr
    weight: UnitFloat


# ===========================================================================
# Evaluation models (Phase 6: StrategyEvaluator output)
# ===========================================================================
class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics relative to a benchmark.

    Parameters
    ----------
    sharpe_ratio : float
        Annualized Sharpe ratio of the portfolio.
    max_drawdown : float
        Maximum drawdown (negative value, e.g. -0.12 = -12%).
    beta : float
        Portfolio beta relative to benchmark.
    information_ratio : float
        Information ratio (active return / tracking error).
    cumulative_return : float
        Cumulative total return over the evaluation period.
    """

    model_config = ConfigDict(frozen=True)

    sharpe_ratio: float
    max_drawdown: NonPositiveFloat
    beta: float
    information_ratio: float
    cumulative_return: float


class AnalystCorrelation(BaseModel):
    """Analyst score correlation results.

    Parameters
    ----------
    spearman_correlation : float | None
        Spearman rank correlation between strategy scores and analyst scores.
        None if sample size < 2.
    sample_size : int
        Number of tickers with both strategy and analyst scores.
    p_value : float | None
        Two-tailed p-value for the correlation.  None if sample_size < 2.
    hit_rate : float | None
        Fraction of top-20% strategy stocks also in top-20% analyst scores.
        None if sample_size == 0.
    """

    model_config = ConfigDict(frozen=True)

    spearman_correlation: float | None
    sample_size: int
    p_value: UnitFloat | None
    hit_rate: UnitFloat | None


class TransparencyMetrics(BaseModel):
    """Transparency metrics for portfolio evaluation.

    Parameters
    ----------
    mean_claim_count : float
        Average number of claims per portfolio holding.
    mean_structural_weight : float
        Average structural (competitive advantage) claim weight.
    coverage_rate : float
        Fraction of holdings with at least one claim.  In [0.0, 1.0].
    """

    model_config = ConfigDict(frozen=True)

    mean_claim_count: float
    mean_structural_weight: float
    coverage_rate: UnitFloat


class AnalystScore(BaseModel):
    """Analyst score for a single ticker.

    Parameters
    ----------
    ticker : str
        Ticker symbol.
    ky : int | None
        KY analyst score (integer rank).  None if not available.
    ak : int | None
        AK analyst score (integer rank).  None if not available.
    """

    model_config = ConfigDict(frozen=True)

    ticker: NonEmptyStr
    ky: int | None = None
    ak: int | None = None


class EvaluationResult(BaseModel):
    """Complete strategy evaluation result for a given threshold.

    Parameters
    ----------
    threshold : float
        Score threshold used to construct the equal-weight portfolio.
    portfolio_size : int
        Number of holdings in the equal-weight portfolio.
    performance : PerformanceMetrics
        Performance metrics relative to benchmark.
    analyst_correlation : AnalystCorrelation
        Correlation with analyst scores.
    transparency : TransparencyMetrics
        Transparency metrics for portfolio holdings.
    as_of_date : date
        The evaluation as-of date (end of measurement period).
    """

    model_config = ConfigDict(frozen=True)

    threshold: float
    portfolio_size: int
    performance: PerformanceMetrics
    analyst_correlation: AnalystCorrelation
    transparency: TransparencyMetrics
    as_of_date: date
