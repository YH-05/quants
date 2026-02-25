"""6-phase sync orchestrator for EDINET DB data with resume support.

This module provides the ``EdinetSyncer`` class that orchestrates the
full data synchronization pipeline from the EDINET DB API to a local
DuckDB database. It manages:

- **6-phase initial sync**: companies -> industries -> rankings ->
  company details -> financials+ratios -> analysis+text-blocks
- **Daily incremental sync**: updates changed data only
- **Resume support**: checkpoint-based recovery via ``_sync_state.json``
- **Graceful stop on rate limit**: saves progress and stops cleanly
- **Error recovery**: 404 skip, 5xx retry (via client), checkpoint save

The sync state is persisted as a JSON file alongside the DuckDB database
file, allowing interrupted syncs to be resumed from the last checkpoint.

Architecture
------------
::

    EdinetSyncer
      -> EdinetClient (HTTP + retry + rate limiting)
      -> EdinetStorage (DuckDB upsert)
      -> _sync_state.json (checkpoint persistence)

Examples
--------
>>> config = EdinetConfig(api_key="your_key")
>>> syncer = EdinetSyncer(config=config)
>>> syncer.run_initial()  # Full 6-phase sync
>>> syncer.get_status()   # Check progress

See Also
--------
market.edinet.client : HTTP client with retry and rate limiting.
market.edinet.storage : DuckDB storage layer.
market.edinet.types : SyncProgress and configuration types.
market.edinet.constants : Phase names, table names, ranking metrics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pandas as pd

from market.edinet.client import EdinetClient
from market.edinet.constants import RANKING_METRICS, RATE_LIMIT_FILENAME
from market.edinet.errors import (
    EdinetAPIError,
    EdinetRateLimitError,
)
from market.edinet.rate_limiter import DailyRateLimiter
from market.edinet.storage import EdinetStorage
from market.edinet.types import SyncProgress
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from market.edinet.types import EdinetConfig

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Phase names (execution order)
# ---------------------------------------------------------------------------

PHASE_COMPANIES: Final[str] = "companies"
PHASE_INDUSTRIES: Final[str] = "industries"
PHASE_RANKINGS: Final[str] = "rankings"
PHASE_COMPANY_DETAILS: Final[str] = "company_details"
PHASE_FINANCIALS_RATIOS: Final[str] = "financials_ratios"
PHASE_ANALYSIS_TEXT: Final[str] = "analysis_text"
PHASE_COMPLETE: Final[str] = "complete"

PHASE_ORDER: Final[list[str]] = [
    PHASE_COMPANIES,
    PHASE_INDUSTRIES,
    PHASE_RANKINGS,
    PHASE_COMPANY_DETAILS,
    PHASE_FINANCIALS_RATIOS,
    PHASE_ANALYSIS_TEXT,
]

# Checkpoint interval: save progress every N companies
CHECKPOINT_INTERVAL: Final[int] = 100


# ---------------------------------------------------------------------------
# Sync result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyncResult:
    """Result of a sync operation.

    Parameters
    ----------
    phase : str
        Phase that was completed or interrupted.
    success : bool
        Whether the phase completed successfully.
    companies_processed : int
        Number of companies processed in this run.
    errors : tuple[str, ...]
        Error messages encountered.
    stopped_reason : str | None
        Reason for stopping (e.g. ``"rate_limit"``, ``None`` if completed).
    """

    phase: str
    success: bool
    companies_processed: int
    errors: tuple[str, ...]
    stopped_reason: str | None = None


class EdinetSyncer:
    """Orchestrate 6-phase EDINET data sync with resume support.

    Manages the full lifecycle of data synchronization from the EDINET DB
    API to a local DuckDB database. Supports checkpoint-based resume,
    graceful rate-limit stops, and per-company error recovery.

    Parameters
    ----------
    config : EdinetConfig
        EDINET configuration (API key, DB path, etc.).
    client : EdinetClient | None
        Optional pre-configured client. If ``None``, one is created
        with a ``DailyRateLimiter``.
    storage : EdinetStorage | None
        Optional pre-configured storage. If ``None``, one is created
        from the config.

    Examples
    --------
    >>> config = EdinetConfig(api_key="key", db_path=Path("/tmp/e.duckdb"))
    >>> syncer = EdinetSyncer(config=config)
    >>> syncer.run_initial()
    """

    def __init__(
        self,
        config: EdinetConfig,
        client: EdinetClient | None = None,
        storage: EdinetStorage | None = None,
    ) -> None:
        self._config = config

        # Create rate limiter
        rate_limit_path = config.resolved_db_path.parent / RATE_LIMIT_FILENAME
        rate_limit_path.parent.mkdir(parents=True, exist_ok=True)
        self._rate_limiter = DailyRateLimiter(state_path=rate_limit_path)

        # Create or use provided client
        self._client = client or EdinetClient(
            config=config,
            rate_limiter=self._rate_limiter,
        )

        # Create or use provided storage
        self._storage = storage or EdinetStorage(config=config)

        # Load sync state
        self._state = self._load_state()

        logger.info(
            "EdinetSyncer initialized",
            current_phase=self._state.current_phase,
            completed_codes=len(self._state.completed_codes),
            today_api_calls=self._state.today_api_calls,
        )

    # =========================================================================
    # Public API
    # =========================================================================

    def run_initial(self) -> list[SyncResult]:
        """Execute the 6-phase initial sync.

        Runs each phase in order: companies -> industries -> rankings ->
        company_details -> financials_ratios -> analysis_text. Resumes
        from the last checkpoint if a previous run was interrupted.

        Returns
        -------
        list[SyncResult]
            Results for each phase that was executed.
        """
        logger.info("Starting initial sync", current_phase=self._state.current_phase)
        results: list[SyncResult] = []

        # Find starting phase index
        start_idx = 0
        if self._state.current_phase != PHASE_COMPANIES:
            try:
                start_idx = PHASE_ORDER.index(self._state.current_phase)
            except ValueError:
                logger.warning(
                    "Unknown phase in state, starting from beginning",
                    phase=self._state.current_phase,
                )
                start_idx = 0

        for phase in PHASE_ORDER[start_idx:]:
            self._update_phase(phase)
            result = self._run_phase(phase)
            results.append(result)

            if not result.success:
                logger.warning(
                    "Phase stopped",
                    phase=phase,
                    reason=result.stopped_reason,
                    errors=len(result.errors),
                )
                break

            # Phase completed, clear completed_codes for next phase
            self._state = SyncProgress(
                current_phase=phase,
                completed_codes=(),
                today_api_calls=self._state.today_api_calls,
                errors=self._state.errors,
            )

        # Mark as complete if all phases finished
        if (
            results
            and all(r.success for r in results)
            and len(results) == len(PHASE_ORDER) - start_idx
        ):
            self._update_phase(PHASE_COMPLETE)

        logger.info(
            "Initial sync finished",
            phases_completed=sum(1 for r in results if r.success),
            total_phases=len(results),
        )
        return results

    def run_daily(self) -> list[SyncResult]:
        """Execute daily incremental sync.

        Updates companies list, then syncs financials and ratios for
        all companies.

        Returns
        -------
        list[SyncResult]
            Results for each phase that was executed.
        """
        logger.info("Starting daily sync")

        # Reset state for daily run
        self._state = SyncProgress(
            current_phase=PHASE_COMPANIES,
            completed_codes=(),
            today_api_calls=self._state.today_api_calls,
            errors=(),
        )
        self._save_state()

        results: list[SyncResult] = []

        # Phase 1: Update companies list
        self._update_phase(PHASE_COMPANIES)
        result = self._run_phase(PHASE_COMPANIES)
        results.append(result)
        if not result.success:
            return results

        # Phase 5: Update financials + ratios
        self._state = SyncProgress(
            current_phase=PHASE_FINANCIALS_RATIOS,
            completed_codes=(),
            today_api_calls=self._state.today_api_calls,
            errors=self._state.errors,
        )
        self._save_state()
        result = self._run_phase(PHASE_FINANCIALS_RATIOS)
        results.append(result)

        logger.info(
            "Daily sync finished",
            phases_completed=sum(1 for r in results if r.success),
        )
        return results

    def resume(self) -> list[SyncResult]:
        """Resume sync from the last checkpoint.

        Loads state from ``_sync_state.json`` and continues from where
        the previous sync was interrupted.

        Returns
        -------
        list[SyncResult]
            Results for each phase that was executed.
        """
        logger.info(
            "Resuming sync",
            phase=self._state.current_phase,
            completed_codes=len(self._state.completed_codes),
        )
        return self.run_initial()

    def get_status(self) -> dict[str, object]:
        """Get current sync status report.

        Returns
        -------
        dict[str, object]
            Status report including current phase, progress, and stats.
        """
        db_stats = self._storage.get_stats()
        remaining = self._rate_limiter.get_remaining()

        return {
            "current_phase": self._state.current_phase,
            "completed_codes_count": len(self._state.completed_codes),
            "today_api_calls": self._state.today_api_calls,
            "remaining_api_calls": remaining,
            "errors_count": len(self._state.errors),
            "db_stats": db_stats,
        }

    def sync_company(self, code: str) -> SyncResult:
        """Sync all data for a single company.

        Fetches and stores financials, ratios, analysis, and text blocks
        for the specified EDINET code.

        Parameters
        ----------
        code : str
            EDINET code (e.g. ``"E00001"``).

        Returns
        -------
        SyncResult
            Result of the single-company sync.
        """
        logger.info("Syncing single company", code=code)
        errors: list[str] = []
        processed = 0

        try:
            self._sync_company_detail(code)
            self._sync_company_financials_ratios(code)
            self._sync_company_analysis_text(code)
            processed = 1
        except EdinetRateLimitError:
            logger.warning("Rate limit reached during single company sync", code=code)
            return SyncResult(
                phase="single_company",
                success=False,
                companies_processed=0,
                errors=tuple(errors),
                stopped_reason="rate_limit",
            )
        except EdinetAPIError as e:
            if e.status_code == 404:
                logger.warning("Company not found (404), skipping", code=code)
                errors.append(f"404: {code}")
            else:
                logger.error(
                    "API error during single company sync", code=code, error=str(e)
                )
                errors.append(f"{code}: {e.message}")

        return SyncResult(
            phase="single_company",
            success=processed > 0,
            companies_processed=processed,
            errors=tuple(errors),
        )

    # =========================================================================
    # Phase Execution
    # =========================================================================

    def _run_phase(self, phase: str) -> SyncResult:
        """Execute a single sync phase.

        Parameters
        ----------
        phase : str
            Phase name to execute.

        Returns
        -------
        SyncResult
            Result of the phase execution.
        """
        logger.info("Running phase", phase=phase)

        phase_handlers: dict[str, Callable[[], SyncResult]] = {
            PHASE_COMPANIES: self._phase_companies,
            PHASE_INDUSTRIES: self._phase_industries,
            PHASE_RANKINGS: self._phase_rankings,
            PHASE_COMPANY_DETAILS: self._phase_company_details,
            PHASE_FINANCIALS_RATIOS: self._phase_financials_ratios,
            PHASE_ANALYSIS_TEXT: self._phase_analysis_text,
        }

        handler = phase_handlers.get(phase)
        if handler is None:
            logger.error("Unknown phase", phase=phase)
            return SyncResult(
                phase=phase,
                success=False,
                companies_processed=0,
                errors=(f"Unknown phase: {phase}",),
            )

        return handler()

    def _phase_companies(self) -> SyncResult:
        """Phase 1: Fetch and store all companies (1 API call).

        Returns
        -------
        SyncResult
            Phase result.
        """
        logger.info("Phase 1: Fetching companies")
        try:
            companies = self._client.list_companies()
            self._storage.upsert_companies(companies)
            self._increment_api_calls(1)
            logger.info("Phase 1 completed", companies_count=len(companies))
            return SyncResult(
                phase=PHASE_COMPANIES,
                success=True,
                companies_processed=len(companies),
                errors=(),
            )
        except EdinetRateLimitError:
            logger.warning("Rate limit reached in Phase 1")
            self._save_state()
            return SyncResult(
                phase=PHASE_COMPANIES,
                success=False,
                companies_processed=0,
                errors=(),
                stopped_reason="rate_limit",
            )
        except EdinetAPIError as e:
            logger.error("API error in Phase 1", error=str(e))
            return SyncResult(
                phase=PHASE_COMPANIES,
                success=False,
                companies_processed=0,
                errors=(e.message,),
            )

    def _phase_industries(self) -> SyncResult:
        """Phase 2: Fetch and store industries (~35 API calls).

        Returns
        -------
        SyncResult
            Phase result.
        """
        logger.info("Phase 2: Fetching industries")
        errors: list[str] = []
        try:
            # List industries (1 call)
            industries = self._client.list_industries()
            self._storage.upsert_industries(industries)
            self._increment_api_calls(1)

            # Get details for each industry
            for industry in industries:
                try:
                    details = self._client.get_industry(industry.slug)
                    details_df = pd.DataFrame([details])
                    if "slug" not in details_df.columns:
                        details_df["slug"] = industry.slug
                    self._storage.upsert_industry_details(details_df)
                    self._increment_api_calls(1)
                except EdinetRateLimitError:
                    self._save_state()
                    return SyncResult(
                        phase=PHASE_INDUSTRIES,
                        success=False,
                        companies_processed=0,
                        errors=tuple(errors),
                        stopped_reason="rate_limit",
                    )
                except EdinetAPIError as e:
                    if e.status_code == 404:
                        logger.warning(
                            "Industry not found (404), skipping",
                            slug=industry.slug,
                        )
                        errors.append(f"404: {industry.slug}")
                    else:
                        raise

            logger.info(
                "Phase 2 completed",
                industries_count=len(industries),
            )
            return SyncResult(
                phase=PHASE_INDUSTRIES,
                success=True,
                companies_processed=0,
                errors=tuple(errors),
            )
        except EdinetRateLimitError:
            logger.warning("Rate limit reached in Phase 2")
            self._save_state()
            return SyncResult(
                phase=PHASE_INDUSTRIES,
                success=False,
                companies_processed=0,
                errors=tuple(errors),
                stopped_reason="rate_limit",
            )
        except EdinetAPIError as e:
            logger.error("API error in Phase 2", error=str(e))
            errors.append(e.message)
            return SyncResult(
                phase=PHASE_INDUSTRIES,
                success=False,
                companies_processed=0,
                errors=tuple(errors),
            )

    def _phase_rankings(self) -> SyncResult:
        """Phase 3: Fetch and store rankings for all 18 metrics (~18 API calls).

        Returns
        -------
        SyncResult
            Phase result.
        """
        logger.info("Phase 3: Fetching rankings")
        errors: list[str] = []
        try:
            for metric in RANKING_METRICS:
                try:
                    entries = self._client.get_ranking(metric)
                    self._storage.upsert_rankings(entries)
                    self._increment_api_calls(1)
                except EdinetRateLimitError:
                    self._save_state()
                    return SyncResult(
                        phase=PHASE_RANKINGS,
                        success=False,
                        companies_processed=0,
                        errors=tuple(errors),
                        stopped_reason="rate_limit",
                    )
                except EdinetAPIError as e:
                    logger.warning(
                        "Ranking fetch failed",
                        metric=metric,
                        error=str(e),
                    )
                    errors.append(f"{metric}: {e.message}")

            logger.info(
                "Phase 3 completed",
                metrics_count=len(RANKING_METRICS),
            )
            return SyncResult(
                phase=PHASE_RANKINGS,
                success=True,
                companies_processed=0,
                errors=tuple(errors),
            )
        except EdinetRateLimitError:
            logger.warning("Rate limit reached in Phase 3")
            self._save_state()
            return SyncResult(
                phase=PHASE_RANKINGS,
                success=False,
                companies_processed=0,
                errors=tuple(errors),
                stopped_reason="rate_limit",
            )

    def _phase_company_details(self) -> SyncResult:
        """Phase 4: Fetch company details (~3,848 API calls).

        Returns
        -------
        SyncResult
            Phase result.
        """
        logger.info("Phase 4: Fetching company details")
        return self._process_companies(
            phase=PHASE_COMPANY_DETAILS,
            process_fn=self._sync_company_detail,
        )

    def _phase_financials_ratios(self) -> SyncResult:
        """Phase 5: Fetch financials and ratios (~7,696 API calls).

        Returns
        -------
        SyncResult
            Phase result.
        """
        logger.info("Phase 5: Fetching financials and ratios")
        return self._process_companies(
            phase=PHASE_FINANCIALS_RATIOS,
            process_fn=self._sync_company_financials_ratios,
        )

    def _phase_analysis_text(self) -> SyncResult:
        """Phase 6: Fetch analysis and text blocks (~7,696 API calls).

        Returns
        -------
        SyncResult
            Phase result.
        """
        logger.info("Phase 6: Fetching analysis and text blocks")
        return self._process_companies(
            phase=PHASE_ANALYSIS_TEXT,
            process_fn=self._sync_company_analysis_text,
        )

    # =========================================================================
    # Company-level sync helpers
    # =========================================================================

    def _sync_company_detail(self, code: str) -> None:
        """Fetch and store company detail for a single code.

        Parameters
        ----------
        code : str
            EDINET code.
        """
        company = self._client.get_company(code)
        self._storage.upsert_companies([company])
        self._increment_api_calls(1)

    def _sync_company_financials_ratios(self, code: str) -> None:
        """Fetch and store financials + ratios for a single code.

        Parameters
        ----------
        code : str
            EDINET code.
        """
        financials = self._client.get_financials(code)
        self._storage.upsert_financials(financials)
        self._increment_api_calls(1)

        ratios = self._client.get_ratios(code)
        self._storage.upsert_ratios(ratios)
        self._increment_api_calls(1)

    def _sync_company_analysis_text(self, code: str) -> None:
        """Fetch and store analysis + text blocks for a single code.

        Parameters
        ----------
        code : str
            EDINET code.
        """
        analysis = self._client.get_analysis(code)
        self._storage.upsert_analyses([analysis])
        self._increment_api_calls(1)

        text_blocks = self._client.get_text_blocks(code)
        self._storage.upsert_text_blocks(text_blocks)
        self._increment_api_calls(1)

    # =========================================================================
    # Batch company processing with checkpoint
    # =========================================================================

    def _process_companies(
        self,
        phase: str,
        process_fn: Callable[[str], None],
    ) -> SyncResult:
        """Process all companies with checkpoint saves.

        Iterates over all company EDINET codes, skipping already-completed
        ones, and calls ``process_fn`` for each. Saves a checkpoint every
        ``CHECKPOINT_INTERVAL`` companies.

        Parameters
        ----------
        phase : str
            Current phase name.
        process_fn : callable
            Function to call for each company code.

        Returns
        -------
        SyncResult
            Phase result.
        """
        all_codes = self._storage.get_all_company_codes()
        completed = set(self._state.completed_codes)
        remaining_codes = [c for c in all_codes if c not in completed]

        logger.info(
            "Processing companies",
            phase=phase,
            total=len(all_codes),
            completed=len(completed),
            remaining=len(remaining_codes),
        )

        errors: list[str] = []
        processed = 0

        for code in remaining_codes:
            try:
                process_fn(code)
                completed.add(code)
                processed += 1

                # Checkpoint save
                if processed % CHECKPOINT_INTERVAL == 0:
                    self._state = self._build_progress(phase, completed, errors)
                    self._save_state()
                    logger.info(
                        "Checkpoint saved",
                        phase=phase,
                        processed=processed,
                        total=len(remaining_codes),
                    )

            except EdinetRateLimitError:
                logger.warning(
                    "Rate limit reached, saving checkpoint",
                    phase=phase,
                    processed=processed,
                )
                self._state = self._build_progress(phase, completed, errors)
                self._save_state()
                return SyncResult(
                    phase=phase,
                    success=False,
                    companies_processed=processed,
                    errors=tuple(errors),
                    stopped_reason="rate_limit",
                )
            except EdinetAPIError as e:
                if e.status_code == 404:
                    logger.warning("Company not found (404), skipping", code=code)
                    errors.append(f"404: {code}")
                    completed.add(code)
                    processed += 1
                else:
                    logger.error(
                        "API error for company",
                        code=code,
                        error=str(e),
                    )
                    errors.append(f"{code}: {e.message}")

        # Final save
        self._state = self._build_progress(phase, completed, errors)
        self._save_state()

        logger.info(
            "Phase completed",
            phase=phase,
            processed=processed,
            errors=len(errors),
        )

        return SyncResult(
            phase=phase,
            success=True,
            companies_processed=processed,
            errors=tuple(errors),
        )

    # =========================================================================
    # State Management
    # =========================================================================

    def _load_state(self) -> SyncProgress:
        """Load sync state from ``_sync_state.json``.

        Returns
        -------
        SyncProgress
            Loaded state or default state if file doesn't exist.
        """
        state_path = self._config.sync_state_path
        if not state_path.exists():
            logger.debug("No sync state file found, using defaults")
            return SyncProgress(current_phase=PHASE_COMPANIES)

        try:
            raw = state_path.read_text(encoding="utf-8")
            if not raw.strip():
                logger.debug("Sync state file is empty, using defaults")
                return SyncProgress(current_phase=PHASE_COMPANIES)

            data = json.loads(raw)
            progress = SyncProgress(
                current_phase=data.get("current_phase", PHASE_COMPANIES),
                completed_codes=tuple(data.get("completed_codes", [])),
                today_api_calls=data.get("today_api_calls", 0),
                errors=tuple(data.get("errors", [])),
            )
            logger.info(
                "Sync state loaded",
                phase=progress.current_phase,
                completed_codes=len(progress.completed_codes),
            )
            return progress
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning(
                "Failed to parse sync state, using defaults",
                error=str(exc),
            )
            return SyncProgress(current_phase=PHASE_COMPANIES)

    def _save_state(self) -> None:
        """Persist current sync state to ``_sync_state.json``."""
        state_path = self._config.sync_state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "current_phase": self._state.current_phase,
            "completed_codes": list(self._state.completed_codes),
            "today_api_calls": self._state.today_api_calls,
            "errors": list(self._state.errors),
        }
        state_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug(
            "Sync state saved",
            phase=self._state.current_phase,
            completed_codes=len(self._state.completed_codes),
        )

    def _update_phase(self, phase: str) -> None:
        """Update the current phase in state and save.

        Parameters
        ----------
        phase : str
            New phase name.
        """
        self._state = SyncProgress(
            current_phase=phase,
            completed_codes=self._state.completed_codes,
            today_api_calls=self._state.today_api_calls,
            errors=self._state.errors,
        )
        self._save_state()

    def _build_progress(
        self,
        phase: str,
        completed: set[str],
        extra_errors: list[str] | None = None,
    ) -> SyncProgress:
        """Build a new SyncProgress from current state.

        Parameters
        ----------
        phase : str
            Phase name.
        completed : set[str]
            Set of completed EDINET codes.
        extra_errors : list[str] | None
            Additional error messages to append.

        Returns
        -------
        SyncProgress
            New immutable progress instance.
        """
        errors = list(self._state.errors)
        if extra_errors:
            errors.extend(extra_errors)
        return SyncProgress(
            current_phase=phase,
            completed_codes=tuple(sorted(completed)),
            today_api_calls=self._state.today_api_calls,
            errors=tuple(errors),
        )

    def _increment_api_calls(self, count: int) -> None:
        """Increment the API call counter in state.

        Parameters
        ----------
        count : int
            Number of calls to add.
        """
        self._state = SyncProgress(
            current_phase=self._state.current_phase,
            completed_codes=self._state.completed_codes,
            today_api_calls=self._state.today_api_calls + count,
            errors=self._state.errors,
        )


__all__ = [
    "CHECKPOINT_INTERVAL",
    "PHASE_ANALYSIS_TEXT",
    "PHASE_COMPANIES",
    "PHASE_COMPANY_DETAILS",
    "PHASE_COMPLETE",
    "PHASE_FINANCIALS_RATIOS",
    "PHASE_INDUSTRIES",
    "PHASE_ORDER",
    "PHASE_RANKINGS",
    "EdinetSyncer",
    "SyncResult",
]
