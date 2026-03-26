"""Tests for market.bursa.constants module.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] Exchange identification: EXCHANGE_CODE, EXCHANGE_NAME, SUFFIX, CURRENCY
- [x] yfinance configuration: YFINANCE_SUPPORTED
- [x] Output settings: DEFAULT_OUTPUT_SUBDIR
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.bursa.constants import (
    CURRENCY,
    DEFAULT_OUTPUT_SUBDIR,
    EXCHANGE_CODE,
    EXCHANGE_NAME,
    SUFFIX,
    YFINANCE_SUPPORTED,
    __all__,
)


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        from market.bursa import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        from market.bursa import constants

        for name in __all__:
            assert hasattr(constants, name)

    def test_正常系_allが6項目を含む(self) -> None:
        assert len(__all__) == 6


class TestExchangeIdentification:
    """Test exchange identification constants."""

    def test_正常系_EXCHANGE_CODEがBURSA(self) -> None:
        assert EXCHANGE_CODE == "BURSA"

    def test_正常系_EXCHANGE_NAMEがBursa_Malaysia(self) -> None:
        assert EXCHANGE_NAME == "Bursa Malaysia"

    def test_正常系_SUFFIXがドットKL(self) -> None:
        assert SUFFIX == ".KL"

    def test_正常系_SUFFIXがドットで始まる(self) -> None:
        assert SUFFIX.startswith(".")

    def test_正常系_CURRENCYがMYR(self) -> None:
        assert CURRENCY == "MYR"

    def test_正常系_CURRENCYが3文字(self) -> None:
        assert len(CURRENCY) == 3
        assert CURRENCY.isupper()


class TestYfinanceConfig:
    """Test yfinance configuration constants."""

    def test_正常系_YFINANCE_SUPPORTEDがTrue(self) -> None:
        assert YFINANCE_SUPPORTED is True


class TestOutputConstants:
    """Test output directory constants."""

    def test_正常系_DEFAULT_OUTPUT_SUBDIRが正しい値(self) -> None:
        assert DEFAULT_OUTPUT_SUBDIR == "raw/bursa"

    def test_正常系_DEFAULT_OUTPUT_SUBDIRがraw_を含む(self) -> None:
        assert "raw/" in DEFAULT_OUTPUT_SUBDIR


class TestFinalAnnotations:
    """Test that all constants have Final type annotations."""

    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        from market.bursa import constants

        annotations = get_type_hints(constants, include_extras=True)
        for name in __all__:
            assert name in annotations
            assert "Final" in str(annotations[name])
