"""Point-in-Time (PoiT) management for the CA Strategy pipeline.

Provides cutoff_date enforcement to prevent survivorship bias and
look-ahead bias in backtesting.  All data access and LLM prompts
must respect the cutoff date.

Features
--------
- CUTOFF_DATE constant: Default cutoff date (2015-09-30)
- filter_by_pit: Filter transcripts by event_date <= cutoff_date
- get_pit_prompt_context: Generate temporal constraint text for LLM prompts
- validate_pit_compliance: Validate all data respects the cutoff date

Notes
-----
The cutoff date is 2015-09-30, corresponding to the end of Q3 FY2015.
This ensures the strategy evaluation uses only information available
at that point in time.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from utils_core.logging import get_logger

if TYPE_CHECKING:
    from dev.ca_strategy.types import Transcript

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CUTOFF_DATE: date = date(2015, 9, 30)
"""Default cutoff date for PoiT management (end of Q3 FY2015)."""

PORTFOLIO_DATE: date = date(2015, 12, 31)
"""Portfolio construction date (end of Q4 FY2015).

The date when the portfolio is assumed to be constructed based on
scores derived from transcripts up to CUTOFF_DATE.
"""

EVALUATION_END_DATE: date = date(2026, 2, 28)
"""Evaluation end date for performance measurement.

The end date for calculating portfolio returns in backtesting.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def filter_by_pit(
    transcripts: list[Transcript],
    cutoff_date: date = CUTOFF_DATE,
) -> list[Transcript]:
    """Filter transcripts to include only those on or before the cutoff date.

    Parameters
    ----------
    transcripts : list[Transcript]
        List of transcripts to filter.
    cutoff_date : date, optional
        The cutoff date for filtering.  Defaults to CUTOFF_DATE.

    Returns
    -------
    list[Transcript]
        Filtered list containing only transcripts with
        event_date <= cutoff_date.
    """
    filtered = [t for t in transcripts if t.metadata.event_date <= cutoff_date]
    logger.debug(
        "PoiT filter applied",
        total=len(transcripts),
        retained=len(filtered),
        cutoff_date=cutoff_date.isoformat(),
    )
    return filtered


def get_pit_prompt_context(cutoff_date: date = CUTOFF_DATE) -> str:
    """Generate temporal constraint text for LLM prompt injection.

    The returned string should be included in LLM system prompts to
    enforce point-in-time constraints on the model's reasoning.

    Parameters
    ----------
    cutoff_date : date, optional
        The cutoff date to embed in the prompt.  Defaults to CUTOFF_DATE.

    Returns
    -------
    str
        Multi-line temporal constraint instructions for LLM prompts.
    """
    date_str = cutoff_date.isoformat()
    return (
        f"TEMPORAL CONSTRAINTS (MANDATORY):\n"
        f"- The current date is {date_str}.\n"
        f"- You must NOT use any information after {date_str}.\n"
        f"- SEC Filings must have filing_date on or before {date_str}.\n"
        f"- Do NOT use knowledge of future stock prices, earnings, or events.\n"
        f"- All analysis must be based solely on information available as of {date_str}."
    )


def validate_pit_compliance(
    transcripts: list[Transcript],
    cutoff_date: date = CUTOFF_DATE,
) -> bool:
    """Validate that all transcripts comply with the cutoff date.

    Parameters
    ----------
    transcripts : list[Transcript]
        List of transcripts to validate.
    cutoff_date : date, optional
        The cutoff date for validation.  Defaults to CUTOFF_DATE.

    Returns
    -------
    bool
        True if all transcripts have event_date <= cutoff_date,
        False otherwise.
    """
    for transcript in transcripts:
        if transcript.metadata.event_date > cutoff_date:
            logger.warning(
                "PoiT compliance violation detected",
                ticker=transcript.metadata.ticker,
                event_date=transcript.metadata.event_date.isoformat(),
                cutoff_date=cutoff_date.isoformat(),
            )
            return False
    return True


__all__ = [
    "CUTOFF_DATE",
    "EVALUATION_END_DATE",
    "PORTFOLIO_DATE",
    "filter_by_pit",
    "get_pit_prompt_context",
    "validate_pit_compliance",
]
