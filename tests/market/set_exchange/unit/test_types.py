"""SetConfig のテスト。"""

from dataclasses import FrozenInstanceError

import pytest

from market.asean_common.types import ExchangeConfig
from market.set_exchange.types import SetConfig


class TestSetConfig:
    """SetConfig dataclass のテスト。"""

    def test_正常系_ExchangeConfigを継承している(self) -> None:
        config = SetConfig()
        assert isinstance(config, ExchangeConfig)

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        config = SetConfig()
        assert config.exchange_code == "SET"
        assert config.suffix == ".BK"
        assert config.timeout == 30.0

    def test_正常系_カスタム値で初期化できる(self) -> None:
        config = SetConfig(timeout=60.0)
        assert config.timeout == 60.0

    def test_正常系_frozen_dataclassである(self) -> None:
        config = SetConfig()
        with pytest.raises(FrozenInstanceError):
            config.timeout = 10.0  # type: ignore[misc]

    def test_正常系_タイムアウト境界値_最小(self) -> None:
        config = SetConfig(timeout=1.0)
        assert config.timeout == 1.0

    def test_正常系_タイムアウト境界値_最大(self) -> None:
        config = SetConfig(timeout=300.0)
        assert config.timeout == 300.0

    def test_異常系_タイムアウトが小さすぎるとValueError(self) -> None:
        with pytest.raises(ValueError, match="timeout"):
            SetConfig(timeout=0.5)

    def test_異常系_タイムアウトが大きすぎるとValueError(self) -> None:
        with pytest.raises(ValueError, match="timeout"):
            SetConfig(timeout=400.0)
