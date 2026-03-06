"""BSE Corporate data collector (non-ABC).

This module provides ``CorporateCollector``, the entry point for fetching
corporate information from the BSE India API.  Unlike other BSE collectors,
this class does **not** inherit from ``DataCollector`` because its methods
return heterogeneous types (``dict``, ``list[FinancialResult]``,
``list[Announcement]``, ``list[CorporateAction]``) rather than a uniform
``pd.DataFrame``.

Features
--------
- Company information retrieval (``get_company_info``)
- Financial results (quarterly / annual) retrieval (``get_financial_results``)
- Corporate announcements retrieval (``get_announcements``)
- Corporate actions retrieval (``get_corporate_actions``)
- Scrip search (``search_scrip``)
- Dependency injection for BseSession (testability)

Examples
--------
Basic company info fetch:

>>> collector = CorporateCollector()
>>> info = collector.get_company_info("500325")
>>> print(info["company_name"])

Financial results:

>>> results = collector.get_financial_results("500325")
>>> for r in results:
...     print(f"{r.period_ended}: EPS {r.eps}")

See Also
--------
market.bse.session : BseSession with bot-blocking countermeasures.
market.bse.parsers : Corporate data parsers.
market.bse.types : FinancialResult, Announcement, CorporateAction dataclasses.
market.bse.collectors.quote : Reference DataCollector implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from market.bse.constants import BASE_URL
from market.bse.parsers import (
    parse_announcements,
    parse_company_info,
    parse_corporate_actions,
    parse_financial_results,
)
from market.bse.session import BseSession
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from market.bse.types import Announcement, CorporateAction, FinancialResult

logger = get_logger(__name__)

# BSE API endpoints for corporate data
_COMPANY_INFO_ENDPOINT: str = f"{BASE_URL}/getScripHeaderData"
_FINANCIAL_RESULTS_ENDPOINT: str = f"{BASE_URL}/FinancialResult"
_ANNOUNCEMENTS_ENDPOINT: str = f"{BASE_URL}/AnnGetData"
_CORPORATE_ACTIONS_ENDPOINT: str = f"{BASE_URL}/CorporateAction"
_SCRIP_SEARCH_ENDPOINT: str = f"{BASE_URL}/suggestscripname"


class CorporateCollector:
    """Collector for BSE corporate data (non-ABC).

    Fetches corporate information from the BSE India API including
    company profiles, financial results, announcements, and corporate
    actions.

    This class does **not** inherit from ``DataCollector`` because
    its methods return heterogeneous types rather than a uniform
    ``pd.DataFrame``.

    The ``BseSession`` can be injected via the constructor for testing
    (dependency injection pattern).  When no session is provided, a new
    session is created internally for each operation.

    Parameters
    ----------
    session : BseSession | None
        Pre-configured BseSession instance.  If None, a new session is
        created internally when needed.

    Attributes
    ----------
    _session_instance : BseSession | None
        Injected session instance (None if creating internally).

    Examples
    --------
    >>> collector = CorporateCollector()
    >>> info = collector.get_company_info("500325")
    >>> info["company_name"]
    'RELIANCE INDUSTRIES LTD'

    >>> # With dependency injection for testing
    >>> from unittest.mock import MagicMock
    >>> mock_session = MagicMock(spec=BseSession)
    >>> collector = CorporateCollector(session=mock_session)
    """

    def __init__(self, session: BseSession | None = None) -> None:
        """Initialize CorporateCollector with optional session injection.

        Parameters
        ----------
        session : BseSession | None
            Pre-configured BseSession for dependency injection.
            If None, a new BseSession is created when needed.
        """
        self._session_instance: BseSession | None = session

        logger.info(
            "CorporateCollector initialized",
            session_injected=session is not None,
        )

    def _get_session(self) -> tuple[BseSession, bool]:
        """Resolve the session: use injected or create new.

        Returns
        -------
        tuple[BseSession, bool]
            A tuple of (session, should_close).  ``should_close`` is True
            when a new session was created internally and must be closed
            by the caller.
        """
        if self._session_instance is not None:
            return self._session_instance, False
        return BseSession(), True

    def get_company_info(self, scrip_code: str) -> dict[str, str | None]:
        """Fetch company information for a BSE scrip.

        Sends a GET request to the BSE API's company info endpoint
        and parses the JSON response into a normalised dictionary.

        Parameters
        ----------
        scrip_code : str
            BSE scrip code (e.g., ``"500325"`` for Reliance Industries).

        Returns
        -------
        dict[str, str | None]
            A dictionary with keys: ``scrip_code``, ``company_name``,
            ``isin``, ``scrip_group``, ``industry``, ``market_cap``,
            ``face_value``.

        Raises
        ------
        BseParseError
            If the JSON response cannot be parsed.
        BseAPIError
            If the API returns an error status code.
        BseRateLimitError
            If rate limiting is detected.

        Examples
        --------
        >>> collector = CorporateCollector()
        >>> info = collector.get_company_info("500325")
        >>> info["scrip_code"]
        '500325'
        """
        logger.info(
            "Fetching company info",
            scrip_code=scrip_code,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _COMPANY_INFO_ENDPOINT,
                params={
                    "Ession_id": "",
                    "scripcode": scrip_code,
                },
            )

            json_data: dict[str, Any] = response.json()
            info = parse_company_info(json_data)

            logger.info(
                "Company info fetched",
                scrip_code=info.get("scrip_code"),
                company_name=info.get("company_name"),
            )

            return info
        finally:
            if should_close:
                session.close()

    def get_financial_results(
        self,
        scrip_code: str,
    ) -> list[FinancialResult]:
        """Fetch financial results for a BSE scrip.

        Sends a GET request to the BSE financial results endpoint
        and parses the JSON response into a list of ``FinancialResult``
        dataclasses.

        Parameters
        ----------
        scrip_code : str
            BSE scrip code (e.g., ``"500325"`` for Reliance Industries).

        Returns
        -------
        list[FinancialResult]
            A list of ``FinancialResult`` frozen dataclasses.

        Raises
        ------
        BseParseError
            If the JSON response cannot be parsed.
        BseAPIError
            If the API returns an error status code.

        Examples
        --------
        >>> collector = CorporateCollector()
        >>> results = collector.get_financial_results("500325")
        >>> results[0].scrip_code
        '500325'
        """
        logger.info(
            "Fetching financial results",
            scrip_code=scrip_code,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _FINANCIAL_RESULTS_ENDPOINT,
                params={
                    "scripcode": scrip_code,
                },
            )

            json_data: list[dict[str, Any]] = response.json()
            results = parse_financial_results(json_data)

            logger.info(
                "Financial results fetched",
                scrip_code=scrip_code,
                count=len(results),
            )

            return results
        finally:
            if should_close:
                session.close()

    def get_announcements(
        self,
        scrip_code: str,
    ) -> list[Announcement]:
        """Fetch corporate announcements for a BSE scrip.

        Sends a GET request to the BSE announcements endpoint
        and parses the JSON response into a list of ``Announcement``
        dataclasses.

        Parameters
        ----------
        scrip_code : str
            BSE scrip code (e.g., ``"500325"`` for Reliance Industries).

        Returns
        -------
        list[Announcement]
            A list of ``Announcement`` frozen dataclasses.

        Raises
        ------
        BseParseError
            If the JSON response cannot be parsed.
        BseAPIError
            If the API returns an error status code.

        Examples
        --------
        >>> collector = CorporateCollector()
        >>> announcements = collector.get_announcements("500325")
        >>> announcements[0].subject
        'Board Meeting Outcome'
        """
        logger.info(
            "Fetching announcements",
            scrip_code=scrip_code,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _ANNOUNCEMENTS_ENDPOINT,
                params={
                    "scripcode": scrip_code,
                },
            )

            json_data: list[dict[str, Any]] = response.json()
            announcements = parse_announcements(json_data)

            logger.info(
                "Announcements fetched",
                scrip_code=scrip_code,
                count=len(announcements),
            )

            return announcements
        finally:
            if should_close:
                session.close()

    def get_corporate_actions(
        self,
        scrip_code: str,
    ) -> list[CorporateAction]:
        """Fetch corporate actions for a BSE scrip.

        Sends a GET request to the BSE corporate actions endpoint
        and parses the JSON response into a list of ``CorporateAction``
        dataclasses.

        Parameters
        ----------
        scrip_code : str
            BSE scrip code (e.g., ``"500325"`` for Reliance Industries).

        Returns
        -------
        list[CorporateAction]
            A list of ``CorporateAction`` frozen dataclasses.

        Raises
        ------
        BseParseError
            If the JSON response cannot be parsed.
        BseAPIError
            If the API returns an error status code.

        Examples
        --------
        >>> collector = CorporateCollector()
        >>> actions = collector.get_corporate_actions("500325")
        >>> actions[0].purpose
        'Dividend - Rs 8 Per Share'
        """
        logger.info(
            "Fetching corporate actions",
            scrip_code=scrip_code,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _CORPORATE_ACTIONS_ENDPOINT,
                params={
                    "scripcode": scrip_code,
                },
            )

            json_data: list[dict[str, Any]] = response.json()
            actions = parse_corporate_actions(json_data)

            logger.info(
                "Corporate actions fetched",
                scrip_code=scrip_code,
                count=len(actions),
            )

            return actions
        finally:
            if should_close:
                session.close()

    def search_scrip(self, query: str) -> list[dict[str, str]]:
        """Search for BSE scrips by name or code.

        Sends a GET request to the BSE scrip search endpoint and
        returns a list of matching scrips.

        Parameters
        ----------
        query : str
            Search query string (e.g., ``"RELIANCE"`` or ``"500325"``).

        Returns
        -------
        list[dict[str, str]]
            A list of dicts, each containing ``scrip_code`` and
            ``scrip_name`` keys.

        Raises
        ------
        BseAPIError
            If the API returns an error status code.

        Examples
        --------
        >>> collector = CorporateCollector()
        >>> results = collector.search_scrip("RELIANCE")
        >>> results[0]["scrip_code"]
        '500325'
        """
        logger.info(
            "Searching scrip",
            query=query,
        )

        session, should_close = self._get_session()
        try:
            response = session.get_with_retry(
                _SCRIP_SEARCH_ENDPOINT,
                params={
                    "flag": "getscrip",
                    "value": query,
                },
            )

            json_data: Any = response.json()

            if not isinstance(json_data, list):
                logger.warning(
                    "Unexpected scrip search response type",
                    response_type=type(json_data).__name__,
                )
                return []

            results: list[dict[str, str]] = []
            for item in json_data:
                if not isinstance(item, dict):
                    continue
                scrip_code = str(item.get("scrip_cd", item.get("SCRIP_CD", ""))).strip()
                scrip_name = str(
                    item.get(
                        "scripname",
                        item.get("SCRIPNAME", item.get("long_name", "")),
                    )
                ).strip()
                if scrip_code or scrip_name:
                    results.append(
                        {
                            "scrip_code": scrip_code,
                            "scrip_name": scrip_name,
                        }
                    )

            logger.info(
                "Scrip search completed",
                query=query,
                count=len(results),
            )

            return results
        finally:
            if should_close:
                session.close()


__all__ = ["CorporateCollector"]
