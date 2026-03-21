"""Database connection management for cross-package access."""

import os
from pathlib import Path

from database.types import DatabaseType

# Project paths
# DEPRECATED: Use get_data_dir() instead. These constants will be removed in future versions.
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def get_data_dir() -> Path:
    """Get data directory path.

    Retrieves the data directory path using the following priority:

    1. DATA_DIR environment variable (if set and non-empty)
    2. Current working directory + /data (if exists)
    3. Fallback: __file__ based path (backward compatibility)

    Returns
    -------
    Path
        Path to the data directory

    Examples
    --------
    >>> # With DATA_DIR environment variable set
    >>> import os
    >>> os.environ["DATA_DIR"] = "/custom/data/path"
    >>> get_data_dir()
    PosixPath('/custom/data/path')

    >>> # Without DATA_DIR, uses ./data if exists
    >>> get_data_dir()  # Returns Path("./data") if it exists

    >>> # Fallback to __file__ based path
    >>> get_data_dir()  # Returns PROJECT_ROOT / "data"
    """
    # Priority 1: DATA_DIR environment variable
    env_data_dir = os.environ.get("DATA_DIR", "")
    if env_data_dir:
        return Path(env_data_dir)

    # Priority 2: Current working directory + /data
    cwd_data = Path.cwd() / "data"
    if cwd_data.exists():
        return cwd_data

    # Priority 3: Fallback to __file__ based path (backward compatibility)
    return DATA_DIR


def get_db_path(db_type: DatabaseType, name: str) -> Path:
    """Get database file path.

    Parameters
    ----------
    db_type : DatabaseType
        Type of database ('sqlite' or 'duckdb')
    name : str
        Name of the database (without extension)

    Returns
    -------
    Path
        Full path to the database file

    Examples
    --------
    >>> path = get_db_path("sqlite", "market")
    >>> path.name
    'market.db'
    >>> path = get_db_path("duckdb", "analytics")
    >>> path.name
    'analytics.duckdb'
    """
    data_dir = get_data_dir()
    if db_type == "sqlite":
        return data_dir / "sqlite" / f"{name}.db"
    return data_dir / "duckdb" / f"{name}.duckdb"


def ensure_data_dirs() -> None:
    """Ensure all data directories exist.

    Creates the complete data directory structure if it doesn't exist.
    Uses get_data_dir() to respect the DATA_DIR environment variable.
    """
    data_dir = get_data_dir()
    dirs = [
        data_dir / "sqlite",
        data_dir / "duckdb",
        data_dir / "raw" / "yfinance" / "stocks",
        data_dir / "raw" / "yfinance" / "forex",
        data_dir / "raw" / "yfinance" / "indices",
        data_dir / "raw" / "fred" / "indicators",
        data_dir / "processed" / "daily",
        data_dir / "processed" / "aggregated",
        data_dir / "exports" / "csv",
        data_dir / "exports" / "json",
    ]
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
