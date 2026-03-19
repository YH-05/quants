"""Tests for market.set_exchange.__init__.py public API exports.

Validates that:
- All SET public API symbols are importable from ``market.set_exchange``.
- Error classes and Config type are accessible.
- __all__ is complete and consistent.

Note: The package name is ``set_exchange`` instead of ``set`` to avoid
collision with the Python built-in ``set`` type.

Test TODO List:
- [x] SET public API importability
- [x] __all__ completeness
- [x] Error classes importable
- [x] Config type importable
- [x] Re-exported symbols match source modules
- [x] Module docstring exists
"""

from __future__ import annotations


class TestSetExchangePackageExports:
    """Test that market.set_exchange re-exports all public API symbols."""

    def test_正常系_SetErrorがインポート可能(self) -> None:
        from market.set_exchange import SetError

        assert issubclass(SetError, Exception)

    def test_正常系_SetAPIErrorがインポート可能(self) -> None:
        from market.set_exchange import SetAPIError

        assert issubclass(SetAPIError, Exception)

    def test_正常系_SetRateLimitErrorがインポート可能(self) -> None:
        from market.set_exchange import SetRateLimitError

        assert issubclass(SetRateLimitError, Exception)

    def test_正常系_SetParseErrorがインポート可能(self) -> None:
        from market.set_exchange import SetParseError

        assert issubclass(SetParseError, Exception)

    def test_正常系_SetValidationErrorがインポート可能(self) -> None:
        from market.set_exchange import SetValidationError

        assert issubclass(SetValidationError, Exception)

    def test_正常系_SetConfigがインポート可能(self) -> None:
        from market.set_exchange import SetConfig

        assert isinstance(SetConfig, type)

    def test_正常系___all__が定義されている(self) -> None:
        import market.set_exchange as set_mod

        assert hasattr(set_mod, "__all__")
        assert isinstance(set_mod.__all__, list)
        assert len(set_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.set_exchange as set_mod

        for name in set_mod.__all__:
            assert hasattr(set_mod, name), (
                f"{name} is in __all__ but not importable from market.set_exchange"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.set_exchange as set_mod

        expected = {
            "SetError",
            "SetAPIError",
            "SetRateLimitError",
            "SetParseError",
            "SetValidationError",
            "SetConfig",
        }
        assert expected.issubset(set(set_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(set_mod.__all__)}"
        )

    def test_正常系_再エクスポートされたSetErrorが元モジュールと同一(self) -> None:
        from market.set_exchange import SetError as ReExported
        from market.set_exchange.errors import SetError as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたSetConfigが元モジュールと同一(self) -> None:
        from market.set_exchange import SetConfig as ReExported
        from market.set_exchange.types import SetConfig as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.set_exchange as set_mod

        assert set_mod.__doc__ is not None
        assert len(set_mod.__doc__) > 0
