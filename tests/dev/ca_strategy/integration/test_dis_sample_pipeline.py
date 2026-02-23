"""Integration tests for DIS sample pipeline (Issue #3629).

Tests the end-to-end agent_io.py pipeline using real DIS transcript data
from ``research/ca_strategy_poc/workspace_dis_sample/transcripts/DIS/``:

1. ``prepare_extraction_input()`` -- real DIS transcripts, PoiT filtering
2. ``validate_extraction_output()`` -- mock DIS claims JSON (agent-style output)
3. ``prepare_scoring_input()`` -- real KB paths
4. ``validate_scoring_output()`` -- mock scoring output with ID restoration

Acceptance criteria (Issue #3629):
- prepare_extraction_input returns >= 1 transcript path for DIS (PoiT filtered)
- validate_extraction_output validates Claim models from mock extraction output
- Pydantic Claim model passes for 5-15 claims with required fields
- each Claim has rule_evaluation, evidence_sources, power_classification
- validate_scoring_output validates ScoredClaim models from mock scoring output
- all ScoredClaim have final_confidence in [0.1, 0.9]
- gatekeeper, kb1_evaluations, kb2_patterns, overall_reasoning are present

Notes
-----
These tests do NOT spawn LLM agents; instead they validate the Python I/O
helper functions with realistic DIS-style fixture data, ensuring the pipeline
layers work correctly with real directory structures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from dev.ca_strategy.agent_io import (
    prepare_extraction_input,
    prepare_scoring_input,
    validate_extraction_output,
    validate_scoring_output,
)
from dev.ca_strategy.pit import CUTOFF_DATE
from dev.ca_strategy.types import (
    Claim,
    GatekeeperResult,
    KB1RuleApplication,
    KB2PatternMatch,
    RuleEvaluation,
    ScoredClaim,
)

# ---------------------------------------------------------------------------
# Paths to real sample data (read-only)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent  # finance/
_WORKSPACE_DIR = _REPO_ROOT / "research" / "ca_strategy_poc" / "workspace_dis_sample"
_TRANSCRIPT_DIR = _WORKSPACE_DIR / "transcripts"
_KB_BASE_DIR = _REPO_ROOT / "analyst" / "transcript_eval"
_CONFIG_PATH = _REPO_ROOT / "research" / "ca_strategy_poc" / "config_dis_sample"

_TICKER = "DIS"

# Number of DIS transcripts within PoiT cutoff (201402 - 201508, 7 files)
_EXPECTED_MIN_TRANSCRIPTS = 1

# Acceptance criteria bounds for claim counts
_CLAIM_COUNT_MIN = 5
_CLAIM_COUNT_MAX = 15

# Acceptance criteria for final_confidence range
_CONFIDENCE_MIN = 0.1
_CONFIDENCE_MAX = 0.9


# ---------------------------------------------------------------------------
# Skip guards for optional real data
# ---------------------------------------------------------------------------
_HAS_TRANSCRIPT_DIR = _TRANSCRIPT_DIR.exists() and any(
    _TRANSCRIPT_DIR.glob("DIS/*.json")
)
_HAS_KB_DIR = _KB_BASE_DIR.exists() and (_KB_BASE_DIR / "kb1_rules_transcript").exists()

_SKIP_IF_NO_TRANSCRIPTS = pytest.mark.skipif(
    not _HAS_TRANSCRIPT_DIR,
    reason="DIS transcript fixtures not present in research/ (run /run-ca-strategy-sample first)",
)
_SKIP_IF_NO_KB = pytest.mark.skipif(
    not _HAS_KB_DIR,
    reason="KB base directory not present in analyst/transcript_eval/",
)


# ---------------------------------------------------------------------------
# Helpers: build realistic DIS-style fixture data
# ---------------------------------------------------------------------------


def _dis_raw_claim(
    n: int,
    confidence: float = 0.7,
    include_power: bool = True,
    include_evidence_sources: bool = True,
) -> dict[str, Any]:
    """Build a realistic DIS Phase 1 claim dict (as emitted by the agent).

    Parameters
    ----------
    n : int
        Claim index (used to ensure unique IDs).
    confidence : float
        rule_evaluation.confidence value.
    include_power : bool
        Whether to include power_classification field.
    include_evidence_sources : bool
        Whether to include evidence_sources list.
    """
    claim: dict[str, Any] = {
        "id": f"DIS-CA-{n:03d}",
        "claim_type": "competitive_advantage",
        "claim": f"Disney maintains structural advantage {n} through its franchise ecosystem.",
        "evidence": f"CEO stated in Q1 2015 earnings call that segment {n} outperformed peers.",
        "rule_evaluation": {
            "applied_rules": ["rule_1_t", "rule_6_t"],
            "results": {"rule_1_t": True, "rule_6_t": True},
            "confidence": confidence,
            "adjustments": [],
        },
    }
    if include_power:
        claim["power_classification"] = {
            "power_type": "branding",
            "benefit": "Premium pricing through iconic franchise characters",
            "barrier": "Accumulated goodwill and emotional connection built over decades",
        }
    if include_evidence_sources:
        claim["evidence_sources"] = [
            {
                "speaker": "Robert Iger",
                "role": "CEO",
                "section_type": "prepared_remarks",
                "quarter": f"Q{n % 4 + 1} 2015",
                "quote": f"Our franchise-driven model delivered record results in segment {n}.",
            }
        ]
    return claim


def _build_extraction_output(n_claims: int = 8) -> dict[str, Any]:
    """Build a Phase 1 extraction output JSON with n_claims DIS claims."""
    return {
        "ticker": _TICKER,
        "transcript_source": "DIS Q1-Q3 2015 Earnings Calls",
        "extraction_date": "2026-02-23",
        "claims": [_dis_raw_claim(i + 1) for i in range(n_claims)],
    }


def _dis_raw_scored_claim(
    claim_id: str,
    final_confidence: float = 0.65,
    gatekeeper_triggered: bool = False,
) -> dict[str, Any]:
    """Build a realistic DIS Phase 2 scored claim dict."""
    scored: dict[str, Any] = {
        "id": claim_id,
        "final_confidence": final_confidence,
        "gatekeeper": {
            "rule9_factual_error": False,
            "rule3_industry_common": gatekeeper_triggered,
            "triggered": gatekeeper_triggered,
            "override_confidence": 0.2 if gatekeeper_triggered else None,
        },
        "kb1_evaluations": [
            {
                "rule_id": "rule_1_t",
                "result": True,
                "reasoning": "Claim specifies a capability, not merely a result.",
            },
            {
                "rule_id": "rule_6_t",
                "result": True,
                "reasoning": "Structural advantage clearly distinguished from complementary.",
            },
        ],
        "kb2_patterns": [
            {
                "pattern_id": "pattern_III",
                "matched": True,
                "adjustment": 0.15,
                "reasoning": "Capability-over-result pattern confirmed by CEO specificity.",
            }
        ],
        "confidence_adjustments": [
            {
                "source": "kb2_pattern_III",
                "adjustment": 0.15,
                "reasoning": "High-confidence pattern match adds 0.15.",
            }
        ],
        "overall_reasoning": (
            "Disney's franchise ecosystem claim passes gatekeeper and KB1-T rules. "
            "KB2-T pattern III (capability over result) matches, boosting confidence."
        ),
    }
    return scored


def _build_scoring_output(claim_ids: list[str]) -> dict[str, Any]:
    """Build a Phase 2 scoring output JSON for the given claim IDs."""
    # Use 0.3-triggered gatekeeper for one claim to simulate realistic distribution
    scored_claims = []
    for i, claim_id in enumerate(claim_ids):
        triggered = i == 0  # first claim triggers gatekeeper (industry common)
        confidence = 0.2 if triggered else (0.5 + (i % 5) * 0.1)
        scored_claims.append(
            _dis_raw_scored_claim(
                claim_id=claim_id,
                final_confidence=confidence,
                gatekeeper_triggered=triggered,
            )
        )
    return {
        "ticker": _TICKER,
        "phase": "phase2",
        "scored_claims": scored_claims,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_workspace(tmp_path: Path) -> Path:
    """Return an isolated workspace directory for each test."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    return ws


@pytest.fixture()
def dis_extraction_output_path(tmp_path: Path) -> Path:
    """Write a realistic DIS Phase 1 extraction output to tmp_path."""
    output_dir = tmp_path / "phase1_output" / _TICKER
    output_dir.mkdir(parents=True)
    output_path = output_dir / "extraction_output.json"
    data = _build_extraction_output(n_claims=8)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


@pytest.fixture()
def dis_claims(dis_extraction_output_path: Path) -> list[Claim]:
    """Return validated Claim list from the DIS fixture output."""
    return validate_extraction_output(
        output_path=dis_extraction_output_path,
        ticker=_TICKER,
    )


# ===========================================================================
# Phase 0 / Step 0: ANTHROPIC_API_KEY not required
# ===========================================================================


class TestNoApiKeyRequired:
    """The Python helper functions must not use ANTHROPIC_API_KEY."""

    def test_正常系_agent_io関数はanthropic_sdkをインポートしない(self) -> None:
        """agent_io.py must not import the anthropic SDK (no ANTHROPIC_API_KEY needed)."""
        agent_io_source = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "dev"
            / "ca_strategy"
            / "agent_io.py"
        ).read_text(encoding="utf-8")

        # anthropic SDK import would require ANTHROPIC_API_KEY
        assert "import anthropic" not in agent_io_source, (
            "agent_io.py must not import anthropic SDK. "
            "Agents are invoked via Claude Code Task tool, not the Python SDK."
        )
        assert "from anthropic" not in agent_io_source, (
            "agent_io.py must not import from anthropic package."
        )


# ===========================================================================
# Phase 1: prepare_extraction_input with real DIS transcripts
# ===========================================================================


class TestPrepareExtractionInputWithRealDIS:
    """Integration tests for prepare_extraction_input() with real DIS data."""

    @_SKIP_IF_NO_TRANSCRIPTS
    @_SKIP_IF_NO_KB
    def test_正常系_DIS実データでextraction_input_jsonが生成される(
        self, isolated_workspace: Path
    ) -> None:
        """prepare_extraction_input() must create extraction_input.json for real DIS data."""
        result = prepare_extraction_input(
            config_path=_CONFIG_PATH,
            transcript_dir=_TRANSCRIPT_DIR,
            kb_base_dir=_KB_BASE_DIR,
            ticker=_TICKER,
            workspace_dir=isolated_workspace,
        )

        output_path = isolated_workspace / "extraction_input.json"
        assert output_path.exists(), "extraction_input.json must be created"

        # Verify content is valid JSON matching the returned dict
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        assert stored["ticker"] == _TICKER
        assert stored["transcript_paths"] == result["transcript_paths"]
        assert stored["cutoff_date"] == CUTOFF_DATE.isoformat()

    @_SKIP_IF_NO_TRANSCRIPTS
    def test_正常系_DISのPoiTフィルタリング済みトランスクリプトが含まれる(
        self, isolated_workspace: Path
    ) -> None:
        """DIS transcripts within the PoiT cutoff (2015-09-30) must be included."""
        result = prepare_extraction_input(
            config_path=_CONFIG_PATH,
            transcript_dir=_TRANSCRIPT_DIR,
            kb_base_dir=_KB_BASE_DIR if _HAS_KB_DIR else isolated_workspace,
            ticker=_TICKER,
            workspace_dir=isolated_workspace,
        )

        paths = result["transcript_paths"]
        assert len(paths) >= _EXPECTED_MIN_TRANSCRIPTS, (
            f"Expected at least {_EXPECTED_MIN_TRANSCRIPTS} DIS transcripts "
            f"within PoiT cutoff, got {len(paths)}"
        )
        # All paths must reference DIS
        assert all(_TICKER in p for p in paths), (
            "All transcript paths must reference the DIS ticker"
        )

    @_SKIP_IF_NO_TRANSCRIPTS
    def test_正常系_DIS_201511トランスクリプトはPoiT対象外で除外される(
        self, isolated_workspace: Path
    ) -> None:
        """The 201511 (Nov 2015) DIS transcript is after PoiT cutoff and must be excluded.

        PoiT cutoff is 2015-09-30. Q4 2015 earnings (event_date ~2015-11-05)
        is after the cutoff and must not appear in transcript_paths.
        """
        result = prepare_extraction_input(
            config_path=_CONFIG_PATH,
            transcript_dir=_TRANSCRIPT_DIR,
            kb_base_dir=_KB_BASE_DIR if _HAS_KB_DIR else isolated_workspace,
            ticker=_TICKER,
            workspace_dir=isolated_workspace,
        )

        paths = result["transcript_paths"]
        assert all("201511" not in p for p in paths), (
            "Q4 FY2015 DIS transcript (201511) is after PoiT cutoff 2015-09-30 and must be excluded"
        )

    @_SKIP_IF_NO_KB
    def test_正常系_KBディレクトリパスが正しく含まれる(
        self, isolated_workspace: Path
    ) -> None:
        """KB directory paths in the payload must point to existing directories."""
        result = prepare_extraction_input(
            config_path=_CONFIG_PATH,
            transcript_dir=_TRANSCRIPT_DIR
            if _HAS_TRANSCRIPT_DIR
            else isolated_workspace,
            kb_base_dir=_KB_BASE_DIR,
            ticker=_TICKER,
            workspace_dir=isolated_workspace,
        )

        kb1_dir = Path(result["kb1_dir"])
        kb3_dir = Path(result["kb3_dir"])

        assert kb1_dir.exists(), f"kb1_dir must exist: {kb1_dir}"
        assert kb3_dir.exists(), f"kb3_dir must exist: {kb3_dir}"
        assert "kb1_rules_transcript" in str(kb1_dir)
        assert "kb3_fewshot_transcript" in str(kb3_dir)


# ===========================================================================
# Phase 1: validate_extraction_output with DIS-style mock claims
# ===========================================================================


class TestValidateExtractionOutputDIS:
    """Integration tests for validate_extraction_output() with DIS-style mock data."""

    def test_正常系_8件のDISクレームがPydanticバリデーションを通過する(
        self, tmp_path: Path
    ) -> None:
        """8 realistic DIS claims must all pass Pydantic Claim validation."""
        n_claims = 8
        output_dir = tmp_path / "phase1_output" / _TICKER
        output_dir.mkdir(parents=True)
        output_path = output_dir / "extraction_output.json"
        data = _build_extraction_output(n_claims=n_claims)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker=_TICKER)

        assert len(claims) == n_claims, (
            f"Expected {n_claims} validated claims, got {len(claims)}"
        )
        assert all(isinstance(c, Claim) for c in claims), (
            "All returned objects must be Claim instances"
        )

    def test_正常系_クレーム件数が受け入れ条件5から15の範囲内(
        self, dis_extraction_output_path: Path
    ) -> None:
        """Validated claim count must be within [5, 15] per acceptance criteria."""
        claims = validate_extraction_output(
            output_path=dis_extraction_output_path, ticker=_TICKER
        )

        count = len(claims)
        assert _CLAIM_COUNT_MIN <= count <= _CLAIM_COUNT_MAX, (
            f"Claim count {count} is outside the acceptance criteria range "
            f"[{_CLAIM_COUNT_MIN}, {_CLAIM_COUNT_MAX}]"
        )

    def test_正常系_各クレームにrule_evaluationが含まれる(
        self, dis_extraction_output_path: Path
    ) -> None:
        """Every Claim must have a rule_evaluation field (acceptance criteria)."""
        claims = validate_extraction_output(
            output_path=dis_extraction_output_path, ticker=_TICKER
        )

        for claim in claims:
            assert isinstance(claim.rule_evaluation, RuleEvaluation), (
                f"Claim {claim.id} must have rule_evaluation, got {type(claim.rule_evaluation)}"
            )
            assert 0.0 <= claim.rule_evaluation.confidence <= 1.0, (
                f"Claim {claim.id} confidence {claim.rule_evaluation.confidence} "
                f"must be in [0.0, 1.0]"
            )

    def test_正常系_各クレームにevidence_sourcesが含まれる(
        self, dis_extraction_output_path: Path
    ) -> None:
        """Every Claim must have at least one evidence_source (acceptance criteria)."""
        claims = validate_extraction_output(
            output_path=dis_extraction_output_path, ticker=_TICKER
        )

        for claim in claims:
            assert len(claim.evidence_sources) >= 1, (
                f"Claim {claim.id} must have evidence_sources, got empty list"
            )

    def test_正常系_各クレームにpower_classificationが含まれる(
        self, dis_extraction_output_path: Path
    ) -> None:
        """Every Claim must have power_classification (acceptance criteria)."""
        claims = validate_extraction_output(
            output_path=dis_extraction_output_path, ticker=_TICKER
        )

        for claim in claims:
            assert claim.power_classification is not None, (
                f"Claim {claim.id} must have power_classification"
            )

    def test_正常系_DIS_IDプレフィックスが含まれる(
        self, dis_extraction_output_path: Path
    ) -> None:
        """Claim IDs must contain the ticker DIS prefix."""
        claims = validate_extraction_output(
            output_path=dis_extraction_output_path, ticker=_TICKER
        )

        for claim in claims:
            assert _TICKER in claim.id, (
                f"Claim ID {claim.id!r} must contain the ticker {_TICKER!r}"
            )

    def test_正常系_confidence_パーセント値を正規化する(self, tmp_path: Path) -> None:
        """Confidence values expressed as percentages (e.g. 70) must be normalized to 0.7."""
        output_dir = tmp_path / "phase1_percent"
        output_dir.mkdir(parents=True)
        output_path = output_dir / "extraction_output.json"

        # Use percentage confidence
        raw_claim = _dis_raw_claim(1, confidence=70)
        data = {"ticker": _TICKER, "claims": [raw_claim]}
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker=_TICKER)

        assert len(claims) == 1
        assert abs(claims[0].rule_evaluation.confidence - 0.7) < 1e-6, (
            f"Expected confidence 0.7 after normalization, got {claims[0].rule_evaluation.confidence}"
        )


# ===========================================================================
# Phase 2: prepare_scoring_input with real KB paths
# ===========================================================================


class TestPrepareScoringInputDIS:
    """Integration tests for prepare_scoring_input() with DIS-style workspace."""

    def test_正常系_scoring_input_jsonが生成される(
        self, isolated_workspace: Path
    ) -> None:
        """prepare_scoring_input() must create scoring_input.json."""
        result = prepare_scoring_input(
            workspace_dir=isolated_workspace,
            kb_base_dir=_KB_BASE_DIR if _HAS_KB_DIR else isolated_workspace,
            ticker=_TICKER,
        )

        output_path = isolated_workspace / "scoring_input.json"
        assert output_path.exists(), "scoring_input.json must be created"

        stored = json.loads(output_path.read_text(encoding="utf-8"))
        assert stored["ticker"] == _TICKER
        assert stored["ticker"] == result["ticker"]

    def test_正常系_phase1出力パスにDISが含まれる(
        self, isolated_workspace: Path
    ) -> None:
        """phase1_output_dir must reference the DIS ticker subdirectory."""
        result = prepare_scoring_input(
            workspace_dir=isolated_workspace,
            kb_base_dir=_KB_BASE_DIR if _HAS_KB_DIR else isolated_workspace,
            ticker=_TICKER,
        )

        assert _TICKER in result["phase1_output_dir"], (
            f"phase1_output_dir must reference {_TICKER}: {result['phase1_output_dir']}"
        )

    @_SKIP_IF_NO_KB
    def test_正常系_実KBディレクトリへのパスが含まれる(
        self, isolated_workspace: Path
    ) -> None:
        """KB paths in payload must point to existing directories."""
        result = prepare_scoring_input(
            workspace_dir=isolated_workspace,
            kb_base_dir=_KB_BASE_DIR,
            ticker=_TICKER,
        )

        assert Path(result["kb1_dir"]).exists(), (
            f"kb1_dir must exist: {result['kb1_dir']}"
        )
        assert Path(result["kb2_dir"]).exists(), (
            f"kb2_dir must exist: {result['kb2_dir']}"
        )
        assert Path(result["kb3_dir"]).exists(), (
            f"kb3_dir must exist: {result['kb3_dir']}"
        )
        assert "kb1_rules_transcript" in result["kb1_dir"]
        assert "kb2_patterns_transcript" in result["kb2_dir"]
        assert "kb3_fewshot_transcript" in result["kb3_dir"]


# ===========================================================================
# Phase 2: validate_scoring_output with DIS-style mock scored claims
# ===========================================================================


class TestValidateScoringOutputDIS:
    """Integration tests for validate_scoring_output() with DIS-style mock data."""

    def test_正常系_全ScoredClaimがPydanticバリデーションを通過する(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """All ScoredClaim objects from mock DIS scoring output must pass validation."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        assert len(scored) == len(dis_claims), (
            f"Expected {len(dis_claims)} scored claims, got {len(scored)}"
        )
        assert all(isinstance(s, ScoredClaim) for s in scored), (
            "All returned objects must be ScoredClaim instances"
        )

    def test_正常系_全final_confidenceが0_1から0_9の範囲内(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """All final_confidence values must be in [0.1, 0.9] per acceptance criteria."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        out_of_range = [
            s
            for s in scored
            if not (_CONFIDENCE_MIN <= s.final_confidence <= _CONFIDENCE_MAX)
        ]
        assert len(out_of_range) == 0, (
            f"{len(out_of_range)} claims have final_confidence outside "
            f"[{_CONFIDENCE_MIN}, {_CONFIDENCE_MAX}]: "
            + ", ".join(f"{s.id}={s.final_confidence}" for s in out_of_range)
        )

    def test_正常系_gatekeeper判定結果が含まれる(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """ScoredClaim must include gatekeeper judgment result (acceptance criteria)."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        # At least one claim should have gatekeeper info
        claims_with_gatekeeper = [s for s in scored if s.gatekeeper is not None]
        assert len(claims_with_gatekeeper) >= 1, (
            "At least one ScoredClaim must have a GatekeeperResult"
        )
        for claim in claims_with_gatekeeper:
            assert isinstance(claim.gatekeeper, GatekeeperResult)

    def test_正常系_kb1_evaluationsが含まれる(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """ScoredClaim must include kb1_evaluations (acceptance criteria)."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        for claim in scored:
            assert len(claim.kb1_evaluations) >= 1, (
                f"ScoredClaim {claim.id} must have kb1_evaluations"
            )
            for eval_item in claim.kb1_evaluations:
                assert isinstance(eval_item, KB1RuleApplication)

    def test_正常系_kb2_patternsが含まれる(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """ScoredClaim must include kb2_patterns (acceptance criteria)."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        for claim in scored:
            assert len(claim.kb2_patterns) >= 1, (
                f"ScoredClaim {claim.id} must have kb2_patterns"
            )
            for pat in claim.kb2_patterns:
                assert isinstance(pat, KB2PatternMatch)

    def test_正常系_overall_reasoningが含まれる(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """ScoredClaim must include overall_reasoning (acceptance criteria)."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        for claim in scored:
            assert claim.overall_reasoning, (
                f"ScoredClaim {claim.id} must have a non-empty overall_reasoning"
            )

    def test_正常系_Phase1のクレーム情報をID照合で復元する(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """validate_scoring_output must restore Phase 1 claim text/evidence via ID lookup."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        claim_lookup = {c.id: c for c in dis_claims}
        for scored_claim in scored:
            original = claim_lookup.get(scored_claim.id)
            if original is not None:
                assert scored_claim.claim == original.claim, (
                    f"Claim text mismatch for {scored_claim.id}: "
                    f"expected {original.claim!r}, got {scored_claim.claim!r}"
                )
                assert scored_claim.evidence == original.evidence, (
                    f"Evidence mismatch for {scored_claim.id}"
                )

    def test_正常系_ゲートキーパー判定により低い確信度が付与される(
        self, dis_claims: list[Claim], tmp_path: Path
    ) -> None:
        """Gatekeeper-triggered claims must receive override_confidence (≤ 0.3)."""
        claim_ids = [c.id for c in dis_claims]
        scoring_data = _build_scoring_output(claim_ids)
        output_path = tmp_path / "scoring_output.json"
        output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker=_TICKER,
            original_claims=dis_claims,
        )

        # The first claim has gatekeeper_triggered=True and final_confidence=0.2
        triggered_claims = [
            s for s in scored if s.gatekeeper and s.gatekeeper.triggered
        ]
        assert len(triggered_claims) >= 1, (
            "At least one claim should have gatekeeper triggered"
        )

        for triggered in triggered_claims:
            assert triggered.final_confidence <= 0.3, (
                f"Gatekeeper-triggered claim {triggered.id} should have "
                f"final_confidence <= 0.3 (industry common penalty), "
                f"got {triggered.final_confidence}"
            )


# ===========================================================================
# End-to-end: Full pipeline flow with mock agent output
# ===========================================================================


class TestEndToEndDISPipeline:
    """End-to-end integration tests for the full DIS agent_io pipeline."""

    @_SKIP_IF_NO_TRANSCRIPTS
    def test_正常系_Phase1入力準備からPhase2バリデーションまでのフロー(
        self, isolated_workspace: Path
    ) -> None:
        """Full pipeline: prepare_extraction_input → mock extraction → validate → prepare_scoring → mock scoring → validate."""
        # Step 1: Prepare Phase 1 input with real DIS transcripts
        extraction_payload = prepare_extraction_input(
            config_path=_CONFIG_PATH,
            transcript_dir=_TRANSCRIPT_DIR,
            kb_base_dir=_KB_BASE_DIR if _HAS_KB_DIR else isolated_workspace,
            ticker=_TICKER,
            workspace_dir=isolated_workspace,
        )

        # Verify extraction input
        assert len(extraction_payload["transcript_paths"]) >= _EXPECTED_MIN_TRANSCRIPTS
        assert extraction_payload["ticker"] == _TICKER

        # Step 2: Simulate Phase 1 agent output (mock extraction)
        phase1_output_dir = isolated_workspace / "phase1_output" / _TICKER
        phase1_output_dir.mkdir(parents=True, exist_ok=True)
        extraction_output_path = phase1_output_dir / "extraction_output.json"
        n_claims = 8
        extraction_data = _build_extraction_output(n_claims=n_claims)
        extraction_output_path.write_text(
            json.dumps(extraction_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Step 3: Validate Phase 1 output
        claims = validate_extraction_output(
            output_path=extraction_output_path,
            ticker=_TICKER,
        )

        assert len(claims) == n_claims
        assert _CLAIM_COUNT_MIN <= len(claims) <= _CLAIM_COUNT_MAX

        # Step 4: Prepare Phase 2 input
        scoring_payload = prepare_scoring_input(
            workspace_dir=isolated_workspace,
            kb_base_dir=_KB_BASE_DIR if _HAS_KB_DIR else isolated_workspace,
            ticker=_TICKER,
        )

        assert scoring_payload["ticker"] == _TICKER
        assert _TICKER in scoring_payload["phase1_output_dir"]

        # Step 5: Simulate Phase 2 agent output (mock scoring)
        claim_ids = [c.id for c in claims]
        scoring_data = _build_scoring_output(claim_ids)
        scoring_output_path = isolated_workspace / "scoring_output.json"
        scoring_output_path.write_text(
            json.dumps(scoring_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Step 6: Validate Phase 2 output
        scored = validate_scoring_output(
            output_path=scoring_output_path,
            ticker=_TICKER,
            original_claims=claims,
        )

        assert len(scored) == len(claims)

        # Acceptance criteria: all final_confidence in [0.1, 0.9]
        out_of_range = [
            s
            for s in scored
            if not (_CONFIDENCE_MIN <= s.final_confidence <= _CONFIDENCE_MAX)
        ]
        assert len(out_of_range) == 0, (
            f"{len(out_of_range)} claims have final_confidence outside "
            f"[{_CONFIDENCE_MIN}, {_CONFIDENCE_MAX}]"
        )

        # Phase 1 info restored via ID lookup
        claim_lookup = {c.id: c for c in claims}
        for scored_claim in scored:
            original = claim_lookup.get(scored_claim.id)
            if original is not None:
                assert scored_claim.claim == original.claim
                assert scored_claim.evidence == original.evidence
