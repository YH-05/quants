"""Unit tests for HistoricalCache class.

FRED 履歴データのローカルキャッシュ機能のテストスイート。
TDD Red フェーズ: 失敗するテストから開始。
"""

import json
import tempfile
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# テスト対象のインポート（まだ存在しない）
from market.fred.historical_cache import (
    FRED_HISTORICAL_CACHE_DIR_ENV,
    HistoricalCache,
    get_default_cache_path,
)

# =============================================================================
# フィクスチャ
# =============================================================================


@pytest.fixture
def temp_cache_dir() -> Generator[Path, None, None]:
    """一時的なキャッシュディレクトリを作成。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_preset_info() -> dict[str, Any]:
    """テスト用のプリセット情報。"""
    return {
        "name_ja": "10年国債利回り",
        "name_en": "10-Year Treasury Constant Maturity Rate",
        "category": "interest_rate",
        "frequency": "daily",
        "units": "percent",
    }


@pytest.fixture
def sample_fred_series() -> pd.Series:
    """テスト用の FRED シリーズデータ。"""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.Series([4.0, 4.1, 4.2, 4.3, 4.4], index=dates, name="DGS10")


@pytest.fixture
def sample_fred_metadata() -> dict[str, Any]:
    """テスト用の FRED メタデータ。"""
    return {
        "id": "DGS10",
        "title": "10-Year Treasury Constant Maturity Rate",
        "observation_start": "1962-01-02",
        "observation_end": "2026-01-28",
        "last_updated": "2026-01-28 15:16:00-05:00",
    }


@pytest.fixture
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """環境変数にモック API キーを設定。"""
    api_key = "test_api_key_12345"
    monkeypatch.setenv("FRED_API_KEY", api_key)
    return api_key


# =============================================================================
# get_default_cache_path のテスト
# =============================================================================


class TestGetDefaultCachePath:
    """get_default_cache_path 関数のテスト。"""

    def test_正常系_環境変数が設定されている場合はそれを優先(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """FRED_HISTORICAL_CACHE_DIR 環境変数が設定されている場合、それを使用することを確認。"""
        env_path = str(tmp_path / "custom_cache")
        monkeypatch.setenv(FRED_HISTORICAL_CACHE_DIR_ENV, env_path)

        result = get_default_cache_path()

        assert result == Path(env_path)

    def test_正常系_環境変数未設定でカレントディレクトリからの相対パスを使用(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """環境変数が未設定の場合、カレントディレクトリからの相対パスを使用することを確認。"""
        # 環境変数をクリア
        monkeypatch.delenv(FRED_HISTORICAL_CACHE_DIR_ENV, raising=False)

        # カレントディレクトリを一時ディレクトリに変更
        original_cwd = Path.cwd()
        monkeypatch.chdir(tmp_path)

        # カレントディレクトリに data/raw/fred/indicators を作成
        expected_path = tmp_path / "data" / "raw" / "fred" / "indicators"
        expected_path.mkdir(parents=True, exist_ok=True)

        try:
            result = get_default_cache_path()
            # カレントディレクトリからの相対パスが使用されることを確認
            assert result == expected_path
        finally:
            monkeypatch.chdir(original_cwd)

    def test_正常系_カレントディレクトリにデータディレクトリがない場合はフォールバック(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """カレントディレクトリに data ディレクトリがない場合、__file__ ベースのパスを使用することを確認。"""
        # 環境変数をクリア
        monkeypatch.delenv(FRED_HISTORICAL_CACHE_DIR_ENV, raising=False)

        # 空の一時ディレクトリに移動（data/raw/fred/indicators なし）
        original_cwd = Path.cwd()
        monkeypatch.chdir(tmp_path)

        try:
            result = get_default_cache_path()
            # __file__ ベースのパスが使用されることを確認
            # historical_cache.py の場所から計算されるパス
            from market.fred import historical_cache

            expected_fallback = (
                Path(historical_cache.__file__).parents[3]
                / "data"
                / "raw"
                / "fred"
                / "indicators"
            )
            assert result == expected_fallback
        finally:
            monkeypatch.chdir(original_cwd)

    def test_正常系_優先順位_環境変数_カレント_フォールバック(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """優先順位が正しいことを確認（環境変数 > カレント > フォールバック）。"""
        # 1. 環境変数が設定されている場合は環境変数
        env_path = str(tmp_path / "env_cache")
        monkeypatch.setenv(FRED_HISTORICAL_CACHE_DIR_ENV, env_path)
        assert get_default_cache_path() == Path(env_path)

        # 2. 環境変数をクリアし、カレントディレクトリに data ディレクトリを作成
        monkeypatch.delenv(FRED_HISTORICAL_CACHE_DIR_ENV, raising=False)
        original_cwd = Path.cwd()
        monkeypatch.chdir(tmp_path)
        cwd_data_path = tmp_path / "data" / "raw" / "fred" / "indicators"
        cwd_data_path.mkdir(parents=True, exist_ok=True)

        try:
            result = get_default_cache_path()
            assert result == cwd_data_path
        finally:
            monkeypatch.chdir(original_cwd)


# =============================================================================
# 初期化のテスト
# =============================================================================


class TestHistoricalCacheInit:
    """HistoricalCache 初期化のテスト。"""

    def test_正常系_デフォルトパスで初期化(self, mock_api_key: str) -> None:
        """デフォルトのベースパスで初期化できることを確認。"""
        cache = HistoricalCache()

        expected_path = get_default_cache_path()
        assert cache.base_path == expected_path

    def test_正常系_カスタムパスで初期化(
        self, temp_cache_dir: Path, mock_api_key: str
    ) -> None:
        """カスタムベースパスで初期化できることを確認。"""
        cache = HistoricalCache(base_path=temp_cache_dir)

        assert cache.base_path == temp_cache_dir

    def test_正常系_ディレクトリが存在しない場合は作成(
        self, temp_cache_dir: Path, mock_api_key: str
    ) -> None:
        """ベースパスのディレクトリが存在しない場合、自動作成されることを確認。"""
        new_path = temp_cache_dir / "new" / "nested" / "dir"
        cache = HistoricalCache(base_path=new_path)

        assert new_path.exists()
        assert cache.base_path == new_path


# =============================================================================
# sync_series のテスト
# =============================================================================


class TestSyncSeries:
    """sync_series メソッドのテスト。"""

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_正常系_新規シリーズの全履歴を取得(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        sample_fred_series: pd.Series,
        sample_fred_metadata: dict[str, Any],
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """新規シリーズの全履歴データを取得しキャッシュすることを確認。"""
        # FREDFetcher のモック設定
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher_class.load_presets.return_value = {
            "Treasury Yields": {"DGS10": sample_preset_info}
        }
        mock_fetcher_class.get_preset_info.return_value = {
            **sample_preset_info,
            "category_name": "Treasury Yields",
        }
        mock_fetcher.get_series_info.return_value = sample_fred_metadata

        # FetchOptions と fetch メソッドのモック
        mock_result = MagicMock()
        mock_result.data = pd.DataFrame({"value": sample_fred_series})
        mock_result.is_empty = False
        mock_fetcher.fetch.return_value = [mock_result]

        cache = HistoricalCache(base_path=temp_cache_dir)
        result = cache.sync_series("DGS10")

        # 結果の検証
        assert result["series_id"] == "DGS10"
        assert result["data_points"] == 5
        assert result["success"] is True

        # ファイルが作成されていることを確認
        cache_file = temp_cache_dir / "DGS10.json"
        assert cache_file.exists()

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_正常系_既存シリーズの増分更新(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        sample_fred_series: pd.Series,
        sample_fred_metadata: dict[str, Any],
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """既存シリーズに新しいデータを増分追加することを確認。"""
        # 既存キャッシュファイルを作成
        existing_data = {
            "series_id": "DGS10",
            "preset_info": sample_preset_info,
            "fred_metadata": sample_fred_metadata,
            "cache_metadata": {
                "last_fetched": "2024-01-03T10:00:00+00:00",
                "data_points": 3,
                "version": 1,
            },
            "data": [
                {"date": "2024-01-01", "value": 4.0},
                {"date": "2024-01-02", "value": 4.1},
                {"date": "2024-01-03", "value": 4.2},
            ],
        }
        cache_file = temp_cache_dir / "DGS10.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # 新しいデータのモック（1月4日と5日のデータを追加）
        new_series = pd.Series(
            [4.3, 4.4],
            index=pd.to_datetime(["2024-01-04", "2024-01-05"]),
        )
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher_class.get_preset_info.return_value = {
            **sample_preset_info,
            "category_name": "Treasury Yields",
        }
        mock_fetcher.get_series_info.return_value = sample_fred_metadata

        mock_result = MagicMock()
        mock_result.data = pd.DataFrame({"value": new_series})
        mock_result.is_empty = False
        mock_fetcher.fetch.return_value = [mock_result]

        cache = HistoricalCache(base_path=temp_cache_dir)
        result = cache.sync_series("DGS10")

        # 結果の検証
        assert result["data_points"] == 5  # 3 + 2 = 5
        assert result["new_points"] == 2

        # キャッシュファイルの内容を検証
        with open(cache_file, encoding="utf-8") as f:
            cached = json.load(f)
        assert len(cached["data"]) == 5

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_異常系_無効なシリーズIDでエラー(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        mock_api_key: str,
    ) -> None:
        """無効なシリーズIDでエラーになることを確認。"""
        mock_fetcher_class.get_preset_info.return_value = None

        cache = HistoricalCache(base_path=temp_cache_dir)

        with pytest.raises(ValueError, match="not found in presets"):
            cache.sync_series("INVALID_SERIES")


# =============================================================================
# sync_all_presets のテスト
# =============================================================================


class TestSyncAllPresets:
    """sync_all_presets メソッドのテスト。"""

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_正常系_全プリセットを同期(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        sample_fred_series: pd.Series,
        sample_fred_metadata: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """全プリセットシリーズを同期できることを確認。"""
        # プリセットのモック
        mock_fetcher_class.load_presets.return_value = {
            "Treasury Yields": {
                "DGS10": {"name_ja": "10年国債利回り"},
                "DGS2": {"name_ja": "2年国債利回り"},
            }
        }
        mock_fetcher_class.get_preset_symbols.return_value = ["DGS10", "DGS2"]
        mock_fetcher_class.get_preset_info.return_value = {
            "name_ja": "テスト",
            "category_name": "Treasury Yields",
        }

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_series_info.return_value = sample_fred_metadata

        mock_result = MagicMock()
        mock_result.data = pd.DataFrame({"value": sample_fred_series})
        mock_result.is_empty = False
        mock_fetcher.fetch.return_value = [mock_result]

        cache = HistoricalCache(base_path=temp_cache_dir)
        results = cache.sync_all_presets()

        assert len(results) == 2
        assert all(r["success"] for r in results)

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_正常系_一部失敗しても継続(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        sample_fred_series: pd.Series,
        sample_fred_metadata: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """一部のシリーズが失敗しても他のシリーズの同期は継続することを確認。"""
        mock_fetcher_class.load_presets.return_value = {
            "Treasury Yields": {
                "DGS10": {"name_ja": "10年国債利回り"},
                "INVALID": {"name_ja": "無効なシリーズ"},
            }
        }
        mock_fetcher_class.get_preset_symbols.return_value = ["DGS10", "INVALID"]

        def get_preset_info_side_effect(series_id: str) -> dict | None:
            if series_id == "DGS10":
                return {"name_ja": "10年国債利回り", "category_name": "Treasury Yields"}
            return None

        mock_fetcher_class.get_preset_info.side_effect = get_preset_info_side_effect

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_series_info.return_value = sample_fred_metadata

        mock_result = MagicMock()
        mock_result.data = pd.DataFrame({"value": sample_fred_series})
        mock_result.is_empty = False
        mock_fetcher.fetch.return_value = [mock_result]

        cache = HistoricalCache(base_path=temp_cache_dir)
        results = cache.sync_all_presets()

        assert len(results) == 2
        success_count = sum(1 for r in results if r["success"])
        fail_count = sum(1 for r in results if not r["success"])
        assert success_count == 1
        assert fail_count == 1


# =============================================================================
# sync_category のテスト
# =============================================================================


class TestSyncCategory:
    """sync_category メソッドのテスト。"""

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_正常系_カテゴリ単位で同期(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        sample_fred_series: pd.Series,
        sample_fred_metadata: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """指定カテゴリのシリーズのみを同期できることを確認。"""
        mock_fetcher_class.load_presets.return_value = {
            "Treasury Yields": {
                "DGS10": {"name_ja": "10年国債利回り"},
                "DGS2": {"name_ja": "2年国債利回り"},
            },
            "Economic Indicators": {
                "GDP": {"name_ja": "実質GDP"},
            },
        }
        mock_fetcher_class.get_preset_symbols.return_value = ["DGS10", "DGS2"]
        mock_fetcher_class.get_preset_info.return_value = {
            "name_ja": "テスト",
            "category_name": "Treasury Yields",
        }

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_series_info.return_value = sample_fred_metadata

        mock_result = MagicMock()
        mock_result.data = pd.DataFrame({"value": sample_fred_series})
        mock_result.is_empty = False
        mock_fetcher.fetch.return_value = [mock_result]

        cache = HistoricalCache(base_path=temp_cache_dir)
        results = cache.sync_category("Treasury Yields")

        assert len(results) == 2

    def test_異常系_存在しないカテゴリでエラー(
        self, temp_cache_dir: Path, mock_api_key: str
    ) -> None:
        """存在しないカテゴリ名でエラーになることを確認。"""
        with patch("market.fred.historical_cache.FREDFetcher") as mock_fetcher_class:
            mock_fetcher_class.load_presets.return_value = {"Treasury Yields": {}}
            mock_fetcher_class.get_preset_symbols.side_effect = KeyError(
                "Category not found"
            )

            cache = HistoricalCache(base_path=temp_cache_dir)

            with pytest.raises(KeyError):
                cache.sync_category("Nonexistent Category")


# =============================================================================
# get_series / get_series_df のテスト
# =============================================================================


class TestGetSeries:
    """get_series メソッドのテスト。"""

    def test_正常系_キャッシュからデータ取得(
        self,
        temp_cache_dir: Path,
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """キャッシュからデータを取得できることを確認。"""
        # キャッシュファイルを作成
        cache_data = {
            "series_id": "DGS10",
            "preset_info": sample_preset_info,
            "fred_metadata": {
                "observation_start": "2024-01-01",
                "observation_end": "2024-01-05",
            },
            "cache_metadata": {
                "last_fetched": "2024-01-06T10:00:00+00:00",
                "data_points": 5,
                "version": 1,
            },
            "data": [
                {"date": "2024-01-01", "value": 4.0},
                {"date": "2024-01-02", "value": 4.1},
                {"date": "2024-01-03", "value": 4.2},
                {"date": "2024-01-04", "value": 4.3},
                {"date": "2024-01-05", "value": 4.4},
            ],
        }
        cache_file = temp_cache_dir / "DGS10.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        with patch("market.fred.historical_cache.FREDFetcher"):
            cache = HistoricalCache(base_path=temp_cache_dir)
            result = cache.get_series("DGS10")

        assert result is not None
        assert result["series_id"] == "DGS10"
        assert len(result["data"]) == 5

    def test_正常系_存在しないシリーズでNone(
        self, temp_cache_dir: Path, mock_api_key: str
    ) -> None:
        """キャッシュに存在しないシリーズでNoneが返ることを確認。"""
        with patch("market.fred.historical_cache.FREDFetcher"):
            cache = HistoricalCache(base_path=temp_cache_dir)
            result = cache.get_series("NONEXISTENT")

        assert result is None


class TestGetSeriesDf:
    """get_series_df メソッドのテスト。"""

    def test_正常系_DataFrameとして取得(
        self,
        temp_cache_dir: Path,
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """キャッシュからDataFrame形式で取得できることを確認。"""
        # キャッシュファイルを作成
        cache_data = {
            "series_id": "DGS10",
            "preset_info": sample_preset_info,
            "fred_metadata": {},
            "cache_metadata": {"data_points": 3, "version": 1},
            "data": [
                {"date": "2024-01-01", "value": 4.0},
                {"date": "2024-01-02", "value": 4.1},
                {"date": "2024-01-03", "value": 4.2},
            ],
        }
        cache_file = temp_cache_dir / "DGS10.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        with patch("market.fred.historical_cache.FREDFetcher"):
            cache = HistoricalCache(base_path=temp_cache_dir)
            df = cache.get_series_df("DGS10")

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "value" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_正常系_存在しないシリーズでNone(
        self, temp_cache_dir: Path, mock_api_key: str
    ) -> None:
        """存在しないシリーズでNoneが返ることを確認。"""
        with patch("market.fred.historical_cache.FREDFetcher"):
            cache = HistoricalCache(base_path=temp_cache_dir)
            result = cache.get_series_df("NONEXISTENT")

        assert result is None


# =============================================================================
# get_status のテスト
# =============================================================================


class TestGetStatus:
    """get_status メソッドのテスト。"""

    def test_正常系_全シリーズのステータスを取得(
        self,
        temp_cache_dir: Path,
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """全シリーズの同期ステータスを取得できることを確認。"""
        # キャッシュファイルを作成
        for series_id in ["DGS10", "DGS2"]:
            cache_data = {
                "series_id": series_id,
                "preset_info": sample_preset_info,
                "fred_metadata": {
                    "observation_start": "2024-01-01",
                    "observation_end": "2024-01-05",
                },
                "cache_metadata": {
                    "last_fetched": "2024-01-06T10:00:00+00:00",
                    "data_points": 5,
                    "version": 1,
                },
                "data": [],
            }
            cache_file = temp_cache_dir / f"{series_id}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

        with patch("market.fred.historical_cache.FREDFetcher") as mock_fetcher_class:
            mock_fetcher_class.load_presets.return_value = {
                "Treasury Yields": {
                    "DGS10": {},
                    "DGS2": {},
                    "DGS30": {},  # キャッシュなし
                }
            }
            mock_fetcher_class.get_preset_symbols.return_value = [
                "DGS10",
                "DGS2",
                "DGS30",
            ]

            cache = HistoricalCache(base_path=temp_cache_dir)
            status = cache.get_status()

        assert "DGS10" in status
        assert "DGS2" in status
        assert "DGS30" in status
        assert status["DGS10"]["cached"] is True
        assert status["DGS2"]["cached"] is True
        assert status["DGS30"]["cached"] is False


# =============================================================================
# invalidate のテスト
# =============================================================================


class TestInvalidate:
    """invalidate メソッドのテスト。"""

    def test_正常系_キャッシュを無効化(
        self,
        temp_cache_dir: Path,
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """キャッシュを無効化（削除）できることを確認。"""
        # キャッシュファイルを作成
        cache_file = temp_cache_dir / "DGS10.json"
        cache_file.write_text('{"series_id": "DGS10"}')

        with patch("market.fred.historical_cache.FREDFetcher"):
            cache = HistoricalCache(base_path=temp_cache_dir)
            result = cache.invalidate("DGS10")

        assert result is True
        assert not cache_file.exists()

    def test_正常系_存在しないキャッシュの無効化(
        self, temp_cache_dir: Path, mock_api_key: str
    ) -> None:
        """存在しないキャッシュの無効化でFalseが返ることを確認。"""
        with patch("market.fred.historical_cache.FREDFetcher"):
            cache = HistoricalCache(base_path=temp_cache_dir)
            result = cache.invalidate("NONEXISTENT")

        assert result is False


# =============================================================================
# インデックスファイルのテスト
# =============================================================================


class TestIndexFile:
    """_index.json ファイルのテスト。"""

    @patch("market.fred.historical_cache.FREDFetcher")
    def test_正常系_インデックスファイルが更新される(
        self,
        mock_fetcher_class: MagicMock,
        temp_cache_dir: Path,
        sample_fred_series: pd.Series,
        sample_fred_metadata: dict[str, Any],
        sample_preset_info: dict[str, Any],
        mock_api_key: str,
    ) -> None:
        """sync_series 後にインデックスファイルが更新されることを確認。"""
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher_class.get_preset_info.return_value = {
            **sample_preset_info,
            "category_name": "Treasury Yields",
        }
        mock_fetcher.get_series_info.return_value = sample_fred_metadata

        mock_result = MagicMock()
        mock_result.data = pd.DataFrame({"value": sample_fred_series})
        mock_result.is_empty = False
        mock_fetcher.fetch.return_value = [mock_result]

        cache = HistoricalCache(base_path=temp_cache_dir)
        cache.sync_series("DGS10")

        # インデックスファイルの確認
        index_file = temp_cache_dir / "_index.json"
        assert index_file.exists()

        with open(index_file, encoding="utf-8") as f:
            index_data = json.load(f)

        assert "version" in index_data
        assert "last_updated" in index_data
        assert "series" in index_data
        assert "DGS10" in index_data["series"]
