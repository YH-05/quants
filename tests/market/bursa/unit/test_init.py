"""Tests for market.bursa.__init__.py public API exports.

Validates that:
- All Bursa public API symbols are importable from ``market.bursa``.
- Error classes and Config type are accessible.
- __all__ is complete and consistent.

Test TODO List:
- [x] Bursa public API importability
- [x] __all__ completeness
- [x] Error classes importable
- [x] Config type importable
- [x] Re-exported symbols match source modules
- [x] Module docstring exists
"""

from __future__ import annotations


class TestBursaPackageExports:
    """Test that market.bursa re-exports all public API symbols."""

    def test_正常系_BursaErrorがインポート可能(self) -> None:
        from market.bursa import BursaError

        assert issubclass(BursaError, Exception)

    def test_正常系_BursaAPIErrorがインポート可能(self) -> None:
        from market.bursa import BursaAPIError

        assert issubclass(BursaAPIError, Exception)

    def test_正常系_BursaRateLimitErrorがインポート可能(self) -> None:
        from market.bursa import BursaRateLimitError

        assert issubclass(BursaRateLimitError, Exception)

    def test_正常系_BursaParseErrorがインポート可能(self) -> None:
        from market.bursa import BursaParseError

        assert issubclass(BursaParseError, Exception)

    def test_正常系_BursaValidationErrorがインポート可能(self) -> None:
        from market.bursa import BursaValidationError

        assert issubclass(BursaValidationError, Exception)

    def test_正常系_BursaConfigがインポート可能(self) -> None:
        from market.bursa import BursaConfig

        assert isinstance(BursaConfig, type)

    def test_正常系___all__が定義されている(self) -> None:
        import market.bursa as bursa_mod

        assert hasattr(bursa_mod, "__all__")
        assert isinstance(bursa_mod.__all__, list)
        assert len(bursa_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.bursa as bursa_mod

        for name in bursa_mod.__all__:
            assert hasattr(bursa_mod, name), (
                f"{name} is in __all__ but not importable from market.bursa"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.bursa as bursa_mod

        expected = {
            "BursaError",
            "BursaAPIError",
            "BursaRateLimitError",
            "BursaParseError",
            "BursaValidationError",
            "BursaConfig",
        }
        assert expected.issubset(set(bursa_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(bursa_mod.__all__)}"
        )

    def test_正常系_再エクスポートされたBursaErrorが元モジュールと同一(self) -> None:
        from market.bursa import BursaError as ReExported
        from market.bursa.errors import BursaError as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたBursaConfigが元モジュールと同一(self) -> None:
        from market.bursa import BursaConfig as ReExported
        from market.bursa.types import BursaConfig as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.bursa as bursa_mod

        assert bursa_mod.__doc__ is not None
        assert len(bursa_mod.__doc__) > 0
