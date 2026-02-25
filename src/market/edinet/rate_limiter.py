"""Daily rate limiter for the EDINET DB API module.

This module provides the ``DailyRateLimiter`` class that manages daily
API call counting with JSON file persistence. The counter automatically
resets when the date changes, and a configurable safety margin prevents
accidental overuse.

The state is persisted to a JSON file with the schema::

    {"date": "YYYY-MM-DD", "calls": N}

Notes
-----
This module is intentionally separated from ``client.py`` to improve
testability and adhere to the single-responsibility principle. The
limiter is designed to be injected into ``EdinetClient`` for call
counting.

See Also
--------
market.edinet.constants : Default values for ``DAILY_RATE_LIMIT`` and
    ``SAFE_MARGIN``.
market.edinet.errors : ``EdinetRateLimitError`` raised when limit is
    exceeded.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from market.edinet.constants import DAILY_RATE_LIMIT, SAFE_MARGIN
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


class DailyRateLimiter:
    """Manage daily API call limits with JSON file persistence.

    Tracks the number of API calls made today and persists the count
    to a JSON file. The counter resets automatically when the date
    changes. A configurable safety margin is subtracted from the
    daily limit to prevent accidental overuse.

    To reduce file I/O overhead, state is only persisted every
    ``flush_interval`` calls (default: 100). Call ``flush()`` explicitly
    to force a write (e.g. before shutdown).

    Parameters
    ----------
    state_path : Path
        Path to the JSON file for persisting the rate limit state.
    daily_limit : int
        Maximum number of API calls allowed per day
        (default: ``DAILY_RATE_LIMIT`` = 1000).
    safe_margin : int
        Safety margin subtracted from the daily limit
        (default: ``SAFE_MARGIN`` = 50).
    flush_interval : int
        Persist state to disk every N calls (default: 100).

    Attributes
    ----------
    daily_limit : int
        The configured daily API call limit.
    safe_margin : int
        The configured safety margin.

    Examples
    --------
    >>> from pathlib import Path
    >>> limiter = DailyRateLimiter(state_path=Path("/tmp/rate.json"))
    >>> limiter.is_allowed()
    True
    >>> limiter.record_call()
    >>> limiter.get_remaining()
    949
    """

    def __init__(
        self,
        state_path: Path,
        daily_limit: int = DAILY_RATE_LIMIT,
        safe_margin: int = SAFE_MARGIN,
        flush_interval: int = 100,
    ) -> None:
        self._state_path = state_path
        self.daily_limit = daily_limit
        self.safe_margin = safe_margin
        self._flush_interval = flush_interval
        self._date: str = date.today().isoformat()
        self._calls: int = 0
        self._dirty: int = 0

        self._load_state()

        logger.debug(
            "DailyRateLimiter initialized",
            state_path=str(state_path),
            daily_limit=daily_limit,
            safe_margin=safe_margin,
            flush_interval=flush_interval,
            current_calls=self._calls,
            current_date=self._date,
        )

    def record_call(self) -> None:
        """Record a single API call.

        Increments the internal call counter by one. State is persisted
        to disk every ``flush_interval`` calls to reduce I/O overhead.

        Examples
        --------
        >>> limiter.record_call()
        """
        self._calls += 1
        self._dirty += 1

        if self._dirty >= self._flush_interval:
            self._save_state()
            self._dirty = 0

        logger.debug(
            "API call recorded",
            calls=self._calls,
            remaining=self.get_remaining(),
        )

    def flush(self) -> None:
        """Force-persist the current state to disk.

        Call this before shutdown or when accurate persistence is needed.

        Examples
        --------
        >>> limiter.flush()
        """
        if self._dirty > 0:
            self._save_state()
            self._dirty = 0
            logger.debug("Rate limiter state flushed", calls=self._calls)

    def get_remaining(self) -> int:
        """Get the number of remaining API calls for today.

        The remaining count is calculated as::

            max(0, daily_limit - safe_margin - calls)

        Returns
        -------
        int
            Number of remaining API calls (never negative).

        Examples
        --------
        >>> limiter.get_remaining()
        950
        """
        remaining = self.daily_limit - self.safe_margin - self._calls
        return max(0, remaining)

    def is_allowed(self) -> bool:
        """Check whether an API call is allowed.

        Returns
        -------
        bool
            ``True`` if the remaining call count is greater than zero,
            ``False`` otherwise.

        Examples
        --------
        >>> limiter.is_allowed()
        True
        """
        return self.get_remaining() > 0

    def reset_if_new_day(self) -> None:
        """Reset the call counter if the date has changed.

        Compares the stored date with today's date. If they differ,
        resets the call counter to zero, updates the stored date, and
        persists the new state.

        Examples
        --------
        >>> limiter.reset_if_new_day()
        """
        today = date.today().isoformat()
        if self._date != today:
            logger.info(
                "Date changed, resetting rate limit counter",
                old_date=self._date,
                new_date=today,
                old_calls=self._calls,
            )
            self._date = today
            self._calls = 0
            self._dirty = 0
            self._save_state()

    def _load_state(self) -> None:
        """Load the rate limit state from the JSON file.

        If the file does not exist, is empty, contains invalid JSON,
        or has an incomplete schema, the state is initialized with
        today's date and zero calls.

        If the loaded date differs from today, the counter is reset.
        """
        if not self._state_path.exists():
            logger.debug("State file not found, using defaults")
            return

        try:
            raw = self._state_path.read_text(encoding="utf-8")
            if not raw.strip():
                logger.debug("State file is empty, using defaults")
                return

            data = json.loads(raw)

            if "date" not in data or "calls" not in data:
                logger.warning(
                    "State file has incomplete schema, using defaults",
                    keys=list(data.keys()),
                )
                return

            stored_date = data["date"]
            stored_calls = data["calls"]

            today = date.today().isoformat()
            if stored_date == today:
                self._date = stored_date
                self._calls = stored_calls
                logger.debug(
                    "State loaded from file",
                    date=stored_date,
                    calls=stored_calls,
                )
            else:
                logger.info(
                    "Stored date differs from today, resetting counter",
                    stored_date=stored_date,
                    today=today,
                )
                self._date = today
                self._calls = 0
                self._save_state()

        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning(
                "Failed to parse state file, using defaults",
                error=str(exc),
            )

    def _save_state(self) -> None:
        """Persist the current state to the JSON file.

        Writes the current date and call count as a JSON object.
        Creates parent directories if they do not exist.
        """
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"date": self._date, "calls": self._calls}
        self._state_path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )


__all__ = [
    "DailyRateLimiter",
]
