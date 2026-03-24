"""JSON response parser for ETF.com REST API endpoints.

This module converts raw JSON responses from the ETF.com ``/v2/fund/fund-details``
POST endpoint (18 queries) and 4 GET endpoints into normalised Python data
structures (``list[dict]`` or ``dict``).

Responsibilities
----------------
- **camelCase to snake_case key conversion** with a special-case mapping for
  abbreviations and non-standard names (e.g. ``aum`` stays ``aum``,
  ``peRatio`` becomes ``pe_ratio``).
- **Date normalisation** — ISO 8601 timestamps (``2026-03-21T00:00:00.000Z``)
  are truncated to date-only strings (``2026-03-21``).
- **Safe null/empty handling** — empty responses and ``None`` values are
  handled gracefully; parsers return empty lists/dicts rather than raising.
- **No external dependencies beyond the standard library**.

Architecture
------------
Each parser function takes the full JSON response body (``dict``) as input
and returns the normalised result.  The ``_extract_fund_details_data()``
helper handles the common ``data[queryName].data`` nesting pattern used by
all 18 fund-details queries.

See Also
--------
market.etfcom.constants : Query name definitions (``FUND_DETAILS_QUERY_NAMES``).
market.etfcom.models : Frozen dataclass records that downstream layers
    construct from the dicts returned by these parsers.
market.nasdaq.parser : Similar camelCase-to-snake_case parser pattern.
"""

from __future__ import annotations

import re
from typing import Any

from utils_core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Internal helpers
# =============================================================================

_CAMEL_TO_SNAKE_PATTERN: re.Pattern[str] = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
"""Regex that inserts an underscore before each uppercase letter preceded
by a lowercase letter or digit."""

_SPECIAL_KEY_MAP: dict[str, str] = {
    "aum": "aum",
    "nav": "nav",
    "iiv": "iiv",
    "peRatio": "pe_ratio",
    "pbRatio": "pb_ratio",
    "rSquared": "r_squared",
    "returnYTD": "return_ytd",
    "return1M": "return_1m",
    "return3M": "return_3m",
    "return1Y": "return_1y",
    "return3Y": "return_3y",
    "return5Y": "return_5y",
    "return10Y": "return_10y",
    "return12M": "return_12m",
    "fundName": "name",
}
"""Special-case key mappings that override the regex-based conversion.

Handles abbreviations (``aum``, ``nav``, ``iiv``) and non-standard names
(``fundName`` -> ``name``, ``peRatio`` -> ``pe_ratio``) that the simple
regex cannot convert correctly.
"""


def _camel_to_snake(name: str) -> str:
    """Convert a camelCase string to snake_case.

    Checks ``_SPECIAL_KEY_MAP`` first for known overrides, then falls back
    to the regex-based conversion.

    Parameters
    ----------
    name : str
        camelCase key name from the API response.

    Returns
    -------
    str
        The snake_case equivalent.

    Examples
    --------
    >>> _camel_to_snake("navChangePercent")
    'nav_change_percent'
    >>> _camel_to_snake("aum")
    'aum'
    >>> _camel_to_snake("peRatio")
    'pe_ratio'
    >>> _camel_to_snake("fundName")
    'name'
    """
    if name in _SPECIAL_KEY_MAP:
        return _SPECIAL_KEY_MAP[name]
    return _CAMEL_TO_SNAKE_PATTERN.sub("_", name).lower()


def _convert_keys(record: dict[str, Any]) -> dict[str, Any]:
    """Convert all keys in a dict from camelCase to snake_case.

    Parameters
    ----------
    record : dict[str, Any]
        A single record with camelCase keys.

    Returns
    -------
    dict[str, Any]
        A new dict with snake_case keys, values unchanged.
    """
    return {_camel_to_snake(k): v for k, v in record.items()}


def _normalize_date(value: str | None) -> str | None:
    """Normalise an ISO 8601 timestamp to a date-only string.

    If the value contains a ``T`` separator (e.g.
    ``2026-03-21T00:00:00.000Z``), returns only the date part
    (``2026-03-21``).  If the value is already date-only or ``None``,
    returns it unchanged.

    Parameters
    ----------
    value : str | None
        An ISO 8601 date or datetime string, or None.

    Returns
    -------
    str | None
        The date-only string, or None if the input was None.

    Examples
    --------
    >>> _normalize_date("2026-03-21T00:00:00.000Z")
    '2026-03-21'
    >>> _normalize_date("2026-03-21")
    '2026-03-21'
    >>> _normalize_date(None) is None
    True
    """
    if value is None:
        return None
    if "T" in value:
        return value.split("T")[0]
    return value


def _extract_fund_details_data(
    response: dict[str, Any],
    query_name: str,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Extract data from the ``data[queryName].data`` nesting pattern.

    All 18 fund-details queries share the response structure::

        {
            "data": {
                "<queryName>": {
                    "data": <list|dict>
                }
            }
        }

    This helper safely navigates the nesting and returns the inner data,
    or ``None`` if the path is missing.

    Parameters
    ----------
    response : dict[str, Any]
        The full JSON response body.
    query_name : str
        The query name key (e.g. ``"fundFlowsData"``).

    Returns
    -------
    list[dict[str, Any]] | dict[str, Any] | None
        The extracted data, or None if the path does not exist.
    """
    data_outer = response.get("data")
    if not isinstance(data_outer, dict):
        logger.warning(
            "Missing 'data' key in response",
            query_name=query_name,
        )
        return None

    query_data = data_outer.get(query_name)
    if not isinstance(query_data, dict):
        logger.warning(
            "Missing query data in response",
            query_name=query_name,
        )
        return None

    inner = query_data.get("data")
    if inner is None:
        logger.warning(
            "Missing inner 'data' key in response",
            query_name=query_name,
        )
        return None

    return inner


# =============================================================================
# Generic list response parser (DRY helper)
# =============================================================================


def _parse_list_response(
    response: dict[str, Any],
    query_name: str,
    date_fields: tuple[str, ...] = ("as_of_date",),
) -> list[dict[str, Any]]:
    """Generic parser for fund-details queries that return a list.

    Extracts data via ``_extract_fund_details_data()``, converts keys
    to snake_case, and normalises the specified date fields.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.
    query_name : str
        The query name key (e.g. ``"fundFlowsData"``).
    date_fields : tuple[str, ...]
        Snake_case date field names to normalise.  Defaults to
        ``("as_of_date",)``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with normalised date fields.
        Returns an empty list if data is missing.
    """
    raw = _extract_fund_details_data(response, query_name)
    if not isinstance(raw, list):
        logger.debug("No list data found", query_name=query_name)
        return []

    results: list[dict[str, Any]] = []
    for record in raw:
        converted = _convert_keys(record)
        for field in date_fields:
            if field in converted:
                converted[field] = _normalize_date(converted.get(field))
        results.append(converted)

    logger.debug(
        "Parsed list response", query_name=query_name, record_count=len(results)
    )
    return results


# =============================================================================
# 18 POST fund-details parsers
# =============================================================================


def parse_fund_flows(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``fundFlowsData`` query response.

    Extracts daily NAV, fund flows, AUM, and premium/discount data.
    Normalises ``navDate`` to date-only format.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with normalised date fields.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "fundFlowsData", date_fields=("nav_date",))


def parse_holdings(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``topHoldings`` query response.

    Extracts top holdings with ticker, name, weight, and market value.
    Normalises ``asOfDate`` to date-only format.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with holding data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "topHoldings")


def parse_portfolio_data(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundPortfolioData`` query response.

    Extracts portfolio-level metrics (P/E, P/B, dividend yield, etc.).
    Normalises ``asOfDate`` to date-only format.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with portfolio characteristics.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundPortfolioData")
    if not isinstance(raw, dict):
        logger.debug("fundPortfolioData: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed portfolio data")
    return converted


def parse_sector_breakdown(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``sectorIndustryBreakdown`` query response.

    Extracts sector allocation data with name, weight, and market value.
    Normalises ``asOfDate`` to date-only format.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with sector allocation data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "sectorIndustryBreakdown")


def parse_regions(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``regions`` query response.

    Extracts regional allocation data.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with region allocation data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "regions")


def parse_countries(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``countries`` query response.

    Extracts country allocation data.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with country allocation data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "countries")


def parse_econ_dev(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``economicDevelopment`` query response.

    Extracts economic development classification data
    (Developed / Emerging).

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with economic development data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "economicDevelopment")


def parse_intra_data(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``fundIntraData`` query response.

    Extracts intraday price, volume, and IIV data.
    Normalises ``date`` to date-only format.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with intraday data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "fundIntraData", date_fields=("date",))


def parse_compare_ticker(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``compareTicker`` query response.

    Extracts competing ETF comparison data.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with comparison data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "compareTicker", date_fields=())


def parse_spread_chart(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``fundSpreadChart`` query response.

    Extracts bid-ask spread chart data over time.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with spread chart data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "fundSpreadChart", date_fields=("date",))


def parse_premium_chart(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``fundPremiumChart`` query response.

    Extracts premium/discount chart data over time.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with premium/discount chart data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "fundPremiumChart", date_fields=("date",))


def parse_tradability(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``fundTradabilityData`` query response.

    Extracts volume, spread, and liquidity time-series data.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case dicts with tradability data.
        Returns an empty list if data is missing.
    """
    return _parse_list_response(response, "fundTradabilityData", date_fields=("date",))


def parse_tradability_summary(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundTradabilitySummary`` query response.

    Extracts aggregated tradability metrics (avg volume, spreads,
    creation unit size, implied liquidity).

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with tradability summary data.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundTradabilitySummary")
    if not isinstance(raw, dict):
        logger.debug("fundTradabilitySummary: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed tradability summary")
    return converted


def parse_portfolio_management(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundPortfolioManData`` query response.

    Extracts expense ratio, tracking difference, and management data.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with portfolio management data.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundPortfolioManData")
    if not isinstance(raw, dict):
        logger.debug("fundPortfolioManData: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed portfolio management")
    return converted


def parse_tax_exposures(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundTaxExposuresData`` query response.

    Extracts tax-related data (tax form, capital gains, distributions).

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with tax exposure data.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundTaxExposuresData")
    if not isinstance(raw, dict):
        logger.debug("fundTaxExposuresData: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed tax exposures")
    return converted


def parse_structure(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundStructureData`` query response.

    Extracts fund structure data (legal structure, replication method,
    derivatives usage, securities lending).

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with structure data.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundStructureData")
    if not isinstance(raw, dict):
        logger.debug("fundStructureData: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed structure")
    return converted


def parse_rankings(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundRankingsData`` query response.

    Extracts ETF.com rating grades (overall, efficiency, tradability, fit).

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with rankings data.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundRankingsData")
    if not isinstance(raw, dict):
        logger.debug("fundRankingsData: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed rankings")
    return converted


def parse_performance_stats(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``fundPerformanceStatsData`` query response.

    Extracts performance statistics (returns, R-squared, beta,
    standard deviation, grade).

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from ``/v2/fund/fund-details``.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with performance statistics.
        Returns an empty dict if data is missing.
    """
    raw = _extract_fund_details_data(response, "fundPerformanceStatsData")
    if not isinstance(raw, dict):
        logger.debug("fundPerformanceStatsData: no dict data found")
        return {}

    converted = _convert_keys(raw)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed performance stats")
    return converted


# =============================================================================
# 4 GET endpoint parsers
# =============================================================================


def parse_tickers(
    response: list[dict[str, Any]] | dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse the ``/v2/fund/tickers`` GET endpoint response.

    The tickers endpoint returns a flat JSON array of ticker objects.
    Each object is converted to snake_case with ``fundName`` mapped to
    ``name``.

    Parameters
    ----------
    response : list[dict[str, Any]] | dict[str, Any]
        Raw JSON response — expected to be a list of ticker dicts.
        If a dict is received (unexpected), returns an empty list.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case ticker dicts.
        Returns an empty list if data is missing or invalid.
    """
    if not isinstance(response, list):
        logger.warning("Tickers response is not a list")
        return []

    results: list[dict[str, Any]] = []
    for record in response:
        converted = _convert_keys(record)
        results.append(converted)

    logger.debug("Parsed tickers", record_count=len(results))
    return results


def parse_delayed_quotes(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``/v2/quotes/delayedquotes`` GET endpoint response.

    The delayed quotes endpoint returns ``{"data": [...]}``.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from the delayed quotes endpoint.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case quote dicts with normalised date fields.
        Returns an empty list if data is missing.
    """
    data = response.get("data")
    if not isinstance(data, list):
        logger.warning("Delayed quotes response missing 'data' list")
        return []

    results: list[dict[str, Any]] = []
    for record in data:
        converted = _convert_keys(record)
        converted["last_trade_date"] = _normalize_date(converted.get("last_trade_date"))
        results.append(converted)

    logger.debug("Parsed delayed quotes", record_count=len(results))
    return results


def parse_charts(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the ``/v2/fund/charts`` GET endpoint response.

    The charts endpoint returns ``{"data": [...]}``.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from the charts endpoint.

    Returns
    -------
    list[dict[str, Any]]
        List of snake_case chart point dicts with normalised date fields.
        Returns an empty list if data is missing.
    """
    data = response.get("data")
    if not isinstance(data, list):
        logger.warning("Charts response missing 'data' list")
        return []

    results: list[dict[str, Any]] = []
    for record in data:
        converted = _convert_keys(record)
        converted["date"] = _normalize_date(converted.get("date"))
        results.append(converted)

    logger.debug("Parsed charts", record_count=len(results))
    return results


def parse_performance(response: dict[str, Any]) -> dict[str, Any]:
    """Parse the ``/v2/fund/performance`` GET endpoint response.

    The performance endpoint returns ``{"data": {...}}``.

    Parameters
    ----------
    response : dict[str, Any]
        Full JSON response from the performance endpoint.

    Returns
    -------
    dict[str, Any]
        Snake_case dict with performance return data.
        Returns an empty dict if data is missing.
    """
    data = response.get("data")
    if not isinstance(data, dict):
        logger.warning("Performance response missing 'data' dict")
        return {}

    converted = _convert_keys(data)
    converted["as_of_date"] = _normalize_date(converted.get("as_of_date"))

    logger.debug("Parsed performance")
    return converted


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "parse_charts",
    "parse_compare_ticker",
    "parse_countries",
    "parse_delayed_quotes",
    "parse_econ_dev",
    "parse_fund_flows",
    "parse_holdings",
    "parse_intra_data",
    "parse_performance",
    "parse_performance_stats",
    "parse_portfolio_data",
    "parse_portfolio_management",
    "parse_premium_chart",
    "parse_rankings",
    "parse_regions",
    "parse_sector_breakdown",
    "parse_spread_chart",
    "parse_structure",
    "parse_tax_exposures",
    "parse_tickers",
    "parse_tradability",
    "parse_tradability_summary",
]
