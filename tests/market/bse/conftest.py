"""Shared test fixtures for market.bse test suite.

BSE モジュール全体で共有されるフィクスチャを定義する。
"""

from unittest.mock import MagicMock

import pytest

from market.bse.types import BseConfig, RetryConfig


@pytest.fixture()
def bse_config() -> BseConfig:
    """Default BseConfig for tests."""
    return BseConfig()


@pytest.fixture()
def retry_config() -> RetryConfig:
    """Default RetryConfig for tests."""
    return RetryConfig()


@pytest.fixture()
def fast_retry_config() -> RetryConfig:
    """Fast RetryConfig for tests that need minimal delays."""
    return RetryConfig(max_attempts=3, initial_delay=0.01)


@pytest.fixture()
def mock_httpx_response_200() -> MagicMock:
    """Mock httpx.Response with status_code 200."""
    response = MagicMock()
    response.status_code = 200
    response.text = '{"result": "ok"}'
    response.content = b'{"result": "ok"}'
    response.json.return_value = {"result": "ok"}
    return response


@pytest.fixture()
def mock_httpx_response_403() -> MagicMock:
    """Mock httpx.Response with status_code 403."""
    response = MagicMock()
    response.status_code = 403
    response.text = "Forbidden"
    return response


@pytest.fixture()
def mock_httpx_response_429() -> MagicMock:
    """Mock httpx.Response with status_code 429."""
    response = MagicMock()
    response.status_code = 429
    response.text = "Too Many Requests"
    return response


@pytest.fixture()
def mock_httpx_response_500() -> MagicMock:
    """Mock httpx.Response with status_code 500."""
    response = MagicMock()
    response.status_code = 500
    response.text = "Internal Server Error"
    return response
