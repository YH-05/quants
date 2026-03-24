"""Shared parsing helpers for the NasdaqClient module.

This module provides common parsing utilities used by NasdaqClient endpoint
methods, including:

- ``unwrap_envelope``: Extracts the ``data`` payload from the standard NASDAQ
  API JSON envelope and validates the response code (``status.rCode``).
- ``_safe_get``: Defensive dictionary access with type checking.
- ``parse_earnings_calendar``: Parses earnings calendar endpoint data.
- ``parse_dividends_calendar``: Parses dividends calendar endpoint data.
- ``parse_splits_calendar``: Parses stock splits calendar endpoint data.
- ``parse_ipo_calendar``: Parses IPO calendar endpoint data.

The existing ``parser.py`` cleaning functions (``clean_price``,
``clean_percentage``, ``clean_market_cap``, ``clean_volume``) are re-exported
from here for convenient access by endpoint-specific parsers.

See Also
--------
market.nasdaq.parser : Low-level cleaning functions for numeric columns.
market.nasdaq.errors : NasdaqAPIError raised by ``unwrap_envelope``.
market.nasdaq.client : NasdaqClient that delegates to these helpers.
market.nasdaq.client_types : Record dataclasses produced by calendar parsers.
"""

from __future__ import annotations

from typing import Any

from market.nasdaq.client_types import (
    DividendCalendarRecord,
    EarningsRecord,
    EtfRecord,
    IpoRecord,
    MarketMover,
    MoverSection,
    SplitRecord,
)
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


def _extract_rows(
    data: dict[str, Any],
    *keys: str,
) -> list[dict[str, Any]]:
    """Extract a ``rows`` list from a possibly nested data structure.

    Traverses *keys* one level at a time (e.g. ``"calendar", "rows"``),
    returning ``[]`` if any intermediate key is missing or ``None``,
    and raising ``NasdaqParseError`` if ``rows`` is present but is not
    a ``list``.

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload.
    *keys : str
        Path of keys to traverse.  The last key is expected to hold a
        ``list[dict]``.

    Returns
    -------
    list[dict[str, Any]]
        The extracted rows, or an empty list when the path does not exist.

    Raises
    ------
    NasdaqParseError
        If the final value exists but is not a ``list``.
    """
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
        if current is None:
            return []

    if not isinstance(current, list):
        raise NasdaqParseError(
            f"Expected '{keys[-1]}' to be a list, got {type(current).__name__}",
            raw_data=str(current)[:500],
            field=".".join(keys),
        )

    return current


# ---------------------------------------------------------------------------
# Calendar parsers
# ---------------------------------------------------------------------------


def parse_earnings_calendar(data: dict[str, Any]) -> list[EarningsRecord]:
    """Parse earnings calendar endpoint data into ``EarningsRecord`` list.

    Expected structure::

        {
            "rows": [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "date": "01/30/2026",
                    "epsEstimate": "$2.35",
                    "epsActual": "$2.40",
                    "surprise": "2.13%",
                    "fiscalQuarterEnding": "Dec/2025",
                    "marketCap": "3,435,123,456,789"
                }, ...
            ]
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the earnings calendar endpoint.

    Returns
    -------
    list[EarningsRecord]
        Parsed earnings records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "rows")
    if not rows:
        logger.debug("No earnings calendar rows to parse")
        return []

    logger.debug("Parsing earnings calendar rows", row_count=len(rows))

    result: list[EarningsRecord] = []
    for row in rows:
        record = EarningsRecord(
            symbol=row.get("symbol", ""),
            name=row.get("name"),
            date=row.get("date"),
            eps_estimate=row.get("epsEstimate"),
            eps_actual=row.get("epsActual"),
            surprise=row.get("surprise"),
            fiscal_quarter_ending=row.get("fiscalQuarterEnding"),
            market_cap=row.get("marketCap"),
        )
        result.append(record)

    logger.info("Earnings calendar parsed", record_count=len(result))
    return result


def parse_dividends_calendar(
    data: dict[str, Any],
) -> list[DividendCalendarRecord]:
    """Parse dividends calendar endpoint data into ``DividendCalendarRecord`` list.

    Expected structure::

        {
            "calendar": {
                "rows": [
                    {
                        "symbol": "AAPL",
                        "companyName": "Apple Inc.",
                        "dividend_Ex_Date": "02/07/2026",
                        "payment_Date": "02/13/2026",
                        "record_Date": "02/10/2026",
                        "dividend_Rate": "$0.25",
                        "indicated_Annual_Dividend": "$1.00"
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the dividends calendar endpoint.

    Returns
    -------
    list[DividendCalendarRecord]
        Parsed dividend records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``calendar.rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "calendar", "rows")
    if not rows:
        logger.debug("No dividends calendar rows to parse")
        return []

    logger.debug("Parsing dividends calendar rows", row_count=len(rows))

    result: list[DividendCalendarRecord] = []
    for row in rows:
        record = DividendCalendarRecord(
            symbol=row.get("symbol", ""),
            company_name=row.get("companyName"),
            ex_date=row.get("dividend_Ex_Date"),
            payment_date=row.get("payment_Date"),
            record_date=row.get("record_Date"),
            dividend_rate=row.get("dividend_Rate"),
            annual_dividend=row.get("indicated_Annual_Dividend"),
        )
        result.append(record)

    logger.info("Dividends calendar parsed", record_count=len(result))
    return result


def parse_splits_calendar(data: dict[str, Any]) -> list[SplitRecord]:
    """Parse stock splits calendar endpoint data into ``SplitRecord`` list.

    Expected structure::

        {
            "rows": [
                {
                    "symbol": "NVDA",
                    "name": "NVIDIA Corporation",
                    "executionDate": "06/10/2024",
                    "ratio": "10:1",
                    "optionable": "Y"
                }, ...
            ]
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the splits calendar endpoint.

    Returns
    -------
    list[SplitRecord]
        Parsed split records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "rows")
    if not rows:
        logger.debug("No splits calendar rows to parse")
        return []

    logger.debug("Parsing splits calendar rows", row_count=len(rows))

    result: list[SplitRecord] = []
    for row in rows:
        record = SplitRecord(
            symbol=row.get("symbol", ""),
            name=row.get("name"),
            execution_date=row.get("executionDate"),
            ratio=row.get("ratio"),
            optionable=row.get("optionable"),
        )
        result.append(record)

    logger.info("Splits calendar parsed", record_count=len(result))
    return result


def parse_ipo_calendar(data: dict[str, Any]) -> list[IpoRecord]:
    """Parse IPO calendar endpoint data into ``IpoRecord`` list.

    The IPO calendar endpoint contains multiple sections (``priced``,
    ``upcoming``, ``filed``).  This parser extracts rows from the first
    non-empty section found, in the order ``priced`` > ``upcoming`` > ``filed``.

    Expected structure::

        {
            "priced": {
                "rows": [
                    {
                        "dealID": "123456",
                        "proposedTickerSymbol": "NEWCO",
                        "companyName": "NewCo Inc.",
                        "proposedExchange": "NASDAQ",
                        "proposedSharePrice": "$15.00-$17.00",
                        "sharesOffered": "10,000,000"
                    }, ...
                ]
            },
            "upcoming": { "rows": [...] },
            "filed": { "rows": [...] }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the IPO calendar endpoint.

    Returns
    -------
    list[IpoRecord]
        Parsed IPO records, or an empty list if no rows are present
        in any section.

    Raises
    ------
    NasdaqParseError
        If ``rows`` in any section exists but is not a list.
    """
    all_rows: list[dict[str, Any]] = []
    for section in ("priced", "upcoming", "filed"):
        section_rows = _extract_rows(data, section, "rows")
        all_rows.extend(section_rows)

    if not all_rows:
        logger.debug("No IPO calendar rows to parse")
        return []

    logger.debug("Parsing IPO calendar rows", row_count=len(all_rows))

    result: list[IpoRecord] = []
    for row in all_rows:
        record = IpoRecord(
            deal_id=row.get("dealID"),
            symbol=row.get("proposedTickerSymbol"),
            company_name=row.get("companyName"),
            exchange=row.get("proposedExchange"),
            share_price=row.get("proposedSharePrice"),
            shares_offered=row.get("sharesOffered"),
        )
        result.append(record)

    logger.info("IPO calendar parsed", record_count=len(result))
    return result


# ---------------------------------------------------------------------------
# Market Movers parser
# ---------------------------------------------------------------------------

_MOVER_SECTION_KEYS: dict[str, MoverSection] = {
    "MostAdvanced": MoverSection.MOST_ADVANCED,
    "MostDeclined": MoverSection.MOST_DECLINED,
    "MostActive": MoverSection.MOST_ACTIVE,
}
"""Mapping from NASDAQ API section keys to ``MoverSection`` enum values."""


def parse_market_movers(
    data: dict[str, Any],
) -> dict[str, list[MarketMover]]:
    """Parse market movers endpoint data into a section-keyed dictionary.

    Expected structure::

        {
            "MostAdvanced": {
                "rows": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "lastSale": "$230.00",
                        "netChange": "5.00",
                        "percentageChange": "2.22%",
                        "volume": "48,123,456"
                    }, ...
                ]
            },
            "MostDeclined": { "rows": [...] },
            "MostActive": { "rows": [...] }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the market movers endpoint.

    Returns
    -------
    dict[str, list[MarketMover]]
        A dictionary keyed by ``MoverSection`` value strings
        (``"most_advanced"``, ``"most_declined"``, ``"most_active"``),
        each mapping to a list of ``MarketMover`` records.

    Raises
    ------
    NasdaqParseError
        If ``rows`` in any section exists but is not a list.
    """
    result: dict[str, list[MarketMover]] = {}

    for api_key, section in _MOVER_SECTION_KEYS.items():
        rows = _extract_rows(data, api_key, "rows")
        movers: list[MarketMover] = []
        for row in rows:
            record = MarketMover(
                symbol=row.get("symbol", ""),
                name=row.get("name"),
                price=row.get("lastSale"),
                change=row.get("netChange"),
                change_percent=row.get("percentageChange"),
                volume=row.get("volume"),
            )
            movers.append(record)
        result[section.value] = movers

    total = sum(len(v) for v in result.values())
    if total == 0:
        logger.debug("No market movers rows to parse")
    else:
        logger.info("Market movers parsed", total_records=total)

    return result


# ---------------------------------------------------------------------------
# ETF Screener parser
# ---------------------------------------------------------------------------


def parse_etf_screener(data: dict[str, Any]) -> list[EtfRecord]:
    """Parse ETF screener endpoint data into ``EtfRecord`` list.

    Expected structure::

        {
            "table": {
                "rows": [
                    {
                        "symbol": "SPY",
                        "name": "SPDR S&P 500 ETF Trust",
                        "lastsale": "$590.50",
                        "netchange": "-2.30",
                        "pctchange": "-0.39%",
                        "volume": "48,123,456",
                        "country": "United States",
                        "sector": "",
                        "industry": "",
                        "url": "/market-activity/funds-and-etfs/spy"
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the ETF screener endpoint.

    Returns
    -------
    list[EtfRecord]
        Parsed ETF records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``table.rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "table", "rows")
    if not rows:
        logger.debug("No ETF screener rows to parse")
        return []

    logger.debug("Parsing ETF screener rows", row_count=len(rows))

    result: list[EtfRecord] = []
    for row in rows:
        record = EtfRecord(
            symbol=row.get("symbol", ""),
            name=row.get("name"),
            last_sale=row.get("lastsale"),
            net_change=row.get("netchange"),
            pct_change=row.get("pctchange"),
            volume=row.get("volume"),
            country=row.get("country"),
            sector=row.get("sector"),
            industry=row.get("industry"),
            url=row.get("url"),
        )
        result.append(record)

    logger.info("ETF screener parsed", record_count=len(result))
    return result


__all__ = [
    "clean_market_cap",
    "clean_percentage",
    "clean_price",
    "clean_volume",
    "parse_dividends_calendar",
    "parse_earnings_calendar",
    "parse_etf_screener",
    "parse_ipo_calendar",
    "parse_market_movers",
    "parse_splits_calendar",
    "unwrap_envelope",
]
