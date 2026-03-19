"""Tests for market.sgx.constants module.

Tests verify all constant definitions for the SGX data retrieval module.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] Exchange identification: EXCHANGE_CODE, EXCHANGE_NAME, SUFFIX, CURRENCY
- [x] yfinance configuration: YFINANCE_SUPPORTED
- [x] Output settings: DEFAULT_OUTPUT_DIR
- [x] Final annotations: all constants annotated with typing.Final
"""

from typing import get_type_hints

from market.sgx.constants import (
    CURRENCY,
    DEFAULT_OUTPUT_DIR,
    EXCHANGE_CODE,
    EXCHANGE_NAME,
    SUFFIX,
    YFINANCE_SUPPORTED,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """constants モジュールが正常にインポートできること。"""
        from market.sgx import constants

        assert constants is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.sgx import constants

        for name in __all__:
            assert hasattr(constants, name), (
                f"{name} is not defined in constants module"
            )

    def test_正常系_allが6項目を含む(self) -> None:
        """__all__ が全6定数をエクスポートしていること。"""
        assert len(__all__) == 6

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        """モジュールの docstring が存在すること。"""
        from market.sgx import constants

        assert constants.__doc__ is not None
        assert len(constants.__doc__) > 0


# =============================================================================
# Exchange identification constants
# =============================================================================


class TestExchangeIdentification:
    """Test exchange identification constants."""

    def test_正常系_EXCHANGE_CODEがSGX(self) -> None:
        """EXCHANGE_CODE が 'SGX' であること。"""
        assert EXCHANGE_CODE == "SGX"

    def test_正常系_EXCHANGE_NAMEがSingapore_Exchange(self) -> None:
        """EXCHANGE_NAME が 'Singapore Exchange' であること。"""
        assert EXCHANGE_NAME == "Singapore Exchange"

    def test_正常系_SUFFIXがドットSI(self) -> None:
        """SUFFIX が '.SI' であること。"""
        assert SUFFIX == ".SI"

    def test_正常系_SUFFIXがドットで始まる(self) -> None:
        """SUFFIX がドットで始まること。"""
        assert SUFFIX.startswith(".")

    def test_正常系_CURRENCYがSGD(self) -> None:
        """CURRENCY が 'SGD' であること。"""
        assert CURRENCY == "SGD"

    def test_正常系_CURRENCYが3文字(self) -> None:
        """CURRENCY が ISO 4217 の3文字コードであること。"""
        assert len(CURRENCY) == 3
        assert CURRENCY.isupper()


# =============================================================================
# yfinance configuration
# =============================================================================


class TestYfinanceConfig:
    """Test yfinance configuration constants."""

    def test_正常系_YFINANCE_SUPPORTEDがTrue(self) -> None:
        """YFINANCE_SUPPORTED が True であること。"""
        assert YFINANCE_SUPPORTED is True


# =============================================================================
# Output settings
# =============================================================================


class TestOutputConstants:
    """Test output directory constants."""

    def test_正常系_DEFAULT_OUTPUT_DIRが空でない文字列(self) -> None:
        """DEFAULT_OUTPUT_DIR が空でない文字列であること。"""
        assert isinstance(DEFAULT_OUTPUT_DIR, str)
        assert len(DEFAULT_OUTPUT_DIR.strip()) > 0

    def test_正常系_DEFAULT_OUTPUT_DIRがdata_rawを含む(self) -> None:
        """DEFAULT_OUTPUT_DIR が data/raw パスを含むこと。"""
        assert "data/raw" in DEFAULT_OUTPUT_DIR

    def test_正常系_DEFAULT_OUTPUT_DIRがsgxを含む(self) -> None:
        """DEFAULT_OUTPUT_DIR が sgx を含むこと。"""
        assert "sgx" in DEFAULT_OUTPUT_DIR

    def test_正常系_DEFAULT_OUTPUT_DIRが正しい値(self) -> None:
        """DEFAULT_OUTPUT_DIR が設計通りの値であること。"""
        assert DEFAULT_OUTPUT_DIR == "data/raw/sgx/"


# =============================================================================
# Final type annotations
# =============================================================================


class TestFinalAnnotations:
    """Test that all constants have Final type annotations."""

    def test_正常系_全定数にFinal型アノテーションが付与されている(self) -> None:
        """__all__ の全定数に typing.Final アノテーションが付与されていること。"""
        from market.sgx import constants

        annotations = get_type_hints(constants, include_extras=True)

        for name in __all__:
            assert name in annotations, (
                f"{name} does not have a type annotation in the module"
            )
            annotation_str = str(annotations[name])
            assert "Final" in annotation_str, (
                f"{name} is not annotated with Final. Got: {annotation_str}"
            )
