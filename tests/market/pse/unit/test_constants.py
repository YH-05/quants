"""Tests for market.pse.constants module.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] Exchange identification: EXCHANGE_CODE, EXCHANGE_NAME, SUFFIX, CURRENCY
- [x] yfinance configuration: YFINANCE_SUPPORTED (False for PSE)
- [x] Output settings: DEFAULT_OUTPUT_DIR
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.pse.constants import (
    CURRENCY,
    DEFAULT_OUTPUT_DIR,
    EXCHANGE_CODE,
    EXCHANGE_NAME,
    SUFFIX,
    YFINANCE_SUPPORTED,
    __all__,
)


class TestModuleExports:
    def test_正常系_モジュールがインポートできる(self) -> None:
        from market.pse import constants

        assert constants is not None

    def test_正常系_allが6項目を含む(self) -> None:
        assert len(__all__) == 6

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        from market.pse import constants

        for name in __all__:
            assert hasattr(constants, name)


class TestExchangeIdentification:
    def test_正常系_EXCHANGE_CODEがPSE(self) -> None:
        assert EXCHANGE_CODE == "PSE"

    def test_正常系_EXCHANGE_NAMEがPhilippine_Stock_Exchange(self) -> None:
        assert EXCHANGE_NAME == "Philippine Stock Exchange"

    def test_正常系_SUFFIXがドットPS(self) -> None:
        assert SUFFIX == ".PS"

    def test_正常系_SUFFIXがドットで始まる(self) -> None:
        assert SUFFIX.startswith(".")

    def test_正常系_CURRENCYがPHP(self) -> None:
        assert CURRENCY == "PHP"

    def test_正常系_CURRENCYが3文字(self) -> None:
        assert len(CURRENCY) == 3
        assert CURRENCY.isupper()


class TestYfinanceConfig:
    """PSE is NOT supported by yfinance."""

    def test_正常系_YFINANCE_SUPPORTEDがFalse(self) -> None:
        """PSE は yfinance 非対応のため False であること。"""
        assert YFINANCE_SUPPORTED is False


class TestOutputConstants:
    def test_正常系_DEFAULT_OUTPUT_DIRが正しい値(self) -> None:
        assert DEFAULT_OUTPUT_DIR == "data/raw/pse/"

    def test_正常系_DEFAULT_OUTPUT_DIRがdata_rawを含む(self) -> None:
        assert "data/raw" in DEFAULT_OUTPUT_DIR


class TestFinalAnnotations:
    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        from market.pse import constants

        annotations = get_type_hints(constants, include_extras=True)
        for name in __all__:
            assert name in annotations
            assert "Final" in str(annotations[name])
