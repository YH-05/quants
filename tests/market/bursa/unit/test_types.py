"""BursaConfig のテスト。"""

from dataclasses import FrozenInstanceError

import pytest

from market.asean_common.types import ExchangeConfig
from market.bursa.types import BursaConfig


class TestBursaConfig:
    """BursaConfig dataclass のテスト。"""

    def test_正常系_ExchangeConfigを継承している(self) -> None:
        config = BursaConfig()
        assert isinstance(config, ExchangeConfig)

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        config = BursaConfig()
        assert config.exchange_code == "BURSA"
        assert config.suffix == ".KL"
        assert config.timeout == 30.0

    def test_正常系_カスタム値で初期化できる(self) -> None:
        config = BursaConfig(timeout=60.0)
        assert config.timeout == 60.0

    def test_正常系_frozen_dataclassである(self) -> None:
        config = BursaConfig()
        with pytest.raises(FrozenInstanceError):
            config.timeout = 10.0  # type: ignore[misc]

    def test_正常系_タイムアウト境界値_最小(self) -> None:
        config = BursaConfig(timeout=1.0)
        assert config.timeout == 1.0

    def test_正常系_タイムアウト境界値_最大(self) -> None:
        config = BursaConfig(timeout=300.0)
        assert config.timeout == 300.0

    def test_異常系_タイムアウトが小さすぎるとValueError(self) -> None:
        with pytest.raises(ValueError, match="timeout"):
            BursaConfig(timeout=0.5)

    def test_異常系_タイムアウトが大きすぎるとValueError(self) -> None:
        with pytest.raises(ValueError, match="timeout"):
            BursaConfig(timeout=400.0)
