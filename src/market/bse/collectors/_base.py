"""Base mixin for BSE collectors with shared session management.

Provides ``_get_session()`` and ``__init__`` logic shared across all
BSE collector classes (QuoteCollector, BhavcopyCollector,
IndexCollector, CorporateCollector).
"""

from __future__ import annotations

from market.bse.session import BseSession
from utils_core.logging import get_logger

logger = get_logger(__name__)


class BseCollectorMixin:
    """Mixin providing BSE session lifecycle management.

    All BSE collectors share the same session injection pattern:
    accept an optional ``BseSession`` in the constructor and resolve
    it lazily via ``_get_session()``.

    Parameters
    ----------
    session : BseSession | None
        Pre-configured BseSession for dependency injection.
        If None, a new BseSession is created when needed.
    """

    def __init__(self, session: BseSession | None = None) -> None:
        self._session_instance: BseSession | None = session

    def _get_session(self) -> tuple[BseSession, bool]:
        """Resolve the session: use injected or create new.

        Returns
        -------
        tuple[BseSession, bool]
            A tuple of (session, should_close).  ``should_close`` is True
            when a new session was created internally and must be closed
            by the caller.

        Examples
        --------
        >>> collector = QuoteCollector()
        >>> session, should_close = collector._get_session()
        >>> try:
        ...     response = session.get_with_retry(url)
        ... finally:
        ...     if should_close:
        ...         session.close()
        """
        if self._session_instance is not None:
            return self._session_instance, False
        return BseSession(), True
