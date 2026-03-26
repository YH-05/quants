"""FRED historical data local cache management.

This module provides functionality for caching FRED economic indicator data
locally as JSON files. It supports full historical data retrieval and
incremental updates.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from database.db.connection import get_data_dir
from market.errors import FREDFetchError
from utils_core.logging import get_logger
from utils_core.settings import load_project_env

from .fetcher import FREDFetcher
from .types import FetchOptions

logger = get_logger(__name__, module="fred_historical_cache")

# Environment variable for cache directory
FRED_HISTORICAL_CACHE_DIR_ENV = "FRED_HISTORICAL_CACHE_DIR"


def get_default_cache_path() -> Path:
    """Get the default cache path with priority-based resolution.

    Resolution priority:
    1. FRED_HISTORICAL_CACHE_DIR environment variable
    2. Fallback: get_data_dir() / "raw" / "fred" / "indicators"

    Returns
    -------
    Path
        Default cache directory path
    """
    load_project_env()

    # Priority 1: Environment variable
    env_path = os.environ.get(FRED_HISTORICAL_CACHE_DIR_ENV)
    if env_path:
        logger.debug(
            "Using cache path from environment variable",
            env_var=FRED_HISTORICAL_CACHE_DIR_ENV,
            path=env_path,
        )
        return Path(env_path)

    # Priority 2: Fallback to get_data_dir() based path
    default_path = get_data_dir() / "raw" / "fred" / "indicators"
    logger.debug(
        "Using cache path from get_data_dir()",
        path=str(default_path),
    )
    return default_path


# For backwards compatibility
DEFAULT_CACHE_PATH = get_data_dir() / "raw" / "fred" / "indicators"

# Cache file version
CACHE_VERSION = 1


class HistoricalCache:
    """Local cache manager for FRED historical data.

    Manages local JSON cache files for FRED economic indicator data.
    Supports full historical data retrieval and incremental updates.

    Parameters
    ----------
    base_path : Path | str | None
        Base directory for cache files.
        If None, uses default path: data/raw/fred/indicators/

    Attributes
    ----------
    base_path : Path
        Directory where cache files are stored

    Examples
    --------
    >>> cache = HistoricalCache()
    >>> cache.sync_series("DGS10")
    >>> df = cache.get_series_df("DGS10")
    >>> print(df.head())
    """

    def __init__(self, base_path: Path | str | None = None) -> None:
        """Initialize HistoricalCache.

        Parameters
        ----------
        base_path : Path | str | None
            Base directory for cache files.
            If None, uses FRED_HISTORICAL_CACHE_DIR environment variable,
            or falls back to data/raw/fred/indicators/.
        """
        if base_path is None:
            self._base_path = get_default_cache_path()
        else:
            self._base_path = Path(base_path)

        # Create directory if it doesn't exist
        self._base_path.mkdir(parents=True, exist_ok=True)

        # Ensure presets are loaded
        FREDFetcher.load_presets()

        logger.debug(
            "HistoricalCache initialized",
            base_path=str(self._base_path),
        )

    @property
    def base_path(self) -> Path:
        """Return the base path for cache files.

        Returns
        -------
        Path
            Base directory for cache files
        """
        return self._base_path

    def sync_series(self, series_id: str) -> dict[str, Any]:
        """Sync a single FRED series.

        For new series, fetches full historical data.
        For existing series, performs incremental update.

        Parameters
        ----------
        series_id : str
            FRED series ID (e.g., "DGS10", "GDP")

        Returns
        -------
        dict[str, Any]
            Sync result containing:
            - series_id: The series ID
            - success: Whether sync was successful
            - data_points: Total number of data points
            - new_points: Number of new points added (for incremental updates)
            - error: Error message if failed

        Raises
        ------
        ValueError
            If series_id is not found in presets
        """
        logger.info("Syncing series", series_id=series_id)

        # Validate series exists in presets
        preset_info = FREDFetcher.get_preset_info(series_id)
        if preset_info is None:
            logger.error(
                "Series not found in presets",
                series_id=series_id,
            )
            raise ValueError(
                f"Series '{series_id}' not found in presets. "
                "Use FREDFetcher.get_preset_symbols() to see available series."
            )

        try:
            # Check for existing cache
            cache_file = self._base_path / f"{series_id}.json"
            existing_data = self._load_cache_file(cache_file)

            # Determine start date for fetch
            if existing_data is not None:
                # Incremental update: fetch from last data point
                last_date = existing_data["data"][-1]["date"]
                start_date = last_date
                logger.debug(
                    "Performing incremental update",
                    series_id=series_id,
                    last_date=last_date,
                )
            else:
                # Full fetch: no start date (get all history)
                start_date = None
                logger.debug(
                    "Performing full historical fetch",
                    series_id=series_id,
                )

            # Fetch data from FRED API
            fetcher = FREDFetcher()
            options = FetchOptions(
                symbols=[series_id],
                start_date=start_date,
                use_cache=False,  # Always fetch from API
            )

            results = fetcher.fetch(options)
            if not results or results[0].is_empty:
                logger.warning(
                    "No data returned from FRED API",
                    series_id=series_id,
                )
                if existing_data is not None:
                    # No new data, but existing cache is valid
                    return {
                        "series_id": series_id,
                        "success": True,
                        "data_points": len(existing_data["data"]),
                        "new_points": 0,
                    }
                raise FREDFetchError(f"No data found for series: {series_id}")

            result = results[0]
            new_df = result.data

            # Get FRED metadata
            fred_metadata = fetcher.get_series_info(series_id)

            # Merge with existing data if applicable
            if existing_data is not None:
                merged_data = self._merge_data(existing_data["data"], new_df)
                new_points = len(merged_data) - len(existing_data["data"])
            else:
                merged_data = self._df_to_data_list(new_df)
                new_points = len(merged_data)

            # Build cache structure
            cache_data = self._build_cache_data(
                series_id=series_id,
                preset_info=preset_info,
                fred_metadata=fred_metadata,
                data=merged_data,
            )

            # Save to file
            self._save_cache_file(cache_file, cache_data)

            # Update index
            self._update_index(series_id, cache_data)

            logger.info(
                "Series synced successfully",
                series_id=series_id,
                data_points=len(merged_data),
                new_points=new_points,
            )

            return {
                "series_id": series_id,
                "success": True,
                "data_points": len(merged_data),
                "new_points": new_points,
            }

        except Exception as e:
            logger.error(
                "Failed to sync series",
                series_id=series_id,
                error=str(e),
            )
            if isinstance(e, ValueError):
                raise
            return {
                "series_id": series_id,
                "success": False,
                "error": str(e),
            }

    def sync_all_presets(self) -> list[dict[str, Any]]:
        """Sync all preset series.

        Returns
        -------
        list[dict[str, Any]]
            List of sync results for each series
        """
        logger.info("Syncing all preset series")

        symbols = FREDFetcher.get_preset_symbols()
        results = []

        for series_id in symbols:
            try:
                result = self.sync_series(series_id)
                results.append(result)
            except ValueError:
                # Series not in presets (shouldn't happen, but handle gracefully)
                results.append(
                    {
                        "series_id": series_id,
                        "success": False,
                        "error": f"Series '{series_id}' not found in presets",
                    }
                )

        success_count = sum(1 for r in results if r.get("success", False))
        logger.info(
            "All presets sync completed",
            total=len(results),
            successful=success_count,
            failed=len(results) - success_count,
        )

        return results

    def sync_category(self, category: str) -> list[dict[str, Any]]:
        """Sync all series in a category.

        Parameters
        ----------
        category : str
            Category name (e.g., "Treasury Yields")

        Returns
        -------
        list[dict[str, Any]]
            List of sync results for each series in the category

        Raises
        ------
        KeyError
            If category does not exist
        """
        logger.info("Syncing category", category=category)

        symbols = FREDFetcher.get_preset_symbols(category)
        results = []

        for series_id in symbols:
            try:
                result = self.sync_series(series_id)
                results.append(result)
            except ValueError as e:
                results.append(
                    {
                        "series_id": series_id,
                        "success": False,
                        "error": str(e),
                    }
                )

        success_count = sum(1 for r in results if r.get("success", False))
        logger.info(
            "Category sync completed",
            category=category,
            total=len(results),
            successful=success_count,
            failed=len(results) - success_count,
        )

        return results

    def get_series(self, series_id: str) -> dict[str, Any] | None:
        """Get cached data for a series.

        Parameters
        ----------
        series_id : str
            FRED series ID

        Returns
        -------
        dict[str, Any] | None
            Cached data structure, or None if not cached
        """
        cache_file = self._base_path / f"{series_id}.json"
        return self._load_cache_file(cache_file)

    def get_series_df(self, series_id: str) -> pd.DataFrame | None:
        """Get cached data as DataFrame.

        Parameters
        ----------
        series_id : str
            FRED series ID

        Returns
        -------
        pd.DataFrame | None
            DataFrame with DatetimeIndex and 'value' column,
            or None if not cached
        """
        data = self.get_series(series_id)
        if data is None:
            return None

        df = pd.DataFrame(data["data"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df.index.name = None

        return df

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get sync status for all preset series.

        Returns
        -------
        dict[str, dict[str, Any]]
            Status for each series containing:
            - cached: Whether data is cached locally
            - last_fetched: Last fetch timestamp (if cached)
            - data_points: Number of data points (if cached)
            - date_range: [start, end] dates (if cached)
        """
        symbols = FREDFetcher.get_preset_symbols()
        status: dict[str, dict[str, Any]] = {}

        for series_id in symbols:
            cache_file = self._base_path / f"{series_id}.json"
            data = self._load_cache_file(cache_file)

            if data is not None:
                cache_meta = data.get("cache_metadata", {})
                fred_meta = data.get("fred_metadata", {})
                status[series_id] = {
                    "cached": True,
                    "last_fetched": cache_meta.get("last_fetched"),
                    "data_points": cache_meta.get(
                        "data_points", len(data.get("data", []))
                    ),
                    "date_range": [
                        fred_meta.get("observation_start"),
                        fred_meta.get("observation_end"),
                    ],
                }
            else:
                status[series_id] = {"cached": False}

        return status

    def invalidate(self, series_id: str) -> bool:
        """Invalidate (delete) cache for a series.

        Parameters
        ----------
        series_id : str
            FRED series ID

        Returns
        -------
        bool
            True if cache was deleted, False if it didn't exist
        """
        cache_file = self._base_path / f"{series_id}.json"

        if cache_file.exists():
            cache_file.unlink()
            logger.info("Cache invalidated", series_id=series_id)

            # Update index
            self._remove_from_index(series_id)

            return True

        return False

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _load_cache_file(self, cache_file: Path) -> dict[str, Any] | None:
        """Load a cache file.

        Parameters
        ----------
        cache_file : Path
            Path to cache file

        Returns
        -------
        dict[str, Any] | None
            Loaded data, or None if file doesn't exist
        """
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(
                "Failed to load cache file",
                file=str(cache_file),
                error=str(e),
            )
            return None

    def _save_cache_file(self, cache_file: Path, data: dict[str, Any]) -> None:
        """Save data to cache file.

        Parameters
        ----------
        cache_file : Path
            Path to cache file
        data : dict[str, Any]
            Data to save
        """
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug("Cache file saved", file=str(cache_file))

    def _build_cache_data(
        self,
        series_id: str,
        preset_info: dict[str, Any],
        fred_metadata: dict[str, Any],
        data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build cache data structure.

        Parameters
        ----------
        series_id : str
            FRED series ID
        preset_info : dict[str, Any]
            Preset information from config
        fred_metadata : dict[str, Any]
            Metadata from FRED API
        data : list[dict[str, Any]]
            Data points

        Returns
        -------
        dict[str, Any]
            Complete cache data structure
        """
        # Extract category_name and remove it from preset_info copy
        preset_copy = {k: v for k, v in preset_info.items() if k != "category_name"}

        # Get date range from data
        date_range_start = data[0]["date"] if data else None
        date_range_end = data[-1]["date"] if data else None

        return {
            "series_id": series_id,
            "preset_info": preset_copy,
            "fred_metadata": {
                "observation_start": fred_metadata.get(
                    "observation_start", date_range_start
                ),
                "observation_end": fred_metadata.get("observation_end", date_range_end),
                "title": fred_metadata.get("title"),
                "last_updated_api": fred_metadata.get("last_updated"),
            },
            "cache_metadata": {
                "last_fetched": datetime.now(timezone.utc).isoformat(),
                "data_points": len(data),
                "version": CACHE_VERSION,
            },
            "data": data,
        }

    def _df_to_data_list(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Convert DataFrame to list of data points.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with DatetimeIndex and 'value' column

        Returns
        -------
        list[dict[str, Any]]
            List of {"date": "YYYY-MM-DD", "value": float}
        """
        result: list[dict[str, Any]] = []

        # Reset index to have date as a column
        df_reset = df.reset_index()
        date_col = df_reset.columns[0]  # First column is the date index

        for _, row in df_reset.iterrows():
            date_val = row[date_col]
            value = row.get("value")

            if value is not None and pd.notna(value):
                # Cast to str for pd.Timestamp compatibility
                date_str = str(date_val) if date_val is not None else ""
                result.append(
                    {
                        "date": pd.Timestamp(date_str).strftime("%Y-%m-%d"),
                        "value": float(value),
                    }
                )
        return result

    def _merge_data(
        self,
        existing: list[dict[str, Any]],
        new_df: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """Merge existing data with new data.

        Parameters
        ----------
        existing : list[dict[str, Any]]
            Existing data points
        new_df : pd.DataFrame
            New data from API

        Returns
        -------
        list[dict[str, Any]]
            Merged data points (sorted by date)
        """
        # Convert new data to list format
        new_data = self._df_to_data_list(new_df)

        # Create a dict keyed by date for efficient merging
        merged: dict[str, dict[str, Any]] = {}

        # Add existing data
        for point in existing:
            merged[point["date"]] = point

        # Add/update with new data
        for point in new_data:
            merged[point["date"]] = point

        # Sort by date and return as list
        return [merged[date] for date in sorted(merged.keys())]

    def _update_index(self, series_id: str, cache_data: dict[str, Any]) -> None:
        """Update the index file after sync.

        Parameters
        ----------
        series_id : str
            FRED series ID
        cache_data : dict[str, Any]
            Cache data that was saved
        """
        index_file = self._base_path / "_index.json"

        # Load existing index or create new
        if index_file.exists():
            try:
                with open(index_file, encoding="utf-8") as f:
                    index_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                index_data = {"version": CACHE_VERSION, "series": {}}
        else:
            index_data = {"version": CACHE_VERSION, "series": {}}

        # Update index entry
        cache_meta = cache_data.get("cache_metadata", {})
        fred_meta = cache_data.get("fred_metadata", {})

        index_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        index_data["series"][series_id] = {
            "file": f"{series_id}.json",
            "last_fetched": cache_meta.get("last_fetched"),
            "data_points": cache_meta.get("data_points"),
            "date_range": [
                fred_meta.get("observation_start"),
                fred_meta.get("observation_end"),
            ],
        }

        # Save index
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def _remove_from_index(self, series_id: str) -> None:
        """Remove a series from the index file.

        Parameters
        ----------
        series_id : str
            FRED series ID to remove
        """
        index_file = self._base_path / "_index.json"

        if not index_file.exists():
            return

        try:
            with open(index_file, encoding="utf-8") as f:
                index_data = json.load(f)

            if series_id in index_data.get("series", {}):
                del index_data["series"][series_id]
                index_data["last_updated"] = datetime.now(timezone.utc).isoformat()

                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, IOError):
            pass


__all__ = [
    "DEFAULT_CACHE_PATH",
    "FRED_HISTORICAL_CACHE_DIR_ENV",
    "HistoricalCache",
    "get_default_cache_path",
]
