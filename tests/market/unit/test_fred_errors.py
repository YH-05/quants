"""Unit tests for FRED error classes.

FRED エラークラスのテストスイート。
FREDError 階層の MarketError 継承と FREDCacheNotFoundError の動作を検証する。
"""

import pytest

from market.errors import (
    FREDCacheNotFoundError,
    FREDError,
    FREDFetchError,
    FREDValidationError,
    MarketError,
)


class TestFREDErrorHierarchy:
    """FREDError 階層の MarketError 継承テスト。"""

    def test_正常系_FREDErrorがMarketErrorを継承(self) -> None:
        """FREDError が MarketError を継承していることを確認。"""
        assert issubclass(FREDError, MarketError)

    def test_正常系_FREDErrorインスタンスがMarketError(self) -> None:
        """FREDError インスタンスが MarketError として扱えることを確認。"""
        error = FREDError("FRED test error")
        assert isinstance(error, MarketError)

    def test_正常系_FREDValidationErrorがMarketError(self) -> None:
        """FREDValidationError が MarketError を継承していることを確認。"""
        assert issubclass(FREDValidationError, MarketError)
        error = FREDValidationError("Validation failed")
        assert isinstance(error, MarketError)

    def test_正常系_FREDFetchErrorがMarketError(self) -> None:
        """FREDFetchError が MarketError を継承していることを確認。"""
        assert issubclass(FREDFetchError, MarketError)
        error = FREDFetchError("Fetch failed")
        assert isinstance(error, MarketError)

    def test_正常系_FREDCacheNotFoundErrorがMarketError(self) -> None:
        """FREDCacheNotFoundError が MarketError を継承していることを確認。"""
        assert issubclass(FREDCacheNotFoundError, MarketError)
        error = FREDCacheNotFoundError(series_ids=["GDP"])
        assert isinstance(error, MarketError)

    def test_正常系_MarketErrorでキャッチ可能(self) -> None:
        """FREDError を MarketError でキャッチできることを確認。"""
        with pytest.raises(MarketError):
            raise FREDError("FRED error caught as MarketError")

    def test_正常系_FREDCacheNotFoundErrorをMarketErrorでキャッチ可能(self) -> None:
        """FREDCacheNotFoundError を MarketError でキャッチできることを確認。"""
        with pytest.raises(MarketError):
            raise FREDCacheNotFoundError(series_ids=["GDP"])

    def test_正常系_Exceptionも継承(self) -> None:
        """FREDError が引き続き Exception も継承していることを確認（後方互換性）。"""
        assert issubclass(FREDError, Exception)


class TestFREDCacheNotFoundError:
    """FREDCacheNotFoundError クラスのテスト。"""

    def test_正常系_単一シリーズIDでエラー作成(self) -> None:
        """単一のシリーズIDでエラーを作成できること。"""
        error = FREDCacheNotFoundError(series_ids=["GDP"])

        assert error.series_ids == ["GDP"]
        assert "GDP" in str(error)
        assert "sync_series" in str(error)
        assert 'sync_series("GDP")' in str(error)

    def test_正常系_複数シリーズIDでエラー作成(self) -> None:
        """複数のシリーズIDでエラーを作成できること。"""
        series_ids = ["GDP", "CPIAUCSL", "UNRATE"]
        error = FREDCacheNotFoundError(series_ids=series_ids)

        assert error.series_ids == series_ids
        assert "GDP" in str(error)
        assert "CPIAUCSL" in str(error)
        assert "UNRATE" in str(error)

    def test_正常系_FREDFetchErrorを継承(self) -> None:
        """FREDFetchError を継承していること。"""
        error = FREDCacheNotFoundError(series_ids=["GDP"])

        assert isinstance(error, FREDFetchError)

    def test_正常系_エラーメッセージに復旧方法を含む(self) -> None:
        """エラーメッセージに復旧方法が含まれること。"""
        error = FREDCacheNotFoundError(series_ids=["DGS10"])
        message = str(error)

        assert "FRED series not found in cache" in message
        assert "DGS10" in message
        assert "HistoricalCache().sync_series" in message

    def test_正常系_raiseで例外として使用可能(self) -> None:
        """raise で例外として使用できること。"""
        with pytest.raises(FREDCacheNotFoundError) as exc_info:
            raise FREDCacheNotFoundError(series_ids=["FEDFUNDS"])

        assert exc_info.value.series_ids == ["FEDFUNDS"]

    def test_正常系_FREDFetchErrorでキャッチ可能(self) -> None:
        """FREDFetchError でキャッチできること。"""
        with pytest.raises(FREDFetchError):
            raise FREDCacheNotFoundError(series_ids=["M2SL"])

    def test_エッジケース_空リストでもエラー作成可能(self) -> None:
        """空のリストでもエラーを作成できること（ただし推奨されない）。"""
        error = FREDCacheNotFoundError(series_ids=[])

        assert error.series_ids == []
        assert "FRED series not found in cache" in str(error)
