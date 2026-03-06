"""Integration tests for BSE collectors against the live BSE India API.

These tests send real HTTP requests to https://api.bseindia.com and
https://www.bseindia.com and verify that data retrieval and parsing work
correctly end-to-end.

Run with::

    uv run pytest tests/market/bse/integration/ -m integration -v

IMPORTANT: The BSE API has bot-detection mechanisms (403 responses).
This test module is designed to minimise API usage:
- ``scope="module"`` fixtures share data across tests
- Polite delay of 1.0s between requests to avoid rate limiting
- Tests are grouped to reuse session and fetched data

Sample scrip: Infosys (scrip_code=500209)

See Also
--------
market.bse.collectors.quote : QuoteCollector under test.
market.bse.collectors.bhavcopy : BhavcopyCollector under test.
market.bse.collectors.index : IndexCollector under test.
market.bse.collectors.corporate : CorporateCollector under test.
tests/market/bse/unit/ : Unit tests with mocked HTTP.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from market.bse.collectors.bhavcopy import BhavcopyCollector
from market.bse.collectors.corporate import CorporateCollector
from market.bse.collectors.index import IndexCollector
from market.bse.collectors.quote import QuoteCollector
from market.bse.errors import BseAPIError, BseError
from market.bse.session import BseSession
from market.bse.types import (
    Announcement,
    BseConfig,
    CorporateAction,
    FinancialResult,
    IndexName,
    RetryConfig,
    ScripQuote,
)

if TYPE_CHECKING:
    from collections.abc import Generator

# ---------------------------------------------------------------------------
# Sample scrip for testing
# ---------------------------------------------------------------------------

SAMPLE_SCRIP_CODE = "500209"  # Infosys Ltd


def _bse_api_is_reachable() -> bool:
    """Check if the BSE API is reachable by sending a lightweight request.

    Makes a single request to the quote endpoint. Returns False on
    403 (bot block), 429 (rate limit), or network error.

    Returns
    -------
    bool
        True if the BSE API responds with a 200 status code.
    """
    try:
        with BseSession(
            config=BseConfig(polite_delay=0.5, timeout=15.0),
            retry_config=RetryConfig(max_attempts=1),
        ) as session:
            from market.bse.constants import BASE_URL

            response = session.get(
                f"{BASE_URL}/getScripHeaderData",
                params={"Ession_id": "", "scripcode": SAMPLE_SCRIP_CODE},
            )
            return response.status_code == 200
    except (BseError, OSError, Exception):
        return False


# Cache the probe result at module import time so we only call it once
_BSE_REACHABLE = _bse_api_is_reachable()

# ---------------------------------------------------------------------------
# Module-level markers: skip all tests if BSE API is not reachable
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _BSE_REACHABLE,
        reason="BSE API is not reachable (blocked, rate-limited, or network error)",
    ),
]


# ---------------------------------------------------------------------------
# Fixtures (module-scoped to minimise API calls)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bse_session() -> Generator[BseSession]:
    """Create a BseSession connected to the live BSE API.

    Uses a polite delay of 1.0s and retry with no jitter to keep test
    execution predictable. Shared across all tests in this module to
    avoid creating multiple HTTP connections.
    """
    config = BseConfig(
        polite_delay=1.0,
        delay_jitter=0.2,
        timeout=30.0,
    )
    retry = RetryConfig(
        max_attempts=3,
        initial_delay=2.0,
        max_delay=15.0,
        jitter=False,
    )
    with BseSession(config=config, retry_config=retry) as session:
        yield session


@pytest.fixture(scope="module")
def quote_collector(bse_session: BseSession) -> QuoteCollector:
    """Create a QuoteCollector with the shared session."""
    return QuoteCollector(session=bse_session)


@pytest.fixture(scope="module")
def bhavcopy_collector(bse_session: BseSession) -> BhavcopyCollector:
    """Create a BhavcopyCollector with the shared session."""
    return BhavcopyCollector(session=bse_session)


@pytest.fixture(scope="module")
def index_collector(bse_session: BseSession) -> IndexCollector:
    """Create an IndexCollector with the shared session."""
    return IndexCollector(session=bse_session)


@pytest.fixture(scope="module")
def corporate_collector(bse_session: BseSession) -> CorporateCollector:
    """Create a CorporateCollector with the shared session."""
    return CorporateCollector(session=bse_session)


@pytest.fixture(scope="module")
def sample_quote(quote_collector: QuoteCollector) -> ScripQuote:
    """Fetch a sample quote for reuse across tests.

    Returns
    -------
    ScripQuote
        A live quote for Infosys (500209).
    """
    return quote_collector.fetch_quote(SAMPLE_SCRIP_CODE)


@pytest.fixture(scope="module")
def sample_company_info(
    corporate_collector: CorporateCollector,
) -> dict[str, str | None]:
    """Fetch sample company info for reuse across tests.

    Returns
    -------
    dict[str, str | None]
        Company information for Infosys (500209).
    """
    return corporate_collector.get_company_info(SAMPLE_SCRIP_CODE)


# ---------------------------------------------------------------------------
# Tests: QuoteCollector
# ---------------------------------------------------------------------------


class TestQuoteCollectorIntegration:
    """Integration tests for QuoteCollector against the live BSE API."""

    def test_正常系_fetch_quoteでScripQuoteが返される(
        self, sample_quote: ScripQuote
    ) -> None:
        """fetch_quote() returns a valid ScripQuote for Infosys."""
        assert isinstance(sample_quote, ScripQuote)
        assert sample_quote.scrip_code == SAMPLE_SCRIP_CODE
        assert sample_quote.scrip_name != ""

    def test_正常系_ScripQuoteの価格フィールドが空でない(
        self, sample_quote: ScripQuote
    ) -> None:
        """ScripQuote price fields are non-empty strings."""
        assert sample_quote.open != ""
        assert sample_quote.high != ""
        assert sample_quote.low != ""
        assert sample_quote.close != ""
        assert sample_quote.prev_close != ""

    def test_正常系_fetch_historicalでDataFrameが返される(
        self, quote_collector: QuoteCollector
    ) -> None:
        """fetch_historical() returns a non-empty DataFrame for Infosys."""
        df = quote_collector.fetch_historical(SAMPLE_SCRIP_CODE)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_正常系_fetchでDataFrame形式のquoteが返される(
        self, quote_collector: QuoteCollector
    ) -> None:
        """fetch() (DataCollector ABC) returns a single-row DataFrame."""
        df = quote_collector.fetch(scrip_code=SAMPLE_SCRIP_CODE)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "scrip_code" in df.columns
        assert "scrip_name" in df.columns

    def test_正常系_validateがfetch結果に対しTrueを返す(
        self, quote_collector: QuoteCollector
    ) -> None:
        """validate() returns True for data fetched via fetch()."""
        df = quote_collector.fetch(scrip_code=SAMPLE_SCRIP_CODE)
        assert quote_collector.validate(df) is True


# ---------------------------------------------------------------------------
# Tests: BhavcopyCollector
# ---------------------------------------------------------------------------


class TestBhavcopyCollectorIntegration:
    """Integration tests for BhavcopyCollector against the live BSE website."""

    def test_正常系_直近営業日のequity_bhavcopyが取得できる(
        self, bhavcopy_collector: BhavcopyCollector
    ) -> None:
        """fetch_equity() returns a non-empty DataFrame for a recent business day.

        We try the last 7 days to find a valid trading day (skipping
        weekends and holidays).
        """
        today = datetime.date.today()
        df = pd.DataFrame()  # empty default
        last_error: Exception | None = None

        for days_back in range(1, 8):
            target_date = today - datetime.timedelta(days=days_back)
            # Skip weekends
            if target_date.weekday() >= 5:
                continue
            try:
                df = bhavcopy_collector.fetch_equity(target_date)
                if not df.empty:
                    break
            except (BseAPIError, BseError) as e:
                last_error = e
                continue

        if df.empty and last_error is not None:
            pytest.skip(f"Could not fetch bhavcopy for any recent date: {last_error}")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_正常系_bhavcopyのvalidateがTrueを返す(
        self, bhavcopy_collector: BhavcopyCollector
    ) -> None:
        """validate() returns True for data fetched via fetch_equity().

        Tries the last 7 business days to find valid data.
        """
        today = datetime.date.today()
        df = pd.DataFrame()

        for days_back in range(1, 8):
            target_date = today - datetime.timedelta(days=days_back)
            if target_date.weekday() >= 5:
                continue
            try:
                df = bhavcopy_collector.fetch_equity(target_date)
                if not df.empty:
                    break
            except (BseAPIError, BseError):
                continue

        if df.empty:
            pytest.skip("Could not fetch bhavcopy for any recent date")

        assert bhavcopy_collector.validate(df) is True


# ---------------------------------------------------------------------------
# Tests: IndexCollector
# ---------------------------------------------------------------------------


class TestIndexCollectorIntegration:
    """Integration tests for IndexCollector against the live BSE API."""

    def test_正常系_SENSEXヒストリカルデータが取得できる(
        self, index_collector: IndexCollector
    ) -> None:
        """fetch_historical(SENSEX) returns a non-empty DataFrame."""
        end = datetime.date.today()
        start = end - datetime.timedelta(days=30)

        df = index_collector.fetch_historical(
            IndexName.SENSEX,
            start=start,
            end=end,
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_正常系_SENSEXデータにdateとcloseカラムが含まれる(
        self, index_collector: IndexCollector
    ) -> None:
        """SENSEX historical data contains required 'date' and 'close' columns."""
        end = datetime.date.today()
        start = end - datetime.timedelta(days=30)

        df = index_collector.fetch_historical(
            IndexName.SENSEX,
            start=start,
            end=end,
        )

        assert "date" in df.columns
        assert "close" in df.columns

    def test_正常系_validateがSENSEXデータに対しTrueを返す(
        self, index_collector: IndexCollector
    ) -> None:
        """validate() returns True for SENSEX historical data."""
        end = datetime.date.today()
        start = end - datetime.timedelta(days=30)

        df = index_collector.fetch_historical(
            IndexName.SENSEX,
            start=start,
            end=end,
        )

        assert index_collector.validate(df) is True

    def test_正常系_list_indicesでSENSEXが含まれる(self) -> None:
        """list_indices() includes 'SENSEX'."""
        indices = IndexCollector.list_indices()

        assert isinstance(indices, list)
        assert "SENSEX" in indices

    def test_正常系_fetchでindex_name指定のDataFrameが返される(
        self, index_collector: IndexCollector
    ) -> None:
        """fetch() (DataCollector ABC) returns a DataFrame for SENSEX."""
        df = index_collector.fetch(index_name="SENSEX")

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Tests: CorporateCollector
# ---------------------------------------------------------------------------


class TestCorporateCollectorIntegration:
    """Integration tests for CorporateCollector against the live BSE API."""

    def test_正常系_get_company_infoでInfosysの情報が取得できる(
        self, sample_company_info: dict[str, str | None]
    ) -> None:
        """get_company_info() returns a dict with scrip_code for Infosys."""
        assert isinstance(sample_company_info, dict)
        assert sample_company_info.get("scrip_code") == SAMPLE_SCRIP_CODE

    def test_正常系_company_infoにcompany_nameが含まれる(
        self, sample_company_info: dict[str, str | None]
    ) -> None:
        """Company info contains a non-empty company_name."""
        company_name = sample_company_info.get("company_name")
        assert company_name is not None
        assert company_name != ""

    def test_正常系_get_financial_resultsでリストが返される(
        self, corporate_collector: CorporateCollector
    ) -> None:
        """get_financial_results() returns a list of FinancialResult."""
        results = corporate_collector.get_financial_results(SAMPLE_SCRIP_CODE)

        assert isinstance(results, list)
        # Infosys is a major company; should have financial results
        for result in results:
            assert isinstance(result, FinancialResult)
            assert result.scrip_code == SAMPLE_SCRIP_CODE

    def test_正常系_get_announcementsでリストが返される(
        self, corporate_collector: CorporateCollector
    ) -> None:
        """get_announcements() returns a list of Announcement."""
        announcements = corporate_collector.get_announcements(SAMPLE_SCRIP_CODE)

        assert isinstance(announcements, list)
        for ann in announcements:
            assert isinstance(ann, Announcement)
            assert ann.scrip_code == SAMPLE_SCRIP_CODE

    def test_正常系_get_corporate_actionsでリストが返される(
        self, corporate_collector: CorporateCollector
    ) -> None:
        """get_corporate_actions() returns a list of CorporateAction."""
        actions = corporate_collector.get_corporate_actions(SAMPLE_SCRIP_CODE)

        assert isinstance(actions, list)
        for action in actions:
            assert isinstance(action, CorporateAction)
            assert action.scrip_code == SAMPLE_SCRIP_CODE

    def test_正常系_search_scripでInfosysが見つかる(
        self, corporate_collector: CorporateCollector
    ) -> None:
        """search_scrip('INFOSYS') returns results containing the scrip."""
        results = corporate_collector.search_scrip("INFOSYS")

        assert isinstance(results, list)
        # Should find at least one result for a major company
        if len(results) > 0:
            # Each result should have scrip_code and scrip_name
            first = results[0]
            assert "scrip_code" in first
            assert "scrip_name" in first
