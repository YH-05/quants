"""Competitive Advantage Strategy package.

AI-driven investment strategy based on competitive advantage evaluation
from earnings call transcripts.
"""

from dev.ca_strategy.batch import BatchProcessor
from dev.ca_strategy.cost import CostTracker
from dev.ca_strategy.extractor import ClaimExtractor
from dev.ca_strategy.orchestrator import Orchestrator
from dev.ca_strategy.price_provider import NullPriceDataProvider, PriceDataProvider
from dev.ca_strategy.scorer import ClaimScorer
from dev.ca_strategy.types import (
    Claim,
    PortfolioHolding,
    PortfolioResult,
    ScoredClaim,
    StockScore,
    Transcript,
)

__all__ = [
    "BatchProcessor",
    "Claim",
    "ClaimExtractor",
    "ClaimScorer",
    "CostTracker",
    "NullPriceDataProvider",
    "Orchestrator",
    "PortfolioHolding",
    "PortfolioResult",
    "PriceDataProvider",
    "ScoredClaim",
    "StockScore",
    "Transcript",
]
