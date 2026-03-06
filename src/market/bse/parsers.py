"""BSE API response parsers and numeric cleaning utilities.

This module converts raw JSON responses from the BSE India API and
historical CSV content into typed dataclasses and pandas DataFrames.

It provides:

- **Cleaner factory**: ``_create_cleaner`` for generating type-safe cleaning
  functions with consistent missing-data and error handling.
- **Cleaning functions**: ``clean_price``, ``clean_volume``,
  ``clean_indian_number`` for converting BSE-formatted string values
  (including Indian numbering with lakhs/crores) to native Python numeric
  types.
- **Response parser**: ``parse_quote_response`` for converting a BSE
  getScripHeaderData JSON payload to a ``ScripQuote`` dataclass.
- **CSV parser**: ``parse_historical_csv`` for converting BSE historical
  CSV content to a cleaned pandas DataFrame.
- **Corporate parsers**: ``parse_company_info``, ``parse_financial_results``,
  ``parse_announcements``, ``parse_corporate_actions`` for converting BSE
  corporate data JSON payloads to typed dicts and dataclasses.

All cleaning functions treat empty strings and ``"N/A"`` as missing data,
returning ``None``.  Unknown or malformed formats also return ``None``
with a warning log.

See Also
--------
market.nasdaq.parser : Similar parser pattern for the NASDAQ module.
market.bse.constants : ``COLUMN_NAME_MAP`` used for column renaming.
market.bse.errors : ``BseParseError`` raised on structural failures.
market.bse.types : ``ScripQuote``, ``FinancialResult``, ``Announcement``,
    ``CorporateAction`` dataclasses for BSE data.
"""

from __future__ import annotations

import io
import math
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import pandas as pd

from market.bse.constants import (
    BHAVCOPY_COLUMN_NAME_MAP,
    COLUMN_NAME_MAP,
    INDEX_COLUMN_NAME_MAP,
)
from market.bse.errors import BseParseError
from market.bse.types import Announcement, CorporateAction, FinancialResult, ScripQuote
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MISSING_VALUES: frozenset[str] = frozenset({"", "N/A", "NA", "n/a", "-"})
"""String values treated as missing data by all cleaning functions."""

_INDIAN_NUMBER_RE: re.Pattern[str] = re.compile(
    r"^[+-]?\d{1,2}(?:,\d{2})*(?:,\d{3})(?:\.\d+)?$"
)
"""Regex for Indian numbering format (lakhs/crores).

Indian format groups digits as: X,XX,XX,XXX (e.g., 1,23,45,678).
The last group is always 3 digits, preceding groups are 2 digits.
"""


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
# Cleaner factory
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
    finite_check : bool
        If ``True``, reject non-finite float results (inf, -inf, nan).

    Returns
    -------
    Callable[[str], T | None]
        A cleaning function that accepts a raw string and returns
        the converted value or ``None``.
    """
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


clean_price: Callable[[str], float | None] = _create_cleaner(
    converter=float,
    name="price",
    strip_chars=",",
    finite_check=True,
)
"""Convert a BSE price string to a float.

Strips commas before conversion. BSE prices do not use currency symbols
in API responses.

Parameters
----------
value : str
    Price string such as ``"2,450.00"`` or ``"-1.95"``.

Returns
-------
float | None
    The numeric price, or ``None`` if the value is missing or
    cannot be parsed.

Examples
--------
>>> clean_price("2,450.00")
2450.0
>>> clean_price("-1.95")
-1.95
>>> clean_price("")
>>> clean_price("N/A")
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
    Volume string such as ``"48,123,456"`` or ``"5000000"``.

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


def clean_indian_number(value: str) -> float | None:
    """Convert an Indian-formatted number string (lakhs/crores) to a float.

    Indian numbering uses the format ``X,XX,XX,XXX`` where the last group
    is 3 digits and preceding groups are 2 digits.  For example:

    - ``"1,23,456"`` = 1,23,456 (1 lakh 23 thousand 456)
    - ``"12,34,56,789"`` = 12,34,56,789 (12 crore 34 lakh 56 thousand 789)

    Also handles standard comma-separated numbers and plain numbers.

    Parameters
    ----------
    value : str
        Number string in Indian or standard format.

    Returns
    -------
    float | None
        The numeric value, or ``None`` if the value is missing or
        cannot be parsed.

    Examples
    --------
    >>> clean_indian_number("1,23,456")
    123456.0
    >>> clean_indian_number("12,34,56,789")
    123456789.0
    >>> clean_indian_number("1234.56")
    1234.56
    >>> clean_indian_number("")
    >>> clean_indian_number("N/A")
    """
    if _is_missing(value):
        return None

    stripped = value.strip()
    if not stripped:
        return None

    try:
        # Remove all commas (works for both Indian and standard formats)
        cleaned = stripped.replace(",", "")
        result = float(cleaned)
        if not math.isfinite(result):
            logger.warning(
                "Failed to parse Indian number value",
                raw_value=value,
            )
            return None
        return result
    except (ValueError, TypeError, OverflowError):
        logger.warning(
            "Failed to parse Indian number value",
            raw_value=value,
        )
        return None


# ---------------------------------------------------------------------------
# Column cleaner mapping
# ---------------------------------------------------------------------------

_COLUMN_CLEANERS: dict[str, Callable[[str], int | float | None]] = {
    "open": clean_price,
    "high": clean_price,
    "low": clean_price,
    "close": clean_price,
    "last": clean_price,
    "prev_close": clean_price,
    "num_trades": clean_volume,
    "num_shares": clean_volume,
    "net_turnover": clean_indian_number,
}
"""Mapping from snake_case column names to their cleaning functions.

Used by ``_apply_numeric_cleaning`` to apply the correct cleaner
to each numeric column in a single loop iteration.
"""


def _apply_numeric_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """Apply numeric cleaning to all known numeric columns in a DataFrame.

    Iterates over ``_COLUMN_CLEANERS`` and applies each cleaner to its
    corresponding column if present in the DataFrame.

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
# Quote response parser
# ---------------------------------------------------------------------------


def parse_quote_response(raw: dict[str, Any]) -> ScripQuote:
    """Parse a BSE getScripHeaderData JSON response into a ScripQuote.

    The BSE API returns quote data with PascalCase keys. This function
    extracts the relevant fields and maps them to a ``ScripQuote`` dataclass.

    Parameters
    ----------
    raw : dict[str, Any]
        The raw JSON response from the BSE API's ``getScripHeaderData``
        endpoint.  Expected keys include ``"ScripCode"``, ``"ScripName"``,
        ``"Open"``, ``"High"``, ``"Low"``, ``"Close"``, etc.

    Returns
    -------
    ScripQuote
        A frozen dataclass containing the parsed quote data.

    Raises
    ------
    BseParseError
        If the response is empty, not a dict, or missing required fields.

    Examples
    --------
    >>> raw = {
    ...     "ScripCode": "500325",
    ...     "ScripName": "RELIANCE INDUSTRIES LTD",
    ...     "ScripGroup": "A",
    ...     "Open": "2450.00",
    ...     "High": "2480.50",
    ...     "Low": "2440.00",
    ...     "Close": "2470.25",
    ...     "last": "2469.90",
    ...     "PrevClose": "2445.00",
    ...     "No_Trades": "125000",
    ...     "No_of_Shrs": "5000000",
    ...     "Net_Turnov": "12345678900",
    ... }
    >>> quote = parse_quote_response(raw)
    >>> quote.scrip_code
    '500325'
    """
    logger.debug("Parsing quote response")

    # Validate input
    if not isinstance(raw, dict):
        raise BseParseError(
            f"Expected dict for quote response, got {type(raw).__name__}",
            raw_data=str(raw)[:500],
            field=None,
        )

    if not raw:
        raise BseParseError(
            "Empty quote response",
            raw_data=str(raw)[:500],
            field=None,
        )

    # Map API keys to ScripQuote field names using COLUMN_NAME_MAP
    # Required API keys for ScripQuote
    _required_api_keys = {
        "ScripCode",
        "ScripName",
        "ScripGroup",
        "Open",
        "High",
        "Low",
        "Close",
        "last",
        "PrevClose",
        "No_Trades",
        "No_of_Shrs",
        "Net_Turnov",
    }

    missing_keys = _required_api_keys - set(raw.keys())
    if missing_keys:
        raise BseParseError(
            f"Missing required keys in quote response: {sorted(missing_keys)}",
            raw_data=str(raw)[:500],
            field=", ".join(sorted(missing_keys)),
        )

    quote = ScripQuote(
        scrip_code=str(raw["ScripCode"]),
        scrip_name=str(raw["ScripName"]),
        scrip_group=str(raw["ScripGroup"]),
        open=str(raw["Open"]),
        high=str(raw["High"]),
        low=str(raw["Low"]),
        close=str(raw["Close"]),
        last=str(raw["last"]),
        prev_close=str(raw["PrevClose"]),
        num_trades=str(raw["No_Trades"]),
        num_shares=str(raw["No_of_Shrs"]),
        net_turnover=str(raw["Net_Turnov"]),
    )

    logger.info(
        "Quote response parsed",
        scrip_code=quote.scrip_code,
        scrip_name=quote.scrip_name,
    )

    return quote


# ---------------------------------------------------------------------------
# Historical CSV parser
# ---------------------------------------------------------------------------


def parse_historical_csv(content: str | bytes) -> pd.DataFrame:
    """Parse BSE historical CSV content into a cleaned pandas DataFrame.

    Reads CSV content (as returned by BSE download endpoints), renames
    columns from BSE API names to snake_case using ``COLUMN_NAME_MAP``,
    and applies numeric cleaning to price and volume columns.

    Parameters
    ----------
    content : str | bytes
        The raw CSV content from a BSE historical data download.
        Can be a string or bytes (utf-8 decoded automatically).

    Returns
    -------
    pd.DataFrame
        A DataFrame with snake_case column names and cleaned numeric
        values.

    Raises
    ------
    BseParseError
        If the CSV content cannot be parsed or is empty.

    Examples
    --------
    >>> csv_content = (
    ...     "ScripCode,ScripName,Open,High,Low,Close\\n"
    ...     "500325,RELIANCE,2450.00,2480.50,2440.00,2470.25\\n"
    ... )
    >>> df = parse_historical_csv(csv_content)
    >>> df["scrip_code"].iloc[0]
    '500325'
    """
    logger.debug("Parsing historical CSV")

    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError:
                content = content.decode("latin-1")

    if not content.strip():
        raise BseParseError(
            "Empty CSV content",
            raw_data=None,
            field=None,
        )

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        raise BseParseError(
            f"Failed to parse CSV: {e}",
            raw_data=content[:500] if len(content) > 500 else content,
            field=None,
        ) from e

    if df.empty:
        logger.info("Historical CSV contains no rows")
        return df

    # Strip whitespace from column names
    df.columns = pd.Index([col.strip() for col in df.columns])

    # Rename columns using COLUMN_NAME_MAP
    rename_map: dict[str, str] = {}
    for col in df.columns:
        mapped = COLUMN_NAME_MAP.get(col)
        if mapped is not None:
            rename_map[col] = mapped
        else:
            # Fallback: lowercase with underscores
            rename_map[col] = col.strip().lower().replace(" ", "_")

    df = df.rename(columns=rename_map)

    # Strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda v: v.strip() if isinstance(v, str) else v,
            )

    # Apply numeric cleaning
    df = _apply_numeric_cleaning(df)

    logger.info(
        "Historical CSV parsed",
        row_count=len(df),
        columns=list(df.columns),
    )

    return df


# ---------------------------------------------------------------------------
# Bhavcopy CSV parser
# ---------------------------------------------------------------------------


def parse_bhavcopy_csv(content: str | bytes) -> pd.DataFrame:
    """Parse BSE Bhavcopy (daily market data) CSV into a cleaned DataFrame.

    Bhavcopy files use uppercase column names (``SC_CODE``, ``SC_NAME``, etc.)
    which differ from the historical CSV format.  This function decodes the
    content, renames columns to snake_case using ``BHAVCOPY_COLUMN_NAME_MAP``,
    strips whitespace, and applies numeric cleaning.

    Parameters
    ----------
    content : str | bytes
        The raw CSV content from a BSE Bhavcopy download.
        Can be a string or bytes (utf-8 decoded automatically).

    Returns
    -------
    pd.DataFrame
        A DataFrame with snake_case column names and cleaned numeric
        values.

    Raises
    ------
    BseParseError
        If the CSV content cannot be parsed or is empty.

    Examples
    --------
    >>> csv_content = (
    ...     "SC_CODE,SC_NAME,OPEN,HIGH,LOW,CLOSE\\n"
    ...     "500325,RELIANCE,2450.00,2480.50,2440.00,2470.25\\n"
    ... )
    >>> df = parse_bhavcopy_csv(csv_content)
    >>> df["scrip_code"].iloc[0]
    '500325'
    """
    logger.debug("Parsing Bhavcopy CSV")

    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError:
                content = content.decode("latin-1")

    if not content.strip():
        raise BseParseError(
            "Empty Bhavcopy CSV content",
            raw_data=None,
            field=None,
        )

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        raise BseParseError(
            f"Failed to parse Bhavcopy CSV: {e}",
            raw_data=content[:500] if len(content) > 500 else content,
            field=None,
        ) from e

    if df.empty:
        logger.info("Bhavcopy CSV contains no rows")
        return df

    # Strip whitespace from column names
    df.columns = pd.Index([col.strip() for col in df.columns])

    # Rename columns using BHAVCOPY_COLUMN_NAME_MAP
    rename_map: dict[str, str] = {}
    for col in df.columns:
        mapped = BHAVCOPY_COLUMN_NAME_MAP.get(col)
        if mapped is not None:
            rename_map[col] = mapped
        else:
            # Fallback: lowercase with underscores
            rename_map[col] = col.strip().lower().replace(" ", "_")

    df = df.rename(columns=rename_map)

    # Strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda v: v.strip() if isinstance(v, str) else v,
            )

    # Apply numeric cleaning
    df = _apply_numeric_cleaning(df)

    logger.info(
        "Bhavcopy CSV parsed",
        row_count=len(df),
        columns=list(df.columns),
    )

    return df


# ---------------------------------------------------------------------------
# Index data parser
# ---------------------------------------------------------------------------


def parse_index_data(raw: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse BSE index historical data JSON into a cleaned pandas DataFrame.

    The BSE Index API returns a JSON array of objects with keys like
    ``I_open``, ``I_high``, ``I_low``, ``I_close``, ``Tdate``, etc.
    This function renames columns to snake_case using
    ``INDEX_COLUMN_NAME_MAP``, parses date strings, and applies numeric
    cleaning to price columns.

    Parameters
    ----------
    raw : list[dict[str, Any]]
        The raw JSON array from the BSE Index API endpoint.
        Each dict represents one trading day with keys such as
        ``"I_open"``, ``"I_high"``, ``"I_low"``, ``"I_close"``,
        ``"Tdate"`` (or ``"TDate"``).

    Returns
    -------
    pd.DataFrame
        A DataFrame with snake_case column names (``open``, ``high``,
        ``low``, ``close``, ``date``, etc.) and cleaned numeric values.
        The ``date`` column is converted to ``datetime64[ns]``.

    Raises
    ------
    BseParseError
        If the input is not a list, is empty, or cannot be parsed.

    Examples
    --------
    >>> raw = [
    ...     {
    ...         "I_open": "73800.50",
    ...         "I_high": "74200.00",
    ...         "I_low": "73500.25",
    ...         "I_close": "74100.75",
    ...         "Tdate": "2026-03-05T00:00:00",
    ...     }
    ... ]
    >>> df = parse_index_data(raw)
    >>> df["close"].iloc[0]
    74100.75
    """
    logger.debug("Parsing index data")

    if not isinstance(raw, list):
        raise BseParseError(
            f"Expected list for index data, got {type(raw).__name__}",
            raw_data=str(raw)[:500],
            field=None,
        )

    if not raw:
        raise BseParseError(
            "Empty index data response",
            raw_data=str(raw)[:500],
            field=None,
        )

    try:
        df = pd.DataFrame(raw)
    except Exception as e:
        raise BseParseError(
            f"Failed to create DataFrame from index data: {e}",
            raw_data=str(raw)[:500],
            field=None,
        ) from e

    if df.empty:
        logger.info("Index data contains no rows")
        return df

    # Rename columns using INDEX_COLUMN_NAME_MAP
    rename_map: dict[str, str] = {}
    for col in df.columns:
        mapped = INDEX_COLUMN_NAME_MAP.get(col)
        if mapped is not None:
            rename_map[col] = mapped
        else:
            rename_map[col] = col.strip().lower().replace(" ", "_")

    df = df.rename(columns=rename_map)

    # Parse date column
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Apply numeric cleaning to price columns
    _index_price_columns = ("open", "high", "low", "close", "pe", "pb", "yield")
    for col in _index_price_columns:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v, c=clean_price: c(str(v)) if pd.notna(v) else None,
            )

    logger.info(
        "Index data parsed",
        row_count=len(df),
        columns=list(df.columns),
    )

    return df


# ---------------------------------------------------------------------------
# Corporate data parsers
# ---------------------------------------------------------------------------


def parse_company_info(raw: dict[str, Any]) -> dict[str, str | None]:
    """Parse a BSE company info JSON response into a normalised dictionary.

    The BSE API returns company information with PascalCase keys. This
    function extracts the relevant fields and maps them to snake_case keys.

    Parameters
    ----------
    raw : dict[str, Any]
        The raw JSON response from the BSE API's company info endpoint.
        Expected keys include ``"scrip_cd"``, ``"SCRIP_CD"``,
        ``"compname"``, ``"COMPNAME"``, ``"ISIN_NUMBER"``, ``"Scrip_grp"``,
        ``"INDUSTRY"``, ``"Mktcap"``, ``"Facevalue"``, etc.

    Returns
    -------
    dict[str, str | None]
        A dictionary containing normalised company info with keys:
        ``scrip_code``, ``company_name``, ``isin``, ``scrip_group``,
        ``industry``, ``market_cap``, ``face_value``.

    Raises
    ------
    BseParseError
        If the response is empty, not a dict, or missing critical fields.

    Examples
    --------
    >>> raw = {
    ...     "scrip_cd": "500325",
    ...     "compname": "RELIANCE INDUSTRIES LTD",
    ...     "ISIN_NUMBER": "INE002A01018",
    ...     "Scrip_grp": "A",
    ...     "INDUSTRY": "Refineries",
    ...     "Mktcap": "1800000",
    ...     "Facevalue": "10.00",
    ... }
    >>> info = parse_company_info(raw)
    >>> info["scrip_code"]
    '500325'
    """
    logger.debug("Parsing company info response")

    if not isinstance(raw, dict):
        raise BseParseError(
            f"Expected dict for company info, got {type(raw).__name__}",
            raw_data=str(raw)[:500],
            field=None,
        )

    if not raw:
        raise BseParseError(
            "Empty company info response",
            raw_data=str(raw)[:500],
            field=None,
        )

    # BSE API uses inconsistent casing; try multiple key variants
    def _get(keys: list[str]) -> str | None:
        for k in keys:
            val = raw.get(k)
            if val is not None:
                return str(val).strip() or None
        return None

    scrip_code = _get(["scrip_cd", "SCRIP_CD", "ScripCode", "scripcode"])
    company_name = _get(["compname", "COMPNAME", "ScripName", "scripname"])

    if scrip_code is None and company_name is None:
        raise BseParseError(
            "Missing both scrip_code and company_name in company info",
            raw_data=str(raw)[:500],
            field="scrip_cd, compname",
        )

    info: dict[str, str | None] = {
        "scrip_code": scrip_code,
        "company_name": company_name,
        "isin": _get(["ISIN_NUMBER", "isin_number", "ISIN"]),
        "scrip_group": _get(["Scrip_grp", "scrip_grp", "ScripGroup"]),
        "industry": _get(["INDUSTRY", "industry", "Industry"]),
        "market_cap": _get(["Mktcap", "mktcap", "MarketCap"]),
        "face_value": _get(["Facevalue", "facevalue", "FaceValue"]),
    }

    logger.info(
        "Company info parsed",
        scrip_code=scrip_code,
        company_name=company_name,
    )

    return info


def parse_financial_results(
    raw: list[dict[str, Any]],
) -> list[FinancialResult]:
    """Parse BSE financial results JSON into a list of FinancialResult.

    The BSE API returns financial results as a JSON array of objects
    with keys like ``"scrip_cd"``, ``"companyname"``, ``"cons_prd_to"``,
    ``"cons_revenue"``, ``"cons_netpnl"``, ``"cons_eps"``.

    Parameters
    ----------
    raw : list[dict[str, Any]]
        The raw JSON array from the BSE financial results endpoint.
        Each dict represents one financial period.

    Returns
    -------
    list[FinancialResult]
        A list of ``FinancialResult`` frozen dataclasses.

    Raises
    ------
    BseParseError
        If the input is not a list.

    Examples
    --------
    >>> raw = [
    ...     {
    ...         "scrip_cd": "500325",
    ...         "companyname": "RELIANCE INDUSTRIES LTD",
    ...         "cons_prd_to": "31-Mar-2025",
    ...         "cons_revenue": "250000",
    ...         "cons_netpnl": "18500",
    ...         "cons_eps": "27.35",
    ...     }
    ... ]
    >>> results = parse_financial_results(raw)
    >>> results[0].scrip_code
    '500325'
    """
    logger.debug("Parsing financial results")

    if not isinstance(raw, list):
        raise BseParseError(
            f"Expected list for financial results, got {type(raw).__name__}",
            raw_data=str(raw)[:500],
            field=None,
        )

    if not raw:
        logger.info("Financial results response is empty")
        return []

    results: list[FinancialResult] = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning(
                "Skipping non-dict item in financial results",
                item_type=type(item).__name__,
            )
            continue

        result = FinancialResult(
            scrip_code=str(item.get("scrip_cd", item.get("SCRIP_CD", ""))).strip(),
            scrip_name=str(
                item.get(
                    "companyname",
                    item.get("COMPANYNAME", item.get("ScripName", "")),
                )
            ).strip(),
            period_ended=str(
                item.get(
                    "cons_prd_to",
                    item.get("CONS_PRD_TO", item.get("prd_to", "")),
                )
            ).strip(),
            revenue=str(
                item.get(
                    "cons_revenue",
                    item.get("CONS_REVENUE", item.get("revenue", "")),
                )
            ).strip(),
            net_profit=str(
                item.get(
                    "cons_netpnl",
                    item.get("CONS_NETPNL", item.get("netpnl", "")),
                )
            ).strip(),
            eps=str(
                item.get(
                    "cons_eps",
                    item.get("CONS_EPS", item.get("eps", "")),
                )
            ).strip(),
        )
        results.append(result)

    logger.info(
        "Financial results parsed",
        count=len(results),
    )

    return results


def parse_announcements(
    raw: list[dict[str, Any]],
) -> list[Announcement]:
    """Parse BSE announcements JSON into a list of Announcement.

    The BSE API returns announcements as a JSON array of objects
    with keys like ``"SCRIP_CD"``, ``"SLONGNAME"``, ``"HEADLINE"``,
    ``"DT_TM"``, ``"CATEGORYNAME"``.

    Parameters
    ----------
    raw : list[dict[str, Any]]
        The raw JSON array from the BSE announcements endpoint.
        Each dict represents one corporate announcement.

    Returns
    -------
    list[Announcement]
        A list of ``Announcement`` frozen dataclasses.

    Raises
    ------
    BseParseError
        If the input is not a list.

    Examples
    --------
    >>> raw = [
    ...     {
    ...         "SCRIP_CD": "500325",
    ...         "SLONGNAME": "RELIANCE INDUSTRIES LTD",
    ...         "HEADLINE": "Board Meeting Outcome",
    ...         "DT_TM": "15-Jan-2025",
    ...         "CATEGORYNAME": "Board Meeting",
    ...     }
    ... ]
    >>> announcements = parse_announcements(raw)
    >>> announcements[0].subject
    'Board Meeting Outcome'
    """
    logger.debug("Parsing announcements")

    if not isinstance(raw, list):
        raise BseParseError(
            f"Expected list for announcements, got {type(raw).__name__}",
            raw_data=str(raw)[:500],
            field=None,
        )

    if not raw:
        logger.info("Announcements response is empty")
        return []

    announcements: list[Announcement] = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning(
                "Skipping non-dict item in announcements",
                item_type=type(item).__name__,
            )
            continue

        ann = Announcement(
            scrip_code=str(item.get("SCRIP_CD", item.get("scrip_cd", ""))).strip(),
            scrip_name=str(
                item.get(
                    "SLONGNAME",
                    item.get("slongname", item.get("ScripName", "")),
                )
            ).strip(),
            subject=str(
                item.get(
                    "HEADLINE",
                    item.get("headline", item.get("NEWS_SUBJECT", "")),
                )
            ).strip(),
            announcement_date=str(
                item.get(
                    "DT_TM",
                    item.get("dt_tm", item.get("NEWS_DT", "")),
                )
            ).strip(),
            category=str(
                item.get(
                    "CATEGORYNAME",
                    item.get("categoryname", item.get("CAT_NAME", "")),
                )
            ).strip(),
        )
        announcements.append(ann)

    logger.info(
        "Announcements parsed",
        count=len(announcements),
    )

    return announcements


def parse_corporate_actions(
    raw: list[dict[str, Any]],
) -> list[CorporateAction]:
    """Parse BSE corporate actions JSON into a list of CorporateAction.

    The BSE API returns corporate actions as a JSON array of objects
    with keys like ``"scrip_code"``, ``"comp_name"``, ``"ex_dt"``,
    ``"PURPOSE"``, ``"Record_dt"``.

    Parameters
    ----------
    raw : list[dict[str, Any]]
        The raw JSON array from the BSE corporate actions endpoint.
        Each dict represents one corporate action.

    Returns
    -------
    list[CorporateAction]
        A list of ``CorporateAction`` frozen dataclasses.

    Raises
    ------
    BseParseError
        If the input is not a list.

    Examples
    --------
    >>> raw = [
    ...     {
    ...         "scrip_code": "500325",
    ...         "comp_name": "RELIANCE INDUSTRIES LTD",
    ...         "ex_dt": "01-Feb-2025",
    ...         "PURPOSE": "Dividend - Rs 8 Per Share",
    ...         "Record_dt": "03-Feb-2025",
    ...     }
    ... ]
    >>> actions = parse_corporate_actions(raw)
    >>> actions[0].purpose
    'Dividend - Rs 8 Per Share'
    """
    logger.debug("Parsing corporate actions")

    if not isinstance(raw, list):
        raise BseParseError(
            f"Expected list for corporate actions, got {type(raw).__name__}",
            raw_data=str(raw)[:500],
            field=None,
        )

    if not raw:
        logger.info("Corporate actions response is empty")
        return []

    actions: list[CorporateAction] = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning(
                "Skipping non-dict item in corporate actions",
                item_type=type(item).__name__,
            )
            continue

        action = CorporateAction(
            scrip_code=str(item.get("scrip_code", item.get("SCRIP_CODE", ""))).strip(),
            scrip_name=str(
                item.get(
                    "comp_name",
                    item.get("COMP_NAME", item.get("ScripName", "")),
                )
            ).strip(),
            ex_date=str(item.get("ex_dt", item.get("EX_DT", ""))).strip(),
            purpose=str(item.get("PURPOSE", item.get("purpose", ""))).strip(),
            record_date=str(item.get("Record_dt", item.get("RECORD_DT", ""))).strip(),
        )
        actions.append(action)

    logger.info(
        "Corporate actions parsed",
        count=len(actions),
    )

    return actions


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "clean_indian_number",
    "clean_price",
    "clean_volume",
    "parse_announcements",
    "parse_bhavcopy_csv",
    "parse_company_info",
    "parse_corporate_actions",
    "parse_financial_results",
    "parse_historical_csv",
    "parse_index_data",
    "parse_quote_response",
]
