"""Unit tests for Japanese market data source integration.

Tests for:
- DataSource enum: JQUANTS and EDINET_API values
- market package exports: JQuantsClient and EdinetApiClient imports
"""

from __future__ import annotations


class TestDataSourceJapanValues:
    """Tests for Japanese data source enum values in DataSource."""

    def test_正常系_JQUANTS値がjquantsである(self) -> None:
        """DataSource.JQUANTS should have value 'jquants'."""
        from market.types import DataSource

        assert DataSource.JQUANTS.value == "jquants"

    def test_正常系_EDINET_API値がedinet_apiである(self) -> None:
        """DataSource.EDINET_API should have value 'edinet_api'."""
        from market.types import DataSource

        assert DataSource.EDINET_API.value == "edinet_api"

    def test_正常系_JQUANTSはstr型Enumメンバーである(self) -> None:
        """DataSource.JQUANTS should be a string enum member."""
        from market.types import DataSource

        assert isinstance(DataSource.JQUANTS, str)
        assert isinstance(DataSource.JQUANTS, DataSource)

    def test_正常系_EDINET_APIはstr型Enumメンバーである(self) -> None:
        """DataSource.EDINET_API should be a string enum member."""
        from market.types import DataSource

        assert isinstance(DataSource.EDINET_API, str)
        assert isinstance(DataSource.EDINET_API, DataSource)


class TestMarketPackageJapanExports:
    """Tests for Japanese module exports from the market package."""

    def test_正常系_JQuantsClientがmarketパッケージからインポートできる(self) -> None:
        """JQuantsClient should be importable from market package."""
        from market import JQuantsClient

        assert JQuantsClient is not None

    def test_正常系_EdinetApiClientがmarketパッケージからインポートできる(self) -> None:
        """EdinetApiClient should be importable from market package."""
        from market import EdinetApiClient

        assert EdinetApiClient is not None

    def test_正常系_JQuantsClientがall_に含まれる(self) -> None:
        """JQuantsClient should be in market.__all__."""
        import market

        assert "JQuantsClient" in market.__all__

    def test_正常系_EdinetApiClientがall_に含まれる(self) -> None:
        """EdinetApiClient should be in market.__all__."""
        import market

        assert "EdinetApiClient" in market.__all__
