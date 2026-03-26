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
    AnalystRatings,
    DividendCalendarRecord,
    DividendRecord,
    EarningsDate,
    EarningsForecast,
    EarningsForecastPeriod,
    EarningsRecord,
    EtfRecord,
    FinancialStatement,
    FinancialStatementRow,
    InsiderTrade,
    InstitutionalHolding,
    IpoRecord,
    MarketMover,
    MoverSection,
    RatingCount,
    ShortInterestRecord,
    SplitRecord,
    TargetPrice,
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

    Expected structure (past date with actual EPS)::

        {
            "rows": [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "eps": "$2.40",
                    "surprise": "1.69",
                    "time": "time-not-supplied",
                    "fiscalQuarterEnding": "Dec/2024",
                    "epsForecast": "$2.36",
                    "noOfEsts": "11",
                    "marketCap": "$3,640,775,908,600"
                }, ...
            ]
        }

    Expected structure (future date without actual EPS)::

        {
            "rows": [
                {
                    "symbol": "GME",
                    "name": "GameStop Corporation",
                    "lastYearRptDt": "N/A",
                    "lastYearEPS": "$0.30",
                    "time": "time-after-hours",
                    "fiscalQuarterEnding": "Jan/2026",
                    "epsForecast": "",
                    "noOfEsts": "1",
                    "marketCap": "$10,111,573,964"
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

    result = [
        EarningsRecord(
            symbol=row.get("symbol", ""),
            name=row.get("name"),
            date=row.get("date"),
            eps_estimate=row.get("epsForecast"),
            eps_actual=row.get("eps"),
            surprise=row.get("surprise"),
            fiscal_quarter_ending=row.get("fiscalQuarterEnding"),
            market_cap=row.get("marketCap"),
            time=row.get("time"),
            no_of_ests=row.get("noOfEsts"),
            last_year_rpt_dt=row.get("lastYearRptDt"),
            last_year_eps=row.get("lastYearEPS"),
        )
        for row in rows
    ]

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

    result = [
        DividendCalendarRecord(
            symbol=row.get("symbol", ""),
            company_name=row.get("companyName"),
            ex_date=row.get("dividend_Ex_Date"),
            payment_date=row.get("payment_Date"),
            record_date=row.get("record_Date"),
            dividend_rate=row.get("dividend_Rate"),
            annual_dividend=row.get("indicated_Annual_Dividend"),
        )
        for row in rows
    ]

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

    result = [
        SplitRecord(
            symbol=row.get("symbol", ""),
            name=row.get("name"),
            execution_date=row.get("executionDate"),
            ratio=row.get("ratio"),
            optionable=row.get("optionable"),
        )
        for row in rows
    ]

    logger.info("Splits calendar parsed", record_count=len(result))
    return result


def parse_ipo_calendar(data: dict[str, Any]) -> list[IpoRecord]:
    """Parse IPO calendar endpoint data into ``IpoRecord`` list.

    The IPO calendar endpoint contains multiple sections (``priced``,
    ``upcoming``, ``filed``).  This parser collects and concatenates rows
    from all three sections and returns them as a single list.

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

    result = [
        IpoRecord(
            deal_id=row.get("dealID"),
            symbol=row.get("proposedTickerSymbol"),
            company_name=row.get("companyName"),
            exchange=row.get("proposedExchange"),
            share_price=row.get("proposedSharePrice"),
            shares_offered=row.get("sharesOffered"),
        )
        for row in all_rows
    ]

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
"""Mapping from NASDAQ API section keys to ``MoverSection`` enum values.

The new API also uses ``MostActiveByShareVolume`` as an alias for
``MostActive``, handled via ``_MOVER_SECTION_KEY_ALIASES``.
"""

_MOVER_SECTION_KEY_ALIASES: dict[str, str] = {
    "MostActiveByShareVolume": "MostActive",
}
"""Aliases for mover section keys in the new API format."""


def parse_market_movers(
    data: dict[str, Any],
) -> dict[str, list[MarketMover]]:
    """Parse market movers endpoint data into a section-keyed dictionary.

    Supports both old flat structure and new nested structure::

        Old: ``{ "MostAdvanced": { "rows": [...] }, ... }``
        New: ``{ "STOCKS": { "MostAdvanced": { "table": { "rows": [...] } }, ... } }``

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

    # New API nests under "STOCKS" -> section -> "table" -> "rows"
    stocks = data.get("STOCKS")
    source = stocks if isinstance(stocks, dict) else data

    for api_key, section in _MOVER_SECTION_KEYS.items():
        # Try new structure: section -> table -> rows
        section_data = source.get(api_key)
        if section_data is None:
            # Try alias (e.g. MostActiveByShareVolume -> MostActive)
            for alias, canonical in _MOVER_SECTION_KEY_ALIASES.items():
                if canonical == api_key:
                    section_data = source.get(alias)
                    if section_data is not None:
                        break

        if isinstance(section_data, dict) and "table" in section_data:
            rows = _extract_rows(section_data, "table", "rows")
        else:
            # Fallback to old structure: section -> rows
            rows = _extract_rows(source, api_key, "rows")

        movers = [
            MarketMover(
                symbol=row.get("symbol", ""),
                name=row.get("name"),
                price=row.get("lastSalePrice") or row.get("lastSale"),
                change=row.get("lastSaleChange") or row.get("netChange"),
                change_percent=row.get("percentageChange"),
                volume=row.get("change") or row.get("volume"),
            )
            for row in rows
        ]
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

    Supports both old and new API structures::

        Old: ``{ "table": { "rows": [...] } }``
        New: ``{ "records": { "data": { "rows": [...] } } }``

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
        If rows exist but are not a list.
    """
    # Try new structure: records -> data -> rows
    rows = _extract_rows(data, "records", "data", "rows")
    if not rows:
        # Fallback to old structure: table -> rows
        rows = _extract_rows(data, "table", "rows")

    if not rows:
        logger.debug("No ETF screener rows to parse")
        return []

    logger.debug("Parsing ETF screener rows", row_count=len(rows))

    result = [
        EtfRecord(
            symbol=row.get("symbol", ""),
            name=row.get("companyName") or row.get("name"),
            last_sale=row.get("lastSalePrice") or row.get("lastsale"),
            net_change=row.get("netChange") or row.get("netchange"),
            pct_change=row.get("percentageChange") or row.get("pctchange"),
            volume=row.get("volume"),
            country=row.get("country"),
            sector=row.get("sector"),
            industry=row.get("industry"),
            url=row.get("url"),
        )
        for row in rows
    ]

    logger.info("ETF screener parsed", record_count=len(result))
    return result


# ---------------------------------------------------------------------------
# Analyst parsers
# ---------------------------------------------------------------------------


def _parse_forecast_rows(
    rows: list[dict[str, Any]],
) -> list[EarningsForecastPeriod]:
    """Parse a list of forecast period rows into ``EarningsForecastPeriod`` list.

    Parameters
    ----------
    rows : list[dict[str, Any]]
        Raw rows from the forecast endpoint.

    Returns
    -------
    list[EarningsForecastPeriod]
        Parsed forecast periods.
    """
    return [
        EarningsForecastPeriod(
            fiscal_end=row.get("fiscalEnd"),
            consensus_eps_forecast=row.get("consensusEPSForecast"),
            num_of_estimates=row.get("numOfEstimates"),
            high_eps_forecast=row.get("highEPSForecast"),
            low_eps_forecast=row.get("lowEPSForecast"),
        )
        for row in rows
    ]


def parse_earnings_forecast(
    data: dict[str, Any],
    symbol: str,
) -> EarningsForecast:
    """Parse earnings forecast endpoint data into ``EarningsForecast``.

    Expected structure::

        {
            "yearlyForecast": {
                "rows": [
                    {
                        "fiscalEnd": "Dec 2025",
                        "consensusEPSForecast": "$6.70",
                        "numOfEstimates": "38",
                        "highEPSForecast": "$7.10",
                        "lowEPSForecast": "$6.30"
                    }, ...
                ]
            },
            "quarterlyForecast": {
                "rows": [
                    {
                        "fiscalEnd": "Q1 2026",
                        "consensusEPSForecast": "$2.35",
                        "numOfEstimates": "28",
                        "highEPSForecast": "$2.60",
                        "lowEPSForecast": "$2.10"
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the forecast endpoint.
    symbol : str
        The ticker symbol for this forecast.

    Returns
    -------
    EarningsForecast
        Parsed earnings forecast with yearly and quarterly periods.
    """
    yearly_rows = _extract_rows(data, "yearlyForecast", "rows")
    quarterly_rows = _extract_rows(data, "quarterlyForecast", "rows")

    yearly = _parse_forecast_rows(yearly_rows)
    quarterly = _parse_forecast_rows(quarterly_rows)

    logger.info(
        "Earnings forecast parsed",
        symbol=symbol,
        yearly_count=len(yearly),
        quarterly_count=len(quarterly),
    )
    return EarningsForecast(symbol=symbol, yearly=yearly, quarterly=quarterly)


def _to_str(value: Any) -> str | None:
    """Convert a value to string, returning None for None values.

    Used to normalize numeric API values (e.g. ``350.0``) into
    string form for consistency with dataclass field types.

    Parameters
    ----------
    value : Any
        Value to convert.

    Returns
    -------
    str | None
        String representation, or ``None`` if value is ``None``.
    """
    if value is None:
        return None
    return str(value)


def _safe_int(value: Any) -> int:
    """Convert a value to int, returning 0 for non-convertible values.

    Parameters
    ----------
    value : Any
        Value to convert.

    Returns
    -------
    int
        Integer value, or 0 if conversion fails.
    """
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def parse_analyst_ratings(
    data: dict[str, Any],
    symbol: str,
) -> AnalystRatings:
    """Parse analyst ratings endpoint data into ``AnalystRatings``.

    Supports both legacy structure (per-period rating breakdowns) and
    new structure (mean rating + summary)::

        Legacy: ``{ "ratings": [ { "date": "...", "strongBuy": 10, ... } ] }``
        New:    ``{ "meanRatingType": "Buy", "ratingsSummary": "Based on..." }``

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the ratings endpoint.
    symbol : str
        The ticker symbol for these ratings.

    Returns
    -------
    AnalystRatings
        Parsed analyst ratings with history (legacy) or mean rating (new).
    """
    # Try legacy structure first
    rows = _extract_rows(data, "ratings")
    if rows:
        logger.debug("Parsing analyst ratings rows (legacy)", row_count=len(rows))

        result = [
            RatingCount(
                date=row.get("date"),
                strong_buy=_safe_int(row.get("strongBuy")),
                buy=_safe_int(row.get("buy")),
                hold=_safe_int(row.get("hold")),
                sell=_safe_int(row.get("sell")),
                strong_sell=_safe_int(row.get("strongSell")),
            )
            for row in rows
        ]

        logger.info(
            "Analyst ratings parsed", symbol=symbol, rating_count=len(result)
        )
        return AnalystRatings(symbol=symbol, ratings=result)

    # New structure: extract mean rating info
    mean_rating = data.get("meanRatingType")
    summary = data.get("ratingsSummary")

    if mean_rating is not None or summary is not None:
        logger.info(
            "Analyst ratings parsed (new format)",
            symbol=symbol,
            mean_rating=mean_rating,
        )
        return AnalystRatings(
            symbol=symbol,
            ratings=[],
            mean_rating=_to_str(mean_rating),
            summary=_to_str(summary),
        )

    logger.debug("No analyst ratings data to parse", symbol=symbol)
    return AnalystRatings(symbol=symbol, ratings=[])


def parse_target_price(
    data: dict[str, Any],
    symbol: str,
) -> TargetPrice:
    """Parse target price endpoint data into ``TargetPrice``.

    Expected structure::

        {
            "targetPrice": {
                "high": "$280.00",
                "low": "$200.00",
                "mean": "$250.00",
                "median": "$248.00"
            }
        }

    or flat structure::

        {
            "high": "$280.00",
            "low": "$200.00",
            "mean": "$250.00",
            "median": "$248.00"
        }

    or new ``consensusOverview`` structure with numeric values::

        {
            "consensusOverview": {
                "lowPriceTarget": 248.0,
                "highPriceTarget": 350.0,
                "priceTarget": 304.4,
                "buy": 14,
                "sell": 1,
                "hold": 9
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the target price endpoint.
    symbol : str
        The ticker symbol for this target price.

    Returns
    -------
    TargetPrice
        Parsed target price with high/low/mean/median.
    """
    # Try new API structure: consensusOverview with numeric values
    consensus = data.get("consensusOverview")
    if isinstance(consensus, dict):
        result = TargetPrice(
            symbol=symbol,
            high=_to_str(consensus.get("highPriceTarget")),
            low=_to_str(consensus.get("lowPriceTarget")),
            mean=_to_str(consensus.get("priceTarget")),
            median=None,  # not provided in new API
        )
    else:
        # Fallback: try old nested/flat structure
        tp_data = data.get("targetPrice")
        source = tp_data if isinstance(tp_data, dict) else data

        result = TargetPrice(
            symbol=symbol,
            high=source.get("high"),
            low=source.get("low"),
            mean=source.get("mean"),
            median=source.get("median"),
        )

    logger.info(
        "Target price parsed",
        symbol=symbol,
        high=result.high,
        low=result.low,
        mean=result.mean,
        median=result.median,
    )
    return result


def parse_earnings_date(
    data: dict[str, Any],
    symbol: str,
) -> EarningsDate:
    """Parse earnings date endpoint data into ``EarningsDate``.

    Expected structure::

        {
            "earningsDate": "01/30/2026",
            "earningsTime": "After Market Close",
            "fiscalQuarterEnding": "Dec/2025",
            "epsForecast": "$2.35"
        }

    or nested under an ``earningsDate`` object::

        {
            "earningsDate": {
                "date": "01/30/2026",
                "time": "After Market Close",
                "fiscalQuarterEnding": "Dec/2025",
                "epsForecast": "$2.35"
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the earnings date endpoint.
    symbol : str
        The ticker symbol for this earnings date.

    Returns
    -------
    EarningsDate
        Parsed earnings date information.
    """
    # Try nested structure
    ed_data = data.get("earningsDate")
    if isinstance(ed_data, dict):
        result = EarningsDate(
            symbol=symbol,
            date=ed_data.get("date"),
            time=ed_data.get("time"),
            fiscal_quarter_ending=ed_data.get("fiscalQuarterEnding"),
            eps_forecast=ed_data.get("epsForecast"),
        )
    else:
        # Flat structure
        result = EarningsDate(
            symbol=symbol,
            date=ed_data if isinstance(ed_data, str) else data.get("date"),
            time=data.get("earningsTime") or data.get("time"),
            fiscal_quarter_ending=data.get("fiscalQuarterEnding"),
            eps_forecast=data.get("epsForecast"),
        )

    logger.info(
        "Earnings date parsed",
        symbol=symbol,
        date=result.date,
        time=result.time,
    )
    return result


# ---------------------------------------------------------------------------
# Company data parsers
# ---------------------------------------------------------------------------


def parse_insider_trades(data: dict[str, Any]) -> list[InsiderTrade]:
    """Parse insider trades endpoint data into ``InsiderTrade`` list.

    Expected structure::

        {
            "insiderTransactions": {
                "rows": [
                    {
                        "insider": "COOK TIMOTHY D",
                        "relation": "Chief Executive Officer",
                        "lastDate": "03/15/2026",
                        "transactionType": "Sold",
                        "ownType": "Direct",
                        "sharesTraded": "50,000",
                        "price": "$227.63",
                        "sharesHeld": "100,000",
                        "value": "$11,381,500",
                        "url": ""
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the insider trades endpoint.

    Returns
    -------
    list[InsiderTrade]
        Parsed insider trade records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``insiderTransactions.rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "insiderTransactions", "rows")
    if not rows:
        logger.debug("No insider trades rows to parse")
        return []

    logger.debug("Parsing insider trades rows", row_count=len(rows))

    result = [
        InsiderTrade(
            insider_name=row.get("insider"),
            relation=row.get("relation"),
            transaction_type=row.get("transactionType"),
            ownership_type=row.get("ownType"),
            shares_traded=row.get("sharesTraded"),
            price=row.get("price"),
            value=row.get("value"),
            date=row.get("lastDate"),
            shares_held=row.get("sharesHeld"),
            url=row.get("url"),
        )
        for row in rows
    ]

    logger.info("Insider trades parsed", record_count=len(result))
    return result


def parse_institutional_holdings(
    data: dict[str, Any],
) -> list[InstitutionalHolding]:
    """Parse institutional holdings endpoint data into ``InstitutionalHolding`` list.

    Expected structure::

        {
            "holdingsTransactions": {
                "rows": [
                    {
                        "ownerName": "Vanguard Group Inc",
                        "date": "12/31/2025",
                        "sharesHeld": "1,200,000,000",
                        "marketValue": "$180,000,000,000",
                        "sharesChange": "5,000,000",
                        "sharesChangePct": "0.42%",
                        "filingDate": "02/14/2026",
                        "url": ""
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the institutional holdings endpoint.

    Returns
    -------
    list[InstitutionalHolding]
        Parsed institutional holding records, or an empty list if no rows
        are present.

    Raises
    ------
    NasdaqParseError
        If ``holdingsTransactions.rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "holdingsTransactions", "rows")
    if not rows:
        logger.debug("No institutional holdings rows to parse")
        return []

    logger.debug("Parsing institutional holdings rows", row_count=len(rows))

    result = [
        InstitutionalHolding(
            holder_name=row.get("ownerName"),
            shares=row.get("sharesHeld"),
            value=row.get("marketValue"),
            change=row.get("sharesChange"),
            change_percent=row.get("sharesChangePct"),
            date_reported=row.get("date"),
            filing_date=row.get("filingDate"),
            url=row.get("url"),
        )
        for row in rows
    ]

    logger.info("Institutional holdings parsed", record_count=len(result))
    return result


def _parse_financial_table_rows(
    data: dict[str, Any],
    table_key: str,
) -> tuple[list[str], list[FinancialStatementRow]]:
    """Parse a financial statement table into headers and rows.

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload.
    table_key : str
        Key for the table (e.g. ``"incomeStatementTable"``).

    Returns
    -------
    tuple[list[str], list[FinancialStatementRow]]
        A tuple of (headers, rows). Headers exclude the first empty element.
    """
    table = data.get(table_key)
    if not isinstance(table, dict):
        return [], []

    # Extract headers
    headers_data = table.get("headers")
    headers: list[str] = []
    if isinstance(headers_data, dict):
        raw_values = headers_data.get("values")
        if isinstance(raw_values, list):
            # Old format: {"values": ["", "2025", "2024", "2023"]}
            headers = [str(v) for v in raw_values[1:] if v]
        else:
            # New format: {"value1": "Period Ending:", "value2": "9/27/2025", ...}
            i = 2  # skip value1 (label column)
            while f"value{i}" in headers_data:
                val = headers_data[f"value{i}"]
                if val:
                    headers.append(str(val))
                i += 1

    # Extract rows
    raw_rows = table.get("rows")
    if not isinstance(raw_rows, list):
        return headers, []

    # Determine value keys from first row if headers didn't give us a count
    num_values = len(headers) if headers else 0
    if num_values == 0 and raw_rows:
        first = raw_rows[0]
        if isinstance(first, dict):
            i = 2
            while f"value{i}" in first:
                num_values += 1
                i += 1
    value_keys = [f"value{i}" for i in range(2, num_values + 2)]

    result: list[FinancialStatementRow] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        label = row.get("value1", "")
        values = [
            str(val) if (val := row.get(key)) is not None else "" for key in value_keys
        ]
        result.append(FinancialStatementRow(label=str(label), values=values))

    return headers, result


def parse_financials(
    data: dict[str, Any],
    symbol: str,
    frequency: str = "annual",
) -> FinancialStatement:
    """Parse financials endpoint data into ``FinancialStatement``.

    Expected structure::

        {
            "incomeStatementTable": {
                "headers": { "values": ["", "2025", "2024", "2023"] },
                "rows": [
                    {
                        "value1": "Total Revenue",
                        "value2": "$394,328",
                        "value3": "$383,285",
                        "value4": "$365,817"
                    }, ...
                ]
            },
            "balanceSheetTable": { ... },
            "cashFlowTable": { ... }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the financials endpoint.
    symbol : str
        The ticker symbol for these financials.
    frequency : str
        Data frequency (``"annual"`` or ``"quarterly"``). Default ``"annual"``.

    Returns
    -------
    FinancialStatement
        Parsed financial statement with income, balance sheet, and cash flow.
    """
    income_headers, income_rows = _parse_financial_table_rows(
        data, "incomeStatementTable"
    )
    balance_headers, balance_rows = _parse_financial_table_rows(
        data, "balanceSheetTable"
    )
    cash_headers, cash_rows = _parse_financial_table_rows(data, "cashFlowTable")

    # Use the first non-empty headers found
    headers = income_headers or balance_headers or cash_headers

    logger.info(
        "Financials parsed",
        symbol=symbol,
        frequency=frequency,
        income_rows=len(income_rows),
        balance_rows=len(balance_rows),
        cash_flow_rows=len(cash_rows),
    )

    return FinancialStatement(
        symbol=symbol,
        frequency=frequency,
        headers=headers,
        income_statement=income_rows,
        balance_sheet=balance_rows,
        cash_flow=cash_rows,
    )


# ---------------------------------------------------------------------------
# Quote data parsers
# ---------------------------------------------------------------------------


def parse_short_interest(data: dict[str, Any]) -> list[ShortInterestRecord]:
    """Parse short interest endpoint data into ``ShortInterestRecord`` list.

    Expected structure::

        {
            "shortInterestTable": {
                "rows": [
                    {
                        "settlementDate": "03/15/2026",
                        "interest": "15,000,000",
                        "averageDailyVolume": "50,000,000",
                        "daysToCover": "0.30",
                        "change": "-500,000",
                        "changePct": "-3.23%"
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the short interest endpoint.

    Returns
    -------
    list[ShortInterestRecord]
        Parsed short interest records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``shortInterestTable.rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "shortInterestTable", "rows")
    if not rows:
        logger.debug("No short interest rows to parse")
        return []

    logger.debug("Parsing short interest rows", row_count=len(rows))

    result = [
        ShortInterestRecord(
            settlement_date=row.get("settlementDate"),
            short_interest=row.get("interest"),
            avg_daily_volume=row.get("averageDailyVolume"),
            days_to_cover=row.get("daysToCover"),
            change=row.get("change"),
            change_percent=row.get("changePct"),
        )
        for row in rows
    ]

    logger.info("Short interest parsed", record_count=len(result))
    return result


def parse_dividend_history(data: dict[str, Any]) -> list[DividendRecord]:
    """Parse dividend history endpoint data into ``DividendRecord`` list.

    Expected structure::

        {
            "dividends": {
                "rows": [
                    {
                        "exOrEffDate": "02/07/2026",
                        "paymentDate": "02/13/2026",
                        "recordDate": "02/10/2026",
                        "declarationDate": "01/30/2026",
                        "type": "Cash",
                        "amount": "$0.25",
                        "yield": "0.44%"
                    }, ...
                ]
            }
        }

    Parameters
    ----------
    data : dict[str, Any]
        The unwrapped ``data`` payload from the dividend history endpoint.

    Returns
    -------
    list[DividendRecord]
        Parsed dividend records, or an empty list if no rows are present.

    Raises
    ------
    NasdaqParseError
        If ``dividends.rows`` exists but is not a list.
    """
    rows = _extract_rows(data, "dividends", "rows")
    if not rows:
        logger.debug("No dividend history rows to parse")
        return []

    logger.debug("Parsing dividend history rows", row_count=len(rows))

    result = [
        DividendRecord(
            ex_date=row.get("exOrEffDate"),
            payment_date=row.get("paymentDate"),
            record_date=row.get("recordDate"),
            declaration_date=row.get("declarationDate"),
            dividend_type=row.get("type"),
            amount=row.get("amount"),
            yield_=row.get("yield"),
        )
        for row in rows
    ]

    logger.info("Dividend history parsed", record_count=len(result))
    return result


__all__ = [
    "clean_market_cap",
    "clean_percentage",
    "clean_price",
    "clean_volume",
    "parse_analyst_ratings",
    "parse_dividend_history",
    "parse_dividends_calendar",
    "parse_earnings_calendar",
    "parse_earnings_date",
    "parse_earnings_forecast",
    "parse_etf_screener",
    "parse_financials",
    "parse_insider_trades",
    "parse_institutional_holdings",
    "parse_ipo_calendar",
    "parse_market_movers",
    "parse_short_interest",
    "parse_splits_calendar",
    "parse_target_price",
    "unwrap_envelope",
]
