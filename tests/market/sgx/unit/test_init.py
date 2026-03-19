"""Tests for market.sgx.__init__.py public API exports.

Validates that:
- All SGX public API symbols are importable from ``market.sgx``.
- Error classes and Config type are accessible.
- __all__ is complete and consistent.

Test TODO List:
- [x] SGX public API importability
- [x] __all__ completeness
- [x] Error classes importable
- [x] Config type importable
- [x] Re-exported symbols match source modules
- [x] Module docstring exists
"""

from __future__ import annotations


class TestSgxPackageExports:
    """Test that market.sgx re-exports all public API symbols."""

    def test_正常系_SgxErrorがインポート可能(self) -> None:
        from market.sgx import SgxError

        assert issubclass(SgxError, Exception)

    def test_正常系_SgxAPIErrorがインポート可能(self) -> None:
        from market.sgx import SgxAPIError

        assert issubclass(SgxAPIError, Exception)

    def test_正常系_SgxRateLimitErrorがインポート可能(self) -> None:
        from market.sgx import SgxRateLimitError

        assert issubclass(SgxRateLimitError, Exception)

    def test_正常系_SgxParseErrorがインポート可能(self) -> None:
        from market.sgx import SgxParseError

        assert issubclass(SgxParseError, Exception)

    def test_正常系_SgxValidationErrorがインポート可能(self) -> None:
        from market.sgx import SgxValidationError

        assert issubclass(SgxValidationError, Exception)

    def test_正常系_SgxConfigがインポート可能(self) -> None:
        from market.sgx import SgxConfig

        assert isinstance(SgxConfig, type)

    def test_正常系___all__が定義されている(self) -> None:
        import market.sgx as sgx_mod

        assert hasattr(sgx_mod, "__all__")
        assert isinstance(sgx_mod.__all__, list)
        assert len(sgx_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.sgx as sgx_mod

        for name in sgx_mod.__all__:
            assert hasattr(sgx_mod, name), (
                f"{name} is in __all__ but not importable from market.sgx"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.sgx as sgx_mod

        expected = {
            "SgxError",
            "SgxAPIError",
            "SgxRateLimitError",
            "SgxParseError",
            "SgxValidationError",
            "SgxConfig",
        }
        assert expected.issubset(set(sgx_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(sgx_mod.__all__)}"
        )

    def test_正常系_再エクスポートされたSgxErrorが元モジュールと同一(self) -> None:
        from market.sgx import SgxError as ReExported
        from market.sgx.errors import SgxError as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたSgxConfigが元モジュールと同一(self) -> None:
        from market.sgx import SgxConfig as ReExported
        from market.sgx.types import SgxConfig as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.sgx as sgx_mod

        assert sgx_mod.__doc__ is not None
        assert len(sgx_mod.__doc__) > 0
