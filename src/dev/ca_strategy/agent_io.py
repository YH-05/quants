"""I/O helper module for the CA Strategy agent-based pipeline.

Provides functions for preparing inputs and validating outputs for
Phase 1 (claim extraction) and Phase 2 (claim scoring) when running
as Claude Code sub-agents via the Task tool.

Functions
---------
- prepare_extraction_input: Build and persist Phase 1 agent input JSON
- validate_extraction_output: Parse and validate Phase 1 agent output JSON
- prepare_scoring_input: Build and persist Phase 2 agent input JSON (single batch)
- prepare_scoring_batches: Split claim IDs into batches and write batch input JSONs
- validate_scoring_output: Parse and validate Phase 2 agent output JSON
- consolidate_scored_claims: Merge scored_batch_*.json files into scoring_output.json
- run_phase3_to_5: Execute Phase 3-5 using existing Python code

Notes
-----
All functions write intermediate JSON files to ``workspace_dir`` so that
agent invocations can be replayed or debugged without re-running earlier
phases.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from dev.ca_strategy.pit import CUTOFF_DATE
from dev.ca_strategy.transcript import TranscriptLoader
from dev.ca_strategy.types import (
    ConfidenceAdjustment,
    GatekeeperResult,
    KB1RuleApplication,
    KB2PatternMatch,
    RuleEvaluation,
    ScoredClaim,
)
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from dev.ca_strategy.types import Claim

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def prepare_extraction_input(
    config_path: Path,
    transcript_dir: Path,
    kb_base_dir: Path,
    ticker: str,
    workspace_dir: Path,
    cutoff_date: date = CUTOFF_DATE,
) -> dict[str, Any]:
    """Build Phase 1 agent input and write it to workspace_dir/extraction_input.json.

    Loads transcripts for *ticker* via TranscriptLoader (which applies PoiT
    filtering), constructs KB directory paths, and writes the result as a
    JSON file that can be passed to the extraction agent.

    Parameters
    ----------
    config_path : Path
        Directory containing ``universe.json``.
    transcript_dir : Path
        Root transcript directory (``{transcript_dir}/{TICKER}/{YYYYMM}_earnings_call.json``).
    kb_base_dir : Path
        Root directory for knowledge base files
        (``kb1_rules_transcript/``, ``kb3_fewshot_transcript/`` subdirs expected).
    ticker : str
        Ticker symbol to prepare input for.
    workspace_dir : Path
        Working directory where ``extraction_input.json`` will be written.
    cutoff_date : date, optional
        PoiT cutoff date for transcript filtering.  Defaults to CUTOFF_DATE.

    Returns
    -------
    dict[str, Any]
        Input payload with keys:
        - ``ticker``: ticker symbol
        - ``transcript_paths``: list of PoiT-filtered transcript file paths (str)
        - ``kb1_dir``: path to KB1-T rules directory (str)
        - ``kb3_dir``: path to KB3-T few-shot examples directory (str)
        - ``workspace_dir``: workspace directory path (str)
        - ``cutoff_date``: PoiT cutoff date as ISO string
    """
    logger.info(
        "Preparing extraction input",
        ticker=ticker,
        transcript_dir=str(transcript_dir),
        cutoff_date=cutoff_date.isoformat(),
    )

    # Load transcripts with PoiT filtering
    loader = TranscriptLoader(base_dir=transcript_dir, cutoff_date=cutoff_date)
    transcripts = loader.load_batch([ticker])
    ticker_transcripts = transcripts.get(ticker, [])

    # Build file paths from the filtered transcripts
    transcript_paths: list[str] = []
    for transcript in ticker_transcripts:
        # Re-derive the expected file path from the transcript metadata
        event_date = transcript.metadata.event_date
        year_month = f"{event_date.year}{event_date.month:02d}"
        filepath = transcript_dir / ticker / f"{year_month}_earnings_call.json"
        if filepath.exists():
            transcript_paths.append(str(filepath))

    # KB paths
    kb1_dir = kb_base_dir / "kb1_rules_transcript"
    kb3_dir = kb_base_dir / "kb3_fewshot_transcript"

    payload: dict[str, Any] = {
        "ticker": ticker,
        "transcript_paths": transcript_paths,
        "kb1_dir": str(kb1_dir),
        "kb3_dir": str(kb3_dir),
        "workspace_dir": str(workspace_dir),
        "cutoff_date": cutoff_date.isoformat(),
    }

    # Write to workspace
    workspace_dir.mkdir(parents=True, exist_ok=True)
    output_path = workspace_dir / "extraction_input.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Extraction input prepared",
        ticker=ticker,
        transcript_count=len(transcript_paths),
        output_path=str(output_path),
    )

    return payload


def validate_extraction_output(
    output_path: Path,
    ticker: str,
) -> list[Claim]:
    """Parse and validate Phase 1 agent output JSON into Claim models.

    Reads the JSON file at *output_path*, normalizes ``confidence`` values
    greater than 1.0 (e.g. ``70 -> 0.7``), validates each raw claim dict
    into a :class:`~dev.ca_strategy.types.Claim` model, and excludes
    invalid entries with a warning log.

    Parameters
    ----------
    output_path : Path
        Path to the Phase 1 agent output JSON file.
        Expected structure: ``{"claims": [...], "ticker": "...", ...}``.
    ticker : str
        Ticker symbol (used for logging context).

    Returns
    -------
    list[Claim]
        Successfully validated Claim models.  Invalid entries are excluded
        and logged as warnings.  Returns ``[]`` if the file does not exist
        or cannot be parsed.
    """
    if not output_path.exists():
        logger.warning(
            "Extraction output file not found",
            ticker=ticker,
            path=str(output_path),
        )
        return []

    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to parse extraction output JSON",
            ticker=ticker,
            path=str(output_path),
            error=str(exc),
        )
        return []

    raw_claims = data.get("claims", [])
    if not raw_claims:
        logger.debug(
            "No claims found in extraction output",
            ticker=ticker,
            path=str(output_path),
        )
        return []

    claims: list[Claim] = []
    for raw in raw_claims:
        claim = _parse_raw_claim(raw, ticker)
        if claim is not None:
            claims.append(claim)

    logger.info(
        "Extraction output validated",
        ticker=ticker,
        total_raw=len(raw_claims),
        valid_count=len(claims),
    )

    return claims


def prepare_scoring_input(
    workspace_dir: Path,
    kb_base_dir: Path,
    ticker: str,
) -> dict[str, Any]:
    """Build Phase 2 agent input and write it to workspace_dir/scoring_input.json.

    Constructs paths to Phase 1 output and KB directories for the scoring
    agent to consume.

    Parameters
    ----------
    workspace_dir : Path
        Working directory containing ``phase1_output/{ticker}/`` subdirectory.
    kb_base_dir : Path
        Root directory for knowledge base files
        (``kb1_rules_transcript/``, ``kb2_patterns_transcript/``,
        ``kb3_fewshot_transcript/`` subdirs expected).
    ticker : str
        Ticker symbol to prepare scoring input for.

    Returns
    -------
    dict[str, Any]
        Scoring input payload with keys:
        - ``ticker``: ticker symbol
        - ``phase1_output_dir``: path to Phase 1 output directory for this ticker
        - ``kb1_dir``: path to KB1-T rules directory (str)
        - ``kb2_dir``: path to KB2-T patterns directory (str)
        - ``kb3_dir``: path to KB3-T few-shot examples directory (str)
        - ``workspace_dir``: workspace directory path (str)
    """
    logger.info(
        "Preparing scoring input",
        ticker=ticker,
        workspace_dir=str(workspace_dir),
    )

    phase1_output_dir = workspace_dir / "phase1_output" / ticker
    kb1_dir = kb_base_dir / "kb1_rules_transcript"
    kb2_dir = kb_base_dir / "kb2_patterns_transcript"
    kb3_dir = kb_base_dir / "kb3_fewshot_transcript"

    payload: dict[str, Any] = {
        "ticker": ticker,
        "phase1_output_dir": str(phase1_output_dir),
        "kb1_dir": str(kb1_dir),
        "kb2_dir": str(kb2_dir),
        "kb3_dir": str(kb3_dir),
        "workspace_dir": str(workspace_dir),
    }

    # Write to workspace
    workspace_dir.mkdir(parents=True, exist_ok=True)
    output_path = workspace_dir / "scoring_input.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Scoring input prepared",
        ticker=ticker,
        output_path=str(output_path),
    )

    return payload


def validate_scoring_output(
    output_path: Path,
    ticker: str,
    original_claims: list[Claim],
) -> list[ScoredClaim]:
    """Parse and validate Phase 2 agent output JSON into ScoredClaim models.

    Reads the JSON file at *output_path*, normalizes ``final_confidence``
    values greater than 1.0 (e.g. ``70 -> 0.7``), restores Phase 1 claim
    information via ID lookup against *original_claims*, and validates
    each entry into a :class:`~dev.ca_strategy.types.ScoredClaim` model.

    Parameters
    ----------
    output_path : Path
        Path to the Phase 2 agent output JSON file.
        Expected structure: ``{"scored_claims": [...]}``.
    ticker : str
        Ticker symbol (used for logging context).
    original_claims : list[Claim]
        Phase 1 claims used for ID lookup to restore claim text, evidence,
        rule_evaluation, and other Phase 1 fields.

    Returns
    -------
    list[ScoredClaim]
        Successfully validated ScoredClaim models.  Invalid entries are
        excluded and logged as warnings.  Returns ``[]`` if the file does
        not exist or cannot be parsed.
    """
    if not output_path.exists():
        logger.warning(
            "Scoring output file not found",
            ticker=ticker,
            path=str(output_path),
        )
        return []

    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to parse scoring output JSON",
            ticker=ticker,
            path=str(output_path),
            error=str(exc),
        )
        return []

    raw_scored_list = data.get("scored_claims", [])
    if not raw_scored_list:
        logger.debug(
            "No scored_claims found in scoring output",
            ticker=ticker,
            path=str(output_path),
        )
        return []

    # Build lookup from original claims by ID
    claim_lookup: dict[str, Claim] = {c.id: c for c in original_claims}

    scored: list[ScoredClaim] = []
    for raw in raw_scored_list:
        parsed = _parse_raw_scored_claim(raw, claim_lookup, ticker)
        if parsed is not None:
            scored.append(parsed)

    logger.info(
        "Scoring output validated",
        ticker=ticker,
        total_raw=len(raw_scored_list),
        valid_count=len(scored),
    )

    return scored


def prepare_scoring_batches(
    workspace_dir: Path,
    kb_base_dir: Path,
    ticker: str,
    batch_size: int = 5,
) -> list[dict[str, Any]]:
    """Split extraction output claim IDs into batches and write input JSON files.

    Reads ``workspace_dir/phase1_output/{ticker}/extraction_output.json`` to
    obtain the list of claim IDs, then partitions them into groups of
    *batch_size* and writes each group as
    ``workspace_dir/batch_inputs/scoring_input_batch_{n}.json``.

    This is the batch counterpart to :func:`prepare_scoring_input`, designed to
    allow the ``transcript-claim-scorer`` agent to process claims in smaller
    chunks and avoid the 32 K-token output limit.

    Parameters
    ----------
    workspace_dir : Path
        Working directory containing ``phase1_output/{ticker}/extraction_output.json``.
    kb_base_dir : Path
        Root directory for knowledge base files
        (``kb1_rules_transcript/``, ``kb2_patterns_transcript/``,
        ``kb3_fewshot_transcript/`` subdirs expected).
    ticker : str
        Ticker symbol to prepare batched scoring inputs for.
    batch_size : int, optional
        Number of claim IDs per batch.  Defaults to 5.

    Returns
    -------
    list[dict[str, Any]]
        One element per batch, each containing:
        - ``input_path``: absolute path of the written batch input JSON (str)
        - ``output_path``: expected path of the scoring agent output (str)
        - ``target_claim_ids``: list of claim IDs for this batch
        - ``batch_index``: 0-based index of this batch
        - ``batch_total``: total number of batches

    Raises
    ------
    ValueError
        If ``extraction_output.json`` does not exist or cannot be read.
    """
    extraction_output_path = (
        workspace_dir / "phase1_output" / ticker / "extraction_output.json"
    )

    if not extraction_output_path.exists():
        msg = (
            f"extraction_output.json not found for ticker {ticker!r}: "
            f"{extraction_output_path}"
        )
        logger.error(
            "extraction_output.json not found",
            ticker=ticker,
            path=str(extraction_output_path),
        )
        raise ValueError(msg)

    try:
        data = json.loads(extraction_output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        msg = f"Failed to read extraction_output.json for ticker {ticker!r}: {exc}"
        logger.error(
            "Failed to read extraction_output.json",
            ticker=ticker,
            path=str(extraction_output_path),
            error=str(exc),
        )
        raise ValueError(msg) from exc

    raw_claims = data.get("claims", [])
    claim_ids: list[str] = [
        c["id"] for c in raw_claims if isinstance(c, dict) and "id" in c
    ]

    logger.info(
        "Preparing scoring batches",
        ticker=ticker,
        total_claims=len(claim_ids),
        batch_size=batch_size,
    )

    # Partition claim IDs into batches
    id_batches: list[list[str]] = [
        claim_ids[i : i + batch_size] for i in range(0, len(claim_ids), batch_size)
    ]
    if not id_batches:
        id_batches = [[]]

    batch_total = len(id_batches)
    batch_input_dir = workspace_dir / "batch_inputs"
    batch_input_dir.mkdir(parents=True, exist_ok=True)

    # KB paths (same as prepare_scoring_input)
    kb1_dir = kb_base_dir / "kb1_rules_transcript"
    kb2_dir = kb_base_dir / "kb2_patterns_transcript"
    kb3_dir = kb_base_dir / "kb3_fewshot_transcript"

    phase2_output_dir = workspace_dir / "phase2_output" / ticker

    results: list[dict[str, Any]] = []
    for batch_index, ids in enumerate(id_batches):
        input_path = batch_input_dir / f"scoring_input_batch_{batch_index}.json"
        output_path = phase2_output_dir / f"scored_batch_{batch_index}.json"

        payload: dict[str, Any] = {
            "ticker": ticker,
            "phase1_output_dir": str(workspace_dir / "phase1_output" / ticker),
            "kb1_dir": str(kb1_dir),
            "kb2_dir": str(kb2_dir),
            "kb3_dir": str(kb3_dir),
            "workspace_dir": str(workspace_dir),
            "target_claim_ids": ids,
            "output_path": str(output_path),
            "batch_index": batch_index,
            "batch_total": batch_total,
        }

        input_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        results.append(
            {
                "input_path": str(input_path),
                "output_path": str(output_path),
                "target_claim_ids": ids,
                "batch_index": batch_index,
                "batch_total": batch_total,
            }
        )

    logger.info(
        "Scoring batches prepared",
        ticker=ticker,
        batch_count=batch_total,
        batch_input_dir=str(batch_input_dir),
    )

    return results


def consolidate_scored_claims(
    workspace_dir: Path,
    ticker: str,
) -> Path:
    """Merge all scored batch files into a single scoring_output.json.

    Globs ``workspace_dir/phase2_output/{ticker}/scored_batch_*.json``, sorts
    them by the numeric batch index extracted from the filename, concatenates
    the ``scored_claims`` lists, and re-calculates the ``metadata`` fields
    (``scored_count``, ``confidence_distribution``, ``gatekeeper_applied``).

    The merged result is written to ``workspace_dir/scoring_output.json``
    (overwriting any existing file).

    Parameters
    ----------
    workspace_dir : Path
        Working directory containing
        ``phase2_output/{ticker}/scored_batch_*.json`` files.
    ticker : str
        Ticker symbol whose batch files should be consolidated.

    Returns
    -------
    Path
        Path to the written ``scoring_output.json`` file.

    Raises
    ------
    ValueError
        If no ``scored_batch_*.json`` files are found for *ticker*.
    """
    phase2_dir = workspace_dir / "phase2_output" / ticker
    batch_pattern = re.compile(r"scored_batch_(\d+)\.json$")

    # Collect and sort batch files by numeric index
    batch_files: list[tuple[int, Path]] = []
    if phase2_dir.exists():
        for f in phase2_dir.iterdir():
            m = batch_pattern.match(f.name)
            if m:
                batch_files.append((int(m.group(1)), f))

    if not batch_files:
        msg = (
            f"No scored_batch_*.json files found for ticker {ticker!r} in {phase2_dir}"
        )
        logger.error(
            "No scored batch files found",
            ticker=ticker,
            phase2_dir=str(phase2_dir),
        )
        raise ValueError(msg)

    batch_files.sort(key=lambda t: t[0])

    logger.info(
        "Consolidating scored claims",
        ticker=ticker,
        batch_count=len(batch_files),
    )

    # Merge scored_claims in order
    all_scored_claims: list[dict[str, Any]] = []
    any_gatekeeper_applied = False

    for _, batch_path in batch_files:
        try:
            batch_data = json.loads(batch_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to read scored batch file, skipping",
                path=str(batch_path),
                error=str(exc),
            )
            continue

        batch_claims = batch_data.get("scored_claims", [])
        all_scored_claims.extend(batch_claims)

        # Track gatekeeper_applied across batches
        batch_meta = batch_data.get("metadata", {})
        if batch_meta.get("gatekeeper_applied", False):
            any_gatekeeper_applied = True

    # Re-calculate metadata
    confidence_distribution: dict[str, int] = {}
    for sc in all_scored_claims:
        raw_conf = sc.get("final_confidence", 0.0)
        if isinstance(raw_conf, (int, float)):
            bucket_low = int(raw_conf * 10) * 10
            bucket_high = bucket_low + 10
            bucket_key = f"{bucket_low}-{bucket_high}"
            confidence_distribution[bucket_key] = (
                confidence_distribution.get(bucket_key, 0) + 1
            )

    metadata: dict[str, Any] = {
        "scored_count": len(all_scored_claims),
        "confidence_distribution": confidence_distribution,
        "gatekeeper_applied": any_gatekeeper_applied,
    }

    output_data: dict[str, Any] = {
        "scored_claims": all_scored_claims,
        "metadata": metadata,
    }

    output_path = workspace_dir / "scoring_output.json"
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Scored claims consolidated",
        ticker=ticker,
        total_claims=len(all_scored_claims),
        output_path=str(output_path),
    )

    return output_path


def run_phase3_to_5(
    workspace_dir: Path,
    config_path: Path,
) -> None:
    """Execute Phase 3-5 using existing Python pipeline code.

    Runs score aggregation, sector neutralization, portfolio construction,
    and output generation using the Orchestrator's checkpoint-based
    resumption from Phase 3.

    Parameters
    ----------
    workspace_dir : Path
        Working directory containing Phase 2 checkpoint
        (``checkpoints/phase2_scored.json``).
    config_path : Path
        Directory containing ``universe.json`` and
        ``benchmark_weights.json``.

    Notes
    -----
    In DIS (Development Integration Smoke) tests, this function can be
    skipped by not calling it.  It requires a valid Phase 2 checkpoint
    and KB base directory to be configured in the Orchestrator.
    """
    logger.info(
        "Running Phase 3-5",
        workspace_dir=str(workspace_dir),
        config_path=str(config_path),
    )

    # Import here to avoid circular imports at module level
    from dev.ca_strategy.orchestrator import Orchestrator

    # AIDEV-NOTE: kb_base_dir is not needed for Phase 3-5, but Orchestrator
    # requires it.  We pass workspace_dir as a fallback path since Phase 3-5
    # does not read KB files.
    orch = Orchestrator(
        config_path=config_path,
        kb_base_dir=workspace_dir,
        workspace_dir=workspace_dir,
    )
    orch.run_from_checkpoint(phase=3)

    logger.info("Phase 3-5 completed", workspace_dir=str(workspace_dir))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_confidence(value: float | int) -> float:
    """Normalize confidence from percentage (0-100) to unit range (0.0-1.0).

    Parameters
    ----------
    value : float | int
        Raw confidence value.  Values > 1.0 are divided by 100.

    Returns
    -------
    float
        Confidence value in [0.0, 1.0].
    """
    if isinstance(value, (int, float)) and value > 1.0:
        return float(value) / 100.0
    return float(value)


def _parse_raw_claim(raw: dict[str, Any], ticker: str) -> Claim | None:
    """Parse a single raw claim dict into a Claim model.

    Mirrors the logic in ``ClaimExtractor._parse_single_claim()`` but is
    designed for reading pre-written agent output rather than LLM responses.

    Parameters
    ----------
    raw : dict[str, Any]
        Raw claim dict from Phase 1 agent output.
    ticker : str
        Ticker symbol for logging context.

    Returns
    -------
    Claim | None
        Validated Claim, or None if required fields are missing or invalid.
    """
    # Import here to avoid issues with delayed loading
    from dev.ca_strategy.types import (
        Claim,
        EvidenceSource,
        PowerClassification,
    )

    try:
        claim_id = raw.get("id", "unknown")

        # rule_evaluation is required
        rule_eval_raw = raw.get("rule_evaluation")
        if not isinstance(rule_eval_raw, dict):
            logger.warning(
                "Claim missing rule_evaluation, excluding",
                claim_id=claim_id,
                ticker=ticker,
            )
            return None

        # Normalize confidence
        raw_confidence = rule_eval_raw.get("confidence", 0.5)
        confidence = _normalize_confidence(raw_confidence)
        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        # Parse results (support dict and list-of-dict formats)
        results_raw = rule_eval_raw.get("results", {})
        if isinstance(results_raw, dict):
            results: dict[str, bool] = {
                k: bool(v) if not isinstance(v, bool) else v
                for k, v in results_raw.items()
            }
        else:
            results = {}

        rule_evaluation = RuleEvaluation(
            applied_rules=rule_eval_raw.get("applied_rules", []),
            results=results,
            confidence=confidence,
            adjustments=rule_eval_raw.get("adjustments", []),
        )

        # Optional 7 Powers structured fields
        power_classification: PowerClassification | None = None
        pc_raw = raw.get("power_classification")
        if isinstance(pc_raw, dict):
            power_type = pc_raw.get("power_type", "")
            benefit = pc_raw.get("benefit", "")
            barrier = pc_raw.get("barrier", "")
            valid_types = {
                "scale_economies",
                "network_economies",
                "counter_positioning",
                "switching_costs",
                "branding",
                "cornered_resource",
                "process_power",
            }
            if power_type in valid_types and benefit and barrier:
                power_classification = PowerClassification(
                    power_type=power_type,  # type: ignore[arg-type]
                    benefit=benefit,
                    barrier=barrier,
                )

        evidence_sources: list[EvidenceSource] = []
        sources_raw = raw.get("evidence_sources", [])
        if isinstance(sources_raw, list):
            for src in sources_raw:
                if not isinstance(src, dict):
                    continue
                speaker = src.get("speaker", "")
                section_type = src.get("section_type", "")
                quarter = src.get("quarter", "")
                quote = src.get("quote", "")
                if speaker and section_type and quarter and quote:
                    evidence_sources.append(
                        EvidenceSource(
                            speaker=speaker,
                            role=src.get("role"),
                            section_type=section_type,
                            quarter=quarter,
                            quote=quote,
                        )
                    )

        # evidence fallback
        evidence = raw.get("evidence") or raw.get("evidence_from_transcript", "")
        if not evidence:
            evidence = raw.get("claim", "No evidence provided")

        claim_text = raw.get("claim", "")
        claim_type = raw.get("claim_type", "competitive_advantage")

        if not claim_text:
            logger.warning(
                "Claim missing 'claim' field, excluding",
                claim_id=claim_id,
                ticker=ticker,
            )
            return None

        return Claim(
            id=claim_id,
            claim_type=claim_type,  # type: ignore[arg-type]
            claim=claim_text,
            evidence=evidence,
            rule_evaluation=rule_evaluation,
            power_classification=power_classification,
            evidence_sources=evidence_sources,
        )

    except Exception:
        claim_id_safe = raw.get("id", "unknown") if isinstance(raw, dict) else "unknown"
        logger.warning(
            "Failed to parse claim, excluding",
            claim_id=claim_id_safe,
            ticker=ticker,
            exc_info=True,
        )
        return None


def _parse_raw_scored_claim(
    raw: dict[str, Any],
    claim_lookup: dict[str, Claim],
    ticker: str,
) -> ScoredClaim | None:
    """Parse a single raw scored claim dict into a ScoredClaim model.

    Mirrors the logic in ``ClaimScorer._parse_single_scored_claim()``.
    Uses *claim_lookup* to restore Phase 1 claim information when a
    matching ID is found.

    Parameters
    ----------
    raw : dict[str, Any]
        Raw scored claim dict from Phase 2 agent output.
    claim_lookup : dict[str, Claim]
        Mapping of claim ID to original Phase 1 Claim.
    ticker : str
        Ticker symbol for logging context.

    Returns
    -------
    ScoredClaim | None
        Validated ScoredClaim, or None if required fields are missing or invalid.
    """
    try:
        claim_id = raw.get("id", "unknown")

        # final_confidence is required
        raw_confidence = raw.get("final_confidence")
        if raw_confidence is None:
            logger.warning(
                "Scored claim missing final_confidence, excluding",
                claim_id=claim_id,
                ticker=ticker,
            )
            return None

        final_confidence = _normalize_confidence(raw_confidence)
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Parse confidence adjustments
        adjustments: list[ConfidenceAdjustment] = []
        for adj_raw in raw.get("confidence_adjustments", []):
            if isinstance(adj_raw, dict):
                adj_value = adj_raw.get("adjustment", 0)
                if isinstance(adj_value, (int, float)):
                    adj_value = max(-1.0, min(1.0, float(adj_value)))
                else:
                    adj_value = 0.0
                adjustments.append(
                    ConfidenceAdjustment(
                        source=adj_raw.get("source", "unknown"),
                        adjustment=adj_value,
                        reasoning=adj_raw.get("reasoning", ""),
                    )
                )

        # Parse structured evaluation fields
        gatekeeper = _parse_gatekeeper(raw)
        kb1_evaluations = _parse_kb1_evaluations(raw)
        kb2_patterns = _parse_kb2_patterns(raw)
        overall_reasoning = raw.get("overall_reasoning", "")

        # Restore Phase 1 data from original claims lookup
        original = claim_lookup.get(claim_id)
        if original is not None:
            return ScoredClaim(
                id=original.id,
                claim_type=original.claim_type,
                claim=original.claim,
                evidence=original.evidence,
                rule_evaluation=original.rule_evaluation,
                final_confidence=final_confidence,
                adjustments=adjustments,
                power_classification=original.power_classification,
                evidence_sources=original.evidence_sources,
                gatekeeper=gatekeeper,
                kb1_evaluations=kb1_evaluations,
                kb2_patterns=kb2_patterns,
                overall_reasoning=overall_reasoning,
            )

        # Fallback: use raw data when original claim not found
        fallback_claim = raw.get("claim", "")
        fallback_evidence = raw.get("evidence", "")
        fallback_claim_type = raw.get("claim_type", "competitive_advantage")

        return ScoredClaim(
            id=claim_id,
            claim_type=fallback_claim_type,  # type: ignore[arg-type]
            claim=fallback_claim,
            evidence=fallback_evidence,
            rule_evaluation=_default_rule_evaluation(),
            final_confidence=final_confidence,
            adjustments=adjustments,
            gatekeeper=gatekeeper,
            kb1_evaluations=kb1_evaluations,
            kb2_patterns=kb2_patterns,
            overall_reasoning=overall_reasoning,
        )

    except Exception:
        claim_id_safe = raw.get("id", "unknown") if isinstance(raw, dict) else "unknown"
        logger.warning(
            "Failed to parse scored claim, excluding",
            claim_id=claim_id_safe,
            ticker=ticker,
            exc_info=True,
        )
        return None


def _parse_gatekeeper(raw: dict[str, Any]) -> GatekeeperResult | None:
    """Parse gatekeeper section from raw scored claim.

    Parameters
    ----------
    raw : dict[str, Any]
        Raw scored claim dict.

    Returns
    -------
    GatekeeperResult | None
        Parsed result, or None if the section is absent.
    """
    gk_raw = raw.get("gatekeeper")
    if not isinstance(gk_raw, dict):
        return None

    rule9 = bool(gk_raw.get("rule9_factual_error", False))
    rule3 = bool(gk_raw.get("rule3_industry_common", False))
    triggered = bool(gk_raw.get("triggered", rule9 or rule3))

    override = gk_raw.get("override_confidence")
    if isinstance(override, (int, float)):
        if override > 1.0:
            override = override / 100.0
        override = max(0.0, min(1.0, float(override)))
    else:
        override = None

    return GatekeeperResult(
        rule9_factual_error=rule9,
        rule3_industry_common=rule3,
        triggered=triggered,
        override_confidence=override,
    )


def _parse_kb1_evaluations(raw: dict[str, Any]) -> list[KB1RuleApplication]:
    """Parse kb1_evaluations list from raw scored claim.

    Parameters
    ----------
    raw : dict[str, Any]
        Raw scored claim dict.

    Returns
    -------
    list[KB1RuleApplication]
        Parsed evaluations.  Empty list if the section is absent.
    """
    evals_raw = raw.get("kb1_evaluations", [])
    if not isinstance(evals_raw, list):
        return []

    evaluations: list[KB1RuleApplication] = []
    for item in evals_raw:
        if not isinstance(item, dict):
            continue
        rule_id = item.get("rule_id", "")
        if not rule_id:
            continue
        evaluations.append(
            KB1RuleApplication(
                rule_id=rule_id,
                result=bool(item.get("result", False)),
                reasoning=item.get("reasoning", ""),
            )
        )
    return evaluations


def _parse_kb2_patterns(raw: dict[str, Any]) -> list[KB2PatternMatch]:
    """Parse kb2_patterns list from raw scored claim.

    Parameters
    ----------
    raw : dict[str, Any]
        Raw scored claim dict.

    Returns
    -------
    list[KB2PatternMatch]
        Parsed pattern matches.  Empty list if the section is absent.
    """
    patterns_raw = raw.get("kb2_patterns", [])
    if not isinstance(patterns_raw, list):
        return []

    patterns: list[KB2PatternMatch] = []
    for pat in patterns_raw:
        if not isinstance(pat, dict):
            continue
        pattern_id = pat.get("pattern_id") or pat.get("pattern", "")
        if not pattern_id:
            continue

        adj_value = pat.get("adjustment", 0)
        if isinstance(adj_value, (int, float)):
            adj_value = max(-1.0, min(1.0, float(adj_value)))
        else:
            adj_value = 0.0

        patterns.append(
            KB2PatternMatch(
                pattern_id=pattern_id,
                matched=bool(pat.get("matched", pat.get("match", False))),
                adjustment=adj_value,
                reasoning=pat.get("reasoning", ""),
            )
        )
    return patterns


def _default_rule_evaluation() -> RuleEvaluation:
    """Create a default RuleEvaluation for fallback cases.

    Returns
    -------
    RuleEvaluation
        Default rule evaluation with empty fields and 0.5 confidence.
    """
    return RuleEvaluation(
        applied_rules=[],
        results={},
        confidence=0.5,
        adjustments=[],
    )


__all__ = [
    "consolidate_scored_claims",
    "prepare_extraction_input",
    "prepare_scoring_batches",
    "prepare_scoring_input",
    "run_phase3_to_5",
    "validate_extraction_output",
    "validate_scoring_output",
]
