"""Configuration management for the edgar package.

This module provides configuration for SEC EDGAR data access including:
- User identity for SEC EDGAR API compliance
- Cache directory and TTL settings
- Rate limiting configuration

Environment Variables
---------------------
SEC_EDGAR_IDENTITY : str
    User identity for SEC EDGAR API in the format "Name Email"
    (e.g., "John Doe john@example.com"). Required by SEC EDGAR
    fair access policy.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from database.db.connection import get_data_dir
from utils_core.logging import get_logger

logger = get_logger(__name__)

# Environment variable name for SEC EDGAR identity
SEC_EDGAR_IDENTITY_ENV = "SEC_EDGAR_IDENTITY"

# Default cache configuration
DEFAULT_CACHE_DIR = get_data_dir() / "cache" / "edgar"
DEFAULT_CACHE_TTL_HOURS = 24
DEFAULT_RATE_LIMIT_PER_SECOND = 10

# Default maximum filing size in bytes (10 MB)
# AIDEV-NOTE: 10-K filings can be several MB in size. This limit provides
# a safety check and warning for unusually large filings that may cause
# high memory usage.
DEFAULT_MAX_FILING_SIZE_BYTES = 10 * 1024 * 1024


@dataclass
class EdgarConfig:
    """Configuration for SEC EDGAR data access.

    Parameters
    ----------
    identity : str
        User identity string for SEC EDGAR API compliance
        (e.g., "John Doe john@example.com")
    cache_dir : Path
        Directory for caching downloaded filings
    cache_ttl_hours : int
        Time-to-live for cached data in hours
    rate_limit_per_second : int
        Maximum requests per second to SEC EDGAR
    max_filing_size_bytes : int
        Maximum filing text size in bytes before emitting a warning.
        Filings exceeding this size will still be processed but a
        warning log will be emitted. Default is 10 MB.

    Examples
    --------
    >>> config = EdgarConfig(
    ...     identity="John Doe john@example.com",
    ...     cache_dir=Path("data/cache/edgar"),
    ...     cache_ttl_hours=24,
    ...     rate_limit_per_second=10,
    ... )
    """

    identity: str = ""
    cache_dir: Path = field(default_factory=lambda: DEFAULT_CACHE_DIR)
    cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS
    rate_limit_per_second: int = DEFAULT_RATE_LIMIT_PER_SECOND
    max_filing_size_bytes: int = DEFAULT_MAX_FILING_SIZE_BYTES

    @property
    def is_identity_configured(self) -> bool:
        """Check if the identity is properly configured.

        Returns
        -------
        bool
            True if identity string is non-empty
        """
        return bool(self.identity.strip())


def load_config() -> EdgarConfig:
    """Load EDGAR configuration from environment variables.

    Reads the SEC_EDGAR_IDENTITY environment variable and creates
    an EdgarConfig instance with the configured identity.

    Returns
    -------
    EdgarConfig
        The loaded configuration

    Examples
    --------
    >>> import os
    >>> os.environ["SEC_EDGAR_IDENTITY"] = "John Doe john@example.com"
    >>> config = load_config()
    >>> config.identity
    'John Doe john@example.com'
    """
    identity = os.environ.get(SEC_EDGAR_IDENTITY_ENV, "")

    if identity:
        logger.info(
            "Loaded SEC EDGAR identity from environment",
            identity=identity,
        )
    else:
        logger.warning(
            "SEC_EDGAR_IDENTITY not set. "
            "Set this environment variable for SEC EDGAR API compliance.",
        )

    return EdgarConfig(identity=identity)


def set_identity(name: str, email: str) -> None:
    """Set the SEC EDGAR identity for API compliance.

    This function sets the identity used for SEC EDGAR API requests.
    SEC EDGAR requires a User-Agent header with contact information.

    If edgartools is available, it also calls edgartools.set_identity()
    to configure the underlying library.

    Parameters
    ----------
    name : str
        Full name of the user or organization
    email : str
        Contact email address

    Raises
    ------
    ValueError
        If name or email is empty

    Examples
    --------
    >>> set_identity("John Doe", "john@example.com")
    """
    if not name.strip():
        msg = "Name must not be empty"
        raise ValueError(msg)

    if not email.strip():
        msg = "Email must not be empty"
        raise ValueError(msg)

    identity = f"{name} {email}"
    os.environ[SEC_EDGAR_IDENTITY_ENV] = identity

    logger.info(
        "Set SEC EDGAR identity",
        name=name,
        email=email,
    )

    # Configure edgartools if available
    # AIDEV-NOTE: edgartools installs as 'edgar' in site-packages, which conflicts
    # with our src/edgar package. We use importlib.util to load it from site-packages
    # by scanning sys.path for the site-packages version.
    _configure_edgartools(identity)


def _configure_edgartools(identity: str) -> None:
    """Configure the edgartools library identity if available.

    Parameters
    ----------
    identity : str
        Identity string to set for edgartools
    """
    try:
        import importlib.machinery
        import importlib.util
        import sys

        # Find the site-packages edgar module (not our src/edgar)
        # Use PathFinder to search only site-packages directories
        site_packages_paths = [p for p in sys.path if "site-packages" in p]
        spec = importlib.machinery.PathFinder.find_spec("edgar", site_packages_paths)
        if spec is not None and spec.origin is not None:
            mod = importlib.util.module_from_spec(spec)
            if spec.loader is not None:
                spec.loader.exec_module(mod)
                if hasattr(mod, "set_identity"):
                    mod.set_identity(identity)
                    logger.info("Configured edgartools identity")
                    return
        logger.debug("edgartools not found in site-packages")
    except Exception:
        logger.debug(
            "Failed to configure edgartools identity",
            exc_info=True,
        )


__all__ = [
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CACHE_TTL_HOURS",
    "DEFAULT_MAX_FILING_SIZE_BYTES",
    "DEFAULT_RATE_LIMIT_PER_SECOND",
    "SEC_EDGAR_IDENTITY_ENV",
    "EdgarConfig",
    "load_config",
    "set_identity",
]
