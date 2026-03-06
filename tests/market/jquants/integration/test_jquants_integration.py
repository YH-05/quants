"""Integration tests for J-Quants API client.

These tests require valid J-Quants API credentials set via
environment variables:
- JQUANTS_MAIL_ADDRESS
- JQUANTS_PASSWORD

Run with: uv run pytest tests/market/jquants/integration/ -m integration -v
"""

import os
from collections.abc import Generator

import pandas as pd
import pytest

from market.jquants.client import JQuantsClient
from market.jquants.types import FetchOptions, JQuantsConfig

# Skip all tests in this module if credentials are not available
pytestmark = pytest.mark.integration


def _has_credentials() -> bool:
    """Check if J-Quants credentials are available."""
    return bool(
        os.environ.get("JQUANTS_MAIL_ADDRESS") and os.environ.get("JQUANTS_PASSWORD")
    )


@pytest.fixture
def client() -> Generator[JQuantsClient]:
    """Create a JQuantsClient with real credentials."""
    if not _has_credentials():
        pytest.skip("J-Quants credentials not available")
    config = JQuantsConfig()
    client = JQuantsClient(config=config)
    yield client
    client.close()


class TestListedInfo:
    """Integration tests for listed info endpoint."""

    @pytest.mark.skipif(not _has_credentials(), reason="No J-Quants credentials")
    def test_正常系_全銘柄取得(self, client: JQuantsClient) -> None:
        df = client.get_listed_info(
            options=FetchOptions(use_cache=False),
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "Code" in df.columns


class TestDailyQuotes:
    """Integration tests for daily quotes endpoint."""

    @pytest.mark.skipif(not _has_credentials(), reason="No J-Quants credentials")
    def test_正常系_日足データ取得(self, client: JQuantsClient) -> None:
        df = client.get_daily_quotes(
            "7203",
            "2024-01-04",
            "2024-01-31",
            options=FetchOptions(use_cache=False),
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


class TestTradingCalendar:
    """Integration tests for trading calendar endpoint."""

    @pytest.mark.skipif(not _has_credentials(), reason="No J-Quants credentials")
    def test_正常系_取引カレンダー取得(self, client: JQuantsClient) -> None:
        df = client.get_trading_calendar(
            options=FetchOptions(use_cache=False),
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
