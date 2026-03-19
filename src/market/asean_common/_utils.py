"""Internal utility helpers for asean_common module."""

from __future__ import annotations

import math

import pandas as pd


def _is_nan(value: object) -> bool:
    """Check if a value is NaN (float or numpy NaN).

    Parameters
    ----------
    value : object
        Value to check.

    Returns
    -------
    bool
        True if the value is NaN, False otherwise.
        None returns False (not considered NaN).
    """
    if value is None:
        return False
    try:
        if isinstance(value, float) and math.isnan(value):
            return True
        return bool(pd.isna(value))
    except (ValueError, TypeError):
        return False


def _coerce_optional_str(value: object) -> str | None:
    """Coerce a value to an optional string, handling NaN.

    Parameters
    ----------
    value : object
        Value to coerce.

    Returns
    -------
    str | None
        String representation of the value, or None if NaN/None.
    """
    if value is None or _is_nan(value):
        return None
    return str(value)


def _coerce_optional_int(value: object) -> int | None:
    """Coerce a value to an optional integer, handling NaN.

    Parameters
    ----------
    value : object
        Value to coerce.

    Returns
    -------
    int | None
        Integer value, or None if NaN/None.
    """
    if value is None or _is_nan(value):
        return None
    return int(value)
