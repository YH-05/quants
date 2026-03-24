"""JSON response parser and numeric cleaning utilities for the NASDAQ Screener API.

This module converts raw JSON responses from the NASDAQ Stock Screener API
into pandas DataFrames with properly typed numeric columns.  It provides:

- **Cleaner factory**: ``_create_cleaner`` for generating type-safe cleaning
  functions with consistent missing-data and error handling.
- **Cleaning functions**: ``clean_price``, ``clean_percentage``,
  ``clean_market_cap``, ``clean_volume``, ``clean_ipo_year`` for converting
  formatted string values (e.g. ``"$1,234.56"``, ``"-0.849%"``) to native
  Python numeric types.
- **Column cleaners**: ``_COLUMN_CLEANERS`` mapping and
  ``_apply_numeric_cleaning`` for DRY application of cleaners to DataFrames.
- **Column name conversion**: ``_camel_to_snake`` for normalising API
  camelCase keys to snake_case.
- **Response parser**: ``parse_screener_response`` for end-to-end
  conversion of the screener JSON payload to a cleaned DataFrame.

All cleaning functions treat empty strings and ``"N/A"`` as missing data,
returning ``None``.  Unknown or malformed formats also return ``None``
with a warning log.

See Also
--------
market.nasdaq.constants : ``COLUMN_NAME_MAP`` used for column renaming.
market.nasdaq.errors : ``NasdaqParseError`` raised on structural failures.
market.nasdaq.types : ``StockRecord`` dataclass for raw row data.
market.etfcom.parser : Reference ``_camel_to_snake`` / ``_normalize_record``.
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import pandas as pd

from market.nasdaq.constants import COLUMN_NAME_MAP
from market.nasdaq.errors import NasdaqParseError
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CAMEL_TO_SNAKE_RE: re.Pattern[str] = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
"""Regex that inserts an underscore before each uppercase letter preceded by
a lowercase letter or digit.  Used by ``_camel_to_snake``."""

_MISSING_VALUES: frozenset[str] = frozenset({"", "N/A", "NA", "n/a"})
"""String values treated as missing data by all cleaning functions."""


def _is_missing(value: str) -> bool:
    """Return ``True`` if *value* should be treated as missing data.

    Parameters
    ----------
    value : str
        The raw string value to check.

    Returns
    -------
    bool
        ``True`` if *value* is in the set of known missing-data sentinels.
    """
    return value.strip() in _MISSING_VALUES


# ---------------------------------------------------------------------------
# Column name conversion
# ---------------------------------------------------------------------------


def _camel_to_snake(name: str) -> str:
    """Convert a camelCase or concatenated string to snake_case.

    Inserts underscores before each uppercase letter that is preceded by a
    lowercase letter or digit, then lowercases the entire result.

    Parameters
    ----------
    name : str
        camelCase string to convert.

    Returns
    -------
    str
        The snake_case equivalent.

    Examples
    --------
    >>> _camel_to_snake("marketCap")
    'market_cap'
    >>> _camel_to_snake("pctchange")
    'pctchange'
    >>> _camel_to_snake("symbol")
    'symbol'
    """
    return _CAMEL_TO_SNAKE_RE.sub("_", name).lower()


# ---------------------------------------------------------------------------
# Cleaner factory (Wave 2)
# ---------------------------------------------------------------------------


def _create_cleaner[T: (int, float)](
    *,
    converter: Callable[[str], T],
    name: str,
    strip_chars: str = "",
    finite_check: bool = False,
) -> Callable[[str], T | None]:
    """Create a cleaning function that converts string values to numeric types.

    Consolidates the common pattern of missing-value check, character
    stripping, type conversion, optional finiteness check, and error
    handling with warning logging into a single factory.

    Parameters
    ----------
    converter : Callable[[str], T]
        The conversion function (e.g. ``float``, ``int``).
    name : str
        Human-readable name for log messages (e.g. ``"price"``).
    strip_chars : str
        Characters to remove from the raw value before conversion.
        Uses a single ``re.sub`` pass for efficiency (Wave 3).
    finite_check : bool
        If ``True``, reject non-finite float results (inf, -inf, nan).

    Returns
    -------
    Callable[[str], T | None]
        A cleaning function that accepts a raw string and returns
        the converted value or ``None``.
    """
    # Pre-compile regex for strip_chars if any are specified (Wave 3)
    strip_re: re.Pattern[str] | None = None
    if strip_chars:
        escaped = re.escape(strip_chars)
        strip_re = re.compile(f"[{escaped}]")

    def _clean(value: str) -> T | None:
        if _is_missing(value):
            return None

        try:
            cleaned = strip_re.sub("", value).strip() if strip_re else value.strip()
            if not cleaned:
                return None

            if finite_check:
                # For converters that produce float intermediates, check finiteness
                float_result = float(cleaned)
                if not math.isfinite(float_result):
                    logger.warning(
                        f"Failed to parse {name} value",
                        raw_value=value,
                    )
                    return None
                return converter(str(float_result))

            return converter(cleaned)
        except (ValueError, TypeError, OverflowError):
            logger.warning(
                f"Failed to parse {name} value",
                raw_value=value,
            )
            return None

    return _clean


# ---------------------------------------------------------------------------
# Cleaning functions (generated via factory)
# ---------------------------------------------------------------------------


clean_price: Callable[[str], float | None] = _create_cleaner(
    converter=float,
    name="price",
    strip_chars="$,",
    finite_check=True,
)
"""Convert a price string to a float.

Strips leading ``$`` signs and commas before conversion.

Parameters
----------
value : str
    Price string such as ``"$1,234.56"`` or ``"-1.95"``.

Returns
-------
float | None
    The numeric price, or ``None`` if the value is missing or
    cannot be parsed.

Examples
--------
>>> clean_price("$1,234.56")
1234.56
>>> clean_price("-1.95")
-1.95
>>> clean_price("")
>>> clean_price("N/A")
"""

clean_percentage: Callable[[str], float | None] = _create_cleaner(
    converter=float,
    name="percentage",
    strip_chars="%,",
    finite_check=True,
)
"""Convert a percentage string to a float.

Strips trailing ``%`` signs before conversion.  The returned value
is the raw percentage number (e.g. ``-0.849``), **not** divided by 100.

Parameters
----------
value : str
    Percentage string such as ``"-0.849%"`` or ``"1.23%"``.

Returns
-------
float | None
    The numeric percentage, or ``None`` if the value is missing or
    cannot be parsed.

Examples
--------
>>> clean_percentage("-0.849%")
-0.849
>>> clean_percentage("1.23%")
1.23
>>> clean_percentage("")
>>> clean_percentage("N/A")
"""


def _float_to_int(value: str) -> int:
    """Convert a string to int via float to handle decimal values.

    Parameters
    ----------
    value : str
        Numeric string, possibly with a decimal point.

    Returns
    -------
    int
        The integer value.
    """
    return int(float(value))


clean_market_cap: Callable[[str], int | None] = _create_cleaner(
    converter=_float_to_int,
    name="market cap",
    strip_chars="$,",
    finite_check=True,
)
"""Convert a market capitalisation string to an integer.

Strips commas and leading ``$`` signs.  The NASDAQ API typically
returns market cap as a comma-separated integer string
(e.g. ``"3,435,123,456,789"``).

Parameters
----------
value : str
    Market cap string such as ``"3,435,123,456,789"``.

Returns
-------
int | None
    The numeric market cap, or ``None`` if the value is missing or
    cannot be parsed.

Examples
--------
>>> clean_market_cap("3,435,123,456,789")
3435123456789
>>> clean_market_cap("")
>>> clean_market_cap("N/A")
"""

clean_volume: Callable[[str], int | None] = _create_cleaner(
    converter=_float_to_int,
    name="volume",
    strip_chars=",",
    finite_check=True,
)
"""Convert a trading volume string to an integer.

Strips commas from the formatted number string.

Parameters
----------
value : str
    Volume string such as ``"48,123,456"``.

Returns
-------
int | None
    The numeric volume, or ``None`` if the value is missing or
    cannot be parsed.

Examples
--------
>>> clean_volume("48,123,456")
48123456
>>> clean_volume("")
>>> clean_volume("N/A")
"""

clean_ipo_year: Callable[[str], int | None] = _create_cleaner(
    converter=int,
    name="IPO year",
    strip_chars="",
    finite_check=False,
)
"""Convert an IPO year string to an integer.

Parameters
----------
value : str
    Year string such as ``"1980"``.

Returns
-------
int | None
    The numeric year, or ``None`` if the value is missing or
    cannot be parsed.

Examples
--------
>>> clean_ipo_year("1980")
1980
>>> clean_ipo_year("")
>>> clean_ipo_year("N/A")
"""

# ---------------------------------------------------------------------------
# Column cleaner mapping (Wave 1)
# ---------------------------------------------------------------------------

_COLUMN_CLEANERS: dict[str, Callable[[str], int | float | None]] = {
    "last_sale": clean_price,
    "net_change": clean_price,
    "pct_change": clean_percentage,
    "market_cap": clean_market_cap,
    "volume": clean_volume,
    "ipo_year": clean_ipo_year,
}
"""Mapping from snake_case column names to their cleaning functions.

Used by ``_apply_numeric_cleaning`` to apply the correct cleaner
to each numeric column in a single loop iteration.
"""


def _apply_numeric_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """Apply numeric cleaning to all known numeric columns in a DataFrame.

    Iterates over ``_COLUMN_CLEANERS`` and applies each cleaner to its
    corresponding column if present in the DataFrame.  Columns not in
    the DataFrame are silently skipped.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame with string-valued numeric columns.

    Returns
    -------
    pd.DataFrame
        The same DataFrame with numeric columns cleaned in-place.
    """
    for column, cleaner in _COLUMN_CLEANERS.items():
        if column in df.columns:
            df[column] = df[column].apply(
                lambda v, c=cleaner: c(str(v)) if pd.notna(v) else None,
            )
    return df


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def parse_screener_response(response: dict[str, Any]) -> pd.DataFrame:
    """Parse a NASDAQ Screener API JSON response into a cleaned DataFrame.

    Extracts row data from ``response["data"]["table"]["rows"]``, renames
    columns from API keys to snake_case using ``COLUMN_NAME_MAP``, and
    applies numeric cleaning to price, percentage, market cap, volume,
    and IPO year columns.

    Parameters
    ----------
    response : dict[str, Any]
        The raw JSON response from the NASDAQ Screener API.  Expected
        structure::

            {
                "data": {
                    "table": {
                        "rows": [{"symbol": "AAPL", ...}, ...]
                    }
                }
            }

    Returns
    -------
    pd.DataFrame
        A DataFrame with snake_case column names and cleaned numeric
        values.  Columns: ``symbol``, ``name``, ``last_sale``,
        ``net_change``, ``pct_change``, ``market_cap``, ``country``,
        ``ipo_year``, ``volume``, ``sector``, ``industry``, ``url``.

    Raises
    ------
    NasdaqParseError
        If the JSON structure does not match the expected schema
        (missing ``data``, ``table``, or ``rows`` keys, or ``rows``
        is not a list).

    Examples
    --------
    >>> resp = {
    ...     "data": {
    ...         "table": {
    ...             "rows": [
    ...                 {
    ...                     "symbol": "AAPL",
    ...                     "name": "Apple Inc.",
    ...                     "lastsale": "$227.63",
    ...                     "netchange": "-1.95",
    ...                     "pctchange": "-0.849%",
    ...                     "marketCap": "3,435,123,456,789",
    ...                     "country": "United States",
    ...                     "ipoyear": "1980",
    ...                     "volume": "48,123,456",
    ...                     "sector": "Technology",
    ...                     "industry": "Computer Manufacturing",
    ...                     "url": "/market-activity/stocks/aapl",
    ...                 }
    ...             ]
    ...         }
    ...     }
    ... }
    >>> df = parse_screener_response(resp)
    >>> df["symbol"].iloc[0]
    'AAPL'
    >>> df["last_sale"].iloc[0]
    227.63
    """
    logger.debug("Parsing screener response")

    # --- Validate structure ---
    data = response.get("data")
    if not isinstance(data, dict):
        raise NasdaqParseError(
            "Missing or invalid 'data' key in response",
            raw_data=str(response)[:500],
            field="data",
        )

    table = data.get("table")
    if not isinstance(table, dict):
        raise NasdaqParseError(
            "Missing or invalid 'data.table' key in response",
            raw_data=str(data)[:500],
            field="data.table",
        )

    rows = table.get("rows")
    if not isinstance(rows, list):
        raise NasdaqParseError(
            "Missing or invalid 'data.table.rows' key in response",
            raw_data=str(table)[:500],
            field="data.table.rows",
        )

    if not rows:
        logger.info("Screener response contains no rows")
        return pd.DataFrame(
            columns=pd.Index(list(COLUMN_NAME_MAP.values())),
        )

    logger.debug("Parsing screener rows", row_count=len(rows))

    # --- Build DataFrame ---
    df = pd.DataFrame(rows)

    # Rename columns using COLUMN_NAME_MAP
    rename_map: dict[str, str] = {}
    for col in df.columns:
        mapped = COLUMN_NAME_MAP.get(col)
        if mapped is not None:
            rename_map[col] = mapped
        else:
            # Fallback: use _camel_to_snake for unknown columns
            rename_map[col] = _camel_to_snake(col)

    df = df.rename(columns=rename_map)

    # --- Apply numeric cleaning (Wave 1: DRY) ---
    df = _apply_numeric_cleaning(df)

    logger.info(
        "Screener response parsed",
        row_count=len(df),
        columns=list(df.columns),
    )

    return df


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "clean_ipo_year",
    "clean_market_cap",
    "clean_percentage",
    "clean_price",
    "clean_volume",
    "parse_screener_response",
]
