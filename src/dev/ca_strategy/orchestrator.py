"""Phase 0-6 pipeline orchestrator for the CA Strategy.

Integrates all pipeline phases in order:

1. **Extraction** (Phase 1): Transcript -> Claims via ClaimExtractor
2. **Scoring** (Phase 2): Claims -> ScoredClaims via ClaimScorer
3. **Neutralization** (Phase 3): Scores -> Ranked DataFrame via
   ScoreAggregator + SectorNeutralizer
4. **Portfolio Construction** (Phase 4): Ranked -> Portfolio via
   PortfolioBuilder
5. **Output Generation** (Phase 5): Portfolio -> Files via OutputGenerator
6. **Evaluation** (Phase 6): Portfolio + Returns -> EvaluationResult via
   StrategyEvaluator + PortfolioReturnCalculator

Supports full pipeline execution and checkpoint-based resumption.
Logs each phase's execution status to ``execution_log.json``.

Examples
--------
>>> orch = Orchestrator(
...     config_path=Path("research/ca_strategy_poc/config"),
...     kb_base_dir=Path("analyst/transcript_eval"),
...     workspace_dir=Path("research/ca_strategy_poc/workspace"),
... )
>>> orch.run_full_pipeline()
>>> # Or resume from a specific phase:
>>> orch.run_from_checkpoint(phase=3)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from dev.ca_strategy.price_provider import PriceDataProvider

import pandas as pd
from pydantic import BaseModel

from dev.ca_strategy._config import ConfigRepository
from dev.ca_strategy.aggregator import ScoreAggregator
from dev.ca_strategy.analyst_scores import load_analyst_scores
from dev.ca_strategy.cost import CostTracker
from dev.ca_strategy.evaluator import StrategyEvaluator
from dev.ca_strategy.extractor import ClaimExtractor
from dev.ca_strategy.neutralizer import SectorNeutralizer
from dev.ca_strategy.output import OutputGenerator
from dev.ca_strategy.pit import CUTOFF_DATE, EVALUATION_END_DATE, PORTFOLIO_DATE
from dev.ca_strategy.portfolio_builder import PortfolioBuilder, RankedStock
from dev.ca_strategy.return_calculator import PortfolioReturnCalculator
from dev.ca_strategy.scorer import ClaimScorer
from dev.ca_strategy.transcript import TranscriptLoader
from dev.ca_strategy.types import (
    AnalystScore,
    BenchmarkWeight,
    Claim,
    EvaluationResult,
    PortfolioResult,
    ScoredClaim,
    StockScore,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_PHASE: int = 1
"""Minimum valid phase number."""

_MAX_PHASE: int = 5
"""Maximum valid phase number."""

_DEFAULT_THRESHOLDS: list[float] = [0.3, 0.4, 0.5, 0.6, 0.7]
"""Default score thresholds for the equal-weight pipeline."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class Orchestrator:
    """Orchestrate the full CA Strategy pipeline (Phase 1-6).

    Loads configuration, manages pipeline state, and coordinates
    execution of each phase in order.  Supports checkpoint-based
    resumption from a specific phase.

    Parameters
    ----------
    config_path : Path | str
        Directory containing ``universe.json``,
        ``benchmark_weights.json``, and optionally
        ``corporate_actions.json``.
    kb_base_dir : Path | str | None
        Root directory for knowledge base files (KB1-T, KB2-T,
        KB3-T, system prompt).  Pass ``None`` when running
        Phase 3-5 only (KB files are not required).
    workspace_dir : Path | str
        Working directory for intermediate outputs, checkpoints,
        and execution logs.
    price_provider : PriceDataProvider | None, optional
        Provider for fetching daily close prices.  When set,
        Phase 6 uses ``PortfolioReturnCalculator`` to compute
        real portfolio and benchmark returns.  When ``None``
        (default), Phase 6 uses empty Series (NaN metrics),
        preserving backward compatibility.
    benchmark_ticker : str | None, optional
        Ticker symbol for the benchmark index (e.g. ``"MXKOKUS"``).
        When set, Phase 6 fetches benchmark returns from
        ``price_provider`` instead of using equal-weight universe
        returns.  When ``None`` (default), uses the equal-weight
        universe method.
    analyst_scores_path : Path | str | None, optional
        Path to the portfolio list JSON file containing analyst
        KY/AK scores.  When set, Phase 6 loads scores and
        passes them to ``StrategyEvaluator``.  When ``None``
        (default), an empty dict is used.

    Raises
    ------
    FileNotFoundError
        If ``config_path`` does not exist.

    Examples
    --------
    >>> orch = Orchestrator(
    ...     config_path=Path("config"),
    ...     kb_base_dir=Path("kb"),
    ...     workspace_dir=Path("workspace"),
    ... )
    >>> orch.run_full_pipeline()
    """

    def __init__(
        self,
        config_path: Path | str,
        kb_base_dir: Path | str | None,
        workspace_dir: Path | str,
        price_provider: PriceDataProvider | None = None,
        benchmark_ticker: str | None = None,
        analyst_scores_path: Path | str | None = None,
    ) -> None:
        self._config_path = Path(config_path)
        self._kb_base_dir = Path(kb_base_dir) if kb_base_dir is not None else None
        self._workspace_dir = Path(workspace_dir)
        self._price_provider = price_provider
        self._benchmark_ticker = benchmark_ticker
        self._analyst_scores_path = (
            Path(analyst_scores_path) if analyst_scores_path is not None else None
        )

        # ConfigRepository validates config_path existence
        self._config = ConfigRepository(self._config_path)

        # Load corporate_actions.json if present (fallback: empty list)
        self._corporate_actions: list[dict[str, Any]] = self._load_corporate_actions()

        # Ensure workspace directory exists
        self._workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize execution log
        self._execution_log: list[dict[str, Any]] = []

        # Initialize cost tracker
        self._cost_tracker = CostTracker()

        logger.info(
            "Orchestrator initialized",
            config_path=str(self._config_path),
            kb_base_dir=str(self._kb_base_dir)
            if self._kb_base_dir is not None
            else None,
            workspace_dir=str(self._workspace_dir),
            price_provider=type(self._price_provider).__name__
            if self._price_provider is not None
            else None,
            corporate_actions_count=len(self._corporate_actions),
            benchmark_ticker=self._benchmark_ticker,
            analyst_scores_path=str(self._analyst_scores_path)
            if self._analyst_scores_path is not None
            else None,
        )

    # -----------------------------------------------------------------------
    # Public methods
    # -----------------------------------------------------------------------
    def run_full_pipeline(self) -> None:
        """Execute the full pipeline (Phase 1 through 5).

        Loads configuration, then runs each phase sequentially,
        passing outputs to the next phase.  Each phase's status
        is logged to ``execution_log.json``.

        Raises
        ------
        RuntimeError
            If any phase fails.  The error is logged before re-raising.
        """
        logger.info("Starting full pipeline execution")

        _claims, scored_claims, scores, ranked = self._run_phases_1_to_3()

        # Phase 4: Portfolio Construction
        portfolio = self._execute_phase(
            phase=4,
            func=self._run_phase4_portfolio_construction,
            args=(ranked, self._config.benchmark),
        )

        # Phase 5: Output Generation
        self._execute_phase(
            phase=5,
            func=self._run_phase5_output_generation,
            args=(portfolio, scored_claims, scores),
        )

        self._save_cost_tracking()

        logger.info(
            "Full pipeline completed",
            total_cost=round(self._cost_tracker.get_total_cost(), 2),
        )

    def run_from_checkpoint(self, phase: int) -> None:
        """Resume pipeline from a specific phase.

        Loads checkpoint data for phases prior to the specified
        phase, then executes from that phase onward.

        Parameters
        ----------
        phase : int
            Phase number to resume from (1-5).

        Raises
        ------
        ValueError
            If phase is not between 1 and 5.
        FileNotFoundError
            If required checkpoint files are missing.
        """
        if phase < _MIN_PHASE or phase > _MAX_PHASE:
            msg = f"phase must be between {_MIN_PHASE} and {_MAX_PHASE}, got {phase}"
            raise ValueError(msg)

        logger.info("Resuming from checkpoint", start_phase=phase)

        # Load checkpoint data for completed phases
        claims: dict[str, list[Claim]] = (
            self._load_checkpoint("phase1_claims.json", Claim) if phase > 1 else {}
        )
        scored_claims: dict[str, list[ScoredClaim]] = (
            self._load_checkpoint("phase2_scored.json", ScoredClaim)
            if phase > 2
            else {}
        )
        scores: dict[str, StockScore] = {}
        ranked: pd.DataFrame = pd.DataFrame()
        portfolio: PortfolioResult | None = None

        # Execute phases sequentially from the start phase
        if phase <= 1:
            claims = self._execute_phase(1, self._run_phase1_extraction)
        if phase <= 2:
            scored_claims = self._execute_phase(2, self._run_phase2_scoring, (claims,))
        if phase <= 3:
            scores = self._aggregate_scores(scored_claims)  # AIDEV-NOTE: CODE-005
            ranked = self._execute_phase(
                3, self._run_phase3_neutralization, (scored_claims, scores)
            )
        if phase <= 4:
            portfolio = self._execute_phase(
                4,
                self._run_phase4_portfolio_construction,
                (ranked, self._config.benchmark),
            )
        if phase <= 5:
            self._execute_phase(
                5,
                self._run_phase5_output_generation,
                (portfolio, scored_claims, scores),
            )

        logger.info("Checkpoint resumption completed", start_phase=phase)

    def run_equal_weight_pipeline(
        self,
        thresholds: list[float] | None = None,
    ) -> list[tuple[PortfolioResult, EvaluationResult]]:
        """Execute Phase 1-3 then loop equal-weight + evaluation per threshold.

        Runs Phase 1 (extraction), Phase 2 (scoring), and Phase 3
        (neutralization) once.  For each threshold in ``thresholds``,
        constructs an equal-weight portfolio (Phase 4b), evaluates it
        (Phase 6), and generates output files (Phase 5 extended) under
        ``{workspace_dir}/output/threshold_{threshold:.2f}/``.

        Parameters
        ----------
        thresholds : list[float] | None, optional
            Score thresholds for equal-weight portfolio construction.
            If None, uses ``[0.3, 0.4, 0.5, 0.6, 0.7]``.

        Returns
        -------
        list[tuple[PortfolioResult, EvaluationResult]]
            List of (portfolio, evaluation) pairs, one per threshold.
            Thresholds that produce an empty portfolio are included
            with an evaluation over zero holdings.

        Raises
        ------
        RuntimeError
            If Phase 1, 2, or 3 fails.
        """
        if thresholds is None:
            thresholds = _DEFAULT_THRESHOLDS

        logger.info(
            "Starting equal-weight pipeline",
            thresholds=thresholds,
        )

        _, scored_claims, scores, ranked = self._run_phases_1_to_3()

        # Phase 4b → Phase 6 → Phase 5 extended (per threshold)
        results: list[tuple[PortfolioResult, EvaluationResult]] = []
        ranked_list = ranked.to_dict("records")
        for threshold in thresholds:
            portfolio, evaluation = self._run_equal_weight_threshold(
                ranked_list=ranked_list,
                scored_claims=scored_claims,
                scores=scores,
                threshold=threshold,
            )
            results.append((portfolio, evaluation))

        self._save_cost_tracking()

        logger.info(
            "Equal-weight pipeline completed",
            threshold_count=len(thresholds),
            total_cost=round(self._cost_tracker.get_total_cost(), 2),
        )

        return results

    # -----------------------------------------------------------------------
    # Private pipeline helpers
    # -----------------------------------------------------------------------
    def _run_phases_1_to_3(
        self,
    ) -> tuple[
        dict[str, list[Claim]],
        dict[str, list[ScoredClaim]],
        dict[str, StockScore],
        pd.DataFrame,
    ]:
        """Run Phase 1 (Extraction), 2 (Scoring), and 3 (Neutralization).

        Shared by :meth:`run_full_pipeline` and
        :meth:`run_equal_weight_pipeline` to avoid code duplication.

        Returns
        -------
        tuple
            ``(claims, scored_claims, scores, ranked)`` ready for Phase 4.

        Raises
        ------
        RuntimeError
            If any of Phase 1, 2, or 3 fails.
        """
        # Phase 1: Extraction
        claims = self._execute_phase(
            phase=1,
            func=self._run_phase1_extraction,
        )

        # Phase 2: Scoring
        scored_claims = self._execute_phase(
            phase=2,
            func=self._run_phase2_scoring,
            args=(claims,),
        )

        # Phase 3: Aggregation + Neutralization
        # AIDEV-NOTE: CODE-005 - _aggregate_scores() を _execute_phase() 経由で
        # 呼ぶと戻り値の scores が Phase 5 でも必要なため型安全性が低下する。
        # 将来は _run_phase3_neutralization() の引数から scores を削除し内部計算化
        # することで完全統一が可能。
        scores = self._aggregate_scores(scored_claims)
        ranked = self._execute_phase(
            phase=3,
            func=self._run_phase3_neutralization,
            args=(scored_claims, scores),
        )

        return claims, scored_claims, scores, ranked

    def _save_cost_tracking(self) -> None:
        """Persist cost tracker data to ``cost_tracking.json``.

        Shared by :meth:`run_full_pipeline` and
        :meth:`run_equal_weight_pipeline` to avoid code duplication.
        """
        cost_path = self._workspace_dir / "cost_tracking.json"
        self._cost_tracker.save(cost_path)

    def _run_equal_weight_threshold(
        self,
        ranked_list: list[dict[str, Any]],
        scored_claims: dict[str, list[ScoredClaim]],
        scores: dict[str, StockScore],
        threshold: float,
    ) -> tuple[PortfolioResult, EvaluationResult]:
        """Run Phase 4b, 6, 5-ext for a single threshold.

        Parameters
        ----------
        ranked_list : list[dict[str, Any]]
            Ranked stocks as list of dicts from Phase 3 DataFrame.
        scored_claims : dict[str, list[ScoredClaim]]
            Scored claims from Phase 2.
        scores : dict[str, StockScore]
            Aggregated stock scores from Phase 3.
        threshold : float
            Score threshold for equal-weight portfolio construction.

        Returns
        -------
        tuple[PortfolioResult, EvaluationResult]
            Portfolio and evaluation results for this threshold.
        """
        # Phase 4b: Equal-weight portfolio construction
        portfolio = self._run_phase4b_equal_weight(ranked_list, threshold)

        # Phase 6: Evaluation
        evaluation = self._run_phase6_evaluation(portfolio, scores, threshold)

        # Phase 5 extended: Output generation with evaluation
        self._run_phase5_extended(
            portfolio, scored_claims, scores, evaluation, threshold
        )

        return portfolio, evaluation

    def _run_phase4b_equal_weight(
        self,
        ranked_list: list[dict[str, Any]],
        threshold: float,
    ) -> PortfolioResult:
        """Execute Phase 4b: equal-weight portfolio construction.

        Parameters
        ----------
        ranked_list : list[dict[str, Any]]
            Ranked stocks as list of dicts.
        threshold : float
            Score threshold.

        Returns
        -------
        PortfolioResult
            Equal-weight portfolio result.
        """
        phase_label = f"phase4b_threshold_{threshold:.2f}"
        logger.info("Phase 4b started", threshold=threshold)

        builder = PortfolioBuilder()
        portfolio = builder.build_equal_weight(
            ranked=ranked_list,  # type: ignore[arg-type]
            threshold=threshold,
            as_of_date=PORTFOLIO_DATE,
        )
        self._save_execution_log(phase_label, "completed", None)

        logger.info(
            "Phase 4b completed",
            threshold=threshold,
            holdings_count=len(portfolio.holdings),
        )

        return portfolio

    def _calculate_phase6_returns(
        self,
        portfolio: PortfolioResult,
    ) -> tuple[pd.Series, pd.Series]:
        """Calculate portfolio and benchmark returns for Phase 6 evaluation.

        When ``price_provider`` is set, uses ``PortfolioReturnCalculator``
        to compute real portfolio and benchmark returns using daily close
        prices.  When ``None`` (default), returns empty Series so that
        ``StrategyEvaluator`` produces NaN performance metrics.

        When ``benchmark_ticker`` is set, fetches the benchmark index
        price data directly from ``price_provider`` and converts to
        daily returns.  Otherwise, uses the equal-weight universe method
        via ``PortfolioReturnCalculator.calculate_benchmark_returns()``.

        Parameters
        ----------
        portfolio : PortfolioResult
            Portfolio from Phase 4 or 4b.

        Returns
        -------
        tuple[pd.Series, pd.Series]
            ``(portfolio_returns, benchmark_returns)``
        """
        if self._price_provider is None:
            return pd.Series([], dtype=float), pd.Series([], dtype=float)

        calculator = PortfolioReturnCalculator(
            price_provider=self._price_provider,
            corporate_actions=self._corporate_actions,
        )
        portfolio_weights = {h.ticker: h.weight for h in portfolio.holdings}
        portfolio_returns = calculator.calculate_returns(
            weights=portfolio_weights,
            start=PORTFOLIO_DATE,
            end=EVALUATION_END_DATE,
        )

        # Benchmark returns: index ticker or equal-weight universe
        if self._benchmark_ticker is not None:
            benchmark_returns = self._fetch_benchmark_index_returns()
        else:
            universe_tickers = [t.ticker for t in self._config.universe.tickers]
            benchmark_returns = calculator.calculate_benchmark_returns(
                tickers=universe_tickers,
                start=PORTFOLIO_DATE,
                end=EVALUATION_END_DATE,
            )
        return portfolio_returns, benchmark_returns

    def _fetch_benchmark_index_returns(self) -> pd.Series:
        """Fetch benchmark index returns from price_provider.

        Uses ``benchmark_ticker`` to fetch daily close prices from
        ``price_provider``, then converts to daily returns via
        ``pct_change().iloc[1:]``.

        Returns
        -------
        pd.Series
            Daily benchmark index returns.
            Empty Series if no data is available.
        """
        assert self._price_provider is not None
        assert self._benchmark_ticker is not None

        price_data = self._price_provider.fetch(
            tickers=[self._benchmark_ticker],
            start=PORTFOLIO_DATE,
            end=EVALUATION_END_DATE,
        )

        if self._benchmark_ticker not in price_data:
            logger.warning(
                "Benchmark ticker not found in price data",
                benchmark_ticker=self._benchmark_ticker,
            )
            return pd.Series([], dtype=float)

        benchmark_prices = price_data[self._benchmark_ticker]
        benchmark_returns: pd.Series = benchmark_prices.pct_change().iloc[1:]

        logger.info(
            "Benchmark index returns calculated",
            benchmark_ticker=self._benchmark_ticker,
            return_count=len(benchmark_returns),
        )

        return benchmark_returns

    def _run_phase6_evaluation(
        self,
        portfolio: PortfolioResult,
        scores: dict[str, StockScore],
        threshold: float,
    ) -> EvaluationResult:
        """Execute Phase 6: strategy evaluation.

        Parameters
        ----------
        portfolio : PortfolioResult
            Portfolio from Phase 4b.
        scores : dict[str, StockScore]
            Aggregated stock scores.
        threshold : float
            Score threshold.

        Returns
        -------
        EvaluationResult
            Evaluation metrics.
        """
        phase6_label = f"phase6_threshold_{threshold:.2f}"
        logger.info("Phase 6 started", threshold=threshold)

        portfolio_returns, benchmark_returns = self._calculate_phase6_returns(portfolio)

        # Load analyst scores if path is configured
        analyst_scores: dict[str, AnalystScore] = self._load_analyst_scores()

        evaluator = StrategyEvaluator()
        evaluation = evaluator.evaluate(
            portfolio=portfolio,
            scores=scores,
            portfolio_returns=portfolio_returns,
            benchmark_returns=benchmark_returns,
            analyst_scores=analyst_scores,
            threshold=threshold,
        )
        self._save_execution_log(phase6_label, "completed", None)

        logger.info(
            "Phase 6 completed",
            threshold=threshold,
            sharpe=evaluation.performance.sharpe_ratio,
        )

        return evaluation

    def _load_analyst_scores(self) -> dict[str, AnalystScore]:
        """Load analyst scores from configured path.

        Returns
        -------
        dict[str, AnalystScore]
            Analyst scores keyed by ticker. Empty dict if no path configured.
        """
        if self._analyst_scores_path is None:
            return {}

        universe_path = self._config_path / "universe.json"
        try:
            scores = load_analyst_scores(
                portfolio_list_path=self._analyst_scores_path,
                universe_path=universe_path,
            )
            logger.info(
                "Analyst scores loaded for Phase 6",
                scores_count=len(scores),
                path=str(self._analyst_scores_path),
            )
            return scores
        except (FileNotFoundError, Exception) as e:
            logger.warning(
                "Failed to load analyst scores, using empty dict",
                error=str(e),
                path=str(self._analyst_scores_path),
            )
            return {}

    def _run_phase5_extended(
        self,
        portfolio: PortfolioResult,
        scored_claims: dict[str, list[ScoredClaim]],
        scores: dict[str, StockScore],
        evaluation: EvaluationResult,
        threshold: float,
    ) -> None:
        """Execute Phase 5 extended: output generation with evaluation.

        Parameters
        ----------
        portfolio : PortfolioResult
            Portfolio from Phase 4b.
        scored_claims : dict[str, list[ScoredClaim]]
            Scored claims from Phase 2.
        scores : dict[str, StockScore]
            Aggregated stock scores.
        evaluation : EvaluationResult
            Evaluation result from Phase 6.
        threshold : float
            Score threshold.
        """
        output_dir = self._workspace_dir / "output" / f"threshold_{threshold:.2f}"
        generator = OutputGenerator()
        generator.generate_all(
            portfolio=portfolio,
            claims=scored_claims,
            scores=scores,
            output_dir=output_dir,
            evaluation=evaluation,
        )

        phase5_label = f"phase5_threshold_{threshold:.2f}"
        self._save_execution_log(phase5_label, "completed", None)

        logger.info(
            "Phase 5 (extended) completed",
            threshold=threshold,
            output_dir=str(output_dir),
        )

    # -----------------------------------------------------------------------
    # Execution log
    # -----------------------------------------------------------------------
    def _save_execution_log(
        self,
        phase: str,
        status: str,
        error: str | None,
    ) -> None:
        """Record a phase execution result to execution_log.json.

        Appends the entry to the in-memory log and persists the
        full log to disk.

        Parameters
        ----------
        phase : str
            Phase identifier (e.g. "phase1", "phase2").
        status : str
            Execution status ("completed" or "failed").
        error : str | None
            Error message if the phase failed, None otherwise.
        """
        entry: dict[str, Any] = {
            "phase": phase,
            "status": status,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self._execution_log.append(entry)

        log_data = {"phases": self._execution_log}
        log_path = self._workspace_dir / "execution_log.json"
        log_path.write_text(
            json.dumps(log_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.debug(
            "Execution log updated",
            phase=phase,
            status=status,
        )

    # -----------------------------------------------------------------------
    # Phase execution wrapper
    # -----------------------------------------------------------------------
    def _execute_phase(
        self,
        phase: int,
        func: Callable[..., Any],
        args: tuple[object, ...] = (),
    ) -> Any:
        """Execute a single phase with logging and error handling.

        Parameters
        ----------
        phase : int
            Phase number (1-5).
        func : callable
            The phase method to call.
        args : tuple
            Arguments to pass to the phase method.

        Returns
        -------
        Any
            The return value of the phase method.

        Raises
        ------
        RuntimeError
            Re-raises any exception after logging it.
        """
        phase_name = f"phase{phase}"
        logger.info("Phase started", phase=phase_name)

        try:
            result = func(*args)
            self._save_execution_log(phase_name, "completed", None)
            logger.info("Phase completed", phase=phase_name)
            return result
        except Exception as exc:
            self._save_execution_log(phase_name, "failed", str(exc))
            logger.error(
                "Phase failed",
                phase=phase_name,
                error=str(exc),
                exc_info=True,
            )
            raise

    # -----------------------------------------------------------------------
    # Phase 1: Extraction
    # -----------------------------------------------------------------------
    def _run_phase1_extraction(self) -> dict[str, list[Claim]]:
        """Execute Phase 1: transcript loading and claim extraction.

        Returns
        -------
        dict[str, list[Claim]]
            Mapping of ticker to list of extracted claims.
        """
        universe = self._config.universe
        tickers = [t.ticker for t in universe.tickers]

        # Load transcripts
        transcript_dir = self._workspace_dir / "transcripts"
        loader = TranscriptLoader(
            base_dir=transcript_dir,
            cutoff_date=CUTOFF_DATE,
        )
        transcripts = loader.load_batch(tickers)

        # Extract claims
        if self._kb_base_dir is None:
            msg = "kb_base_dir is required for Phase 1 (claim extraction)"
            raise ValueError(msg)
        extractor = ClaimExtractor(
            kb1_dir=self._kb_base_dir / "kb1_rules_transcript",
            kb3_dir=self._kb_base_dir / "kb3_fewshot_transcript",
            system_prompt_path=self._kb_base_dir / "system_prompt_transcript.md",
            cost_tracker=self._cost_tracker,
        )

        output_dir = self._workspace_dir / "phase1_output"
        claims = extractor.extract_batch(
            transcripts=transcripts,
            output_dir=output_dir,
        )

        # Save checkpoint
        self._save_checkpoint(claims, "phase1_claims.json")

        logger.info(
            "Phase 1 completed",
            ticker_count=len(claims),
            total_claims=sum(len(v) for v in claims.values()),
        )

        return claims

    # -----------------------------------------------------------------------
    # Phase 2: Scoring
    # -----------------------------------------------------------------------
    def _run_phase2_scoring(
        self,
        claims: dict[str, list[Claim]],
    ) -> dict[str, list[ScoredClaim]]:
        """Execute Phase 2: claim scoring.

        Parameters
        ----------
        claims : dict[str, list[Claim]]
            Claims from Phase 1.

        Returns
        -------
        dict[str, list[ScoredClaim]]
            Mapping of ticker to list of scored claims.
        """
        if self._kb_base_dir is None:
            msg = "kb_base_dir is required for Phase 2 (claim scoring)"
            raise ValueError(msg)
        scorer = ClaimScorer(
            kb1_dir=self._kb_base_dir / "kb1_rules_transcript",
            kb2_dir=self._kb_base_dir / "kb2_patterns_transcript",
            kb3_dir=self._kb_base_dir / "kb3_fewshot_transcript",
            cost_tracker=self._cost_tracker,
        )

        output_dir = self._workspace_dir / "phase2_output"
        scored = scorer.score_batch(claims=claims, output_dir=output_dir)

        # Save checkpoint
        self._save_checkpoint(scored, "phase2_scored.json")

        logger.info(
            "Phase 2 completed",
            ticker_count=len(scored),
            total_scored=sum(len(v) for v in scored.values()),
        )

        return scored

    # -----------------------------------------------------------------------
    # Phase 3: Aggregation + Neutralization
    # -----------------------------------------------------------------------
    def _run_phase3_neutralization(
        self,
        scored_claims: dict[str, list[ScoredClaim]],
        scores: dict[str, StockScore],
    ) -> pd.DataFrame:
        """Execute Phase 3: score aggregation and sector neutralization.

        Parameters
        ----------
        scored_claims : dict[str, list[ScoredClaim]]
            Scored claims from Phase 2.
        scores : dict[str, StockScore]
            Aggregated stock scores.

        Returns
        -------
        pd.DataFrame
            Ranked DataFrame with sector-neutral Z-scores.
        """
        universe = self._config.universe

        # Build scores DataFrame
        scores_data = [
            {
                "ticker": ticker,
                "aggregate_score": score.aggregate_score,
                "claim_count": score.claim_count,
                "structural_weight": score.structural_weight,
                "as_of_date": CUTOFF_DATE,
            }
            for ticker, score in scores.items()
        ]
        scores_df = pd.DataFrame(scores_data)

        # Apply sector neutralization
        neutralizer = SectorNeutralizer(min_samples=2)
        ranked = neutralizer.neutralize(scores_df, universe)

        logger.info(
            "Phase 3 completed",
            ranked_count=len(ranked),
        )

        return ranked

    # -----------------------------------------------------------------------
    # Phase 4: Portfolio Construction
    # -----------------------------------------------------------------------
    def _run_phase4_portfolio_construction(
        self,
        ranked: pd.DataFrame,
        benchmark: list[BenchmarkWeight],
    ) -> PortfolioResult:
        """Execute Phase 4: portfolio construction.

        Parameters
        ----------
        ranked : pd.DataFrame
            Ranked DataFrame from Phase 3.
        benchmark : list[BenchmarkWeight]
            Benchmark sector weights.

        Returns
        -------
        PortfolioResult
            Portfolio result with holdings, sector_allocations, as_of_date.
        """
        builder = PortfolioBuilder(target_size=30)

        ranked_list = cast("list[RankedStock]", ranked.to_dict("records"))
        portfolio = builder.build(
            ranked=ranked_list,
            benchmark=benchmark,
            as_of_date=PORTFOLIO_DATE,
        )

        logger.info(
            "Phase 4 completed",
            holdings_count=len(portfolio.holdings),
        )

        return portfolio

    # -----------------------------------------------------------------------
    # Phase 5: Output Generation
    # -----------------------------------------------------------------------
    def _run_phase5_output_generation(
        self,
        portfolio: PortfolioResult,
        scored_claims: dict[str, list[ScoredClaim]],
        scores: dict[str, StockScore],
    ) -> None:
        """Execute Phase 5: output file generation.

        Parameters
        ----------
        portfolio : PortfolioResult
            Portfolio result from Phase 4.
        scored_claims : dict[str, list[ScoredClaim]]
            Scored claims from Phase 2.
        scores : dict[str, StockScore]
            Aggregated stock scores.
        """
        output_dir = self._workspace_dir / "output"
        generator = OutputGenerator()
        generator.generate_all(
            portfolio=portfolio,
            claims=scored_claims,
            scores=scores,
            output_dir=output_dir,
        )

        logger.info(
            "Phase 5 completed",
            output_dir=str(output_dir),
        )

    # -----------------------------------------------------------------------
    # Score aggregation helper
    # -----------------------------------------------------------------------
    def _aggregate_scores(
        self,
        scored_claims: dict[str, list[ScoredClaim]],
    ) -> dict[str, StockScore]:
        """Aggregate scored claims into per-stock scores.

        Parameters
        ----------
        scored_claims : dict[str, list[ScoredClaim]]
            Scored claims from Phase 2.

        Returns
        -------
        dict[str, StockScore]
            Aggregated stock scores.
        """
        aggregator = ScoreAggregator()
        return aggregator.aggregate(scored_claims)

    # -----------------------------------------------------------------------
    # Corporate actions loading
    # -----------------------------------------------------------------------
    def _load_corporate_actions(self) -> list[dict[str, Any]]:
        """Load corporate actions from ``corporate_actions.json`` in config_path.

        Returns an empty list if the file does not exist or contains
        invalid data, allowing graceful fallback for configurations
        without corporate action data.

        Returns
        -------
        list[dict[str, Any]]
            List of validated corporate action records.
        """
        ca_path = self._config_path / "corporate_actions.json"
        if not ca_path.exists():
            logger.debug(
                "corporate_actions.json not found, using empty list",
                config_path=str(self._config_path),
            )
            return []

        try:
            data = json.loads(ca_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to parse corporate_actions.json, using empty list",
                error=str(e),
                path=str(ca_path),
            )
            return []

        if not isinstance(data, dict) or "corporate_actions" not in data:
            logger.warning(
                "Invalid corporate_actions.json structure, "
                "expected {'corporate_actions': [...]}, using empty list",
                path=str(ca_path),
            )
            return []

        actions_raw = data["corporate_actions"]
        if not isinstance(actions_raw, list):
            logger.warning(
                "corporate_actions field is not a list, using empty list",
                path=str(ca_path),
            )
            return []

        # Validate each action has required fields
        required_fields = {"ticker", "action_date", "action_type"}
        valid_actions: list[dict[str, Any]] = []
        for i, action in enumerate(actions_raw):
            if not isinstance(action, dict):
                logger.warning(
                    "Skipping non-dict corporate action entry",
                    index=i,
                )
                continue
            missing = required_fields - set(action.keys())
            if missing:
                logger.warning(
                    "Skipping corporate action with missing required fields",
                    index=i,
                    missing_fields=sorted(missing),
                )
                continue
            valid_actions.append(action)

        logger.info(
            "Corporate actions loaded",
            count=len(valid_actions),
            skipped=len(actions_raw) - len(valid_actions),
            path=str(ca_path),
        )
        return valid_actions

    # -----------------------------------------------------------------------
    # Checkpoint I/O
    # -----------------------------------------------------------------------
    def _save_checkpoint[M: BaseModel](
        self,
        data: dict[str, list[M]],
        filename: str,
    ) -> None:
        """Save a phase checkpoint to a JSON file.

        Parameters
        ----------
        data : dict[str, list[M]]
            Per-ticker model data to persist.
        filename : str
            Checkpoint filename (e.g. "phase1_claims.json").
        """
        checkpoint_dir = self._workspace_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        serialized = {
            ticker: [c.model_dump() for c in items] for ticker, items in data.items()
        }

        path = checkpoint_dir / filename
        path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Checkpoint saved", path=str(path), filename=filename)

    def _load_checkpoint[M: BaseModel](
        self,
        filename: str,
        model_cls: type[M],
    ) -> dict[str, list[M]]:
        """Load a phase checkpoint from a JSON file.

        Parameters
        ----------
        filename : str
            Checkpoint filename (e.g. "phase1_claims.json").
        model_cls : type[M]
            Pydantic model class for deserialization.

        Returns
        -------
        dict[str, list[M]]
            Per-ticker model data.

        Raises
        ------
        FileNotFoundError
            If the checkpoint file does not exist.
        """
        path = self._workspace_dir / "checkpoints" / filename
        if not path.exists():
            msg = f"Checkpoint not found: {path}"
            raise FileNotFoundError(msg)

        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            ticker: [model_cls.model_validate(c) for c in items]
            for ticker, items in data.items()
        }


__all__ = [
    "Orchestrator",
]
