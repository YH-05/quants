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
- prepare_universe_chunks: Split universe.json into chunk_{n:02d}.json files
- build_phase2_checkpoint: Aggregate phase2 scoring outputs into phase2_scored.json

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

_TICKER_RE = re.compile(r"^[A-Z]{1,10}$")

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
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Build Phase 1 agent input and write it to extraction_input.json.

    Loads transcripts for *ticker* via TranscriptLoader (which applies PoiT
    filtering), constructs KB directory paths, and writes the result as a
    JSON file that can be passed to the extraction agent.

    By default the file is written to ``workspace_dir/extraction_input.json``.
    When *output_dir* is given, the file is written to
    ``output_dir/extraction_input.json`` instead, and the ``workspace_dir``
    key in the returned payload reflects *output_dir*.

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
        Working directory used as the default output location.
    cutoff_date : date, optional
        PoiT cutoff date for transcript filtering.  Defaults to CUTOFF_DATE.
    output_dir : Path | None, optional
        When provided, ``extraction_input.json`` is written to this directory
        instead of *workspace_dir*.  The ``workspace_dir`` field in the
        returned payload is set to *output_dir*.  Defaults to ``None``
        (uses *workspace_dir*).

    Returns
    -------
    dict[str, Any]
        Input payload with keys:
        - ``ticker``: ticker symbol
        - ``transcript_paths``: list of PoiT-filtered transcript file paths (str)
        - ``kb1_dir``: path to KB1-T rules directory (str)
        - ``kb3_dir``: path to KB3-T few-shot examples directory (str)
        - ``workspace_dir``: effective output directory path (str)
        - ``cutoff_date``: PoiT cutoff date as ISO string
    """
    _validate_ticker(ticker)
    logger.info(
        "Preparing extraction input",
        ticker=ticker,
        transcript_dir=str(transcript_dir),
        cutoff_date=cutoff_date.isoformat(),
    )

    # Determine the effective output directory
    effective_dir = output_dir if output_dir is not None else workspace_dir

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

    # KB paths (extraction only uses KB1 and KB3)
    kb1_dir, _kb2_dir, kb3_dir = _build_kb_dirs(kb_base_dir)

    payload: dict[str, Any] = {
        "ticker": ticker,
        "transcript_paths": transcript_paths,
        "kb1_dir": str(kb1_dir),
        "kb3_dir": str(kb3_dir),
        "workspace_dir": str(effective_dir),
        "cutoff_date": cutoff_date.isoformat(),
    }

    # Write to effective output directory
    output_path = effective_dir / "extraction_input.json"
    _write_json_file(output_path, payload)

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

    data = _read_json_file(output_path, context=f"extraction_output ticker={ticker}")
    if data is None:
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
    _validate_ticker(ticker)
    logger.info(
        "Preparing scoring input",
        ticker=ticker,
        workspace_dir=str(workspace_dir),
    )

    kb_dirs = _build_kb_dirs(kb_base_dir)
    payload: dict[str, Any] = _build_scoring_base_payload(
        ticker, workspace_dir, kb_dirs
    )

    # Write to workspace
    output_path = workspace_dir / "scoring_input.json"
    _write_json_file(output_path, payload)

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

    data = _read_json_file(output_path, context=f"scoring_output ticker={ticker}")
    if data is None:
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
        If ``batch_size`` is not a positive integer.
    """
    _validate_ticker(ticker)
    if batch_size <= 0:
        raise ValueError(f"batch_size must be a positive integer, got {batch_size}")

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

    data = _read_json_file(
        extraction_output_path,
        context=f"extraction_output ticker={ticker}",
    )
    if data is None:
        msg = f"Failed to read extraction_output.json for ticker {ticker!r}: {extraction_output_path}"
        raise ValueError(msg)

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

    kb_dirs = _build_kb_dirs(kb_base_dir)
    phase2_output_dir = workspace_dir / "phase2_output" / ticker

    results: list[dict[str, Any]] = []
    for batch_index, ids in enumerate(id_batches):
        input_path = batch_input_dir / f"scoring_input_batch_{batch_index}.json"
        output_path = phase2_output_dir / f"scored_batch_{batch_index}.json"

        payload: dict[str, Any] = {
            **_build_scoring_base_payload(ticker, workspace_dir, kb_dirs),
            "target_claim_ids": ids,
            "output_path": str(output_path),
            "batch_index": batch_index,
            "batch_total": batch_total,
        }

        _write_json_file(input_path, payload)

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
    output_path: Path | None = None,
) -> Path:
    """Merge all scored batch files into a single scoring_output.json.

    Globs ``workspace_dir/phase2_output/{ticker}/scored_batch_*.json``, sorts
    them by the numeric batch index extracted from the filename, concatenates
    the ``scored_claims`` lists, and re-calculates the ``metadata`` fields
    (``scored_count``, ``confidence_distribution``, ``gatekeeper_applied``).

    By default the merged result is written to
    ``workspace_dir/scoring_output.json`` (overwriting any existing file).
    When *output_path* is given, the file is written to that path instead.

    Parameters
    ----------
    workspace_dir : Path
        Working directory containing
        ``phase2_output/{ticker}/scored_batch_*.json`` files.
    ticker : str
        Ticker symbol whose batch files should be consolidated.
    output_path : Path | None, optional
        Destination path for the consolidated JSON file.  When ``None``
        (default), the file is written to
        ``workspace_dir/scoring_output.json``.

    Returns
    -------
    Path
        Path to the written consolidated JSON file.

    Raises
    ------
    ValueError
        If no ``scored_batch_*.json`` files are found for *ticker*.
    """
    _validate_ticker(ticker)
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
        batch_data = _read_json_file(batch_path, context="scored_batch")
        if batch_data is None:
            continue

        batch_claims = batch_data.get("scored_claims", [])
        all_scored_claims.extend(batch_claims)

        # Track gatekeeper_applied across batches
        batch_meta = batch_data.get("metadata", {})
        if batch_meta.get("gatekeeper_applied", False):
            any_gatekeeper_applied = True

    # Re-calculate metadata using the same normalization as the scoring path
    confidence_distribution: dict[str, int] = {}
    for sc in all_scored_claims:
        raw_conf = sc.get("final_confidence", 0.0)
        if isinstance(raw_conf, (int, float)):
            normalized = _normalize_confidence(raw_conf)
            bucket_low = int(normalized * 10) * 10
            bucket_key = f"{bucket_low}-{min(bucket_low + 10, 100)}"
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

    effective_output_path = (
        output_path
        if output_path is not None
        else workspace_dir / "scoring_output.json"
    )
    _write_json_file(effective_output_path, output_data)

    logger.info(
        "Scored claims consolidated",
        ticker=ticker,
        total_claims=len(all_scored_claims),
        output_path=str(effective_output_path),
    )

    return effective_output_path


def prepare_universe_chunks(
    universe_path: Path,
    chunk_size: int = 10,
) -> list[Path]:
    """Split universe.json into chunk_{n:02d}.json files.

    Reads the ``tickers`` array from *universe_path*, partitions it into
    groups of *chunk_size*, and writes each group as
    ``chunk_{n:02d}.json`` in the same directory as *universe_path*.

    Parameters
    ----------
    universe_path : Path
        Path to ``universe.json`` containing a ``tickers`` list.
    chunk_size : int, optional
        Number of tickers per chunk.  Defaults to 10.

    Returns
    -------
    list[Path]
        Sorted list of paths to the written chunk files.
        Returns an empty list when the ``tickers`` array is empty.

    Raises
    ------
    ValueError
        If *universe_path* does not exist.
        If *chunk_size* is not a positive integer.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be a positive integer, got {chunk_size}")

    if not universe_path.exists():
        msg = f"universe.json not found: {universe_path}"
        logger.error("universe.json not found", path=str(universe_path))
        raise ValueError(msg)

    data = _read_json_file(universe_path, context="universe.json")
    if data is None:
        msg = f"Failed to read universe.json: {universe_path}"
        raise ValueError(msg)

    tickers: list[dict[str, Any]] = data.get("tickers", [])

    logger.info(
        "Splitting universe into chunks",
        universe_path=str(universe_path),
        total_tickers=len(tickers),
        chunk_size=chunk_size,
    )

    if not tickers:
        return []

    output_dir = universe_path.parent
    chunk_paths: list[Path] = []

    ticker_batches: list[list[dict[str, Any]]] = [
        tickers[i : i + chunk_size] for i in range(0, len(tickers), chunk_size)
    ]

    for idx, batch in enumerate(ticker_batches):
        chunk_path = output_dir / f"chunk_{idx:02d}.json"
        chunk_data: dict[str, Any] = {"tickers": batch}
        _write_json_file(chunk_path, chunk_data)
        chunk_paths.append(chunk_path)

    logger.info(
        "Universe chunks prepared",
        chunk_count=len(chunk_paths),
        output_dir=str(output_dir),
    )

    return chunk_paths


def _build_phase1_evidence_lookup(
    phase1_dirs: list[Path],
) -> dict[str, dict[str, Claim]]:
    """Phase 1 extraction outputs から {ticker: {claim_id: Claim}} を構築.

    Parameters
    ----------
    phase1_dirs : list[Path]
        Phase 1 output ディレクトリのリスト。各ディレクトリの直下に
        ``{TICKER}/extraction_output.json`` が存在する想定。

    Returns
    -------
    dict[str, dict[str, Claim]]
        ``{ticker: {claim_id: Claim}}`` の lookup 辞書。
    """
    from dev.ca_strategy.types import Claim

    lookup: dict[str, dict[str, Claim]] = {}
    for phase1_dir in phase1_dirs:
        for extraction_path in sorted(phase1_dir.glob("*/extraction_output.json")):
            ticker = extraction_path.parent.name
            claims = validate_extraction_output(extraction_path, ticker)
            if claims:
                ticker_lookup = lookup.setdefault(ticker, {})
                for claim in claims:
                    ticker_lookup[claim.id] = claim
                logger.debug(
                    "Phase 1 evidence loaded",
                    ticker=ticker,
                    claim_count=len(claims),
                    source=str(phase1_dir),
                )
    return lookup


def build_phase2_checkpoint(
    workspace_dir: Path,
    output_path: Path,
    skip_missing: bool = False,
    phase1_dirs: list[Path] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Aggregate phase2 scoring outputs into a single checkpoint file.

    Scans ``workspace_dir/phase2_output/`` for per-ticker subdirectories,
    reads ``scoring_output.json`` from each, and builds a mapping of
    ``{ticker: [ScoredClaim.model_dump()]}`` which is written to
    *output_path* as JSON.

    Parameters
    ----------
    workspace_dir : Path
        Working directory containing ``phase2_output/{TICKER}/scoring_output.json``
        files.
    output_path : Path
        Destination path for the checkpoint JSON.  Parent directories are
        created automatically.
    skip_missing : bool, optional
        When ``True``, ticker subdirectories that lack a
        ``scoring_output.json`` are silently skipped.  When ``False``
        (default), a missing file raises :class:`ValueError`.
    phase1_dirs : list[Path] | None, optional
        Phase 1 output ディレクトリのリスト。指定すると、Phase 1 の
        extraction_output.json から evidence を復元する。
        デフォルトは ``None``（既存動作と同一）。

    Returns
    -------
    dict[str, list[dict[str, Any]]]
        Mapping of ticker symbol to list of scored claim dicts
        (``ScoredClaim.model_dump()`` format).

    Raises
    ------
    ValueError
        If no ``scoring_output.json`` files are found and
        *skip_missing* is ``False``.
    """
    # Build Phase 1 evidence lookup if phase1_dirs provided
    from dev.ca_strategy.types import Claim as _Claim

    phase1_lookup: dict[str, dict[str, _Claim]] = {}
    if phase1_dirs:
        phase1_lookup = _build_phase1_evidence_lookup(phase1_dirs)
        logger.info(
            "Phase 1 evidence lookup built",
            ticker_count=len(phase1_lookup),
            total_claims=sum(len(v) for v in phase1_lookup.values()),
        )

    phase2_dir = workspace_dir / "phase2_output"

    logger.info(
        "Building phase2 checkpoint",
        workspace_dir=str(workspace_dir),
        output_path=str(output_path),
        skip_missing=skip_missing,
    )

    # Collect ticker subdirectories
    ticker_dirs: list[Path] = []
    if phase2_dir.exists():
        ticker_dirs = [d for d in sorted(phase2_dir.iterdir()) if d.is_dir()]

    if not ticker_dirs:
        if not skip_missing:
            msg = (
                f"No scoring_output.json found in {phase2_dir}: "
                "phase2_output directory is empty or does not exist"
            )
            logger.error(
                "No phase2 ticker directories found",
                phase2_dir=str(phase2_dir),
            )
            raise ValueError(msg)
        # skip_missing=True: return empty dict
        checkpoint: dict[str, list[dict[str, Any]]] = {}
        _write_json_file(output_path, checkpoint)
        return checkpoint

    checkpoint = {}
    found_any = False

    for ticker_dir in ticker_dirs:
        ticker = ticker_dir.name
        scoring_output_path = ticker_dir / "scoring_output.json"

        if not scoring_output_path.exists():
            if skip_missing:
                logger.debug(
                    "scoring_output.json not found, skipping",
                    ticker=ticker,
                    path=str(scoring_output_path),
                )
                continue
            msg = (
                f"No scoring_output.json found for ticker {ticker!r}: "
                f"{scoring_output_path}"
            )
            logger.error(
                "scoring_output.json not found",
                ticker=ticker,
                path=str(scoring_output_path),
            )
            raise ValueError(msg)

        data = _read_json_file(
            scoring_output_path,
            context=f"scoring_output ticker={ticker}",
        )
        if data is None:
            if skip_missing:
                continue
            msg = f"Failed to read scoring_output.json for ticker {ticker!r}: {scoring_output_path}"
            raise ValueError(msg)

        raw_scored_list: list[dict[str, Any]] = data.get("scored_claims", [])

        # Restore as ScoredClaim models and dump back to validate the schema
        scored_dicts: list[dict[str, Any]] = []
        for raw in raw_scored_list:
            if not isinstance(raw, dict):
                continue
            # Reconstruct a minimal ScoredClaim-compatible dict by passing through
            # _parse_raw_scored_claim (which validates fields) then model_dump()
            ticker_lookup = phase1_lookup.get(ticker, {})
            parsed = _parse_raw_scored_claim(raw, ticker_lookup, ticker)
            if parsed is not None:
                scored_dicts.append(parsed.model_dump())

        checkpoint[ticker] = scored_dicts
        found_any = True
        logger.debug(
            "Loaded scoring output",
            ticker=ticker,
            scored_count=len(scored_dicts),
        )

    if not found_any and not skip_missing:
        msg = (
            f"No scoring_output.json found in {phase2_dir}: "
            "all ticker directories were missing scoring_output.json"
        )
        logger.error(
            "No scoring_output.json found in any ticker directory",
            phase2_dir=str(phase2_dir),
        )
        raise ValueError(msg)

    _write_json_file(output_path, checkpoint)

    logger.info(
        "Phase2 checkpoint built",
        ticker_count=len(checkpoint),
        output_path=str(output_path),
    )

    return checkpoint


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

    orch = Orchestrator(
        config_path=config_path,
        kb_base_dir=None,
        workspace_dir=workspace_dir,
    )
    orch.run_from_checkpoint(phase=3)

    logger.info("Phase 3-5 completed", workspace_dir=str(workspace_dir))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_scoring_base_payload(
    ticker: str,
    workspace_dir: Path,
    kb_dirs: tuple[Path, Path, Path],
) -> dict[str, str]:
    """スコアリングAPIの共通ベースペイロードを構築する。

    Parameters
    ----------
    ticker : str
        ティッカーシンボル。
    workspace_dir : Path
        ワークスペースディレクトリ。
    kb_dirs : tuple[Path, Path, Path]
        (kb1_dir, kb2_dir, kb3_dir) のタプル。

    Returns
    -------
    dict[str, str]
        スコアリング用の共通ベースペイロード。
    """
    kb1_dir, kb2_dir, kb3_dir = kb_dirs
    return {
        "ticker": ticker,
        "phase1_output_dir": str(workspace_dir / "phase1_output" / ticker),
        "kb1_dir": str(kb1_dir),
        "kb2_dir": str(kb2_dir),
        "kb3_dir": str(kb3_dir),
        "workspace_dir": str(workspace_dir),
    }


def _read_json_file(path: Path, context: str) -> dict[str, Any] | None:
    """JSONファイルを安全に読み込む。失敗時はNoneを返す。

    Parameters
    ----------
    path : Path
        読み込むJSONファイルのパス。
    context : str
        ログ出力用のコンテキスト文字列。

    Returns
    -------
    dict[str, Any] | None
        パースされたJSONデータ、またはエラー時はNone。
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "Failed to parse JSON",
            path=str(path),
            context=context,
            error=str(exc),
        )
        return None


def _write_json_file(path: Path, data: Any) -> None:
    """JSONファイルを書き込む。親ディレクトリを自動作成する。

    Parameters
    ----------
    path : Path
        書き込み先のパス。
    data : Any
        シリアライズするデータ。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_ticker(ticker: str) -> None:
    """Validate that ticker is a valid ticker symbol (1-10 uppercase ASCII letters).

    Parameters
    ----------
    ticker : str
        Ticker symbol to validate.

    Raises
    ------
    ValueError
        If ticker does not match the expected format.
    """
    if not _TICKER_RE.fullmatch(ticker):
        raise ValueError(
            f"Invalid ticker symbol: {ticker!r}. "
            "Expected 1-10 uppercase ASCII letters (e.g. 'AAPL', 'DIS')."
        )


def _build_kb_dirs(kb_base_dir: Path) -> tuple[Path, Path, Path]:
    """Build KB directory paths from the base knowledge base directory.

    Parameters
    ----------
    kb_base_dir : Path
        Root directory containing knowledge base subdirectories.

    Returns
    -------
    tuple[Path, Path, Path]
        Tuple of (kb1_dir, kb2_dir, kb3_dir).
    """
    return (
        kb_base_dir / "kb1_rules_transcript",
        kb_base_dir / "kb2_patterns_transcript",
        kb_base_dir / "kb3_fewshot_transcript",
    )


def _normalize_confidence(value: float | int) -> float:
    """Normalize confidence from percentage (0-100) to unit range (0.0-1.0).

    Values greater than 1.0 are treated as percentages and divided by 100.
    The result is clamped to [0.0, 1.0].

    Parameters
    ----------
    value : float | int
        Raw confidence value.  Values > 1.0 are divided by 100.

    Returns
    -------
    float
        Confidence value clamped to [0.0, 1.0].
    """
    normalized = float(value) / 100.0 if float(value) > 1.0 else float(value)
    return max(0.0, min(1.0, normalized))


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
        claim_id = raw.get("id") or raw.get("claim_id", "unknown")
        if isinstance(claim_id, int):
            claim_id = str(claim_id)

        # rule_evaluation is optional – Schema B/D may omit it
        rule_eval_raw = raw.get("rule_evaluation")
        if not isinstance(rule_eval_raw, dict):
            raw_confidence = raw.get("confidence", 0.5)
            confidence = _normalize_confidence(raw_confidence)
            rule_evaluation = RuleEvaluation(
                applied_rules=[],
                results={},
                confidence=confidence,
                adjustments=[],
            )
        else:
            # Normalize confidence (clamping included in _normalize_confidence)
            raw_confidence = rule_eval_raw.get("confidence", 0.5)
            confidence = _normalize_confidence(raw_confidence)

            # Parse results (support dict and list-of-dict formats)
            results_raw = rule_eval_raw.get("results", {})
            if isinstance(results_raw, dict):
                results: dict[str, bool] = {
                    k: bool(v) if not isinstance(v, bool) else v
                    for k, v in results_raw.items()
                }
            else:
                results = {}

            # Normalize adjustments: accept list[str] or list[dict]
            raw_adjustments = rule_eval_raw.get("adjustments", [])
            adjustments_list: list[str] = []
            if isinstance(raw_adjustments, list):
                for adj in raw_adjustments:
                    if isinstance(adj, str):
                        adjustments_list.append(adj)
                    elif isinstance(adj, dict):
                        # Convert dict adjustment to descriptive string
                        source = adj.get("source", "")
                        reasoning = adj.get("reasoning", "")
                        adj_val = adj.get("adjustment", "")
                        adjustments_list.append(
                            f"{source}: {adj_val} ({reasoning})"
                            if reasoning
                            else f"{source}: {adj_val}"
                        )

            rule_evaluation = RuleEvaluation(
                applied_rules=rule_eval_raw.get("applied_rules", []),
                results=results,
                confidence=confidence,
                adjustments=adjustments_list,
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

        # evidence fallback (Schema A/C: evidence/evidence_from_transcript,
        # Schema B: evidence_quotes (list), Schema D: evidence_quote (str))
        evidence = raw.get("evidence") or raw.get("evidence_from_transcript", "")
        if not evidence:
            eq = raw.get("evidence_quotes") or raw.get("evidence_quote")
            if isinstance(eq, list):
                evidence = "; ".join(eq)
            elif isinstance(eq, str):
                evidence = eq
        if not evidence:
            evidence = raw.get("claim") or raw.get("claim_text", "No evidence provided")

        claim_text = raw.get("claim", "") or raw.get("claim_text", "")
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
        claim_id = raw.get("id") or raw.get("claim_id", "unknown")
        if isinstance(claim_id, int):
            claim_id = str(claim_id)

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
        if original is None:
            # Try original_claim_id (Phase 2 may use a different ID scheme)
            orig_id = raw.get("original_claim_id")
            if orig_id is not None:
                original = claim_lookup.get(str(orig_id))
        if original is None:
            # Ordinal fallback: extract trailing number from claim_id
            # e.g. "WMT-001" → "1", "TICKER_003" → "3"
            import re

            m = re.search(r"[-_]0*(\d+)$", claim_id)
            if m:
                original = claim_lookup.get(m.group(1))
        if original is None and claim_id.isdigit():
            # Reverse ordinal: P2 has bare integer "1", P1 has "TICKER_001"
            # Search P1 lookup for a claim whose trailing number matches
            for p1_id, p1_claim in claim_lookup.items():
                m2 = re.search(r"[-_]0*(\d+)$", p1_id)
                if m2 and m2.group(1) == claim_id:
                    original = p1_claim
                    break
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
        fallback_claim = raw.get("claim", "") or raw.get("claim_text", "")
        fallback_evidence = raw.get("evidence", "")
        if not fallback_evidence:
            fallback_evidence = raw.get("evidence_from_transcript", "")
        if not fallback_evidence:
            eq = raw.get("evidence_quotes") or raw.get("evidence_quote")
            if isinstance(eq, list):
                fallback_evidence = "; ".join(eq)
            elif isinstance(eq, str):
                fallback_evidence = eq
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
        override = _normalize_confidence(override)
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
    "build_phase2_checkpoint",
    "consolidate_scored_claims",
    "prepare_extraction_input",
    "prepare_scoring_batches",
    "prepare_scoring_input",
    "prepare_universe_chunks",
    "run_phase3_to_5",
    "validate_extraction_output",
    "validate_scoring_output",
]
