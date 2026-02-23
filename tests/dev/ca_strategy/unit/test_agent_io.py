"""Unit tests for agent_io.py I/O helper module.

Tests cover all acceptance criteria from Issue #3624:
- prepare_extraction_input() generates JSON with PoiT-filtered transcript paths
- validate_extraction_output() normalizes confidence > 1.0 (70 -> 0.7)
- validate_extraction_output() logs and excludes claims with missing required fields
- prepare_scoring_input() builds phase 1 output + KB paths JSON
- validate_scoring_output() restores Phase 1 info via original_claims ID lookup
- All functions write to workspace_dir correctly

Tests cover all acceptance criteria from Issue #3650:
- consolidate_scored_claims() accepts optional output_path parameter
- prepare_extraction_input() accepts optional output_dir parameter
- prepare_universe_chunks() splits universe.json into chunk_{n:02d}.json files
- build_phase2_checkpoint() aggregates phase2 scoring outputs into phase2_scored.json
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import pytest

from dev.ca_strategy.agent_io import (
    build_phase2_checkpoint,
    consolidate_scored_claims,
    prepare_extraction_input,
    prepare_scoring_batches,
    prepare_scoring_input,
    prepare_universe_chunks,
    validate_extraction_output,
    validate_scoring_output,
)
from dev.ca_strategy.types import (
    Claim,
    ConfidenceAdjustment,
    EvidenceSource,
    GatekeeperResult,
    KB1RuleApplication,
    KB2PatternMatch,
    PowerClassification,
    RuleEvaluation,
    ScoredClaim,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_claim(
    *,
    claim_id: str = "AAPL-CA-001",
    claim_type: str = "competitive_advantage",
    claim_text: str = "Apple has strong brand loyalty.",
    evidence: str = "Customers repurchase at high rate.",
    confidence: float = 0.7,
) -> Claim:
    """Build a minimal valid Claim instance."""
    return Claim(
        id=claim_id,
        claim_type=claim_type,  # type: ignore[arg-type]
        claim=claim_text,
        evidence=evidence,
        rule_evaluation=RuleEvaluation(
            applied_rules=["rule_1_t"],
            results={"rule_1_t": True},
            confidence=confidence,
            adjustments=[],
        ),
    )


def _make_scored_claim(
    *,
    claim_id: str = "AAPL-CA-001",
    final_confidence: float = 0.7,
    claim_text: str = "Apple has strong brand loyalty.",
) -> ScoredClaim:
    """Build a minimal valid ScoredClaim instance."""
    return ScoredClaim(
        id=claim_id,
        claim_type="competitive_advantage",
        claim=claim_text,
        evidence="Customers repurchase at high rate.",
        rule_evaluation=RuleEvaluation(
            applied_rules=["rule_1_t"],
            results={"rule_1_t": True},
            confidence=0.7,
            adjustments=[],
        ),
        final_confidence=final_confidence,
        adjustments=[],
    )


def _make_extraction_output_json(
    claims: list[dict[str, Any]],
    ticker: str = "AAPL",
) -> dict[str, Any]:
    """Build a claims JSON dict as returned by Phase 1 agent."""
    return {
        "ticker": ticker,
        "transcript_source": "Q1 2015 Earnings Call",
        "claims": claims,
    }


def _make_raw_claim(
    *,
    claim_id: str = "AAPL-CA-001",
    confidence: float = 0.7,
    claim_text: str = "Apple has strong brand loyalty.",
) -> dict[str, Any]:
    """Build a raw claim dict as output by Phase 1 LLM agent."""
    return {
        "id": claim_id,
        "claim_type": "competitive_advantage",
        "claim": claim_text,
        "evidence": "Evidence text.",
        "rule_evaluation": {
            "applied_rules": ["rule_1_t"],
            "results": {"rule_1_t": True},
            "confidence": confidence,
            "adjustments": [],
        },
    }


def _make_raw_scored_claim(
    *,
    claim_id: str = "AAPL-CA-001",
    final_confidence: float = 0.7,
) -> dict[str, Any]:
    """Build a raw scored claim dict as output by Phase 2 LLM agent."""
    return {
        "id": claim_id,
        "final_confidence": final_confidence,
        "gatekeeper": {
            "rule9_factual_error": False,
            "rule3_industry_common": False,
            "triggered": False,
            "override_confidence": None,
        },
        "kb1_evaluations": [
            {
                "rule_id": "rule_1_t",
                "result": True,
                "reasoning": "Claim is specific and verifiable.",
            }
        ],
        "kb2_patterns": [],
        "confidence_adjustments": [],
        "overall_reasoning": "Strong evidence supports the claim.",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace_dir(tmp_path: Path) -> Path:
    """Return a temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    return ws


@pytest.fixture()
def kb_base_dir(tmp_path: Path) -> Path:
    """Return a temporary KB base directory with minimal structure."""
    kb = tmp_path / "kb"
    (kb / "kb1_rules_transcript").mkdir(parents=True)
    (kb / "kb2_patterns_transcript").mkdir(parents=True)
    (kb / "kb3_fewshot_transcript").mkdir(parents=True)
    return kb


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    """Return a temporary config path with universe.json."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    universe = {
        "tickers": [
            {"ticker": "AAPL", "gics_sector": "Information Technology"},
        ]
    }
    (cfg / "universe.json").write_text(
        json.dumps(universe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return cfg


@pytest.fixture()
def transcript_dir(tmp_path: Path) -> Path:
    """Return a temporary transcript directory with one AAPL transcript."""
    td = tmp_path / "transcripts"
    aapl_dir = td / "AAPL"
    aapl_dir.mkdir(parents=True)

    transcript_data = {
        "metadata": {
            "ticker": "AAPL",
            "event_date": "2015-01-28",
            "fiscal_quarter": "Q1 2015",
            "is_truncated": False,
        },
        "sections": [
            {
                "speaker": "Tim Cook",
                "role": "CEO",
                "section_type": "prepared_remarks",
                "content": "We had a great quarter.",
            }
        ],
    }
    (aapl_dir / "201501_earnings_call.json").write_text(
        json.dumps(transcript_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return td


# ===========================================================================
# Tests: prepare_extraction_input
# ===========================================================================


class TestPrepareExtractionInput:
    """Tests for prepare_extraction_input()."""

    def test_正常系_extraction_input_jsonが生成される(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """prepare_extraction_input() should create extraction_input.json."""
        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        output_path = workspace_dir / "extraction_input.json"
        assert output_path.exists(), "extraction_input.json should be created"
        assert isinstance(result, dict)

    def test_正常系_PoiTフィルタリング済みトランスクリプトパスを含む(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """Result must contain transcript_paths filtered by PoiT."""
        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        assert "transcript_paths" in result
        paths = result["transcript_paths"]
        assert isinstance(paths, list)
        # The Q1 2015 transcript is within the PoiT cutoff (2015-09-30)
        assert len(paths) >= 1
        assert all("AAPL" in p for p in paths)

    def test_正常系_KBパスが含まれる(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """Result must include kb1_dir, kb3_dir, system_prompt_path."""
        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        assert "kb1_dir" in result
        assert "kb3_dir" in result
        assert "ticker" in result
        assert result["ticker"] == "AAPL"

    def test_正常系_カットオフ以降のトランスクリプトは除外される(
        self,
        config_path: Path,
        tmp_path: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """Transcripts after the cutoff date (2015-09-30) must be excluded."""
        # Create transcript dir with a post-cutoff transcript
        td = tmp_path / "transcripts2"
        aapl_dir = td / "AAPL"
        aapl_dir.mkdir(parents=True)

        late_transcript = {
            "metadata": {
                "ticker": "AAPL",
                "event_date": "2016-01-28",  # after cutoff
                "fiscal_quarter": "Q1 2016",
                "is_truncated": False,
            },
            "sections": [
                {
                    "speaker": "Tim Cook",
                    "role": "CEO",
                    "section_type": "prepared_remarks",
                    "content": "We had a great quarter.",
                }
            ],
        }
        (aapl_dir / "201601_earnings_call.json").write_text(
            json.dumps(late_transcript, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=td,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        paths = result["transcript_paths"]
        # Post-cutoff transcript should be excluded
        assert all("201601" not in p for p in paths)

    def test_正常系_jsonファイルが書き出される(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """extraction_input.json contents must match the returned dict."""
        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        output_path = workspace_dir / "extraction_input.json"
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        assert stored["ticker"] == result["ticker"]
        assert stored["transcript_paths"] == result["transcript_paths"]

    def test_エッジケース_トランスクリプトが存在しない場合は空リスト(
        self,
        config_path: Path,
        tmp_path: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """When no transcripts exist for the ticker, transcript_paths is empty."""
        empty_td = tmp_path / "empty_transcripts"
        empty_td.mkdir(parents=True)

        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=empty_td,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        assert result["transcript_paths"] == []


# ===========================================================================
# Tests: validate_extraction_output
# ===========================================================================


class TestValidateExtractionOutput:
    """Tests for validate_extraction_output()."""

    def test_正常系_有効なJSONからClaimリストを返す(self, tmp_path: Path) -> None:
        """Valid claims JSON should deserialize into Claim models."""
        raw_claim = _make_raw_claim(claim_id="AAPL-CA-001", confidence=0.7)
        output_data = _make_extraction_output_json([raw_claim])
        output_path = tmp_path / "claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert len(claims) == 1
        assert claims[0].id == "AAPL-CA-001"
        assert isinstance(claims[0], Claim)

    def test_正常系_confidence_70を0_7に正規化する(self, tmp_path: Path) -> None:
        """confidence > 1.0 (e.g. 70) must be normalized to 0-1 range (0.7)."""
        raw_claim = _make_raw_claim(confidence=70)
        output_data = _make_extraction_output_json([raw_claim])
        output_path = tmp_path / "claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert len(claims) == 1
        assert abs(claims[0].rule_evaluation.confidence - 0.7) < 1e-6

    def test_正常系_confidence_90を0_9に正規化する(self, tmp_path: Path) -> None:
        """confidence=90 should be normalized to 0.9."""
        raw_claim = _make_raw_claim(confidence=90)
        output_data = _make_extraction_output_json([raw_claim])
        output_path = tmp_path / "claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert len(claims) == 1
        assert abs(claims[0].rule_evaluation.confidence - 0.9) < 1e-6

    def test_正常系_confidence_0_7はそのまま(self, tmp_path: Path) -> None:
        """confidence already in [0.0, 1.0] must not be modified."""
        raw_claim = _make_raw_claim(confidence=0.7)
        output_data = _make_extraction_output_json([raw_claim])
        output_path = tmp_path / "claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert abs(claims[0].rule_evaluation.confidence - 0.7) < 1e-6

    def test_異常系_必須フィールド欠落時はエラーログ記録して除外(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Claims missing required fields must be excluded with a warning log."""
        bad_claim: dict[str, Any] = {
            "id": "AAPL-CA-BAD",
            # 'claim' field is missing entirely - but id is present, claim_type,
            # and rule_evaluation are missing too
        }
        good_claim = _make_raw_claim(claim_id="AAPL-CA-001")
        output_data = _make_extraction_output_json([bad_claim, good_claim])
        output_path = tmp_path / "claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with caplog.at_level(logging.WARNING):
            claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        # Bad claim excluded, good claim retained
        assert len(claims) == 1
        assert claims[0].id == "AAPL-CA-001"
        # Warning log recorded for the failed claim
        assert any(
            "AAPL-CA-BAD" in msg or "failed" in msg.lower() for msg in caplog.messages
        )

    def test_異常系_ファイルが存在しない場合は空リストを返す(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing output file should return [] with warning log."""
        output_path = tmp_path / "nonexistent.json"

        with caplog.at_level(logging.WARNING):
            claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert claims == []
        assert any(
            "not found" in msg.lower() or "exist" in msg.lower()
            for msg in caplog.messages
        )

    def test_異常系_不正なJSONは空リストを返す(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Invalid JSON in output file should return [] with warning log."""
        output_path = tmp_path / "bad.json"
        output_path.write_text("not valid json", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert claims == []

    def test_エッジケース_claims配列が空の場合は空リストを返す(
        self, tmp_path: Path
    ) -> None:
        """Empty claims array should return empty list."""
        output_data = _make_extraction_output_json([])
        output_path = tmp_path / "empty_claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert claims == []

    def test_エッジケース_複数claimの混在処理(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Mixed valid/invalid claims: valid ones retained, invalid excluded."""
        raw_claims = [
            _make_raw_claim(claim_id="AAPL-CA-001"),
            {"id": "AAPL-CA-BAD"},  # missing required fields
            _make_raw_claim(claim_id="AAPL-CA-002", confidence=80),
        ]
        output_data = _make_extraction_output_json(raw_claims)
        output_path = tmp_path / "mixed_claims.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with caplog.at_level(logging.WARNING):
            claims = validate_extraction_output(output_path=output_path, ticker="AAPL")

        assert len(claims) == 2
        claim_ids = {c.id for c in claims}
        assert "AAPL-CA-001" in claim_ids
        assert "AAPL-CA-002" in claim_ids
        assert "AAPL-CA-BAD" not in claim_ids


# ===========================================================================
# Tests: prepare_scoring_input
# ===========================================================================


class TestPrepareScoringInput:
    """Tests for prepare_scoring_input()."""

    def test_正常系_scoring_input_jsonが生成される(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """prepare_scoring_input() should create scoring_input.json."""
        # Prepare phase 1 output file first
        phase1_output = workspace_dir / "phase1_output" / "AAPL"
        phase1_output.mkdir(parents=True)
        claims_data = _make_extraction_output_json([_make_raw_claim()], ticker="AAPL")
        (phase1_output / "Q1_2015_claims.json").write_text(
            json.dumps(claims_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        result = prepare_scoring_input(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
        )

        output_path = workspace_dir / "scoring_input.json"
        assert output_path.exists(), "scoring_input.json should be created"
        assert isinstance(result, dict)

    def test_正常系_phase1出力パスが含まれる(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """Result must contain phase1_output_dir pointing to ticker's claims."""
        result = prepare_scoring_input(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
        )

        assert "phase1_output_dir" in result
        assert "AAPL" in result["phase1_output_dir"]

    def test_正常系_KBパスが含まれる(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """Result must include kb1_dir, kb2_dir, kb3_dir."""
        result = prepare_scoring_input(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
        )

        assert "kb1_dir" in result
        assert "kb2_dir" in result
        assert "kb3_dir" in result
        assert result["ticker"] == "AAPL"

    def test_正常系_jsonファイルが書き出される(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """scoring_input.json contents must match the returned dict."""
        result = prepare_scoring_input(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
        )

        output_path = workspace_dir / "scoring_input.json"
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        assert stored["ticker"] == result["ticker"]
        assert stored["kb1_dir"] == result["kb1_dir"]


# ===========================================================================
# Tests: validate_scoring_output
# ===========================================================================


class TestValidateScoringOutput:
    """Tests for validate_scoring_output()."""

    def test_正常系_有効なJSONからScoredClaimリストを返す(self, tmp_path: Path) -> None:
        """Valid scored output JSON should deserialize into ScoredClaim models."""
        original_claims = [_make_claim()]
        raw_scored = _make_raw_scored_claim(
            claim_id="AAPL-CA-001", final_confidence=0.7
        )
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=original_claims,
        )

        assert len(scored) == 1
        assert scored[0].id == "AAPL-CA-001"
        assert isinstance(scored[0], ScoredClaim)

    def test_正常系_original_claimsとのID照合でPhase1情報を復元する(
        self, tmp_path: Path
    ) -> None:
        """validate_scoring_output() must restore Phase 1 fields from original_claims."""
        original = _make_claim(
            claim_id="AAPL-CA-001",
            claim_text="Apple has strong brand loyalty.",
        )
        raw_scored = _make_raw_scored_claim(
            claim_id="AAPL-CA-001", final_confidence=0.8
        )
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=[original],
        )

        assert len(scored) == 1
        result = scored[0]
        # Phase 1 fields restored from original
        assert result.claim == original.claim
        assert result.evidence == original.evidence
        assert result.claim_type == original.claim_type
        assert result.rule_evaluation == original.rule_evaluation

    def test_正常系_final_confidence_70を0_7に正規化する(self, tmp_path: Path) -> None:
        """final_confidence > 1.0 must be normalized (70 -> 0.7)."""
        original_claims = [_make_claim()]
        raw_scored = _make_raw_scored_claim(claim_id="AAPL-CA-001", final_confidence=70)
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=original_claims,
        )

        assert abs(scored[0].final_confidence - 0.7) < 1e-6

    def test_正常系_GatekeeperResultのパース(self, tmp_path: Path) -> None:
        """Gatekeeper fields must be parsed from scored output."""
        original_claims = [_make_claim()]
        raw_scored = _make_raw_scored_claim(claim_id="AAPL-CA-001")
        raw_scored["gatekeeper"] = {
            "rule9_factual_error": True,
            "rule3_industry_common": False,
            "triggered": True,
            "override_confidence": 0.1,
        }
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=original_claims,
        )

        assert scored[0].gatekeeper is not None
        assert scored[0].gatekeeper.rule9_factual_error is True
        assert scored[0].gatekeeper.triggered is True

    def test_正常系_KB1RuleApplicationのパース(self, tmp_path: Path) -> None:
        """kb1_evaluations list must be parsed into KB1RuleApplication models."""
        original_claims = [_make_claim()]
        raw_scored = _make_raw_scored_claim(claim_id="AAPL-CA-001")
        raw_scored["kb1_evaluations"] = [
            {"rule_id": "rule_1_t", "result": True, "reasoning": "Specific claim."},
            {"rule_id": "rule_2_t", "result": False, "reasoning": "Lacks evidence."},
        ]
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=original_claims,
        )

        assert len(scored[0].kb1_evaluations) == 2
        assert scored[0].kb1_evaluations[0].rule_id == "rule_1_t"
        assert scored[0].kb1_evaluations[1].rule_id == "rule_2_t"
        assert scored[0].kb1_evaluations[1].result is False

    def test_正常系_KB2PatternMatchのパース(self, tmp_path: Path) -> None:
        """kb2_patterns list must be parsed into KB2PatternMatch models."""
        original_claims = [_make_claim()]
        raw_scored = _make_raw_scored_claim(claim_id="AAPL-CA-001")
        raw_scored["kb2_patterns"] = [
            {
                "pattern_id": "pattern_I",
                "matched": True,
                "adjustment": 0.2,
                "reasoning": "Strong brand evidence.",
            }
        ]
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=original_claims,
        )

        assert len(scored[0].kb2_patterns) == 1
        assert scored[0].kb2_patterns[0].pattern_id == "pattern_I"
        assert scored[0].kb2_patterns[0].matched is True
        assert abs(scored[0].kb2_patterns[0].adjustment - 0.2) < 1e-6

    def test_異常系_ファイルが存在しない場合は空リストを返す(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing output file should return [] with warning log."""
        output_path = tmp_path / "nonexistent.json"

        with caplog.at_level(logging.WARNING):
            scored = validate_scoring_output(
                output_path=output_path,
                ticker="AAPL",
                original_claims=[],
            )

        assert scored == []
        assert any(
            "not found" in msg.lower() or "exist" in msg.lower()
            for msg in caplog.messages
        )

    def test_異常系_不正なJSONは空リストを返す(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Invalid JSON in output file should return [] with warning log."""
        output_path = tmp_path / "bad.json"
        output_path.write_text("{not valid json}", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            scored = validate_scoring_output(
                output_path=output_path,
                ticker="AAPL",
                original_claims=[],
            )

        assert scored == []

    def test_正常系_original_claimが見つからない場合はフォールバック(
        self, tmp_path: Path
    ) -> None:
        """When no original claim matches, ScoredClaim is created from raw data."""
        # No original claims provided
        raw_scored = _make_raw_scored_claim(
            claim_id="AAPL-CA-999", final_confidence=0.5
        )
        # Provide minimal fields in raw for fallback
        raw_scored["claim_type"] = "competitive_advantage"
        raw_scored["claim"] = "Some claim text."
        raw_scored["evidence"] = "Some evidence."
        output_data = {"scored_claims": [raw_scored]}
        output_path = tmp_path / "scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=[],  # empty - no lookup possible
        )

        # Fallback should produce at least a minimal ScoredClaim
        assert len(scored) == 1
        assert scored[0].id == "AAPL-CA-999"
        assert abs(scored[0].final_confidence - 0.5) < 1e-6

    def test_エッジケース_scored_claims配列が空の場合は空リストを返す(
        self, tmp_path: Path
    ) -> None:
        """Empty scored_claims array should return empty list."""
        output_data = {"scored_claims": []}
        output_path = tmp_path / "empty_scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scored = validate_scoring_output(
            output_path=output_path,
            ticker="AAPL",
            original_claims=[],
        )

        assert scored == []

    def test_エッジケース_複数scored_claimの混在処理(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Mixed valid/invalid scored claims: valid ones retained."""
        original_claims = [
            _make_claim(claim_id="AAPL-CA-001"),
            _make_claim(claim_id="AAPL-CA-002"),
        ]
        raw_scored_list = [
            _make_raw_scored_claim(claim_id="AAPL-CA-001", final_confidence=0.7),
            {"id": "AAPL-CA-BAD"},  # missing required fields for scoring
            _make_raw_scored_claim(claim_id="AAPL-CA-002", final_confidence=0.5),
        ]
        output_data = {"scored_claims": raw_scored_list}
        output_path = tmp_path / "mixed_scored.json"
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with caplog.at_level(logging.WARNING):
            scored = validate_scoring_output(
                output_path=output_path,
                ticker="AAPL",
                original_claims=original_claims,
            )

        assert len(scored) == 2
        scored_ids = {s.id for s in scored}
        assert "AAPL-CA-001" in scored_ids
        assert "AAPL-CA-002" in scored_ids
        assert "AAPL-CA-BAD" not in scored_ids


# ===========================================================================
# Tests: prepare_scoring_batches
# ===========================================================================


class TestPrepareScoringBatches:
    """Tests for prepare_scoring_batches()."""

    def _write_extraction_output(
        self,
        workspace_dir: Path,
        ticker: str,
        claim_ids: list[str],
    ) -> Path:
        """Write extraction_output.json with given claim IDs to workspace_dir."""
        phase1_dir = workspace_dir / "phase1_output" / ticker
        phase1_dir.mkdir(parents=True, exist_ok=True)
        output_path = phase1_dir / "extraction_output.json"
        data = {
            "ticker": ticker,
            "claims": [{"id": cid} for cid in claim_ids],
        }
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return output_path

    def test_正常系_バッチ入力JSONがbatch_inputs以下に書き出される(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """prepare_scoring_batches() should write batch JSON files under batch_inputs/."""
        claim_ids = ["AAPL-CA-001", "AAPL-CA-002", "AAPL-CA-003"]
        self._write_extraction_output(workspace_dir, "AAPL", claim_ids)

        batches = prepare_scoring_batches(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            batch_size=5,
        )

        assert len(batches) == 1
        batch_input_dir = workspace_dir / "batch_inputs"
        assert batch_input_dir.exists()
        expected_file = batch_input_dir / "scoring_input_batch_0.json"
        assert expected_file.exists()

    def test_正常系_batch_size5で15件は3バッチになる(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """15 claims with batch_size=5 should produce 3 batches."""
        claim_ids = [f"AAPL-CA-{i:03d}" for i in range(15)]
        self._write_extraction_output(workspace_dir, "AAPL", claim_ids)

        batches = prepare_scoring_batches(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            batch_size=5,
        )

        assert len(batches) == 3
        # Verify all batch files were created
        batch_input_dir = workspace_dir / "batch_inputs"
        for i in range(3):
            assert (batch_input_dir / f"scoring_input_batch_{i}.json").exists()

    def test_正常系_各バッチのtarget_claim_idsが正しく分割される(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """Each batch dict must have correct target_claim_ids split."""
        claim_ids = [f"AAPL-CA-{i:03d}" for i in range(7)]
        self._write_extraction_output(workspace_dir, "AAPL", claim_ids)

        batches = prepare_scoring_batches(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            batch_size=3,
        )

        assert len(batches) == 3  # 3 + 3 + 1
        assert batches[0]["target_claim_ids"] == [
            "AAPL-CA-000",
            "AAPL-CA-001",
            "AAPL-CA-002",
        ]
        assert batches[1]["target_claim_ids"] == [
            "AAPL-CA-003",
            "AAPL-CA-004",
            "AAPL-CA-005",
        ]
        assert batches[2]["target_claim_ids"] == ["AAPL-CA-006"]

    def test_正常系_各バッチのメタデータが正しい(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """Each batch dict must include input_path, output_path, batch_index, batch_total."""
        claim_ids = [f"AAPL-CA-{i:03d}" for i in range(6)]
        self._write_extraction_output(workspace_dir, "AAPL", claim_ids)

        batches = prepare_scoring_batches(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            batch_size=3,
        )

        assert len(batches) == 2
        for i, batch in enumerate(batches):
            assert "input_path" in batch
            assert "output_path" in batch
            assert batch["batch_index"] == i
            assert batch["batch_total"] == 2

    def test_異常系_extraction_output_jsonが存在しない場合はValueError(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """prepare_scoring_batches() should raise ValueError when extraction_output.json is missing."""
        with pytest.raises(ValueError):
            prepare_scoring_batches(
                workspace_dir=workspace_dir,
                kb_base_dir=kb_base_dir,
                ticker="AAPL",
                batch_size=5,
            )

    def test_エッジケース_claimsが空リストのとき空のtarget_claim_idsで1バッチ生成される(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """When extraction_output.json has no claims, one batch with empty target_claim_ids is produced."""
        self._write_extraction_output(workspace_dir, "AAPL", [])

        batches = prepare_scoring_batches(
            workspace_dir=workspace_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            batch_size=5,
        )

        assert len(batches) == 1
        assert batches[0]["target_claim_ids"] == []

    def test_異常系_extraction_output_jsonが破損JSONの場合はValueError(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """prepare_scoring_batches() should raise ValueError when extraction_output.json contains invalid JSON."""
        phase1_dir = workspace_dir / "phase1_output" / "AAPL"
        phase1_dir.mkdir(parents=True, exist_ok=True)
        (phase1_dir / "extraction_output.json").write_text(
            "{ broken json", encoding="utf-8"
        )

        with pytest.raises(ValueError):
            prepare_scoring_batches(
                workspace_dir=workspace_dir,
                kb_base_dir=kb_base_dir,
                ticker="AAPL",
                batch_size=5,
            )

    def test_異常系_batch_sizeが0以下の場合はValueError(
        self,
        workspace_dir: Path,
        kb_base_dir: Path,
    ) -> None:
        """prepare_scoring_batches() should raise ValueError when batch_size <= 0."""
        self._write_extraction_output(workspace_dir, "AAPL", ["AAPL-CA-001"])

        with pytest.raises(ValueError, match="batch_size must be a positive integer"):
            prepare_scoring_batches(
                workspace_dir=workspace_dir,
                kb_base_dir=kb_base_dir,
                ticker="AAPL",
                batch_size=0,
            )


# ===========================================================================
# Tests: consolidate_scored_claims
# ===========================================================================


def _make_scored_batch_data(
    claim_ids: list[str],
    *,
    confidence: float = 0.7,
    gatekeeper_applied: bool = False,
) -> dict[str, Any]:
    """Build a scored_batch JSON dict as output by the scoring agent."""
    scored_claims = []
    for cid in claim_ids:
        scored_claims.append(
            {
                "id": cid,
                "final_confidence": confidence,
                "claim_type": "competitive_advantage",
                "claim": f"Claim for {cid}",
                "evidence": "Some evidence.",
                "gatekeeper": {
                    "rule9_factual_error": False,
                    "rule3_industry_common": False,
                    "triggered": False,
                    "override_confidence": None,
                },
                "kb1_evaluations": [],
                "kb2_patterns": [],
                "confidence_adjustments": [],
                "overall_reasoning": "Good claim.",
            }
        )

    confidence_distribution: dict[str, int] = {}
    for sc in scored_claims:
        bucket_low = int(sc["final_confidence"] * 10) * 10
        bucket_key = f"{bucket_low}-{bucket_low + 10}"
        confidence_distribution[bucket_key] = (
            confidence_distribution.get(bucket_key, 0) + 1
        )

    return {
        "scored_claims": scored_claims,
        "metadata": {
            "scored_count": len(scored_claims),
            "confidence_distribution": confidence_distribution,
            "gatekeeper_applied": gatekeeper_applied,
        },
    }


class TestConsolidateScoredClaims:
    """Tests for consolidate_scored_claims()."""

    def _write_scored_batch(
        self,
        workspace_dir: Path,
        ticker: str,
        batch_num: int,
        claim_ids: list[str],
        *,
        confidence: float = 0.7,
        gatekeeper_applied: bool = False,
    ) -> Path:
        """Write a scored_batch_N.json file to phase2_output/{ticker}/."""
        phase2_dir = workspace_dir / "phase2_output" / ticker
        phase2_dir.mkdir(parents=True, exist_ok=True)
        batch_path = phase2_dir / f"scored_batch_{batch_num}.json"
        data = _make_scored_batch_data(
            claim_ids,
            confidence=confidence,
            gatekeeper_applied=gatekeeper_applied,
        )
        batch_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return batch_path

    def test_正常系_複数バッチを統合してscoring_output_jsonを生成する(
        self,
        workspace_dir: Path,
    ) -> None:
        """consolidate_scored_claims() should merge all batches into scoring_output.json."""
        self._write_scored_batch(
            workspace_dir, "AAPL", 0, ["AAPL-CA-000", "AAPL-CA-001"]
        )
        self._write_scored_batch(
            workspace_dir, "AAPL", 1, ["AAPL-CA-002", "AAPL-CA-003"]
        )

        output_path = consolidate_scored_claims(
            workspace_dir=workspace_dir, ticker="AAPL"
        )

        assert (workspace_dir / "scoring_output.json").exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data["scored_claims"]) == 4

    def test_正常系_バッチ番号順にソートされて統合される(
        self,
        workspace_dir: Path,
    ) -> None:
        """Batch files must be sorted by batch number, not filename lexicographically."""
        # Write batch 2 before batch 0 to test sort order
        self._write_scored_batch(workspace_dir, "AAPL", 2, ["AAPL-CA-004"])
        self._write_scored_batch(workspace_dir, "AAPL", 0, ["AAPL-CA-000"])
        self._write_scored_batch(workspace_dir, "AAPL", 10, ["AAPL-CA-010"])
        self._write_scored_batch(workspace_dir, "AAPL", 1, ["AAPL-CA-002"])

        output_path = consolidate_scored_claims(
            workspace_dir=workspace_dir, ticker="AAPL"
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))
        all_ids = [sc["id"] for sc in data["scored_claims"]]
        # Batch 0 first, then 1, 2, 10
        assert all_ids == ["AAPL-CA-000", "AAPL-CA-002", "AAPL-CA-004", "AAPL-CA-010"]

    def test_正常系_metadataが再集計される(
        self,
        workspace_dir: Path,
    ) -> None:
        """consolidate_scored_claims() must recalculate metadata from merged results."""
        self._write_scored_batch(
            workspace_dir,
            "AAPL",
            0,
            ["AAPL-CA-000", "AAPL-CA-001"],
            gatekeeper_applied=True,
        )
        self._write_scored_batch(
            workspace_dir,
            "AAPL",
            1,
            ["AAPL-CA-002"],
            gatekeeper_applied=False,
        )

        output_path = consolidate_scored_claims(
            workspace_dir=workspace_dir, ticker="AAPL"
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))
        metadata = data["metadata"]
        assert metadata["scored_count"] == 3
        assert "confidence_distribution" in metadata
        assert "gatekeeper_applied" in metadata

    def test_異常系_scored_batch_jsonが1件も存在しない場合はValueError(
        self,
        workspace_dir: Path,
    ) -> None:
        """consolidate_scored_claims() should raise ValueError when no batch files found."""
        with pytest.raises(ValueError):
            consolidate_scored_claims(workspace_dir=workspace_dir, ticker="AAPL")

    def test_エッジケース_一部バッチが破損JSONのときスキップして残りを統合する(
        self,
        workspace_dir: Path,
    ) -> None:
        """consolidate_scored_claims() should skip corrupted batch files and merge the rest."""
        # 正常バッチ 0 と 2、破損バッチ 1
        self._write_scored_batch(workspace_dir, "AAPL", 0, ["AAPL-CA-000"])
        # 破損ファイルを直接書き込む
        phase2_dir = workspace_dir / "phase2_output" / "AAPL"
        phase2_dir.mkdir(parents=True, exist_ok=True)
        (phase2_dir / "scored_batch_1.json").write_text(
            "{ broken json", encoding="utf-8"
        )
        self._write_scored_batch(workspace_dir, "AAPL", 2, ["AAPL-CA-002"])

        output_path = consolidate_scored_claims(
            workspace_dir=workspace_dir, ticker="AAPL"
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))
        all_ids = [sc["id"] for sc in data["scored_claims"]]
        # バッチ 1 はスキップ、バッチ 0 と 2 のみ統合される
        assert all_ids == ["AAPL-CA-000", "AAPL-CA-002"]
        assert data["metadata"]["scored_count"] == 2


# ===========================================================================
# Tests: consolidate_scored_claims (output_path parameter extension)
# ===========================================================================


class TestConsolidateScoredClaimsOutputPath:
    """Tests for consolidate_scored_claims() output_path parameter (Issue #3650)."""

    def _write_scored_batch(
        self,
        workspace_dir: Path,
        ticker: str,
        batch_num: int,
        claim_ids: list[str],
    ) -> Path:
        """Write a scored_batch_N.json file to phase2_output/{ticker}/."""
        phase2_dir = workspace_dir / "phase2_output" / ticker
        phase2_dir.mkdir(parents=True, exist_ok=True)
        batch_path = phase2_dir / f"scored_batch_{batch_num}.json"
        data = _make_scored_batch_data(claim_ids)
        batch_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return batch_path

    def test_正常系_output_pathがNoneのときデフォルトパスに書き出される(
        self,
        workspace_dir: Path,
    ) -> None:
        """When output_path=None, result is written to workspace_dir/scoring_output.json."""
        self._write_scored_batch(workspace_dir, "AAPL", 0, ["AAPL-CA-000"])

        result_path = consolidate_scored_claims(
            workspace_dir=workspace_dir,
            ticker="AAPL",
            output_path=None,
        )

        assert result_path == workspace_dir / "scoring_output.json"
        assert result_path.exists()

    def test_正常系_output_pathを指定すると指定先に書き出される(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """When output_path is given, file is written to that path."""
        self._write_scored_batch(workspace_dir, "AAPL", 0, ["AAPL-CA-000"])

        custom_path = tmp_path / "custom_output" / "my_scoring.json"
        result_path = consolidate_scored_claims(
            workspace_dir=workspace_dir,
            ticker="AAPL",
            output_path=custom_path,
        )

        assert result_path == custom_path
        assert custom_path.exists()
        data = json.loads(custom_path.read_text(encoding="utf-8"))
        assert len(data["scored_claims"]) == 1

    def test_正常系_引数なしで呼ぶと後方互換性を維持する(
        self,
        workspace_dir: Path,
    ) -> None:
        """Calling without output_path keyword arg maintains backward compatibility."""
        self._write_scored_batch(workspace_dir, "AAPL", 0, ["AAPL-CA-001"])

        # Call without output_path (original signature)
        result_path = consolidate_scored_claims(
            workspace_dir=workspace_dir,
            ticker="AAPL",
        )

        assert result_path == workspace_dir / "scoring_output.json"
        assert result_path.exists()


# ===========================================================================
# Tests: prepare_extraction_input (output_dir parameter extension)
# ===========================================================================


class TestPrepareExtractionInputOutputDir:
    """Tests for prepare_extraction_input() output_dir parameter (Issue #3650)."""

    def test_正常系_output_dirがNoneのときworkspace_dirに書き出される(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """When output_dir=None, extraction_input.json is written to workspace_dir."""
        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
            output_dir=None,
        )

        assert (workspace_dir / "extraction_input.json").exists()
        assert result["workspace_dir"] == str(workspace_dir)

    def test_正常系_output_dirを指定すると指定先に書き出される(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """When output_dir is given, extraction_input.json is written to that dir."""
        custom_dir = tmp_path / "custom_extraction"

        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
            output_dir=custom_dir,
        )

        assert (custom_dir / "extraction_input.json").exists()
        # workspace_dir in payload reflects the output_dir
        assert result["workspace_dir"] == str(custom_dir)

    def test_正常系_引数なしで呼ぶと後方互換性を維持する(
        self,
        config_path: Path,
        transcript_dir: Path,
        kb_base_dir: Path,
        workspace_dir: Path,
    ) -> None:
        """Calling without output_dir keyword arg maintains backward compatibility."""
        result = prepare_extraction_input(
            config_path=config_path,
            transcript_dir=transcript_dir,
            kb_base_dir=kb_base_dir,
            ticker="AAPL",
            workspace_dir=workspace_dir,
        )

        assert (workspace_dir / "extraction_input.json").exists()
        assert isinstance(result, dict)


# ===========================================================================
# Tests: prepare_universe_chunks (new function)
# ===========================================================================


def _write_universe_json(path: Path, tickers: list[str]) -> None:
    """Write a universe.json with given ticker symbols to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "_metadata": {
            "description": "test universe",
            "total_count": len(tickers),
        },
        "tickers": [{"ticker": t, "gics_sector": "Financials"} for t in tickers],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class TestPrepareUniverseChunks:
    """Tests for prepare_universe_chunks() (Issue #3650)."""

    def test_正常系_10銘柄を1チャンクに分割する(self, tmp_path: Path) -> None:
        """10 tickers with chunk_size=10 should produce 1 chunk file."""
        tickers = [f"TK{i:02d}" for i in range(10)]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=10,
        )

        assert len(chunk_paths) == 1
        assert chunk_paths[0].name == "chunk_00.json"

    def test_正常系_25銘柄をchunk_size10で3チャンクに分割する(
        self, tmp_path: Path
    ) -> None:
        """25 tickers with chunk_size=10 should produce 3 chunk files."""
        tickers = [f"TK{i:02d}" for i in range(25)]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=10,
        )

        assert len(chunk_paths) == 3
        assert chunk_paths[0].name == "chunk_00.json"
        assert chunk_paths[1].name == "chunk_01.json"
        assert chunk_paths[2].name == "chunk_02.json"

    def test_正常系_チャンクファイルがuniverse_pathと同じディレクトリに生成される(
        self, tmp_path: Path
    ) -> None:
        """Chunk files are written to the same directory as universe_path."""
        tickers = [f"TK{i:02d}" for i in range(5)]
        universe_path = tmp_path / "config" / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=10,
        )

        for p in chunk_paths:
            assert p.parent == universe_path.parent
            assert p.exists()

    def test_正常系_各チャンクにtickersフィールドが含まれる(
        self, tmp_path: Path
    ) -> None:
        """Each chunk JSON should contain a 'tickers' list."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=2,
        )

        assert len(chunk_paths) == 2
        chunk0_data = json.loads(chunk_paths[0].read_text(encoding="utf-8"))
        assert "tickers" in chunk0_data
        assert len(chunk0_data["tickers"]) == 2
        chunk1_data = json.loads(chunk_paths[1].read_text(encoding="utf-8"))
        assert len(chunk1_data["tickers"]) == 1

    def test_正常系_全銘柄が損失なくチャンクに含まれる(self, tmp_path: Path) -> None:
        """All tickers must appear across all chunks with no loss."""
        tickers = [f"TK{i:02d}" for i in range(22)]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=10,
        )

        all_tickers_in_chunks: list[str] = []
        for p in chunk_paths:
            data = json.loads(p.read_text(encoding="utf-8"))
            all_tickers_in_chunks.extend(t["ticker"] for t in data["tickers"])

        assert sorted(all_tickers_in_chunks) == sorted(tickers)

    def test_正常系_chunk_size1で銘柄ごとに1ファイル生成される(
        self, tmp_path: Path
    ) -> None:
        """chunk_size=1 should produce one file per ticker."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=1,
        )

        assert len(chunk_paths) == 3

    def test_正常系_デフォルトchunk_sizeは10(self, tmp_path: Path) -> None:
        """Default chunk_size should be 10."""
        tickers = [f"TK{i:02d}" for i in range(15)]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        chunk_paths = prepare_universe_chunks(universe_path=universe_path)

        # 15 tickers with default chunk_size=10 -> 2 chunks
        assert len(chunk_paths) == 2

    def test_異常系_universe_pathが存在しない場合はValueError(
        self, tmp_path: Path
    ) -> None:
        """prepare_universe_chunks() should raise ValueError when universe_path missing."""
        with pytest.raises(ValueError, match="universe.json not found"):
            prepare_universe_chunks(
                universe_path=tmp_path / "nonexistent.json",
                chunk_size=10,
            )

    def test_異常系_chunk_sizeが0以下の場合はValueError(self, tmp_path: Path) -> None:
        """prepare_universe_chunks() should raise ValueError when chunk_size <= 0."""
        tickers = ["AAPL"]
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, tickers)

        with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
            prepare_universe_chunks(universe_path=universe_path, chunk_size=0)

    def test_エッジケース_tickersが空のとき空リストを返す(self, tmp_path: Path) -> None:
        """Empty tickers list in universe.json should return empty list."""
        universe_path = tmp_path / "universe.json"
        _write_universe_json(universe_path, [])

        chunk_paths = prepare_universe_chunks(
            universe_path=universe_path,
            chunk_size=10,
        )

        assert chunk_paths == []


# ===========================================================================
# Tests: build_phase2_checkpoint (new function)
# ===========================================================================


def _write_scoring_output(
    workspace_dir: Path,
    ticker: str,
    scored_claims: list[dict[str, Any]],
) -> Path:
    """Write phase2_output/{ticker}/scoring_output.json with scored claims."""
    output_dir = workspace_dir / "phase2_output" / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "scoring_output.json"
    data = {
        "scored_claims": scored_claims,
        "metadata": {
            "scored_count": len(scored_claims),
            "gatekeeper_applied": False,
        },
    }
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def _make_scored_claim_dict(
    claim_id: str, *, final_confidence: float = 0.7
) -> dict[str, Any]:
    """Build a minimal scored claim dict for use in scoring_output.json."""
    return {
        "id": claim_id,
        "claim_type": "competitive_advantage",
        "claim": f"Claim text for {claim_id}",
        "evidence": "Evidence for claim.",
        "rule_evaluation": {
            "applied_rules": ["rule_1_t"],
            "results": {"rule_1_t": True},
            "confidence": 0.7,
            "adjustments": [],
        },
        "final_confidence": final_confidence,
        "adjustments": [],
        "gatekeeper": None,
        "kb1_evaluations": [],
        "kb2_patterns": [],
        "overall_reasoning": "Good claim.",
    }


class TestBuildPhase2Checkpoint:
    """Tests for build_phase2_checkpoint() (Issue #3650)."""

    def test_正常系_複数銘柄のscoring_outputをcheckpointに集約する(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """build_phase2_checkpoint() should aggregate scoring outputs from multiple tickers."""
        _write_scoring_output(
            workspace_dir,
            "AAPL",
            [
                _make_scored_claim_dict("AAPL-CA-001"),
                _make_scored_claim_dict("AAPL-CA-002"),
            ],
        )
        _write_scoring_output(
            workspace_dir,
            "MSFT",
            [
                _make_scored_claim_dict("MSFT-CA-001"),
            ],
        )

        output_path = tmp_path / "phase2_scored.json"
        result = build_phase2_checkpoint(
            workspace_dir=workspace_dir,
            output_path=output_path,
        )

        assert output_path.exists()
        assert "AAPL" in result
        assert "MSFT" in result
        assert len(result["AAPL"]) == 2
        assert len(result["MSFT"]) == 1

    def test_正常系_出力はticker_to_scored_claims形式になる(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Output must be {ticker: [ScoredClaim.model_dump()]} format."""
        _write_scoring_output(
            workspace_dir,
            "AAPL",
            [
                _make_scored_claim_dict("AAPL-CA-001", final_confidence=0.8),
            ],
        )

        output_path = tmp_path / "phase2_scored.json"
        result = build_phase2_checkpoint(
            workspace_dir=workspace_dir,
            output_path=output_path,
        )

        assert "AAPL" in result
        claims = result["AAPL"]
        assert len(claims) == 1
        claim = claims[0]
        # Must be a dict (model_dump() output)
        assert isinstance(claim, dict)
        assert "id" in claim
        assert "final_confidence" in claim
        assert abs(claim["final_confidence"] - 0.8) < 1e-6

    def test_正常系_jsonファイルがoutput_pathに書き出される(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """build_phase2_checkpoint() must write JSON to output_path."""
        _write_scoring_output(
            workspace_dir,
            "AAPL",
            [
                _make_scored_claim_dict("AAPL-CA-001"),
            ],
        )

        output_path = tmp_path / "checkpoint" / "phase2_scored.json"
        build_phase2_checkpoint(
            workspace_dir=workspace_dir,
            output_path=output_path,
        )

        assert output_path.exists()
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        assert "AAPL" in stored
        assert len(stored["AAPL"]) == 1

    def test_正常系_skip_missing_Falseで存在しない銘柄はValueError(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """With skip_missing=False, missing scoring_output.json raises ValueError."""
        # phase2_output/AAPL/ does not exist
        output_path = tmp_path / "phase2_scored.json"

        with pytest.raises(ValueError, match="No scoring_output.json found"):
            build_phase2_checkpoint(
                workspace_dir=workspace_dir,
                output_path=output_path,
                skip_missing=False,
            )

    def test_正常系_skip_missing_Trueで存在しない銘柄はスキップ(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """With skip_missing=True, missing scoring_output.json files are skipped."""
        # One ticker has output, one dir exists but no scoring_output.json
        _write_scoring_output(
            workspace_dir,
            "AAPL",
            [
                _make_scored_claim_dict("AAPL-CA-001"),
            ],
        )
        # Create an empty dir for MSFT (no scoring_output.json)
        (workspace_dir / "phase2_output" / "MSFT").mkdir(parents=True, exist_ok=True)

        output_path = tmp_path / "phase2_scored.json"
        result = build_phase2_checkpoint(
            workspace_dir=workspace_dir,
            output_path=output_path,
            skip_missing=True,
        )

        assert "AAPL" in result
        assert "MSFT" not in result

    def test_エッジケース_phase2_outputが空ディレクトリのとき空dictを返す(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """When phase2_output dir is empty, result should be empty dict."""
        # Create empty phase2_output dir
        (workspace_dir / "phase2_output").mkdir(parents=True, exist_ok=True)

        output_path = tmp_path / "phase2_scored.json"
        result = build_phase2_checkpoint(
            workspace_dir=workspace_dir,
            output_path=output_path,
            skip_missing=True,
        )

        assert result == {}
        assert output_path.exists()

    def test_エッジケース_scored_claimsが空のticker銘柄も含まれる(
        self,
        workspace_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Tickers with empty scored_claims list should still appear in output."""
        _write_scoring_output(workspace_dir, "AAPL", [])

        output_path = tmp_path / "phase2_scored.json"
        result = build_phase2_checkpoint(
            workspace_dir=workspace_dir,
            output_path=output_path,
            skip_missing=True,
        )

        assert "AAPL" in result
        assert result["AAPL"] == []
