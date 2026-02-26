"""Integration tests for EdinetClient against the live EDINET DB API.

These tests send real HTTP requests to https://edinetdb.jp and verify
that data retrieval and parsing work correctly end-to-end. All tests
are skipped when the ``EDINET_DB_API_KEY`` environment variable is not
set or when the API key is invalid (HTTP 403).

Run with::

    EDINET_DB_API_KEY=your_key uv run pytest tests/market/integration/edinet/ -v

IMPORTANT: The EDINET DB API has a daily rate limit of 1,000 calls
(Pro plan). This test module is designed to minimise API usage:
- ``scope="module"`` fixtures share data across tests
- Only 10 API calls are made per full test run (one per endpoint)
- ``polite_delay=0.5`` adds a 500ms wait between requests

See Also
--------
market.edinet.client : The module under test.
market.edinet.types : Data record dataclasses.
tests/market/unit/edinet/test_client.py : Unit tests with mocked HTTP.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
import pytest

from market.edinet.client import EdinetClient
from market.edinet.constants import DEFAULT_BASE_URL
from market.edinet.types import (
    AnalysisResult,
    Company,
    EdinetConfig,
    FinancialRecord,
    Industry,
    RankingEntry,
    RatioRecord,
    RetryConfig,
    TextBlock,
)

if TYPE_CHECKING:
    from collections.abc import Generator


def _api_key_is_valid() -> bool:
    """Check if the EDINET_DB_API_KEY env var is set and the API returns non-403.

    Makes a single lightweight request to /v1/industries to verify
    the key is accepted. Returns False on 403, missing key, or network error.
    """
    api_key = os.environ.get("EDINET_DB_API_KEY", "")
    if not api_key:
        return False
    try:
        resp = httpx.get(
            f"{DEFAULT_BASE_URL}/v1/industries",
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )
        return resp.status_code != 403
    except (httpx.HTTPError, OSError):
        return False


# Cache the probe result at module import time so we only call it once
_VALID_KEY = _api_key_is_valid()

# ---------------------------------------------------------------------------
# Module-level markers: skip all tests if API key is not available or invalid
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _VALID_KEY,
        reason="EDINET_DB_API_KEY not set or invalid (HTTP 403)",
    ),
]


# ---------------------------------------------------------------------------
# Fixtures (module-scoped to minimise API calls)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Generator[EdinetClient]:
    """Create an EdinetClient connected to the live API.

    The client uses a polite delay of 0.5s and retry with no jitter
    to keep test execution deterministic. Shared across all tests in
    this module to avoid creating multiple HTTP connections.
    """
    config = EdinetConfig(
        api_key=os.environ["EDINET_DB_API_KEY"],
        polite_delay=0.5,
    )
    retry = RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        jitter=False,
    )
    with EdinetClient(config=config, retry_config=retry) as c:
        yield c


@pytest.fixture(scope="module")
def companies(client: EdinetClient) -> list[Company]:
    """Fetch a small set of companies (shared across tests).

    Retrieves 10 companies via ``list_companies(per_page=10)`` so that
    subsequent tests can pick a real EDINET code without extra API calls.

    Returns
    -------
    list[Company]
        List of up to 10 Company records from the live API.
    """
    return client.list_companies(per_page=10)


@pytest.fixture(scope="module")
def sample_edinet_code(companies: list[Company]) -> str:
    """Extract the EDINET code of the first company in the list.

    This code is used by tests that require a real company identifier
    (get_company, get_financials, get_ratios, get_analysis, get_text_blocks).

    Returns
    -------
    str
        A valid EDINET code (e.g. ``"E00001"``).
    """
    assert len(companies) > 0, (
        "list_companies returned 0 results; cannot extract sample code"
    )
    return companies[0].edinet_code


@pytest.fixture(scope="module")
def industries(client: EdinetClient) -> list[Industry]:
    """Fetch all industry classifications (shared across tests).

    Returns
    -------
    list[Industry]
        List of Industry records from the live API.
    """
    return client.list_industries()


# ---------------------------------------------------------------------------
# Tests (one per endpoint, 10 total)
# ---------------------------------------------------------------------------


class TestSearchIntegration:
    """search() endpoint integration test."""

    def test_正常系_検索クエリでリスト型の結果が返される(
        self, client: EdinetClient
    ) -> None:
        """'トヨタ' で検索し、list が返ること。"""
        results = client.search("トヨタ")

        assert isinstance(results, list)
        # "トヨタ" is a well-known company; at least 1 result expected
        assert len(results) > 0
        # Each result should be a dict with company-related keys
        first = results[0]
        assert isinstance(first, dict)


class TestListCompaniesIntegration:
    """list_companies() endpoint integration test."""

    def test_正常系_企業一覧がCompanyリストで返される(
        self, companies: list[Company]
    ) -> None:
        """per_page=10 で取得し、list[Company] で len > 0、各フィールドが非空。"""
        assert isinstance(companies, list)
        assert len(companies) > 0

        for company in companies:
            assert isinstance(company, Company)
            assert company.edinet_code != ""
            assert company.corp_name != ""
            assert company.sec_code != ""
            assert company.industry_name != ""


class TestGetCompanyIntegration:
    """get_company() endpoint integration test."""

    def test_正常系_実在コードでCompanyが返される(
        self, client: EdinetClient, sample_edinet_code: str
    ) -> None:
        """実在する EDINET コードで Company 型が返り、コードが一致すること。"""
        company = client.get_company(sample_edinet_code)

        assert isinstance(company, Company)
        assert company.edinet_code == sample_edinet_code
        assert company.corp_name != ""


class TestGetFinancialsIntegration:
    """get_financials() endpoint integration test."""

    def test_正常系_実在コードで財務データリストが返される(
        self, client: EdinetClient, sample_edinet_code: str
    ) -> None:
        """実在コードで list[FinancialRecord] が返り、fiscal_year が非空であること。"""
        records = client.get_financials(sample_edinet_code)

        assert isinstance(records, list)
        # Some companies may have 0 financial records; just verify type
        for record in records:
            assert isinstance(record, FinancialRecord)
            assert record.fiscal_year != ""
            assert record.edinet_code == sample_edinet_code


class TestGetRatiosIntegration:
    """get_ratios() endpoint integration test."""

    def test_正常系_実在コードで財務比率リストが返される(
        self, client: EdinetClient, sample_edinet_code: str
    ) -> None:
        """実在コードで list[RatioRecord] が返ること。"""
        records = client.get_ratios(sample_edinet_code)

        assert isinstance(records, list)
        for record in records:
            assert isinstance(record, RatioRecord)
            assert record.edinet_code == sample_edinet_code


class TestGetAnalysisIntegration:
    """get_analysis() endpoint integration test."""

    def test_正常系_実在コードで分析結果が返される(
        self, client: EdinetClient, sample_edinet_code: str
    ) -> None:
        """実在コードで AnalysisResult が返り、health_score が 0-100 の範囲であること。"""
        result = client.get_analysis(sample_edinet_code)

        assert isinstance(result, AnalysisResult)
        assert result.edinet_code == sample_edinet_code
        assert 0 <= result.health_score <= 100
        assert result.commentary != ""


class TestGetTextBlocksIntegration:
    """get_text_blocks() endpoint integration test."""

    def test_正常系_実在コードでテキストブロックリストが返される(
        self, client: EdinetClient, sample_edinet_code: str
    ) -> None:
        """実在コードで list[TextBlock] が返ること。"""
        blocks = client.get_text_blocks(sample_edinet_code)

        assert isinstance(blocks, list)
        for block in blocks:
            assert isinstance(block, TextBlock)
            assert block.edinet_code == sample_edinet_code


class TestGetRankingIntegration:
    """get_ranking() endpoint integration test."""

    def test_正常系_ROEランキングでランク1から始まるリストが返される(
        self, client: EdinetClient
    ) -> None:
        """'roe' メトリクスで list[RankingEntry] が返り、rank=1 から始まること。"""
        entries = client.get_ranking("roe")

        assert isinstance(entries, list)
        assert len(entries) > 0

        for entry in entries:
            assert isinstance(entry, RankingEntry)
            assert entry.metric == "roe"

        # Verify ranking starts at 1
        ranks = [e.rank for e in entries]
        assert min(ranks) == 1


class TestListIndustriesIntegration:
    """list_industries() endpoint integration test."""

    def test_正常系_業種一覧がIndustryリストで返される(
        self, industries: list[Industry]
    ) -> None:
        """list[Industry] で len > 0 であること。"""
        assert isinstance(industries, list)
        assert len(industries) > 0

        for industry in industries:
            assert isinstance(industry, Industry)
            assert industry.slug != ""
            assert industry.name != ""
            assert industry.company_count >= 0


class TestGetIndustryIntegration:
    """get_industry() endpoint integration test."""

    def test_正常系_実在slugで業種詳細dictが返される(
        self, client: EdinetClient, industries: list[Industry]
    ) -> None:
        """実在する slug で dict が返り、'name' キーを含むこと。"""
        assert len(industries) > 0, "list_industries returned 0 results"
        slug = industries[0].slug

        result = client.get_industry(slug)

        assert isinstance(result, dict)
        assert "name" in result
        assert result["name"] != ""
