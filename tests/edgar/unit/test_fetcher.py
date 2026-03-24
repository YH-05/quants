"""Unit tests for edgar.fetcher module.

Tests for EdgarFetcher class including fetch() and fetch_latest() methods
with mocked edgartools Company class and configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

from edgar.config import DEFAULT_RATE_LIMIT_PER_SECOND
from edgar.errors import EdgarError, FilingNotFoundError
from edgar.fetcher import EdgarFetcher
from database.rate_limiter import RateLimiter
from edgar.types import FilingType


class TestEdgarFetcherFetch:
    """Tests for EdgarFetcher.fetch() method."""

    def test_正常系_有効なCIKで10K取得成功(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should return filings for a valid CIK.

        Verify that fetch() calls Company(cik), get_filings(form=),
        and latest(limit) in the correct order.
        """
        mock_company_cls, mock_company, mock_filings = mock_filings_chain
        mock_filing_list = [MagicMock(), MagicMock()]
        mock_filings.latest.return_value = mock_filing_list

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        result = fetcher.fetch("0000320193", FilingType.FORM_10K, limit=5)

        assert len(result) == 2
        mock_company_cls.assert_called_once_with("0000320193")
        mock_company.get_filings.assert_called_once_with(form="10-K")
        mock_filings.latest.assert_called_once_with(5)

    def test_正常系_有効なTickerで10Q取得成功(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should return filings for a valid ticker symbol.

        Verify that fetch() passes the ticker string directly to Company().
        """
        mock_company_cls, mock_company, mock_filings = mock_filings_chain
        mock_filings.latest.return_value = [MagicMock()]

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        result = fetcher.fetch("AAPL", FilingType.FORM_10Q, limit=3)

        assert len(result) == 1
        mock_company_cls.assert_called_once_with("AAPL")
        mock_company.get_filings.assert_called_once_with(form="10-Q")

    def test_正常系_limitで取得件数制限(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should pass limit to filings.latest().

        Verify that the limit parameter is forwarded correctly
        to the edgartools latest() method.
        """
        mock_company_cls, _mock_company, mock_filings = mock_filings_chain

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        fetcher.fetch("AAPL", FilingType.FORM_10K, limit=20)

        mock_filings.latest.assert_called_once_with(20)

    def test_正常系_デフォルトlimitは10件(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should use default limit of 10 when not specified.

        Verify that the default limit parameter value is 10.
        """
        mock_company_cls, _mock_company, mock_filings = mock_filings_chain

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        fetcher.fetch("AAPL", FilingType.FORM_10K)

        mock_filings.latest.assert_called_once_with(10)

    def test_異常系_identity未設定でEdgarError(self) -> None:
        """fetch() should raise EdgarError when identity is not configured.

        Verify that fetch() checks identity configuration before
        attempting to fetch filings.
        """
        fetcher = EdgarFetcher()

        with patch("edgar.fetcher.load_config") as mock_config:
            mock_config.return_value = MagicMock(is_identity_configured=False)
            with pytest.raises(EdgarError, match="identity is not configured"):
                fetcher.fetch("AAPL", FilingType.FORM_10K)

    def test_異常系_not_foundエラーでFilingNotFoundError(
        self,
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should raise FilingNotFoundError for 'not found' errors.

        Verify that ValueError containing 'not found' from edgartools
        is wrapped in FilingNotFoundError.
        """
        mock_company_cls = MagicMock(
            side_effect=ValueError("Company not found in EDGAR")
        )

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        with pytest.raises(FilingNotFoundError):
            fetcher.fetch("INVALID", FilingType.FORM_10K)

    def test_異常系_no_cikエラーでFilingNotFoundError(
        self,
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should raise FilingNotFoundError for 'no cik' errors.

        Verify that errors containing 'no cik' from edgartools
        are wrapped in FilingNotFoundError.
        """
        mock_company_cls = MagicMock(side_effect=ValueError("No CIK found for ticker"))

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        with pytest.raises(FilingNotFoundError):
            fetcher.fetch("ZZZZZ", FilingType.FORM_10K)

    def test_異常系_予期しないエラーでEdgarError(
        self,
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should wrap unexpected errors in EdgarError.

        Verify that non-domain errors (e.g., network timeouts) are
        wrapped in EdgarError with the original error preserved.
        """
        mock_company_cls = MagicMock(side_effect=RuntimeError("Network timeout"))

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        with pytest.raises(EdgarError, match="Failed to fetch filings"):
            fetcher.fetch("AAPL", FilingType.FORM_10K)

    def test_異常系_EdgarErrorはそのまま再送出される(
        self,
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should re-raise EdgarError without wrapping.

        Verify that EdgarError raised during fetching is propagated
        directly without being wrapped in another EdgarError.
        """
        original_error = EdgarError("edgartools module error")
        mock_company_cls = MagicMock(side_effect=original_error)

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        with pytest.raises(EdgarError) as exc_info:
            fetcher.fetch("AAPL", FilingType.FORM_10K)

        assert exc_info.value is original_error

    def test_エッジケース_Filingが0件で空リスト(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should return empty list when no filings found.

        Verify that fetch() returns an empty list when the company
        has no filings matching the specified form type.
        """
        mock_company_cls, _mock_company, _mock_filings = mock_filings_chain

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        result = fetcher.fetch("AAPL", FilingType.FORM_10K)

        assert result == []

    def test_エッジケース_13Fフォームタイプで取得成功(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should correctly pass 13F form type value.

        Verify that fetch() handles all supported FilingType values
        including FORM_13F.
        """
        mock_company_cls, mock_company, mock_filings = mock_filings_chain
        mock_filings.latest.return_value = [MagicMock()]

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        result = fetcher.fetch("AAPL", FilingType.FORM_13F, limit=1)

        assert len(result) == 1
        mock_company.get_filings.assert_called_once_with(form="13F")


class TestEdgarFetcherFetchLatest:
    """Tests for EdgarFetcher.fetch_latest() method."""

    def test_正常系_fetch_latestで最新Filing取得成功(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch_latest() should return the first filing from fetch().

        Verify that fetch_latest() calls fetch(limit=1) and returns
        the first element.
        """
        mock_company_cls, _mock_company, mock_filings = mock_filings_chain
        single_filing = MagicMock()
        mock_filings.latest.return_value = [single_filing]

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        result = fetcher.fetch_latest("AAPL", FilingType.FORM_10K)

        assert result is single_filing
        mock_filings.latest.assert_called_once_with(1)

    def test_エッジケース_fetch_latestでFiling0件でNone(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch_latest() should return None when no filings found.

        Verify that fetch_latest() returns None instead of raising
        an error when the company has no filings.
        """
        mock_company_cls, _mock_company, _mock_filings = mock_filings_chain

        fetcher = EdgarFetcher()
        fetcher._company_cls = mock_company_cls

        result = fetcher.fetch_latest("AAPL", FilingType.FORM_10K)

        assert result is None


class TestEdgarFetcherInit:
    """Tests for EdgarFetcher initialization."""

    def test_正常系_初期化時にcompany_clsはNone(self) -> None:
        """EdgarFetcher should initialize with _company_cls as None.

        Verify lazy loading: Company class is not loaded during init.
        """
        fetcher = EdgarFetcher()
        assert fetcher._company_cls is None

    def test_正常系_get_company_clsで遅延ロード(self) -> None:
        """_get_company_cls() should lazy-load and cache the Company class.

        Verify that _get_company_cls() calls _import_edgartools_company()
        once and caches the result.
        """
        mock_cls = MagicMock()
        fetcher = EdgarFetcher()

        with patch("edgar.fetcher._import_edgartools_company", return_value=mock_cls):
            result1 = fetcher._get_company_cls()
            result2 = fetcher._get_company_cls()

        assert result1 is mock_cls
        assert result2 is mock_cls


class TestEdgarFetcherRateLimit:
    """Tests for EdgarFetcher rate limiting integration."""

    def test_正常系_デフォルトでレートリミッターが設定される(self) -> None:
        """EdgarFetcher should have a rate limiter with default config.

        Verify that EdgarFetcher creates a RateLimiter with the default
        rate of DEFAULT_RATE_LIMIT_PER_SECOND.
        """
        fetcher = EdgarFetcher()
        assert isinstance(fetcher._rate_limiter, RateLimiter)
        assert (
            fetcher._rate_limiter.max_requests_per_second
            == DEFAULT_RATE_LIMIT_PER_SECOND
        )

    def test_正常系_カスタムレートリミッターで初期化(self) -> None:
        """EdgarFetcher should accept a custom rate limiter.

        Verify that a custom RateLimiter instance can be injected.
        """
        custom_limiter = RateLimiter(max_requests_per_second=5)
        fetcher = EdgarFetcher(rate_limiter=custom_limiter)
        assert fetcher._rate_limiter is custom_limiter

    def test_正常系_fetch時にacquireが呼ばれる(
        self,
        mock_filings_chain: tuple[MagicMock, MagicMock, MagicMock],
        patched_identity_config: MagicMock,
    ) -> None:
        """fetch() should call rate_limiter.acquire() before making request.

        Verify that the rate limiter is consulted before each fetch request.
        """
        mock_company_cls, _mock_company, mock_filings = mock_filings_chain
        mock_filings.latest.return_value = [MagicMock()]

        mock_limiter = MagicMock(spec=RateLimiter)
        mock_limiter.max_requests_per_second = 10

        fetcher = EdgarFetcher(rate_limiter=mock_limiter)
        fetcher._company_cls = mock_company_cls

        fetcher.fetch("AAPL", FilingType.FORM_10K, limit=1)

        mock_limiter.acquire.assert_called_once()

    def test_正常系_rate_limit_per_secondパラメータで初期化(self) -> None:
        """EdgarFetcher should accept rate_limit_per_second parameter.

        Verify that an integer rate limit can be passed directly.
        """
        fetcher = EdgarFetcher(rate_limit_per_second=3)
        assert fetcher._rate_limiter.max_requests_per_second == 3


class TestImportEdgartoolsCompany:
    """Tests for _import_edgartools_company() function."""

    @pytest.fixture(autouse=True)
    def _clear_import_cache(self) -> Generator[None, None, None]:
        """Clear _import_edgartools_company lru_cache before/after each test."""
        from edgar.fetcher import _import_edgartools_company

        _import_edgartools_company.cache_clear()
        yield
        _import_edgartools_company.cache_clear()

    def test_異常系_edgartoolsが未インストールでEdgarError(self) -> None:
        """_import_edgartools_company should raise EdgarError when edgartools not found.

        Verify that when PathFinder.find_spec returns None,
        an EdgarError is raised with an install instruction.
        """
        from edgar.fetcher import _import_edgartools_company

        with (
            patch(
                "edgar.fetcher.importlib.machinery.PathFinder.find_spec",
                return_value=None,
            ),
            pytest.raises(EdgarError, match="edgartools is not installed"),
        ):
            _import_edgartools_company()

    def test_異常系_loaderがNoneでEdgarError(self) -> None:
        """_import_edgartools_company should raise EdgarError when loader is None.

        Verify that when the module spec has a None loader,
        an EdgarError is raised.
        """
        from edgar.fetcher import _import_edgartools_company

        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/edgar/__init__.py"
        mock_spec.loader = None

        with (
            patch(
                "edgar.fetcher.importlib.machinery.PathFinder.find_spec",
                return_value=mock_spec,
            ),
            patch(
                "edgar.fetcher.importlib.util.module_from_spec",
                return_value=MagicMock(),
            ),
            pytest.raises(EdgarError, match="loader is None"),
        ):
            _import_edgartools_company()

    def test_異常系_CompanyクラスなしでEdgarError(self) -> None:
        """_import_edgartools_company should raise EdgarError when Company not exported.

        Verify that when the edgartools module does not export a Company
        class, an EdgarError is raised.
        """
        from edgar.fetcher import _import_edgartools_company

        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/edgar/__init__.py"
        mock_loader = MagicMock()
        mock_spec.loader = mock_loader

        mock_module = MagicMock(spec=[])  # Module without 'Company' attribute

        with (
            patch(
                "edgar.fetcher.importlib.machinery.PathFinder.find_spec",
                return_value=mock_spec,
            ),
            patch(
                "edgar.fetcher.importlib.util.module_from_spec",
                return_value=mock_module,
            ),
            pytest.raises(EdgarError, match="does not export 'Company'"),
        ):
            _import_edgartools_company()

    def test_正常系_edgartoolsのCompanyクラスを正常にインポート(self) -> None:
        """_import_edgartools_company should return Company class on success.

        Verify that when edgartools is properly installed and the Company
        class is exported, it is returned successfully.
        """
        from edgar.fetcher import _import_edgartools_company

        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/edgar/__init__.py"
        mock_loader = MagicMock()
        mock_spec.loader = mock_loader

        mock_company_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.Company = mock_company_cls

        with (
            patch(
                "edgar.fetcher.importlib.machinery.PathFinder.find_spec",
                return_value=mock_spec,
            ),
            patch(
                "edgar.fetcher.importlib.util.module_from_spec",
                return_value=mock_module,
            ),
        ):
            result = _import_edgartools_company()

        assert result is mock_company_cls
        mock_loader.exec_module.assert_called_once_with(mock_module)
