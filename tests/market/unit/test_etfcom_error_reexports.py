"""Unit tests for ETFCom error re-exports from market.errors.

market.errors から ETFComHTTPError / ETFComNotFoundError が
正しく re-export されていることを検証するテスト。
"""

from market.errors import ETFComHTTPError, ETFComNotFoundError
from market.etfcom.errors import (
    ETFComHTTPError as OriginalHTTPError,
)
from market.etfcom.errors import (
    ETFComNotFoundError as OriginalNotFoundError,
)


class TestETFComErrorReExports:
    """market.errors からの ETFCom エラー re-export テスト。"""

    def test_正常系_ETFComHTTPErrorがreexportされている(self) -> None:
        """market.errors.ETFComHTTPError が元クラスと同一であること。"""
        assert ETFComHTTPError is OriginalHTTPError

    def test_正常系_ETFComNotFoundErrorがreexportされている(self) -> None:
        """market.errors.ETFComNotFoundError が元クラスと同一であること。"""
        assert ETFComNotFoundError is OriginalNotFoundError

    def test_正常系_ETFComNotFoundErrorがETFComHTTPErrorのサブクラス(self) -> None:
        """re-export された ETFComNotFoundError が ETFComHTTPError のサブクラスであること。"""
        assert issubclass(ETFComNotFoundError, ETFComHTTPError)
