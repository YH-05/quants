"""Tests for market.eodhd.types module."""

import pytest

from market.eodhd.types import EodhdConfig


class TestEodhdConfig:
    """Tests for EodhdConfig dataclass."""

    def test_正常系_デフォルト値(self) -> None:
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
        config = EodhdConfig()
        with pytest.raises(AttributeError):
            config.timeout = 60.0

    def test_正常系_api_keyがreprに含まれない(self) -> None:
        config = EodhdConfig(api_key="secret_key_123")
        repr_str = repr(config)
        assert "secret_key_123" not in repr_str

    def test_異常系_タイムアウトが範囲外_小さすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            EodhdConfig(timeout=0.5)

    def test_異常系_タイムアウトが範囲外_大きすぎ(self) -> None:
        with pytest.raises(ValueError, match="timeout must be between"):
            EodhdConfig(timeout=400.0)

    def test_異常系_不正なフォーマット(self) -> None:
        with pytest.raises(ValueError, match="fmt must be"):
            EodhdConfig(fmt="xml")

    def test_正常系_タイムアウト境界値_最小(self) -> None:
        config = EodhdConfig(timeout=1.0)
        assert config.timeout == 1.0

    def test_正常系_タイムアウト境界値_最大(self) -> None:
        config = EodhdConfig(timeout=300.0)
        assert config.timeout == 300.0

    def test_正常系_csvフォーマット(self) -> None:
        config = EodhdConfig(fmt="csv")
        assert config.fmt == "csv"
