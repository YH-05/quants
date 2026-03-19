"""Tests for market.pse.__init__.py public API exports.

Validates that:
- All PSE public API symbols are importable from ``market.pse``.
- Error classes and Config type are accessible.
- __all__ is complete and consistent.

Test TODO List:
- [x] PSE public API importability
- [x] __all__ completeness
- [x] Error classes importable
- [x] Config type importable
- [x] Re-exported symbols match source modules
- [x] Module docstring exists
"""

from __future__ import annotations


class TestPsePackageExports:
    """Test that market.pse re-exports all public API symbols."""

    def test_正常系_PseErrorがインポート可能(self) -> None:
        from market.pse import PseError

        assert issubclass(PseError, Exception)

    def test_正常系_PseAPIErrorがインポート可能(self) -> None:
        from market.pse import PseAPIError

        assert issubclass(PseAPIError, Exception)

    def test_正常系_PseRateLimitErrorがインポート可能(self) -> None:
        from market.pse import PseRateLimitError

        assert issubclass(PseRateLimitError, Exception)

    def test_正常系_PseParseErrorがインポート可能(self) -> None:
        from market.pse import PseParseError

        assert issubclass(PseParseError, Exception)

    def test_正常系_PseValidationErrorがインポート可能(self) -> None:
        from market.pse import PseValidationError

        assert issubclass(PseValidationError, Exception)

    def test_正常系_PseConfigがインポート可能(self) -> None:
        from market.pse import PseConfig

        assert isinstance(PseConfig, type)

    def test_正常系___all__が定義されている(self) -> None:
        import market.pse as pse_mod

        assert hasattr(pse_mod, "__all__")
        assert isinstance(pse_mod.__all__, list)
        assert len(pse_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.pse as pse_mod

        for name in pse_mod.__all__:
            assert hasattr(pse_mod, name), (
                f"{name} is in __all__ but not importable from market.pse"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.pse as pse_mod

        expected = {
            "PseError",
            "PseAPIError",
            "PseRateLimitError",
            "PseParseError",
            "PseValidationError",
            "PseConfig",
        }
        assert expected.issubset(set(pse_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(pse_mod.__all__)}"
        )

    def test_正常系_再エクスポートされたPseErrorが元モジュールと同一(self) -> None:
        from market.pse import PseError as ReExported
        from market.pse.errors import PseError as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたPseConfigが元モジュールと同一(self) -> None:
        from market.pse import PseConfig as ReExported
        from market.pse.types import PseConfig as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.pse as pse_mod

        assert pse_mod.__doc__ is not None
        assert len(pse_mod.__doc__) > 0
