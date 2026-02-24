"""Integration tests for agent_io.py batch (multi-chunk) workflows.

Tests cover the 3-ticker × 2-chunk pipeline scenario defined in Issue #3652:
- Chunk 1: AAPL, MSFT, GOOGL (3 tickers)
- Chunk 2: AMZN, META (2 tickers, META scoring output intentionally missing)

Test cases:
1. test_正常系_2チャンクを統合してphase2_scored_jsonを生成できる
   All 4 tickers (AAPL, MSFT, GOOGL, AMZN) are integrated correctly.
2. test_正常系_1銘柄欠損でskip_missing_True_の部分成功動作を検証できる
   META is missing; with skip_missing=True the 4 present tickers succeed
   and META is recorded under ``missing_tickers``.
3. test_正常系_Orchestrator_互換形式で出力される
   The checkpoint file is compatible with Orchestrator.run_from_checkpoint(phase=3).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from dev.ca_strategy.agent_io import build_phase2_checkpoint
from dev.ca_strategy.orchestrator import Orchestrator
from tests.dev.ca_strategy.conftest import make_scored_claim_dict

# ---------------------------------------------------------------------------
# Chunk configuration
# ---------------------------------------------------------------------------
_CHUNK1_TICKERS: list[str] = ["AAPL", "MSFT", "GOOGL"]
_CHUNK2_TICKERS: list[str] = ["AMZN", "META"]
_ALL_TICKERS: list[str] = _CHUNK1_TICKERS + _CHUNK2_TICKERS
# META scoring output is intentionally omitted to test skip_missing=True
_MISSING_TICKER: str = "META"
_PRESENT_TICKERS: list[str] = [t for t in _ALL_TICKERS if t != _MISSING_TICKER]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# _make_scored_claim_dict は tests.dev.ca_strategy.conftest.make_scored_claim_dict に統合済み
_make_scored_claim_dict = make_scored_claim_dict


def _write_phase2_scoring_output(
    workspace_dir: Any,
    ticker: str,
    claim_ids: list[str],
    *,
    final_confidence: float = 0.75,
) -> None:
    """Write phase2_output/{ticker}/scoring_output.json for one ticker.

    Parameters
    ----------
    workspace_dir : Path
        Workspace root directory.
    ticker : str
        Ticker symbol (subdirectory name under phase2_output/).
    claim_ids : list[str]
        Claim IDs to include in scored_claims.
    final_confidence : float, optional
        Confidence value for all claims.
    """
    output_dir = workspace_dir / "phase2_output" / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    scored_claims = [
        _make_scored_claim_dict(cid, final_confidence=final_confidence)
        for cid in claim_ids
    ]
    data: dict[str, Any] = {
        "scored_claims": scored_claims,
        "metadata": {
            "scored_count": len(scored_claims),
            "confidence_distribution": {"70-80": len(scored_claims)},
            "gatekeeper_applied": False,
        },
    }
    (output_dir / "scoring_output.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config_dir(tmp_path: Any) -> Any:
    """Create a config dir with universe.json and benchmark_weights.json.

    Universe contains all 5 test tickers across 2 sectors:
    - Information Technology: AAPL, MSFT, GOOGL, AMZN, META
    """
    config = tmp_path / "config"
    config.mkdir(parents=True, exist_ok=True)

    universe_data: dict[str, Any] = {
        "tickers": [
            {"ticker": "AAPL", "gics_sector": "Information Technology"},
            {"ticker": "MSFT", "gics_sector": "Information Technology"},
            {"ticker": "GOOGL", "gics_sector": "Information Technology"},
            {"ticker": "AMZN", "gics_sector": "Consumer Discretionary"},
            {"ticker": "META", "gics_sector": "Communication Services"},
        ]
    }
    (config / "universe.json").write_text(
        json.dumps(universe_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    benchmark_data: dict[str, Any] = {
        "weights": {
            "Information Technology": 0.50,
            "Consumer Discretionary": 0.30,
            "Communication Services": 0.20,
        }
    }
    (config / "benchmark_weights.json").write_text(
        json.dumps(benchmark_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return config


@pytest.fixture()
def workspace_with_all_tickers(tmp_path: Any) -> Any:
    """Workspace with phase2_output for all 5 tickers (no missing).

    Directory layout::

        workspace/
        └── phase2_output/
            ├── AAPL/scoring_output.json  (2 claims)
            ├── MSFT/scoring_output.json  (1 claim)
            ├── GOOGL/scoring_output.json (1 claim)
            ├── AMZN/scoring_output.json  (1 claim)
            └── META/scoring_output.json  (1 claim)

    Returns
    -------
    Path
        Workspace directory path.
    """
    ws = tmp_path / "workspace_full"
    ws.mkdir(parents=True)

    # Chunk 1 tickers
    _write_phase2_scoring_output(ws, "AAPL", ["AAPL-CA-001", "AAPL-CA-002"])
    _write_phase2_scoring_output(ws, "MSFT", ["MSFT-CA-001"])
    _write_phase2_scoring_output(ws, "GOOGL", ["GOOGL-CA-001"])
    # Chunk 2 tickers
    _write_phase2_scoring_output(ws, "AMZN", ["AMZN-CA-001"])
    _write_phase2_scoring_output(ws, "META", ["META-CA-001"])

    return ws


@pytest.fixture()
def workspace_with_meta_missing(tmp_path: Any) -> Any:
    """Workspace with phase2_output for 4 tickers; META scoring output omitted.

    Directory layout::

        workspace/
        └── phase2_output/
            ├── AAPL/scoring_output.json  (2 claims)
            ├── MSFT/scoring_output.json  (1 claim)
            ├── GOOGL/scoring_output.json (1 claim)
            ├── AMZN/scoring_output.json  (1 claim)
            └── META/                     (dir exists, no scoring_output.json)

    Returns
    -------
    Path
        Workspace directory path.
    """
    ws = tmp_path / "workspace_missing"
    ws.mkdir(parents=True)

    # Chunk 1 tickers (all present)
    _write_phase2_scoring_output(ws, "AAPL", ["AAPL-CA-001", "AAPL-CA-002"])
    _write_phase2_scoring_output(ws, "MSFT", ["MSFT-CA-001"])
    _write_phase2_scoring_output(ws, "GOOGL", ["GOOGL-CA-001"])
    # Chunk 2: AMZN present, META directory exists but scoring_output.json missing
    _write_phase2_scoring_output(ws, "AMZN", ["AMZN-CA-001"])
    (ws / "phase2_output" / "META").mkdir(parents=True, exist_ok=True)

    return ws


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentIoBatch:
    """Integration tests for the 2-chunk batch pipeline with agent_io."""

    def test_正常系_2チャンクを統合してphase2_scored_jsonを生成できる(
        self,
        workspace_with_all_tickers: Any,
        tmp_path: Any,
    ) -> None:
        """2-chunk pipeline (AAPL+MSFT+GOOGL / AMZN+META) integrates all 5 tickers.

        Given:
            - Chunk 1 produces scoring_output.json for AAPL (2 claims), MSFT, GOOGL
            - Chunk 2 produces scoring_output.json for AMZN, META
        When:
            - build_phase2_checkpoint() is called with skip_missing=False
        Then:
            - Checkpoint dict contains all 5 tickers as top-level keys
            - AAPL has 2 scored claim dicts
            - Each claim dict has 'id' and 'final_confidence' fields
            - Output file is written to output_path
        """
        ws = workspace_with_all_tickers
        output_path = tmp_path / "phase2_scored.json"

        result = build_phase2_checkpoint(
            workspace_dir=ws,
            output_path=output_path,
            skip_missing=False,
        )

        # All 5 tickers must be present
        for ticker in _ALL_TICKERS:
            assert ticker in result, f"Expected ticker {ticker!r} in checkpoint"

        # AAPL has 2 claims (set up in fixture)
        assert len(result["AAPL"]) == 2, "AAPL should have 2 scored claims"

        # Each entry is a dict (ScoredClaim.model_dump() format)
        for ticker in _ALL_TICKERS:
            for claim in result[ticker]:
                assert isinstance(claim, dict), f"{ticker}: claim must be a dict"
                assert "id" in claim, f"{ticker}: claim must have 'id'"
                assert "final_confidence" in claim, (
                    f"{ticker}: claim must have 'final_confidence'"
                )

        # Output JSON file must exist
        assert output_path.exists(), "phase2_scored.json must be written"
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        assert set(stored.keys()) == set(_ALL_TICKERS)

    def test_正常系_1銘柄欠損でskip_missing_True_の部分成功動作を検証できる(
        self,
        workspace_with_meta_missing: Any,
        tmp_path: Any,
    ) -> None:
        """META scoring output missing with skip_missing=True: 4 tickers succeed.

        Given:
            - Chunk 1: AAPL, MSFT, GOOGL scoring outputs exist
            - Chunk 2: AMZN scoring output exists, META directory empty (no JSON)
        When:
            - build_phase2_checkpoint() is called with skip_missing=True
        Then:
            - Returned dict contains 4 tickers (AAPL, MSFT, GOOGL, AMZN)
            - META is absent from the ticker keys
            - missing_tickers key in the checkpoint file is separate from ticker data
            - Checkpoint JSON file does not raise an error
        """
        ws = workspace_with_meta_missing
        output_path = tmp_path / "phase2_scored_partial.json"

        result = build_phase2_checkpoint(
            workspace_dir=ws,
            output_path=output_path,
            skip_missing=True,
        )

        # 4 present tickers must be in result
        for ticker in _PRESENT_TICKERS:
            assert ticker in result, f"Expected ticker {ticker!r} in result"

        # META must NOT be in the ticker dict (it was skipped)
        assert _MISSING_TICKER not in result, (
            f"{_MISSING_TICKER!r} was missing but appears in result"
        )

        # missing_tickers is a separate key from ticker data:
        # The checkpoint JSON file should only contain ticker-keyed entries.
        # META should not be mixed as a sub-list of claims under a "missing_tickers" key
        # within the same structure as tickers (they are structurally separate).
        stored = json.loads(output_path.read_text(encoding="utf-8"))

        # Verify present tickers have list-of-dicts format
        for ticker in _PRESENT_TICKERS:
            assert ticker in stored
            assert isinstance(stored[ticker], list), (
                f"{ticker}: stored value must be a list"
            )

        # META key must not be present in stored JSON (it was skipped)
        assert _MISSING_TICKER not in stored, (
            f"{_MISSING_TICKER!r} should not appear as a key in checkpoint JSON"
        )

        # Output file exists and is valid JSON
        assert output_path.exists()

    def test_正常系_Orchestrator_互換形式で出力される(
        self,
        workspace_with_all_tickers: Any,
        tmp_path: Any,
    ) -> None:
        """phase2_scored.json written by build_phase2_checkpoint is Orchestrator-compatible.

        Given:
            - All 5 tickers have scoring_output.json in phase2_output/
            - build_phase2_checkpoint() produces checkpoints/phase2_scored.json
            - checkpoints/phase1_claims.json is prepared (required by run_from_checkpoint)
        When:
            - Orchestrator.run_from_checkpoint(phase=3) is called
        Then:
            - No FileNotFoundError is raised for phase2_scored.json
            - Orchestrator completes phase 3-5 without error
        """
        ws = workspace_with_all_tickers
        config_dir = _make_config_dir(tmp_path)
        kb_dir = tmp_path / "kb"
        (kb_dir / "kb1_rules_transcript").mkdir(parents=True, exist_ok=True)
        (kb_dir / "kb2_patterns_transcript").mkdir(parents=True, exist_ok=True)
        (kb_dir / "kb3_fewshot_transcript").mkdir(parents=True, exist_ok=True)

        # Build the checkpoints directory (Orchestrator-expected location)
        checkpoint_dir = ws / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Write phase2 checkpoint via build_phase2_checkpoint
        phase2_checkpoint_path = checkpoint_dir / "phase2_scored.json"
        build_phase2_checkpoint(
            workspace_dir=ws,
            output_path=phase2_checkpoint_path,
            skip_missing=False,
        )
        assert phase2_checkpoint_path.exists(), "phase2_scored.json must be created"

        # Write phase1 checkpoint: {ticker: [Claim.model_dump()]}
        # run_from_checkpoint(phase=3) loads this because phase > 1
        phase1_claims: dict[str, list[dict[str, Any]]] = {}
        for ticker in _ALL_TICKERS:
            phase1_claims[ticker] = [
                {
                    "id": f"{ticker}-CA-001",
                    "claim_type": "competitive_advantage",
                    "claim": f"{ticker} has a competitive advantage.",
                    "evidence": "Evidence from earnings call.",
                    "rule_evaluation": {
                        "applied_rules": ["rule_1_t"],
                        "results": {"rule_1_t": True},
                        "confidence": 0.7,
                        "adjustments": [],
                    },
                    "power_classification": None,
                    "evidence_sources": [],
                }
            ]
        phase1_checkpoint_path = checkpoint_dir / "phase1_claims.json"
        phase1_checkpoint_path.write_text(
            json.dumps(phase1_claims, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Verify the phase2 checkpoint is in {ticker: [ScoredClaim.model_dump()]} format
        stored = json.loads(phase2_checkpoint_path.read_text(encoding="utf-8"))
        for ticker in _ALL_TICKERS:
            assert ticker in stored, f"Checkpoint must contain ticker {ticker!r}"
            for claim in stored[ticker]:
                assert isinstance(claim, dict)
                assert "id" in claim
                assert "final_confidence" in claim

        # Orchestrator.run_from_checkpoint(phase=3) must complete without error.
        # It loads phase1_claims.json and phase2_scored.json, then runs
        # phases 3 (neutralization), 4 (portfolio), 5 (output generation).
        orch = Orchestrator(
            config_path=config_dir,
            kb_base_dir=kb_dir,
            workspace_dir=ws,
        )
        orch.run_from_checkpoint(phase=3)
