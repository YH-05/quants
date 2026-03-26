"""Configuration loader for industry research presets.

This module provides Pydantic models for the industry research preset
configuration file (``data/config/industry-research-presets.json``) and
a loader function to read and validate the configuration.

The preset file defines per-sector settings including:

- Sub-sector classifications
- Data source configurations (URLs, tiers, difficulty levels)
- Peer group ticker symbols and structured peer group definitions
- Sector-specific scraping queries for report collection
- Competitive factors for industry analysis
- Industry-specific media sources
- Key financial and operational metrics

Functions
---------
load_presets
    Load and validate industry research presets from a JSON file.

See Also
--------
market.industry.types : Data types used by the industry module.
rss.core.config : Similar config-loading pattern for the RSS module.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from database.db.connection import get_data_dir
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

DEFAULT_PRESETS_PATH: Path = (
    get_data_dir() / "config" / "industry-research-presets.json"
)
"""Default path to the industry research presets JSON file.

Resolved via ``get_data_dir()`` at import time.

See Also
--------
database.db.connection.get_data_dir
"""


# =============================================================================
# Configuration Models
# =============================================================================


class SourceConfig(BaseModel, frozen=True):
    """Configuration for a single data source.

    Parameters
    ----------
    name : str
        Human-readable name of the data source (e.g. ``"McKinsey Insights"``).
    url : str
        Base URL of the data source.
    tier : str
        Source tier: ``"api"``, ``"scraping"``, or ``"media"``.
    difficulty : str | None
        Scraping difficulty level (e.g. ``"easy"``, ``"medium"``, ``"hard"``).
        Only applicable to scraping sources. Defaults to ``None``.
    enabled : bool
        Whether this source is currently enabled for collection.
        Defaults to ``True``.

    Examples
    --------
    >>> source = SourceConfig(
    ...     name="McKinsey Insights",
    ...     url="https://mckinsey.com/featured-insights",
    ...     tier="scraping",
    ...     difficulty="medium",
    ... )
    >>> source.name
    'McKinsey Insights'
    """

    name: str
    url: str
    tier: str
    difficulty: str | None = None
    enabled: bool = True


class PeerGroupConfig(BaseModel, frozen=True):
    """Configuration for a peer group within a sector.

    Defines a group of companies within a specific sub-sector for
    competitive comparison and industry analysis.

    Parameters
    ----------
    sub_sector : str
        Sub-sector classification (e.g. ``"Semiconductors"``).
    companies : list[str]
        List of ticker symbols in the peer group.
    description : str | None
        Optional description of the peer group.
        Defaults to ``None``.

    Examples
    --------
    >>> group = PeerGroupConfig(
    ...     sub_sector="Semiconductors",
    ...     companies=["NVDA", "AMD", "INTC", "TSM", "AVGO"],
    ...     description="Major semiconductor manufacturers",
    ... )
    >>> group.sub_sector
    'Semiconductors'
    """

    sub_sector: str
    companies: list[str]
    description: str | None = None


class ScrapingQueryConfig(BaseModel, frozen=True):
    """Configuration for a sector-specific scraping query.

    Defines a search query to be used when scraping industry reports
    from consulting firms and investment banks.

    Parameters
    ----------
    query : str
        The search query string (e.g. ``"semiconductor industry outlook 2026"``).
    target_sources : list[str]
        List of source names to target with this query.
        Defaults to empty list (all sources).
    sector_specific : bool
        Whether this query is sector-specific.
        Defaults to ``False``.

    Examples
    --------
    >>> q = ScrapingQueryConfig(
    ...     query="semiconductor industry outlook 2026",
    ...     target_sources=["McKinsey", "BCG"],
    ...     sector_specific=True,
    ... )
    >>> q.query
    'semiconductor industry outlook 2026'
    """

    query: str
    target_sources: list[str] = Field(default_factory=list)
    sector_specific: bool = False


class CompetitiveFactorConfig(BaseModel, frozen=True):
    """Configuration for a competitive factor within a sector.

    Defines an industry-specific factor used for competitive
    analysis and positioning assessment.

    Parameters
    ----------
    factor_name : str
        Name of the competitive factor (e.g. ``"R&D Investment"``).
    description : str
        Description of what the factor measures.
    importance : str
        Importance level: ``"high"``, ``"medium"``, or ``"low"``.
        Defaults to ``"medium"``.

    Examples
    --------
    >>> factor = CompetitiveFactorConfig(
    ...     factor_name="R&D Investment",
    ...     description="Annual R&D spending as % of revenue",
    ...     importance="high",
    ... )
    >>> factor.factor_name
    'R&D Investment'
    """

    factor_name: str
    description: str
    importance: str = "medium"


class IndustryMediaConfig(BaseModel, frozen=True):
    """Configuration for an industry-specific media source.

    Defines a sector-specific publication or website for
    targeted news and analysis collection.

    Parameters
    ----------
    name : str
        Name of the media source (e.g. ``"SemiWiki"``).
    url : str
        Base URL of the media source.
    focus_areas : list[str]
        List of topic areas covered by this source.
        Defaults to empty list.

    Examples
    --------
    >>> media = IndustryMediaConfig(
    ...     name="SemiWiki",
    ...     url="https://semiwiki.com",
    ...     focus_areas=["semiconductors", "EDA"],
    ... )
    >>> media.name
    'SemiWiki'
    """

    name: str
    url: str
    focus_areas: list[str] = Field(default_factory=list)


class KeyMetricConfig(BaseModel, frozen=True):
    """Configuration for a key industry metric.

    Defines an important financial or operational metric
    for tracking sector performance and competitive positioning.

    Parameters
    ----------
    name : str
        Metric name (e.g. ``"Gross Margin"``).
    description : str
        Description of the metric and how it is calculated.
    data_source : str | None
        Where to obtain the metric data (e.g. ``"SEC filings"``).
        Defaults to ``None``.

    Examples
    --------
    >>> metric = KeyMetricConfig(
    ...     name="Gross Margin",
    ...     description="Revenue minus COGS divided by revenue",
    ...     data_source="SEC filings",
    ... )
    >>> metric.name
    'Gross Margin'
    """

    name: str
    description: str
    data_source: str | None = None


class IndustryPreset(BaseModel, frozen=True):
    """Preset configuration for a single industry sector.

    Parameters
    ----------
    sector : str
        GICS-style sector name (e.g. ``"Technology"``, ``"Healthcare"``).
    sub_sectors : list[str]
        List of sub-sector classifications within this sector
        (e.g. ``["Semiconductors", "Software_Infrastructure"]``).
    sources : list[SourceConfig]
        Data sources configured for this sector.
    peer_tickers : list[str]
        Default peer group ticker symbols for competitive analysis.
        Defaults to empty list.
    peer_groups : list[PeerGroupConfig]
        Structured peer group definitions per sub-sector.
        Defaults to empty list.
    scraping_queries : list[ScrapingQueryConfig]
        Sector-specific scraping queries for report collection.
        Defaults to empty list.
    competitive_factors : list[CompetitiveFactorConfig]
        Key competitive factors for the sector.
        Defaults to empty list.
    industry_media : list[IndustryMediaConfig]
        Sector-specific media sources.
        Defaults to empty list.
    key_metrics : list[KeyMetricConfig]
        Key financial/operational metrics for the sector.
        Defaults to empty list.

    Examples
    --------
    >>> preset = IndustryPreset(
    ...     sector="Technology",
    ...     sub_sectors=["Semiconductors"],
    ...     sources=[],
    ...     peer_tickers=["NVDA", "AMD", "INTC"],
    ... )
    >>> preset.sector
    'Technology'
    """

    sector: str
    sub_sectors: list[str]
    sources: list[SourceConfig]
    peer_tickers: list[str] = Field(default_factory=list)
    peer_groups: list[PeerGroupConfig] = Field(default_factory=list)
    scraping_queries: list[ScrapingQueryConfig] = Field(default_factory=list)
    competitive_factors: list[CompetitiveFactorConfig] = Field(default_factory=list)
    industry_media: list[IndustryMediaConfig] = Field(default_factory=list)
    key_metrics: list[KeyMetricConfig] = Field(default_factory=list)


class IndustryPresetsConfig(BaseModel, frozen=True):
    """Top-level configuration for industry research presets.

    Parameters
    ----------
    version : str
        Configuration file version (e.g. ``"1.0"``).
    presets : list[IndustryPreset]
        List of per-sector preset configurations.

    Examples
    --------
    >>> config = IndustryPresetsConfig(
    ...     version="1.0",
    ...     presets=[],
    ... )
    >>> config.version
    '1.0'
    """

    version: str
    presets: list[IndustryPreset]

    def get_sector(self, sector_name: str) -> IndustryPreset | None:
        """Look up a sector preset by name.

        Parameters
        ----------
        sector_name : str
            The sector name to search for (case-sensitive).

        Returns
        -------
        IndustryPreset | None
            The matching preset, or ``None`` if not found.

        Examples
        --------
        >>> config = IndustryPresetsConfig(version="1.0", presets=[
        ...     IndustryPreset(sector="Technology", sub_sectors=[], sources=[]),
        ... ])
        >>> config.get_sector("Technology")
        IndustryPreset(sector='Technology', ...)
        >>> config.get_sector("NonExistent") is None
        True
        """
        for preset in self.presets:
            if preset.sector == sector_name:
                return preset
        return None

    @property
    def sector_names(self) -> list[str]:
        """Return a list of all configured sector names.

        Returns
        -------
        list[str]
            Ordered list of sector names as they appear in the config.

        Examples
        --------
        >>> config.sector_names
        ['Technology', 'Healthcare', 'Financials']
        """
        return [preset.sector for preset in self.presets]


# =============================================================================
# Loader Function
# =============================================================================


def load_presets(path: Path | None = None) -> IndustryPresetsConfig:
    """Load and validate industry research presets from a JSON file.

    Reads the specified JSON file (or the default path), parses it,
    and validates the structure using Pydantic models.

    Parameters
    ----------
    path : Path | None
        Path to the JSON configuration file. If ``None``, uses
        ``DEFAULT_PRESETS_PATH``. Defaults to ``None``.

    Returns
    -------
    IndustryPresetsConfig
        Validated configuration object.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If the JSON file cannot be parsed or validated.

    Examples
    --------
    >>> config = load_presets()
    >>> config.version
    '1.0'

    >>> config = load_presets(Path("custom/presets.json"))
    """
    config_path = path or DEFAULT_PRESETS_PATH

    if not config_path.exists():
        logger.error(
            "Presets file not found",
            path=str(config_path),
        )
        raise FileNotFoundError(
            f"Industry presets file not found: {config_path}. "
            f"Create the file at: {DEFAULT_PRESETS_PATH}"
        )

    logger.info("Loading industry presets", path=str(config_path))

    try:
        raw_text = config_path.read_text(encoding="utf-8")
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse presets JSON",
            path=str(config_path),
            error=str(e),
        )
        raise ValueError(
            f"Failed to parse industry presets JSON: {config_path}: {e}"
        ) from e

    config = IndustryPresetsConfig.model_validate(raw_data)

    logger.info(
        "Industry presets loaded successfully",
        version=config.version,
        sector_count=len(config.presets),
        sectors=config.sector_names,
    )

    return config


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "DEFAULT_PRESETS_PATH",
    "CompetitiveFactorConfig",
    "IndustryMediaConfig",
    "IndustryPreset",
    "IndustryPresetsConfig",
    "KeyMetricConfig",
    "PeerGroupConfig",
    "ScrapingQueryConfig",
    "SourceConfig",
    "load_presets",
]
