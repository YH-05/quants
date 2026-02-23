"""Embedding - News Embedding Pipeline for finance project."""

from .pipeline import run_pipeline
from .types import ArticleRecord, ExtractionResult, PipelineConfig

__version__ = "0.1.0"
__all__ = [
    "ArticleRecord",
    "ExtractionResult",
    "PipelineConfig",
    "__version__",
    "run_pipeline",
]
