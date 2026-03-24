"""Shared parsing helpers for the NasdaqClient module.

This module provides common parsing utilities used by NasdaqClient endpoint
methods, including:

- ``unwrap_envelope``: Extracts the ``data`` payload from the standard NASDAQ
  API JSON envelope and validates the response code (``status.rCode``).
- ``_safe_get``: Defensive dictionary access with type checking.

The existing ``parser.py`` cleaning functions (``clean_price``,
``clean_percentage``, ``clean_market_cap``, ``clean_volume``) are re-exported
from here for convenient access by endpoint-specific parsers.

See Also
--------
market.nasdaq.parser : Low-level cleaning functions for numeric columns.
market.nasdaq.errors : NasdaqAPIError raised by ``unwrap_envelope``.
market.nasdaq.client : NasdaqClient that delegates to these helpers.
"""

from __future__ import annotations

from typing import Any

from market.nasdaq.errors import NasdaqAPIError, NasdaqParseError
from market.nasdaq.parser import (
    clean_market_cap,
    clean_percentage,
    clean_price,
    clean_volume,
)
from utils_core.logging import get_logger

logger = get_logger(__name__)


def unwrap_envelope(raw: dict[str, Any], url: str) -> dict[str, Any]:
    """Extract the ``data`` payload from a NASDAQ API JSON envelope.

    The standard NASDAQ API response format is::

        {
            "data": { ... },
            "message": null,
            "status": { "rCode": 200, "bCodeMessage": null, ... }
        }

    This function validates that ``status.rCode == 200`` and returns the
    ``data`` dictionary. If ``rCode`` is not 200, a ``NasdaqAPIError`` is
    raised with the status code and response body.

    Parameters
    ----------
    raw : dict[str, Any]
        The full JSON response from a NASDAQ API endpoint.
    url : str
        The URL that produced this response (for error messages).

    Returns
    -------
    dict[str, Any]
        The ``data`` dictionary extracted from the envelope.

    Raises
    ------
    NasdaqAPIError
        If ``status.rCode`` is not 200.
    NasdaqParseError
        If the response does not contain the expected envelope structure
        (missing ``data`` or ``status`` keys).

    Examples
    --------
    >>> raw = {"data": {"quote": {}}, "status": {"rCode": 200}}
    >>> unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/AAPL/info")
    {'quote': {}}

    >>> raw = {"data": None, "status": {"rCode": 400}}
    >>> unwrap_envelope(raw, "https://api.nasdaq.com/api/quote/BAD/info")
    Traceback (most recent call last):
        ...
    market.nasdaq.errors.NasdaqAPIError: ...
    """
    # Validate envelope structure
    status = raw.get("status")
    if not isinstance(status, dict):
        raise NasdaqParseError(
            "Missing or invalid 'status' key in NASDAQ API response",
            raw_data=str(raw)[:500],
            field="status",
        )

    r_code = status.get("rCode")
    if r_code != 200:
        logger.warning(
            "NASDAQ API returned non-200 rCode",
            url=url,
            r_code=r_code,
            status=status,
        )
        raise NasdaqAPIError(
            message=f"NASDAQ API returned rCode {r_code} for {url}",
            url=url,
            status_code=r_code if isinstance(r_code, int) else 0,
            response_body=str(raw)[:1000],
        )

    data = raw.get("data")
    if data is None:
        raise NasdaqParseError(
            "Missing 'data' key in NASDAQ API response",
            raw_data=str(raw)[:500],
            field="data",
        )

    if not isinstance(data, dict):
        raise NasdaqParseError(
            f"Expected 'data' to be a dict, got {type(data).__name__}",
            raw_data=str(raw)[:500],
            field="data",
        )

    logger.debug("Envelope unwrapped successfully", url=url)
    return data


def _safe_get(
    data: dict[str, Any],
    key: str,
    expected_type: type | None = None,
) -> Any:
    """Defensively access a dictionary key with optional type checking.

    Parameters
    ----------
    data : dict[str, Any]
        The dictionary to access.
    key : str
        The key to look up.
    expected_type : type | None
        If provided, validates that the value is an instance of this type.
        Returns ``None`` if the type does not match.

    Returns
    -------
    Any
        The value at ``data[key]``, or ``None`` if the key is missing
        or the type check fails.

    Examples
    --------
    >>> _safe_get({"name": "Apple"}, "name")
    'Apple'

    >>> _safe_get({"name": "Apple"}, "ticker")

    >>> _safe_get({"count": "5"}, "count", expected_type=int)
    """
    value = data.get(key)
    if value is None:
        return None

    if expected_type is not None and not isinstance(value, expected_type):
        logger.debug(
            "Type mismatch in _safe_get",
            key=key,
            expected=expected_type.__name__,
            actual=type(value).__name__,
        )
        return None

    return value


__all__ = [
    "clean_market_cap",
    "clean_percentage",
    "clean_price",
    "clean_volume",
    "unwrap_envelope",
]
