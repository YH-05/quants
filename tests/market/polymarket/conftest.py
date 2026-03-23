"""Shared test fixtures for the Polymarket test suite.

Provides a ``tmp_path``-based SQLite fixture that creates a fresh
``PolymarketStorage`` instance for each test function, ensuring
test isolation with no persistent side-effects.
"""

from pathlib import Path

import pytest

from market.polymarket.storage import PolymarketStorage


@pytest.fixture()
def pm_storage(tmp_path: Path) -> PolymarketStorage:
    """Create a temporary PolymarketStorage instance.

    Uses ``tmp_path`` to create an isolated SQLite database file
    that is automatically cleaned up after the test. All 8 tables
    are created on initialization via ``ensure_tables()``.

    Parameters
    ----------
    tmp_path : Path
        Pytest-provided temporary directory path.

    Returns
    -------
    PolymarketStorage
        A configured storage instance pointing to a temporary database.
    """
    db_path = tmp_path / "polymarket_test.db"
    return PolymarketStorage(db_path=db_path)
