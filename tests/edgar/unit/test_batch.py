"""Unit tests for edgar.batch module.

Tests for BatchFetcher, BatchExtractor classes, and _run_batch helper,
including parallel fetch/extraction, partial failure handling, and edge cases.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from database.rate_limiter import RateLimiter
from edgar.batch import BatchExtractor, BatchFetcher, _run_batch
from edgar.fetcher import EdgarFetcher
from edgar.types import FilingType


class TestRunBatch:
    """Tests for _run_batch helper function."""

    def test_正常系_複数アイテムを並列処理し結果をdict返却(self) -> None:
        """_run_batch should process items in parallel and return results dict."""

        def task_fn(item: str) -> str:
            return f"result_{item}"

        results = _run_batch(
            items=["a", "b", "c"],
            key_fn=lambda item: item,
            task_fn=task_fn,
            desc="Testing",
            max_workers=2,
        )

        assert len(results) == 3
        assert results["a"] == "result_a"
        assert results["b"] == "result_b"
        assert results["c"] == "result_c"

    def test_正常系_key_fnでカスタムキーを使用(self) -> None:
        """_run_batch should use key_fn to determine result dict keys."""
        items = [{"id": "x", "val": 1}, {"id": "y", "val": 2}]

        def task_fn(item: dict) -> int:
            return item["val"] * 10

        results = _run_batch(
            items=items,
            key_fn=lambda item: item["id"],
            task_fn=task_fn,
            desc="Testing",
            max_workers=2,
        )

        assert results["x"] == 10
        assert results["y"] == 20

    def test_異常系_一部失敗時にExceptionを格納し他は続行(self) -> None:
        """_run_batch should store Exception for failed items, continue others."""

        def task_fn(item: str) -> str:
            if item == "fail":
                msg = "Intentional error"
                raise RuntimeError(msg)
            return f"ok_{item}"

        results = _run_batch(
            items=["good", "fail"],
            key_fn=lambda item: item,
            task_fn=task_fn,
            desc="Testing",
            max_workers=2,
        )

        assert len(results) == 2
        assert results["good"] == "ok_good"
        assert isinstance(results["fail"], Exception)

    def test_異常系_全アイテム失敗でも全Exceptionを保持(self) -> None:
        """_run_batch should store all Exceptions when all items fail."""

        def task_fn(item: str) -> str:
            msg = "All fail"
            raise RuntimeError(msg)

        results = _run_batch(
            items=["a", "b"],
            key_fn=lambda item: item,
            task_fn=task_fn,
            desc="Testing",
            max_workers=2,
        )

        assert len(results) == 2
        for value in results.values():
            assert isinstance(value, Exception)

    def test_エッジケース_空リストで空dict返却(self) -> None:
        """_run_batch should return empty dict for empty input."""
        results: dict[str, str | Exception] = _run_batch(
            items=[],
            key_fn=lambda item: str(item),
            task_fn=lambda item: str(item),
            desc="Testing",
            max_workers=2,
        )
        assert results == {}

    def test_エッジケース_max_workers_1でも正常動作(self) -> None:
        """_run_batch should work correctly with max_workers=1."""

        def task_fn(item: str) -> str:
            return f"result_{item}"

        results = _run_batch(
            items=["a", "b"],
            key_fn=lambda item: item,
            task_fn=task_fn,
            desc="Testing",
            max_workers=1,
        )

        assert len(results) == 2
        assert results["a"] == "result_a"
        assert results["b"] == "result_b"


class TestBatchFetcher:
    """Tests for BatchFetcher class."""

    def test_正常系_fetch_batchで複数CIK並列取得(self) -> None:
        """fetch_batch should return results for multiple tickers."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = [
            [MagicMock(), MagicMock()],  # AAPL: 2 filings
            [MagicMock()],  # MSFT: 1 filing
        ]

        batch = BatchFetcher(fetcher=mock_fetcher)
        results = batch.fetch_batch(
            ["AAPL", "MSFT"],
            FilingType.FORM_10K,
            limit=5,
            max_workers=2,
        )

        assert len(results) == 2
        assert "AAPL" in results
        assert "MSFT" in results
        assert not isinstance(results["AAPL"], Exception)
        assert not isinstance(results["MSFT"], Exception)

    def test_正常系_fetch_latest_batchで複数CIK最新取得(self) -> None:
        """fetch_latest_batch should return latest filing per ticker."""
        mock_fetcher = MagicMock()
        mock_filing_aapl = MagicMock()
        mock_filing_msft = MagicMock()
        mock_fetcher.fetch_latest.side_effect = [
            mock_filing_aapl,
            mock_filing_msft,
        ]

        batch = BatchFetcher(fetcher=mock_fetcher)
        results = batch.fetch_latest_batch(
            ["AAPL", "MSFT"],
            FilingType.FORM_10K,
            max_workers=2,
        )

        assert len(results) == 2
        assert "AAPL" in results
        assert "MSFT" in results
        # Both should be successful (not exceptions)
        for value in results.values():
            assert not isinstance(value, Exception)

    def test_正常系_max_workersで並列度制御(self) -> None:
        """fetch_batch should respect max_workers parameter."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = []

        batch = BatchFetcher(fetcher=mock_fetcher)
        # Should not raise even with max_workers=1
        results = batch.fetch_batch(
            ["AAPL"],
            FilingType.FORM_10K,
            max_workers=1,
        )

        assert len(results) == 1
        assert "AAPL" in results
        assert results["AAPL"] == []

    def test_異常系_一部CIK失敗時も他のCIK取得続行(self) -> None:
        """fetch_batch should continue processing when some tickers fail."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = [
            [MagicMock()],  # AAPL succeeds
            RuntimeError("Network error"),  # INVALID fails
        ]

        batch = BatchFetcher(fetcher=mock_fetcher)
        results = batch.fetch_batch(
            ["AAPL", "INVALID"],
            FilingType.FORM_10K,
            max_workers=2,
        )

        assert len(results) == 2
        # One should be successful, one should be an exception
        exceptions = [v for v in results.values() if isinstance(v, Exception)]
        successes = [v for v in results.values() if not isinstance(v, Exception)]
        assert len(exceptions) == 1
        assert len(successes) == 1

    def test_異常系_全CIK失敗時もException保持(self) -> None:
        """fetch_batch should store all exceptions when all tickers fail."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = RuntimeError("All failed")

        batch = BatchFetcher(fetcher=mock_fetcher)
        results = batch.fetch_batch(
            ["INVALID1", "INVALID2"],
            FilingType.FORM_10K,
            max_workers=2,
        )

        assert len(results) == 2
        for value in results.values():
            assert isinstance(value, Exception)

    def test_エッジケース_空リスト入力で空dict(self) -> None:
        """fetch_batch should return empty dict for empty input."""
        mock_fetcher = MagicMock()
        batch = BatchFetcher(fetcher=mock_fetcher)
        results = batch.fetch_batch([], FilingType.FORM_10K)
        assert results == {}

    def test_エッジケース_fetch_latest_batch空リスト入力で空dict(self) -> None:
        """fetch_latest_batch should return empty dict for empty input."""
        mock_fetcher = MagicMock()
        batch = BatchFetcher(fetcher=mock_fetcher)
        results = batch.fetch_latest_batch([], FilingType.FORM_10K)
        assert results == {}

    def test_エッジケース_デフォルトFetcher作成(self) -> None:
        """BatchFetcher should create default EdgarFetcher when None."""
        batch = BatchFetcher()
        assert batch._fetcher is not None


class TestBatchExtractor:
    """Tests for BatchExtractor class."""

    def test_正常系_extract_text_batchで複数Filing並列抽出(self) -> None:
        """extract_text_batch should extract text from multiple filings."""
        mock_text_ext = MagicMock()
        mock_text_ext.extract_text.side_effect = ["Text content 1", "Text content 2"]

        filing1 = MagicMock()
        filing1.accession_number = "0001-24-000001"
        filing2 = MagicMock()
        filing2.accession_number = "0001-24-000002"

        batch = BatchExtractor(text_extractor=mock_text_ext)
        results = batch.extract_text_batch([filing1, filing2], max_workers=2)

        assert len(results) == 2
        assert "0001-24-000001" in results
        assert "0001-24-000002" in results
        # Both values should be strings (not exceptions)
        for value in results.values():
            assert isinstance(value, str)

    def test_正常系_extract_sections_batchで複数セクション並列抽出(self) -> None:
        """extract_sections_batch should extract sections from multiple filings."""
        mock_section_ext = MagicMock()
        mock_section_ext.extract_section.return_value = "Section text"

        filing1 = MagicMock()
        filing1.accession_number = "0001-24-000001"

        batch = BatchExtractor(section_extractor=mock_section_ext)
        results = batch.extract_sections_batch(
            [filing1],
            ["item_1", "item_7"],
            max_workers=2,
        )

        assert len(results) == 1
        assert "0001-24-000001" in results
        section_result = results["0001-24-000001"]
        assert not isinstance(section_result, Exception)
        assert "item_1" in section_result
        assert "item_7" in section_result

    def test_異常系_一部Filing抽出失敗時も他のFiling処理続行(self) -> None:
        """extract_text_batch should continue when some filings fail."""
        mock_text_ext = MagicMock()
        mock_text_ext.extract_text.side_effect = [
            "Success text",
            RuntimeError("Extraction failed"),
        ]

        filing1 = MagicMock()
        filing1.accession_number = "0001-24-000001"
        filing2 = MagicMock()
        filing2.accession_number = "0001-24-000002"

        batch = BatchExtractor(text_extractor=mock_text_ext)
        results = batch.extract_text_batch([filing1, filing2], max_workers=2)

        assert len(results) == 2
        exceptions = [v for v in results.values() if isinstance(v, Exception)]
        successes = [v for v in results.values() if not isinstance(v, Exception)]
        assert len(exceptions) == 1
        assert len(successes) == 1

    def test_エッジケース_extract_text_batch空リスト入力で空dict(self) -> None:
        """extract_text_batch should return empty dict for empty input."""
        mock_text_ext = MagicMock()
        batch = BatchExtractor(text_extractor=mock_text_ext)
        results = batch.extract_text_batch([])
        assert results == {}

    def test_エッジケース_extract_sections_batch空リスト入力で空dict(self) -> None:
        """extract_sections_batch should return empty dict for empty input."""
        mock_section_ext = MagicMock()
        batch = BatchExtractor(section_extractor=mock_section_ext)
        results = batch.extract_sections_batch([], ["item_1"])
        assert results == {}

    def test_エッジケース_デフォルトExtractor作成(self) -> None:
        """BatchExtractor should create default extractors when None."""
        batch = BatchExtractor()
        assert batch._text_extractor is not None
        assert batch._section_extractor is not None


class TestBatchFetcherRateLimit:
    """Tests for BatchFetcher rate limiting compliance."""

    def test_正常系_BatchFetcherがEdgarFetcherのレートリミッターを使用(self) -> None:
        """BatchFetcher should use EdgarFetcher's rate limiter.

        Verify that BatchFetcher delegates rate limiting to the underlying
        EdgarFetcher, which has its own RateLimiter instance.
        """
        custom_limiter = RateLimiter(max_requests_per_second=5)
        fetcher = EdgarFetcher(rate_limiter=custom_limiter)
        batch = BatchFetcher(fetcher=fetcher)

        # BatchFetcher uses the EdgarFetcher which has the rate limiter
        assert batch._fetcher._rate_limiter is custom_limiter

    def test_正常系_fetch_batch時にレートリミッターが呼ばれる(self) -> None:
        """fetch_batch should trigger rate limiter via EdgarFetcher.fetch().

        Verify that each call to EdgarFetcher.fetch() within fetch_batch
        goes through the rate limiter.
        """
        mock_limiter = MagicMock(spec=RateLimiter)
        mock_limiter.max_requests_per_second = 10

        mock_filings = MagicMock()
        mock_filings.latest.return_value = [MagicMock()]
        mock_company = MagicMock()
        mock_company.get_filings.return_value = mock_filings
        mock_company_cls = MagicMock(return_value=mock_company)

        from unittest.mock import patch

        fetcher = EdgarFetcher(rate_limiter=mock_limiter)
        fetcher._company_cls = mock_company_cls

        batch = BatchFetcher(fetcher=fetcher)

        with patch("edgar.fetcher.load_config") as mock_config:
            mock_config.return_value = MagicMock(is_identity_configured=True)
            batch.fetch_batch(
                ["AAPL", "MSFT"],
                FilingType.FORM_10K,
                limit=1,
                max_workers=2,
            )

        # Rate limiter acquire() should be called once per ticker
        assert mock_limiter.acquire.call_count == 2
