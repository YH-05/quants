"""Unit tests for agent_io.py I/O helper module.

Tests cover all acceptance criteria from Issue #3624:
- prepare_extraction_input() generates JSON with PoiT-filtered transcript paths
- validate_extraction_output() normalizes confidence > 1.0 (70 -> 0.7)
- validate_extraction_output() logs and excludes claims with missing required fields
- prepare_scoring_input() builds phase 1 output + KB paths JSON
- validate_scoring_output() restores Phase 1 info via original_claims ID lookup
- All functions write to workspace_dir correctly
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import pytest

from dev.ca_strategy.agent_io import (
    prepare_extraction_input,
    prepare_scoring_input,
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
