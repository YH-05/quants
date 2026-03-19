"""Tests for market.hose.__init__.py public API exports.

Validates that:
- All HOSE public API symbols are importable from ``market.hose``.
- Error classes and Config type are accessible.
- __all__ is complete and consistent.

Test TODO List:
- [x] HOSE public API importability
- [x] __all__ completeness
- [x] Error classes importable
- [x] Config type importable
- [x] Re-exported symbols match source modules
- [x] Module docstring exists
"""

from __future__ import annotations


class TestHosePackageExports:
    """Test that market.hose re-exports all public API symbols."""

    def test_正常系_HoseErrorがインポート可能(self) -> None:
        from market.hose import HoseError

        assert issubclass(HoseError, Exception)

    def test_正常系_HoseAPIErrorがインポート可能(self) -> None:
        from market.hose import HoseAPIError

        assert issubclass(HoseAPIError, Exception)

    def test_正常系_HoseRateLimitErrorがインポート可能(self) -> None:
        from market.hose import HoseRateLimitError

        assert issubclass(HoseRateLimitError, Exception)

    def test_正常系_HoseParseErrorがインポート可能(self) -> None:
        from market.hose import HoseParseError

        assert issubclass(HoseParseError, Exception)

    def test_正常系_HoseValidationErrorがインポート可能(self) -> None:
        from market.hose import HoseValidationError

        assert issubclass(HoseValidationError, Exception)

    def test_正常系_HoseConfigがインポート可能(self) -> None:
        from market.hose import HoseConfig

        assert isinstance(HoseConfig, type)

    def test_正常系___all__が定義されている(self) -> None:
        import market.hose as hose_mod

        assert hasattr(hose_mod, "__all__")
        assert isinstance(hose_mod.__all__, list)
        assert len(hose_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.hose as hose_mod

        for name in hose_mod.__all__:
            assert hasattr(hose_mod, name), (
                f"{name} is in __all__ but not importable from market.hose"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.hose as hose_mod

        expected = {
            "HoseError",
            "HoseAPIError",
            "HoseRateLimitError",
            "HoseParseError",
            "HoseValidationError",
            "HoseConfig",
        }
        assert expected.issubset(set(hose_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(hose_mod.__all__)}"
        )

    def test_正常系_再エクスポートされたHoseErrorが元モジュールと同一(self) -> None:
        from market.hose import HoseError as ReExported
        from market.hose.errors import HoseError as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたHoseConfigが元モジュールと同一(self) -> None:
        from market.hose import HoseConfig as ReExported
        from market.hose.types import HoseConfig as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.hose as hose_mod

        assert hose_mod.__doc__ is not None
        assert len(hose_mod.__doc__) > 0
