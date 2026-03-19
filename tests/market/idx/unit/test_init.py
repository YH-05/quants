"""Tests for market.idx.__init__.py public API exports.

Validates that:
- All IDX public API symbols are importable from ``market.idx``.
- Error classes and Config type are accessible.
- __all__ is complete and consistent.

Test TODO List:
- [x] IDX public API importability
- [x] __all__ completeness
- [x] Error classes importable
- [x] Config type importable
- [x] Re-exported symbols match source modules
- [x] Module docstring exists
"""

from __future__ import annotations


class TestIdxPackageExports:
    """Test that market.idx re-exports all public API symbols."""

    def test_正常系_IdxErrorがインポート可能(self) -> None:
        from market.idx import IdxError

        assert issubclass(IdxError, Exception)

    def test_正常系_IdxAPIErrorがインポート可能(self) -> None:
        from market.idx import IdxAPIError

        assert issubclass(IdxAPIError, Exception)

    def test_正常系_IdxRateLimitErrorがインポート可能(self) -> None:
        from market.idx import IdxRateLimitError

        assert issubclass(IdxRateLimitError, Exception)

    def test_正常系_IdxParseErrorがインポート可能(self) -> None:
        from market.idx import IdxParseError

        assert issubclass(IdxParseError, Exception)

    def test_正常系_IdxValidationErrorがインポート可能(self) -> None:
        from market.idx import IdxValidationError

        assert issubclass(IdxValidationError, Exception)

    def test_正常系_IdxConfigがインポート可能(self) -> None:
        from market.idx import IdxConfig

        assert isinstance(IdxConfig, type)

    def test_正常系___all__が定義されている(self) -> None:
        import market.idx as idx_mod

        assert hasattr(idx_mod, "__all__")
        assert isinstance(idx_mod.__all__, list)
        assert len(idx_mod.__all__) > 0

    def test_正常系___all__の全シンボルが実際にインポート可能(self) -> None:
        import market.idx as idx_mod

        for name in idx_mod.__all__:
            assert hasattr(idx_mod, name), (
                f"{name} is in __all__ but not importable from market.idx"
            )

    def test_正常系___all__が期待するシンボルを含む(self) -> None:
        import market.idx as idx_mod

        expected = {
            "IdxError",
            "IdxAPIError",
            "IdxRateLimitError",
            "IdxParseError",
            "IdxValidationError",
            "IdxConfig",
        }
        assert expected.issubset(set(idx_mod.__all__)), (
            f"Missing symbols in __all__: {expected - set(idx_mod.__all__)}"
        )

    def test_正常系_再エクスポートされたIdxErrorが元モジュールと同一(self) -> None:
        from market.idx import IdxError as ReExported
        from market.idx.errors import IdxError as Original

        assert ReExported is Original

    def test_正常系_再エクスポートされたIdxConfigが元モジュールと同一(self) -> None:
        from market.idx import IdxConfig as ReExported
        from market.idx.types import IdxConfig as Original

        assert ReExported is Original

    def test_正常系_モジュールDocstringが存在する(self) -> None:
        import market.idx as idx_mod

        assert idx_mod.__doc__ is not None
        assert len(idx_mod.__doc__) > 0
