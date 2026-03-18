"""Tests for the EDINET DB API HTTP client (EdinetClient).

Tests cover all 10+ API methods, _parse_record generic helper,
_unwrap_response wrapper handling, retry logic with exponential backoff,
polite delay, rate limiter integration, error handling (4xx/5xx),
and context manager support. All HTTP calls are mocked via httpx.Client.

See Also
--------
market.edinet.client : The module under test.
market.edinet.types : EdinetConfig, RetryConfig, and data record types.
market.edinet.errors : Custom exception classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from market.edinet.client import EdinetClient
from market.edinet.constants import DEFAULT_BASE_URL
from market.edinet.errors import (
    EdinetAPIError,
    EdinetRateLimitError,
)
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
    from pathlib import Path


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config(tmp_path: Path) -> EdinetConfig:
    """Create a test EdinetConfig with minimal polite delay."""
    return EdinetConfig(
        api_key="test_key_12345",
        polite_delay=0.0,
        db_path=tmp_path / "edinet.duckdb",
    )


@pytest.fixture
def retry_config() -> RetryConfig:
    """Create a RetryConfig with short delays for testing."""
    return RetryConfig(
        max_attempts=3,
        initial_delay=0.01,
        max_delay=0.05,
        jitter=False,
    )


@pytest.fixture
def mock_rate_limiter() -> MagicMock:
    """Create a mock DailyRateLimiter that always allows requests."""
    limiter = MagicMock()
    limiter.is_allowed.return_value = True
    limiter.get_remaining.return_value = 900
    return limiter


def _make_response(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
) -> httpx.Response:
    """Create a mock httpx.Response.

    Parameters
    ----------
    status_code : int
        HTTP status code.
    json_data : Any
        JSON body (takes precedence over text).
    text : str
        Raw text body.

    Returns
    -------
    httpx.Response
        Configured mock response.
    """
    import json

    if json_data is not None:
        content = json.dumps(json_data).encode("utf-8")
        headers = {"content-type": "application/json"}
    else:
        content = text.encode("utf-8")
        headers = {"content-type": "text/plain"}

    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers,
        request=httpx.Request("GET", f"{DEFAULT_BASE_URL}/test"),
    )


# =============================================================================
# Context Manager
# =============================================================================


class TestContextManager:
    """Test context manager support."""

    def test_正常系_コンテキストマネージャでクライアントを使用できる(
        self, config: EdinetConfig
    ) -> None:
        with EdinetClient(config=config) as client:
            assert client is not None

    def test_正常系_closeでリソースが解放される(self, config: EdinetConfig) -> None:
        client = EdinetClient(config=config)
        client.close()
        # Should not raise


# =============================================================================
# _parse_record
# =============================================================================


class TestParseRecord:
    """Test the _parse_record[T] generic helper method."""

    def test_正常系_既知フィールドのみ抽出される(self, config: EdinetConfig) -> None:
        """Known fields are extracted, unknown fields are ignored."""
        data = {
            "edinet_code": "E00001",
            "sec_code": "10000",
            "name": "テスト株式会社",
            "industry": "情報・通信業",
            "unknown_field_1": "should be ignored",
            "unknown_field_2": 12345,
        }
        with EdinetClient(config=config) as client:
            result = client._parse_record(Company, data)
            assert isinstance(result, Company)
            assert result.edinet_code == "E00001"
            assert result.name == "テスト株式会社"

    def test_正常系_未知フィールドが無視される(self, config: EdinetConfig) -> None:
        """Unknown fields do not cause errors."""
        data = {
            "edinet_code": "E00001",
            "fiscal_year": 2025,
            "revenue": 1_000_000.0,
            "completely_new_api_field": "this should not break",
            "another_unknown": 999,
        }
        with EdinetClient(config=config) as client:
            result = client._parse_record(FinancialRecord, data)
            assert isinstance(result, FinancialRecord)
            assert result.edinet_code == "E00001"
            assert result.fiscal_year == 2025
            assert result.revenue == 1_000_000.0

    def test_正常系_Optionalフィールドが欠落してもデフォルトNone(
        self, config: EdinetConfig
    ) -> None:
        """Optional fields default to None when not present in data."""
        data = {
            "edinet_code": "E00001",
            "fiscal_year": 2025,
        }
        with EdinetClient(config=config) as client:
            result = client._parse_record(FinancialRecord, data)
            assert result.revenue is None
            assert result.net_income is None

    def test_正常系_RatioRecordで未知フィールドが無視される(
        self, config: EdinetConfig
    ) -> None:
        """RatioRecord also ignores unknown fields."""
        data = {
            "edinet_code": "E00001",
            "fiscal_year": 2025,
            "roe": 10.5,
            "new_ratio_field": 42.0,
        }
        with EdinetClient(config=config) as client:
            result = client._parse_record(RatioRecord, data)
            assert isinstance(result, RatioRecord)
            assert result.roe == 10.5


# =============================================================================
# _unwrap_response
# =============================================================================


class TestUnwrapResponse:
    """Test the _unwrap_response helper method."""

    def test_正常系_dataキーでアンラップされる(self, config: EdinetConfig) -> None:
        """Response with 'data' key is unwrapped correctly."""
        response_body = {"data": [{"edinet_code": "E00001"}], "meta": {"total": 1}}
        with EdinetClient(config=config) as client:
            result = client._unwrap_response(response_body)
            assert result == [{"edinet_code": "E00001"}]

    def test_正常系_dataキーがない場合はそのまま返す(
        self, config: EdinetConfig
    ) -> None:
        """Response without 'data' key is returned as-is."""
        response_body = {"edinet_code": "E00001", "name": "Test"}
        with EdinetClient(config=config) as client:
            result = client._unwrap_response(response_body)
            assert result == response_body

    def test_正常系_リスト直接の場合はそのまま返す(self, config: EdinetConfig) -> None:
        """Response that is a plain list is returned as-is."""
        response_body = [{"edinet_code": "E00001"}]
        with EdinetClient(config=config) as client:
            result = client._unwrap_response(response_body)
            assert result == [{"edinet_code": "E00001"}]


# =============================================================================
# get_status()
# =============================================================================


class TestGetStatus:
    """Test the get_status() method."""

    def test_正常系_ステータス情報が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": {
                "available_industries": ["情報・通信業", "輸送用機器"],
                "total_companies": 3848,
            }
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            result = client.get_status()
            assert isinstance(result, dict)
            assert "available_industries" in result
            assert result["total_companies"] == 3848

    def test_正常系_認証ヘッダーなしでもアクセス可能(
        self, config: EdinetConfig
    ) -> None:
        """get_status uses /v1/status which requires no auth."""
        response_data = {"data": {"status": "ok"}}
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ) as mock_get,
        ):
            client.get_status()
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/v1/status"


# =============================================================================
# Authentication
# =============================================================================


class TestAuthentication:
    """Test X-API-Key header is sent with requests."""

    def test_正常系_認証ヘッダーが送信される(
        self,
        config: EdinetConfig,
    ) -> None:
        with EdinetClient(config=config) as client:
            # Verify X-API-Key header is set on the underlying httpx.Client
            assert client._client.headers.get("x-api-key") == "test_key_12345"

    def test_正常系_認証ヘッダーがリクエストに含まれる(
        self,
        config: EdinetConfig,
    ) -> None:
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(
                    json_data={"data": [], "meta": {"total": 0}}
                ),
            ) as mock_get,
        ):
            client.search("テスト")
            mock_get.assert_called_once()
            # Verify the request was made (headers are set at client level)
            call_args = mock_get.call_args
            assert call_args is not None
            assert call_args[0][0] == "/v1/search"


# =============================================================================
# search()
# =============================================================================


class TestSearch:
    """Test the search(query) method."""

    def test_正常系_検索結果が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": [{"edinet_code": "E00001", "name": "テスト株式会社"}],
            "meta": {"query": "テスト", "total": 1},
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            result = client.search("テスト")
            assert len(result) == 1
            assert result[0]["edinet_code"] == "E00001"

    def test_正常系_空の検索結果(self, config: EdinetConfig) -> None:
        response_data: dict[str, Any] = {
            "data": [],
            "meta": {"query": "存在しない企業", "total": 0},
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            result = client.search("存在しない企業")
            assert result == []


# =============================================================================
# list_companies()
# =============================================================================


class TestListCompanies:
    """Test the list_companies() method."""

    def test_正常系_企業一覧が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": [
                {
                    "edinet_code": "E00001",
                    "sec_code": "10000",
                    "name": "テスト株式会社",
                    "industry": "情報・通信業",
                }
            ],
            "meta": {"pagination": {"total": 1}},
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            companies = client.list_companies()
            assert len(companies) == 1
            assert isinstance(companies[0], Company)
            assert companies[0].edinet_code == "E00001"
            assert companies[0].name == "テスト株式会社"


# =============================================================================
# get_company()
# =============================================================================


class TestGetCompany:
    """Test the get_company(code) method."""

    def test_正常系_企業情報が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": {
                "edinet_code": "E00001",
                "sec_code": "10000",
                "name": "テスト株式会社",
                "industry": "情報・通信業",
            }
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            company = client.get_company("E00001")
            assert isinstance(company, Company)
            assert company.edinet_code == "E00001"


# =============================================================================
# get_financials()
# =============================================================================


class TestGetFinancials:
    """Test the get_financials(code) method."""

    def test_正常系_財務データが返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": [
                {
                    "edinet_code": "E00001",
                    "fiscal_year": 2025,
                    "revenue": 1_000_000_000.0,
                    "operating_income": 100_000_000.0,
                    "ordinary_income": 110_000_000.0,
                    "net_income": 70_000_000.0,
                    "total_assets": 5_000_000_000.0,
                    "net_assets": 2_000_000_000.0,
                    "shareholders_equity": 1_800_000_000.0,
                    "cf_operating": 150_000_000.0,
                    "cf_investing": -80_000_000.0,
                    "cf_financing": -50_000_000.0,
                    "eps": 350.0,
                    "bps": 9_000.0,
                    "dividend_per_share": 100.0,
                    "num_employees": 5_000,
                    "capex": 80_000_000.0,
                    "depreciation": 60_000_000.0,
                    "rnd_expenses": 30_000_000.0,
                    "goodwill": 10_000_000.0,
                }
            ]
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            records = client.get_financials("E00001")
            assert len(records) == 1
            assert isinstance(records[0], FinancialRecord)
            assert records[0].revenue == 1_000_000_000.0

    def test_正常系_未知フィールドが含まれても正常に処理される(
        self, config: EdinetConfig
    ) -> None:
        """API response with unknown fields should not break parsing."""
        response_data = {
            "data": [
                {
                    "edinet_code": "E00001",
                    "fiscal_year": 2025,
                    "revenue": 500_000.0,
                    "future_api_field": "should_be_ignored",
                    "another_new_field": 42,
                }
            ]
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            records = client.get_financials("E00001")
            assert len(records) == 1
            assert records[0].revenue == 500_000.0


# =============================================================================
# get_ratios()
# =============================================================================


class TestGetRatios:
    """Test the get_ratios(code) method."""

    def test_正常系_財務比率データが返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": [
                {
                    "edinet_code": "E00001",
                    "fiscal_year": 2025,
                    "roe": 3.89,
                    "roa": 1.40,
                    "net_margin": 7.0,
                    "equity_ratio": 36.0,
                    "payout_ratio": 28.57,
                    "asset_turnover": 0.20,
                    "eps": 350.0,
                    "bps": 9_000.0,
                    "dividend_per_share": 100.0,
                    "per": 15.0,
                }
            ]
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            records = client.get_ratios("E00001")
            assert len(records) == 1
            assert isinstance(records[0], RatioRecord)
            assert records[0].roe == 3.89

    def test_正常系_未知フィールドが含まれても正常に処理される(
        self, config: EdinetConfig
    ) -> None:
        """RatioRecord parsing ignores unknown API fields."""
        response_data = {
            "data": [
                {
                    "edinet_code": "E00001",
                    "fiscal_year": 2025,
                    "roe": 5.0,
                    "new_growth_metric": 12.3,
                }
            ]
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            records = client.get_ratios("E00001")
            assert len(records) == 1
            assert records[0].roe == 5.0


# =============================================================================
# get_analysis()
# =============================================================================


class TestGetAnalysis:
    """Test the get_analysis(code) method."""

    def test_正常系_分析結果が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "ai_summary": {
                "generated_at": "2026-03-15 21:02:18",
                "has_qualitative": True,
                "model_version": "claude-opus-4-6-v2",
                "text": "健全な財務状況です。",
                "text_en": "The company is financially healthy.",
            },
            "history": [
                {
                    "benchmark_strong_count": 2,
                    "benchmark_summary": "強みが多い",
                    "benchmark_weak_count": 0,
                    "credit_flag_count": 0,
                    "credit_rating": "S",
                    "credit_score": 93,
                    "fiscal_year": 2025,
                    "health_score": 93.0,
                }
            ],
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            result = client.get_analysis("E00001")
            assert isinstance(result, AnalysisResult)
            assert result.edinet_code == "E00001"
            assert result.health_score == 93.0
            assert result.credit_score == 93
            assert result.credit_rating == "S"
            assert result.benchmark_summary == "強みが多い"
            assert result.commentary == "健全な財務状況です。"
            assert result.fiscal_year == 2025

    def test_正常系_空のhistoryでも処理できる(self, config: EdinetConfig) -> None:
        """history が空の場合でもエラーにならないこと。"""
        response_data: dict[str, Any] = {
            "ai_summary": {"text": "分析テキスト"},
            "history": [],
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            result = client.get_analysis("E00001")
            assert isinstance(result, AnalysisResult)
            assert result.edinet_code == "E00001"
            assert result.commentary == "分析テキスト"
            assert result.health_score is None
            assert result.fiscal_year is None


# =============================================================================
# get_text_blocks()
# =============================================================================


class TestGetTextBlocks:
    """Test the get_text_blocks(code) method."""

    def test_正常系_テキストブロックが返される(self, config: EdinetConfig) -> None:
        response_data = [
            {"section": "事業の内容", "text": "事業概要テキスト"},
            {"section": "経営者による分析", "text": "経営分析テキスト"},
        ]
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            blocks = client.get_text_blocks("E00001")
            assert len(blocks) == 2
            assert isinstance(blocks[0], TextBlock)
            assert blocks[0].edinet_code == "E00001"
            assert blocks[0].section == "事業の内容"
            assert blocks[0].text == "事業概要テキスト"
            assert blocks[1].section == "経営者による分析"


# =============================================================================
# get_ranking()
# =============================================================================


class TestGetRanking:
    """Test the get_ranking(metric) method."""

    def test_正常系_ランキングが返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": [
                {
                    "metric": "roe",
                    "rank": 1,
                    "edinet_code": "E00001",
                    "name": "テスト株式会社",
                    "value": 25.5,
                }
            ]
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            entries = client.get_ranking("roe")
            assert len(entries) == 1
            assert isinstance(entries[0], RankingEntry)
            assert entries[0].rank == 1

    def test_異常系_無効なメトリクスでValidationError(
        self, config: EdinetConfig
    ) -> None:
        with (
            EdinetClient(config=config) as client,
            pytest.raises(ValueError, match="Invalid ranking metric"),
        ):
            client.get_ranking("invalid_metric")


# =============================================================================
# list_industries()
# =============================================================================


class TestListIndustries:
    """Test the list_industries() method."""

    def test_正常系_業種一覧が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": [
                {
                    "slug": "information-communication",
                    "name": "情報・通信業",
                    "company_count": 500,
                }
            ]
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            industries = client.list_industries()
            assert len(industries) == 1
            assert isinstance(industries[0], Industry)
            assert industries[0].slug == "information-communication"


# =============================================================================
# get_industry()
# =============================================================================


class TestGetIndustry:
    """Test the get_industry(slug) method."""

    def test_正常系_業種詳細が返される(self, config: EdinetConfig) -> None:
        response_data = {
            "data": {
                "slug": "information-communication",
                "name": "情報・通信業",
                "company_count": 500,
                "companies": [{"edinet_code": "E00001"}],
                "averages": {"roe": 10.0},
            }
        }
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
        ):
            result = client.get_industry("information-communication")
            assert isinstance(result, dict)
            assert result["slug"] == "information-communication"


# =============================================================================
# Retry (exponential backoff)
# =============================================================================


class TestRetry:
    """Test retry logic with exponential backoff."""

    def test_正常系_5xxでリトライ後に成功(
        self,
        config: EdinetConfig,
        retry_config: RetryConfig,
    ) -> None:
        responses = [
            _make_response(status_code=500, json_data={"error": "ISE"}),
            _make_response(json_data={"data": [], "meta": {"total": 0}}),
        ]
        with (
            EdinetClient(config=config, retry_config=retry_config) as client,
            patch.object(client._client, "get", side_effect=responses),
        ):
            result = client.search("test")
            assert result == []

    def test_異常系_5xxで最大リトライ後にAPIError(
        self,
        config: EdinetConfig,
        retry_config: RetryConfig,
    ) -> None:
        responses = [
            _make_response(status_code=500, json_data={"error": "ISE"})
            for _ in range(retry_config.max_attempts)
        ]
        with (
            EdinetClient(config=config, retry_config=retry_config) as client,
            patch.object(client._client, "get", side_effect=responses),
            pytest.raises(EdinetAPIError) as exc_info,
        ):
            client.search("test")
        assert exc_info.value.status_code == 500

    def test_異常系_ネットワークエラーでリトライ(
        self,
        config: EdinetConfig,
        retry_config: RetryConfig,
    ) -> None:
        effects: list[Any] = [
            httpx.ConnectError("Connection refused"),
            _make_response(json_data={"data": [], "meta": {"total": 0}}),
        ]
        with (
            EdinetClient(config=config, retry_config=retry_config) as client,
            patch.object(client._client, "get", side_effect=effects),
        ):
            result = client.search("test")
            assert result == []

    def test_異常系_タイムアウトでリトライ(
        self,
        config: EdinetConfig,
        retry_config: RetryConfig,
    ) -> None:
        effects: list[Any] = [
            httpx.ReadTimeout("Read timed out"),
            _make_response(json_data={"data": [], "meta": {"total": 0}}),
        ]
        with (
            EdinetClient(config=config, retry_config=retry_config) as client,
            patch.object(client._client, "get", side_effect=effects),
        ):
            result = client.search("test")
            assert result == []


# =============================================================================
# No retry on 4xx
# =============================================================================


class TestNoRetryOn4xx:
    """Test that 4xx errors are NOT retried."""

    def test_異常系_4xxでリトライしない(
        self,
        config: EdinetConfig,
        retry_config: RetryConfig,
    ) -> None:
        with (
            EdinetClient(config=config, retry_config=retry_config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(
                    status_code=400,
                    json_data={"error": "Bad Request"},
                ),
            ) as mock_get,
            pytest.raises(EdinetAPIError) as exc_info,
        ):
            client.search("test")
        assert exc_info.value.status_code == 400
        # Should only be called once (no retry)
        assert mock_get.call_count == 1

    def test_異常系_401でEdinetAPIError(self, config: EdinetConfig) -> None:
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(
                    status_code=401,
                    json_data={"error": "Unauthorized"},
                ),
            ),
            pytest.raises(EdinetAPIError) as exc_info,
        ):
            client.list_companies()
        assert exc_info.value.status_code == 401

    def test_異常系_429でEdinetRateLimitError(self, config: EdinetConfig) -> None:
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(
                    status_code=429,
                    json_data={"error": "Too Many Requests"},
                ),
            ),
            pytest.raises(EdinetRateLimitError),
        ):
            client.list_companies()


# =============================================================================
# Polite delay
# =============================================================================


class TestPoliteDelay:
    """Test polite delay between requests."""

    def test_正常系_ポリートディレイが適用される(self, tmp_path: Path) -> None:
        polite_delay = 0.1
        cfg = EdinetConfig(
            api_key="test_key",
            polite_delay=polite_delay,
            db_path=tmp_path / "edinet.duckdb",
        )
        response_data: dict[str, Any] = {"results": [], "total": 0}
        with (
            EdinetClient(config=cfg) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(json_data=response_data),
            ),
            patch("market.edinet.client.time.sleep") as mock_sleep,
        ):
            client.search("test1")
            client.search("test2")
            # Verify that sleep was called with a positive delay
            # (polite delay is applied between consecutive requests)
            assert mock_sleep.call_count >= 1
            sleep_arg = mock_sleep.call_args[0][0]
            assert sleep_arg > 0


# =============================================================================
# Rate limiter integration
# =============================================================================


class TestRateLimiterIntegration:
    """Test DailyRateLimiter integration."""

    def test_正常系_レートリミッターが呼び出される(
        self,
        config: EdinetConfig,
        mock_rate_limiter: MagicMock,
    ) -> None:
        with (
            EdinetClient(config=config, rate_limiter=mock_rate_limiter) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(
                    json_data={"data": [], "meta": {"total": 0}}
                ),
            ),
        ):
            client.search("test")
            mock_rate_limiter.is_allowed.assert_called()
            mock_rate_limiter.record_call.assert_called_once()

    def test_異常系_レート制限超過でEdinetRateLimitError(
        self,
        config: EdinetConfig,
    ) -> None:
        limiter = MagicMock()
        limiter.is_allowed.return_value = False
        limiter.get_remaining.return_value = 0
        limiter._calls = 950
        limiter.daily_limit = 1000
        limiter.safe_margin = 50
        with (
            EdinetClient(config=config, rate_limiter=limiter) as client,
            pytest.raises(
                EdinetRateLimitError,
            ),
        ):
            client.search("test")

    def test_正常系_レートリミッターなしでも動作する(
        self,
        config: EdinetConfig,
    ) -> None:
        """Client should work without a rate limiter."""
        with (
            EdinetClient(config=config) as client,
            patch.object(
                client._client,
                "get",
                return_value=_make_response(
                    json_data={"data": [], "meta": {"total": 0}}
                ),
            ),
        ):
            result = client.search("test")
            assert result == []


# =============================================================================
# get_remaining_calls()
# =============================================================================


class TestGetRemainingCalls:
    """Test the get_remaining_calls() method."""

    def test_正常系_レートリミッターありで残り回数を返す(
        self,
        config: EdinetConfig,
        mock_rate_limiter: MagicMock,
    ) -> None:
        mock_rate_limiter.get_remaining.return_value = 800
        with EdinetClient(config=config, rate_limiter=mock_rate_limiter) as client:
            assert client.get_remaining_calls() == 800

    def test_正常系_レートリミッターなしでNoneを返す(
        self,
        config: EdinetConfig,
    ) -> None:
        with EdinetClient(config=config) as client:
            assert client.get_remaining_calls() is None
