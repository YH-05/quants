"""Tests for market.eodhd.types module."""

import logging
from unittest.mock import patch

import pytest

from market.eodhd.constants import EODHD_API_KEY_ENV
from market.eodhd.types import EodhdConfig


class TestEodhdConfig:
    """Tests for EodhdConfig dataclass."""

    def test_正常系_デフォルト値_環境変数未設定(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            config = EodhdConfig()
            assert config.api_key == ""
            assert config.base_url == "https://eodhd.com/api"
            assert config.timeout == 30.0
            assert config.fmt == "json"

    def test_正常系_カスタム値(self) -> None:
        config = EodhdConfig(
            api_key="demo",
            base_url="https://custom.api.com",
            timeout=60.0,
            fmt="csv",
        )
        assert config.api_key == "demo"
        assert config.base_url == "https://custom.api.com"
        assert config.timeout == 60.0
        assert config.fmt == "csv"

    def test_正常系_frozen(self) -> None:
        config = EodhdConfig(api_key="test")
        with pytest.raises(AttributeError):
            config.timeout = 60.0

    def test_正常系_api_keyがreprに含まれない(self) -> None:
        config = EodhdConfig(api_key="secret_key_123")
        repr_str = repr(config)
        assert "secret_key_123" not in repr_str

    def test_異常系_タイムアウトが範囲外_小さすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            EodhdConfig(api_key="test", timeout=0.5)

    def test_異常系_タイムアウトが範囲外_大きすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            EodhdConfig(api_key="test", timeout=400.0)

    def test_異常系_不正なフォーマット(self) -> None:
        with pytest.raises(ValueError, match="fmt must be"):
            EodhdConfig(api_key="test", fmt="xml")

    def test_正常系_タイムアウト境界値_最小(self) -> None:
        config = EodhdConfig(api_key="test", timeout=1.0)
        assert config.timeout == 1.0

    def test_正常系_タイムアウト境界値_最大(self) -> None:
        config = EodhdConfig(api_key="test", timeout=300.0)
        assert config.timeout == 300.0

    def test_正常系_csvフォーマット(self) -> None:
        config = EodhdConfig(api_key="test", fmt="csv")
        assert config.fmt == "csv"


class TestEodhdConfigApiKeyEnvFallback:
    """Tests for EodhdConfig api_key environment variable fallback."""

    def test_正常系_環境変数からapi_keyを取得(self) -> None:
        """api_key が空文字のとき EODHD_API_KEY 環境変数からフォールバック取得する。"""
        with patch.dict("os.environ", {EODHD_API_KEY_ENV: "env_key_abc"}):
            config = EodhdConfig()
            assert config.api_key == "env_key_abc"

    def test_正常系_明示的api_keyが環境変数より優先(self) -> None:
        """明示的に渡された api_key は環境変数より優先される。"""
        with patch.dict("os.environ", {EODHD_API_KEY_ENV: "env_key"}):
            config = EodhdConfig(api_key="explicit_key")
            assert config.api_key == "explicit_key"

    def test_正常系_環境変数が空文字の場合はフォールバックしない(self) -> None:
        """環境変数が空文字の場合、api_key は空文字のまま。"""
        with patch.dict("os.environ", {EODHD_API_KEY_ENV: ""}):
            config = EodhdConfig()
            assert config.api_key == ""

    def test_正常系_環境変数未設定の場合はapi_keyが空文字(self) -> None:
        """環境変数が設定されていない場合、api_key は空文字のまま。"""
        with patch.dict("os.environ", {}, clear=True):
            config = EodhdConfig()
            assert config.api_key == ""

    def test_正常系_環境変数のスペースのみの場合はフォールバックしない(self) -> None:
        """環境変数がスペースのみの場合、strip 後に空文字となるためフォールバックしない。"""
        with patch.dict("os.environ", {EODHD_API_KEY_ENV: "   "}):
            config = EodhdConfig()
            assert config.api_key == ""


class TestEodhdConfigApiKeyEmptyWarning:
    """Tests for EodhdConfig api_key empty string warning log."""

    def test_正常系_api_keyが空文字のとき警告ログが出力される(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """api_key が最終的に空文字の場合、警告ログが出力される。"""
        with patch.dict("os.environ", {}, clear=True), caplog.at_level(logging.WARNING):
            EodhdConfig()
        assert any(
            "EODHD_API_KEY" in record.message
            for record in caplog.records
            if record.levelno >= logging.WARNING
        )

    def test_正常系_api_keyが設定済みのとき警告ログが出力されない(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """api_key が非空の場合、警告ログは出力されない。"""
        with caplog.at_level(logging.WARNING):
            EodhdConfig(api_key="valid_key")
        warning_records = [
            r
            for r in caplog.records
            if r.levelno >= logging.WARNING and "EODHD_API_KEY" in r.message
        ]
        assert len(warning_records) == 0

    def test_正常系_環境変数からapi_keyを取得した場合は警告ログが出力されない(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """環境変数から api_key を取得した場合、警告ログは出力されない。"""
        with (
            patch.dict("os.environ", {EODHD_API_KEY_ENV: "env_key"}),
            caplog.at_level(logging.WARNING),
        ):
            EodhdConfig()
        warning_records = [
            r
            for r in caplog.records
            if r.levelno >= logging.WARNING and "EODHD_API_KEY" in r.message
        ]
        assert len(warning_records) == 0
