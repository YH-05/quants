"""JSON response parser and numeric cleaning utilities for the Alpha Vantage API.

This module converts raw JSON responses from the Alpha Vantage API into
pandas DataFrames or normalized dictionaries. It provides:

- **7 parse functions**: ``parse_time_series``, ``parse_global_quote``,
  ``parse_company_overview``, ``parse_financial_statements``,
  ``parse_earnings``, ``parse_economic_indicator``, ``parse_forex_rate``
- **3 internal helpers**:
  - ``_detect_time_series_key``: whitelist-based key detection for time series data
  - ``_normalize_ohlcv_columns``: ``'1. open'`` -> ``'open'`` normalization
  - ``_clean_numeric``: string -> float conversion with missing-data handling

Alpha Vantage response keys use number prefixes (``'1. open'``, ``'2. high'``)
that need normalization before data analysis. The parser handles this
transparently.

See Also
--------
market.nasdaq.parser : Reference implementation for cleaner factory pattern.
market.alphavantage.errors : AlphaVantageParseError raised on structural failures.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from market.alphavantage.constants import MAX_RESPONSE_BODY_LOG
from market.alphavantage.errors import AlphaVantageParseError
from utils_core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regex for removing number prefixes: '1. open' -> 'open', '10. change percent' -> 'change percent'
_NUMBER_PREFIX_RE: re.Pattern[str] = re.compile(r"^\d+\.\s*")

# Whitelist of known time series keys in Alpha Vantage responses
_TIME_SERIES_KEY_WHITELIST: frozenset[str] = frozenset(
    {
        "Time Series (Daily)",
        "Time Series (Weekly)",
        "Time Series (Monthly)",
        "Weekly Time Series",
        "Weekly Adjusted Time Series",
        "Monthly Time Series",
        "Monthly Adjusted Time Series",
        # Intraday intervals
        "Time Series (1min)",
        "Time Series (5min)",
        "Time Series (15min)",
        "Time Series (30min)",
        "Time Series (60min)",
    }
)

# Numeric fields in company overview that should be converted to float
_OVERVIEW_NUMERIC_FIELDS: frozenset[str] = frozenset(
    {
        "MarketCapitalization",
        "EBITDA",
        "PERatio",
        "PEGRatio",
        "BookValue",
        "DividendPerShare",
        "DividendYield",
        "EPS",
        "52WeekHigh",
        "52WeekLow",
        "50DayMovingAverage",
        "200DayMovingAverage",
        "SharesOutstanding",
        "RevenuePerShareTTM",
        "ProfitMargin",
        "OperatingMarginTTM",
        "ReturnOnAssetsTTM",
        "ReturnOnEquityTTM",
        "RevenueTTM",
        "GrossProfitTTM",
        "DilutedEPSTTM",
        "QuarterlyEarningsGrowthYOY",
        "QuarterlyRevenueGrowthYOY",
        "AnalystTargetPrice",
        "AnalystRatingStrongBuy",
        "AnalystRatingBuy",
        "AnalystRatingHold",
        "AnalystRatingSell",
        "AnalystRatingStrongSell",
        "TrailingPE",
        "ForwardPE",
        "PriceToSalesRatioTTM",
        "PriceToBookRatio",
        "EVToRevenue",
        "EVToEBITDA",
        "Beta",
    }
)

# Missing data sentinel values used by Alpha Vantage
_MISSING_VALUES: frozenset[str] = frozenset({"None", "-", "", "none", "N/A"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_numeric(value: str) -> float | None:
    """Convert a string value to float, handling AV missing-data sentinels.

    Alpha Vantage uses ``'None'``, ``'-'``, and empty strings to represent
    missing data in its JSON responses.

    Parameters
    ----------
    value : str
        The raw string value from the Alpha Vantage JSON response.

    Returns
    -------
    float | None
        The numeric value, or ``None`` if the value is missing or
        cannot be parsed.

    Examples
    --------
    >>> _clean_numeric("228.5000")
    228.5
    >>> _clean_numeric("None")
    >>> _clean_numeric("-")
    >>> _clean_numeric("")
    """
    stripped = value.strip()

    if stripped in _MISSING_VALUES:
        return None

    try:
        return float(stripped)
    except (ValueError, TypeError):
        logger.warning(
            "Failed to parse numeric value",
            raw_value=value,
        )
        return None


def _normalize_ohlcv_columns(data: dict[str, str]) -> dict[str, str]:
    """Remove number prefixes from Alpha Vantage response keys.

    Converts keys like ``'1. open'`` to ``'open'`` and ``'5. volume'``
    to ``'volume'`` using a regex pattern. Keys without number prefixes
    are kept unchanged.

    The normalization is idempotent: applying it twice yields the same
    result as applying it once.

    Parameters
    ----------
    data : dict[str, str]
        Raw key-value pairs from an Alpha Vantage response.

    Returns
    -------
    dict[str, str]
        Dictionary with normalized keys.

    Examples
    --------
    >>> _normalize_ohlcv_columns({"1. open": "228.5", "2. high": "232.1"})
    {'open': '228.5', 'high': '232.1'}
    >>> _normalize_ohlcv_columns({"open": "228.5"})
    {'open': '228.5'}
    """
    return {_NUMBER_PREFIX_RE.sub("", key): value for key, value in data.items()}


def _detect_time_series_key(data: dict[str, Any]) -> str | None:
    """Detect the time series data key in an Alpha Vantage response.

    Uses a whitelist approach to find the key containing the time series
    data. This is necessary because Alpha Vantage uses different key names
    for different time series functions (daily, weekly, monthly, intraday).

    Parameters
    ----------
    data : dict[str, Any]
        The raw Alpha Vantage API response as a dictionary.

    Returns
    -------
    str | None
        The detected time series key, or ``None`` if no known key is found.

    Examples
    --------
    >>> _detect_time_series_key({"Meta Data": {}, "Time Series (Daily)": {}})
    'Time Series (Daily)'
    >>> _detect_time_series_key({"Meta Data": {}, "unrelated": {}})
    """
    for key in data:
        if key in _TIME_SERIES_KEY_WHITELIST:
            return key
    return None


# ---------------------------------------------------------------------------
# Parse functions
# ---------------------------------------------------------------------------


def parse_time_series(data: dict[str, Any]) -> pd.DataFrame:
    """Parse an Alpha Vantage time series response into a DataFrame.

    Automatically detects the time series key (daily, weekly, monthly,
    intraday) using a whitelist, normalizes column names by removing
    number prefixes, and converts numeric values to float.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage time series JSON response.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: ``date``, ``open``, ``high``, ``low``,
        ``close``, ``volume`` (and any additional columns in the response).
        Rows are sorted by date descending.

    Raises
    ------
    AlphaVantageParseError
        If no time series key is found in the response.

    Examples
    --------
    >>> df = parse_time_series(response_dict)
    >>> df.columns.tolist()
    ['date', 'open', 'high', 'low', 'close', 'volume']
    """
    logger.debug("Parsing time series response")

    ts_key = _detect_time_series_key(data)
    if ts_key is None:
        raise AlphaVantageParseError(
            "No time series key found in response. "
            f"Expected one of: {sorted(_TIME_SERIES_KEY_WHITELIST)}",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field="time_series_key",
        )

    ts_data = data[ts_key]
    if not ts_data:
        logger.info("Time series data is empty")
        return pd.DataFrame(
            columns=pd.Index(["date", "open", "high", "low", "close", "volume"]),
        )

    # Build rows as strings, then vectorized numeric conversion
    rows: list[dict[str, Any]] = []
    for date_str, values in ts_data.items():
        normalized = _normalize_ohlcv_columns(values)
        row: dict[str, Any] = {"date": date_str}
        for col_name, col_value in normalized.items():
            row[col_name] = str(col_value).strip()
        rows.append(row)

    df = pd.DataFrame(rows)
    # Vectorized numeric conversion (avoid per-cell _clean_numeric calls)
    numeric_cols = [c for c in df.columns if c != "date"]
    for col in numeric_cols:
        df[col] = df[col].replace(list(_MISSING_VALUES), pd.NA)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(
        "Time series parsed",
        row_count=len(df),
        columns=list(df.columns),
        time_series_key=ts_key,
    )

    return df


def parse_global_quote(data: dict[str, Any]) -> dict[str, Any]:
    """Parse an Alpha Vantage GLOBAL_QUOTE response into a normalized dict.

    Removes number prefixes from keys (e.g., ``'01. symbol'`` -> ``'symbol'``)
    and converts numeric values to float.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage GLOBAL_QUOTE JSON response.

    Returns
    -------
    dict[str, Any]
        Normalized dictionary with cleaned keys and numeric values.

    Raises
    ------
    AlphaVantageParseError
        If the ``Global Quote`` key is missing.

    Examples
    --------
    >>> result = parse_global_quote(response_dict)
    >>> result["symbol"]
    'AAPL'
    >>> result["price"]
    230.5
    """
    logger.debug("Parsing global quote response")

    if "Global Quote" not in data:
        raise AlphaVantageParseError(
            "Missing 'Global Quote' key in response",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field="Global Quote",
        )

    raw_quote = data["Global Quote"]
    normalized = _normalize_ohlcv_columns(raw_quote)

    # Convert numeric values
    result: dict[str, Any] = {}
    for key, value in normalized.items():
        str_value = str(value)
        # Try to clean as percent (strip % sign)
        if str_value.endswith("%"):
            cleaned = _clean_numeric(str_value.rstrip("%"))
            result[key] = cleaned if cleaned is not None else str_value
        else:
            cleaned = _clean_numeric(str_value)
            result[key] = cleaned if cleaned is not None else str_value

    logger.info("Global quote parsed", keys=list(result.keys()))
    return result


def parse_company_overview(data: dict[str, Any]) -> dict[str, Any]:
    """Parse an Alpha Vantage OVERVIEW response into a dict with numeric conversions.

    Converts known numeric fields (market cap, PE ratio, EPS, etc.) to float
    while preserving string fields (symbol, name, description, etc.) as-is.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage OVERVIEW JSON response.

    Returns
    -------
    dict[str, Any]
        Dictionary with numeric fields converted to float and string
        fields preserved.

    Raises
    ------
    AlphaVantageParseError
        If the response is empty or missing the ``Symbol`` key.

    Examples
    --------
    >>> result = parse_company_overview(response_dict)
    >>> result["Symbol"]
    'AAPL'
    >>> isinstance(result["MarketCapitalization"], float)
    True
    """
    logger.debug("Parsing company overview response")

    if not data or "Symbol" not in data:
        raise AlphaVantageParseError(
            "Missing 'Symbol' key in overview response",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field="Symbol",
        )

    result: dict[str, Any] = {}
    for key, value in data.items():
        if key in _OVERVIEW_NUMERIC_FIELDS:
            cleaned = _clean_numeric(str(value))
            result[key] = cleaned if cleaned is not None else value
        else:
            result[key] = value

    logger.info("Company overview parsed", symbol=result.get("Symbol"))
    return result


def parse_financial_statements(
    data: dict[str, Any],
    report_type: str = "annualReports",
) -> pd.DataFrame:
    """Parse Alpha Vantage financial statement responses into a DataFrame.

    Supports INCOME_STATEMENT, BALANCE_SHEET, and CASH_FLOW endpoints.
    Each endpoint returns both annual and quarterly reports.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage financial statement JSON response.
    report_type : str
        Which report type to extract: ``'annualReports'`` or
        ``'quarterlyReports'`` (default: ``'annualReports'``).

    Returns
    -------
    pd.DataFrame
        DataFrame with financial statement data. Columns vary by endpoint.

    Raises
    ------
    AlphaVantageParseError
        If the specified report type key is not found in the response.

    Examples
    --------
    >>> df = parse_financial_statements(response_dict, report_type="annualReports")
    >>> "fiscalDateEnding" in df.columns
    True
    """
    logger.debug("Parsing financial statements", report_type=report_type)

    valid_report_types = {"annualReports", "quarterlyReports"}
    if report_type not in valid_report_types:
        raise AlphaVantageParseError(
            f"Invalid report_type '{report_type}'. "
            f"Expected one of: {sorted(valid_report_types)}",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field=report_type,
        )

    if report_type not in data:
        raise AlphaVantageParseError(
            f"Missing '{report_type}' key in response",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field=report_type,
        )

    reports = data[report_type]
    if not reports:
        logger.info("Financial statements data is empty", report_type=report_type)
        return pd.DataFrame()

    # Build DataFrame from raw reports, then vectorized numeric conversion
    df = pd.DataFrame(reports)
    non_numeric_cols = {"fiscalDateEnding", "reportedCurrency"}
    numeric_cols = [c for c in df.columns if c not in non_numeric_cols]
    for col in numeric_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace(list(_MISSING_VALUES), pd.NA)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(
        "Financial statements parsed",
        report_type=report_type,
        row_count=len(df),
    )
    return df


def parse_earnings(data: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse an Alpha Vantage EARNINGS response into annual and quarterly DataFrames.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage EARNINGS JSON response.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        A tuple of (annual_earnings, quarterly_earnings) DataFrames.

    Raises
    ------
    AlphaVantageParseError
        If the required earnings keys are not found in the response.

    Examples
    --------
    >>> annual, quarterly = parse_earnings(response_dict)
    >>> "reportedEPS" in annual.columns
    True
    """
    logger.debug("Parsing earnings response")

    if "annualEarnings" not in data and "quarterlyEarnings" not in data:
        raise AlphaVantageParseError(
            "Missing 'annualEarnings' and 'quarterlyEarnings' keys in response",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field="annualEarnings/quarterlyEarnings",
        )

    # Parse annual earnings with vectorized numeric conversion
    annual_data = data.get("annualEarnings", [])
    if annual_data:
        annual_df = pd.DataFrame(annual_data)
        annual_non_numeric = {"fiscalDateEnding"}
        annual_numeric_cols = [
            c for c in annual_df.columns if c not in annual_non_numeric
        ]
        for col in annual_numeric_cols:
            annual_df[col] = annual_df[col].astype(str).str.strip()
            annual_df[col] = annual_df[col].replace(list(_MISSING_VALUES), pd.NA)
            annual_df[col] = pd.to_numeric(annual_df[col], errors="coerce")
    else:
        annual_df = pd.DataFrame()

    # Parse quarterly earnings with vectorized numeric conversion
    quarterly_data = data.get("quarterlyEarnings", [])
    if quarterly_data:
        quarterly_df = pd.DataFrame(quarterly_data)
        quarterly_non_numeric = {"fiscalDateEnding", "reportedDate"}
        quarterly_numeric_cols = [
            c for c in quarterly_df.columns if c not in quarterly_non_numeric
        ]
        for col in quarterly_numeric_cols:
            quarterly_df[col] = quarterly_df[col].astype(str).str.strip()
            quarterly_df[col] = quarterly_df[col].replace(list(_MISSING_VALUES), pd.NA)
            quarterly_df[col] = pd.to_numeric(quarterly_df[col], errors="coerce")
    else:
        quarterly_df = pd.DataFrame()

    logger.info(
        "Earnings parsed",
        annual_count=len(annual_df),
        quarterly_count=len(quarterly_df),
    )
    return annual_df, quarterly_df


def parse_economic_indicator(data: dict[str, Any]) -> pd.DataFrame:
    """Parse an Alpha Vantage economic indicator response into a DataFrame.

    Supports endpoints like REAL_GDP, CPI, INFLATION, UNEMPLOYMENT, etc.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage economic indicator JSON response.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: ``date``, ``value``.

    Raises
    ------
    AlphaVantageParseError
        If the ``data`` key is missing from the response.

    Examples
    --------
    >>> df = parse_economic_indicator(response_dict)
    >>> df.columns.tolist()
    ['date', 'value']
    """
    logger.debug("Parsing economic indicator response")

    if "data" not in data:
        raise AlphaVantageParseError(
            "Missing 'data' key in economic indicator response",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field="data",
        )

    raw_data_points = data["data"]
    if not raw_data_points:
        logger.info("Economic indicator data is empty")
        return pd.DataFrame(columns=pd.Index(["date", "value"]))

    # Build DataFrame from raw data, then vectorized numeric conversion
    df = pd.DataFrame(raw_data_points)
    if "value" in df.columns:
        df["value"] = df["value"].astype(str).str.strip()
        df["value"] = df["value"].replace(list(_MISSING_VALUES), pd.NA)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    logger.info(
        "Economic indicator parsed",
        row_count=len(df),
        name=data.get("name", "unknown"),
    )
    return df


def parse_forex_rate(data: dict[str, Any]) -> dict[str, Any]:
    """Parse an Alpha Vantage CURRENCY_EXCHANGE_RATE response into a normalized dict.

    Removes number prefixes from keys and converts numeric values to float.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage CURRENCY_EXCHANGE_RATE JSON response.

    Returns
    -------
    dict[str, Any]
        Normalized dictionary with cleaned keys and numeric values.

    Raises
    ------
    AlphaVantageParseError
        If the ``Realtime Currency Exchange Rate`` key is missing.

    Examples
    --------
    >>> result = parse_forex_rate(response_dict)
    >>> "Exchange Rate" in result or "exchange_rate" in result
    True
    """
    logger.debug("Parsing forex rate response")

    key = "Realtime Currency Exchange Rate"
    if key not in data:
        raise AlphaVantageParseError(
            f"Missing '{key}' key in response",
            raw_data=str(data)[:MAX_RESPONSE_BODY_LOG],
            field=key,
        )

    raw_rate = data[key]
    normalized = _normalize_ohlcv_columns(raw_rate)

    # Convert numeric values where possible
    result: dict[str, Any] = {}
    for norm_key, value in normalized.items():
        str_value = str(value)
        cleaned = _clean_numeric(str_value)
        result[norm_key] = cleaned if cleaned is not None else str_value

    logger.info("Forex rate parsed", keys=list(result.keys()))
    return result


# ---------------------------------------------------------------------------
# Keyed time series helpers (FX, Crypto)
# ---------------------------------------------------------------------------


def _parse_keyed_time_series(
    data: dict[str, Any],
    data_key: str,
    default_columns: list[str],
) -> pd.DataFrame:
    """Parse a time series response using a specific data key.

    This is a shared helper for FX and Crypto endpoints that use
    non-standard time series keys not in the standard whitelist.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage JSON response.
    data_key : str
        The key containing the time series data
        (e.g. ``'Time Series FX (Daily)'``).
    default_columns : list[str]
        Column names for the empty DataFrame fallback.

    Returns
    -------
    pd.DataFrame
        DataFrame with date column and numeric columns.
    """
    ts_data = data.get(data_key, {})

    if not ts_data:
        logger.info("Time series data is empty", data_key=data_key)
        return pd.DataFrame(columns=pd.Index(["date", *default_columns]))

    rows: list[dict[str, Any]] = []
    for date_str, values in ts_data.items():
        normalized = _normalize_ohlcv_columns(values)
        row: dict[str, Any] = {"date": date_str}
        for col_name, col_value in normalized.items():
            row[col_name] = str(col_value).strip()
        rows.append(row)

    df = pd.DataFrame(rows)
    # Vectorized numeric conversion (avoid per-cell _clean_numeric calls)
    numeric_cols = [c for c in df.columns if c != "date"]
    for col in numeric_cols:
        df[col] = df[col].replace(list(_MISSING_VALUES), pd.NA)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    logger.info("Keyed time series parsed", data_key=data_key, row_count=len(df))
    return df


def parse_fx_time_series(data: dict[str, Any]) -> pd.DataFrame:
    """Parse an Alpha Vantage FX_DAILY response into a DataFrame.

    FX_DAILY uses ``'Time Series FX (Daily)'`` as the data key,
    which is not in the standard time series whitelist.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage FX_DAILY JSON response.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: date, open, high, low, close.

    Examples
    --------
    >>> df = parse_fx_time_series(fx_response)
    >>> "open" in df.columns
    True
    """
    return _parse_keyed_time_series(
        data,
        data_key="Time Series FX (Daily)",
        default_columns=["open", "high", "low", "close"],
    )


def parse_crypto_time_series(data: dict[str, Any]) -> pd.DataFrame:
    """Parse an Alpha Vantage DIGITAL_CURRENCY_DAILY response into a DataFrame.

    Crypto daily uses ``'Time Series (Digital Currency Daily)'`` as
    the data key.

    Parameters
    ----------
    data : dict[str, Any]
        Raw Alpha Vantage crypto daily JSON response.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: date, open, high, low, close, volume.

    Examples
    --------
    >>> df = parse_crypto_time_series(crypto_response)
    >>> "close" in df.columns
    True
    """
    return _parse_keyed_time_series(
        data,
        data_key="Time Series (Digital Currency Daily)",
        default_columns=["open", "high", "low", "close", "volume"],
    )


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "parse_company_overview",
    "parse_crypto_time_series",
    "parse_earnings",
    "parse_economic_indicator",
    "parse_financial_statements",
    "parse_forex_rate",
    "parse_fx_time_series",
    "parse_global_quote",
    "parse_time_series",
]
