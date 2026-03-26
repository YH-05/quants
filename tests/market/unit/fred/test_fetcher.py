"""Unit tests for FREDFetcher class.

市場データ取得パッケージ market.fred の FREDFetcher クラスのテストスイート。
FRED (Federal Reserve Economic Data) API との連携機能をテストする。
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market.errors import FREDFetchError, FREDValidationError

# 新パッケージからのインポート（Red フェーズ: まだ実装なし）
from market.fred import FREDFetcher
from market.fred.cache import SQLiteCache
from market.fred.constants import FRED_API_KEY_ENV, FRED_SERIES_PATTERN
from market.fred.types import (
    DataSource,
    FetchOptions,
    Interval,
    RetryConfig,
)

# =============================================================================
# 定数のテスト
# =============================================================================


class TestFREDSeriesPattern:
    """FRED シリーズ ID パターンのテスト。"""

    @pytest.mark.parametrize(
        "series_id",
        [
            "GDP",
            "CPIAUCSL",
            "DGS10",
            "UNRATE",
            "FEDFUNDS",
            "T10Y2Y",
            "SP500",
            "M2SL",
            "PAYEMS",
        ],
    )
    def test_パラメトライズ_有効なシリーズIDがパターンにマッチ(
        self, series_id: str
    ) -> None:
        """有効な FRED シリーズ ID がパターンにマッチすることを確認。"""
        assert FRED_SERIES_PATTERN.match(series_id) is not None

    @pytest.mark.parametrize(
        "series_id",
        [
            "gdp",  # 小文字
            "123ABC",  # 数字開始
            "GDP-10",  # ハイフン含む
            "GDP.10",  # ピリオド含む
            "gdp123",  # 小文字混在
            "A B",  # スペース含む
        ],
    )
    def test_パラメトライズ_無効なシリーズIDがパターンにマッチしない(
        self, series_id: str
    ) -> None:
        """無効な FRED シリーズ ID がパターンにマッチしないことを確認。"""
        assert FRED_SERIES_PATTERN.match(series_id) is None


# =============================================================================
# FREDFetcher 初期化のテスト
# =============================================================================


class TestFREDFetcherInit:
    """FREDFetcher 初期化のテスト。"""

    def test_正常系_パラメータでAPIキーを渡して初期化(self) -> None:
        """API キーをパラメータで渡して初期化できることを確認。"""
        fetcher = FREDFetcher(api_key="my_api_key")

        assert fetcher._api_key == "my_api_key"

    def test_正常系_環境変数からAPIキーを取得して初期化(
        self, mock_api_key: str
    ) -> None:
        """環境変数から API キーを取得して初期化できることを確認。"""
        fetcher = FREDFetcher()

        assert fetcher._api_key == mock_api_key

    def test_異常系_APIキーが設定されていないとValidationError(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """API キーが設定されていない場合、FREDValidationError が発生することを確認。"""
        monkeypatch.delenv(FRED_API_KEY_ENV, raising=False)

        with pytest.raises(FREDValidationError) as exc_info:
            FREDFetcher()

        assert FRED_API_KEY_ENV in str(exc_info.value)


# =============================================================================
# プロパティのテスト
# =============================================================================


class TestFREDFetcherProperties:
    """FREDFetcher プロパティのテスト。"""

    @pytest.fixture
    def fetcher(self, mock_api_key: str) -> FREDFetcher:
        """テスト用 FREDFetcher インスタンスを作成。"""
        return FREDFetcher()

    def test_正常系_sourceプロパティがFREDを返す(self, fetcher: FREDFetcher) -> None:
        """source プロパティが DataSource.FRED を返すことを確認。"""
        assert fetcher.source == DataSource.FRED

    def test_正常系_default_intervalプロパティがMONTHLYを返す(
        self, fetcher: FREDFetcher
    ) -> None:
        """default_interval プロパティが Interval.MONTHLY を返すことを確認。"""
        assert fetcher.default_interval == Interval.MONTHLY


# =============================================================================
# シンボル検証のテスト
# =============================================================================


class TestValidateSymbol:
    """validate_symbol メソッドのテスト。"""

    @pytest.fixture
    def fetcher(self, mock_api_key: str) -> FREDFetcher:
        """テスト用 FREDFetcher インスタンスを作成。"""
        return FREDFetcher()

    @pytest.mark.parametrize(
        "series_id",
        [
            "GDP",
            "CPIAUCSL",
            "DGS10",
            "T10Y2Y",
            "UNRATE",
        ],
    )
    def test_パラメトライズ_有効なシリーズIDでTrueを返す(
        self, fetcher: FREDFetcher, series_id: str
    ) -> None:
        """有効な FRED シリーズ ID で True を返すことを確認。"""
        assert fetcher.validate_symbol(series_id) is True

    @pytest.mark.parametrize(
        "series_id",
        [
            "",
            "   ",
            "gdp",  # 小文字
            "123ABC",  # 数字開始
            "GDP-10",  # ハイフン含む
        ],
    )
    def test_パラメトライズ_無効なシリーズIDでFalseを返す(
        self, fetcher: FREDFetcher, series_id: str
    ) -> None:
        """無効な FRED シリーズ ID で False を返すことを確認。"""
        assert fetcher.validate_symbol(series_id) is False


# =============================================================================
# データ取得のテスト
# =============================================================================


class TestFetch:
    """fetch メソッドのテスト。"""

    @pytest.fixture
    def fetcher(self, mock_api_key: str) -> FREDFetcher:
        """テスト用 FREDFetcher インスタンスを作成。"""
        return FREDFetcher()

    @patch("market.fred.fetcher.Fred")
    def test_正常系_単一シリーズのデータ取得(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
        sample_series: pd.Series,
    ) -> None:
        """単一シリーズのデータを正常に取得できることを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = sample_series
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(
            symbols=["GDP"],
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        results = fetcher.fetch(options)

        assert len(results) == 1
        assert results[0].symbol == "GDP"
        assert results[0].source == DataSource.FRED
        assert results[0].from_cache is False
        assert len(results[0].data) == 3
        # FRED データは単一時系列なので value カラムのみ
        assert list(results[0].data.columns) == ["value"]

    @patch("market.fred.fetcher.Fred")
    def test_正常系_複数シリーズのデータ取得(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
        sample_series: pd.Series,
    ) -> None:
        """複数シリーズのデータを正常に取得できることを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = sample_series
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(symbols=["GDP", "CPIAUCSL", "UNRATE"])

        results = fetcher.fetch(options)

        assert len(results) == 3
        assert [r.symbol for r in results] == ["GDP", "CPIAUCSL", "UNRATE"]

    def test_異常系_空のシンボルリストでValidationError(
        self, fetcher: FREDFetcher
    ) -> None:
        """空のシンボルリストで FREDValidationError が発生することを確認。"""
        options = FetchOptions(symbols=[])

        with pytest.raises(FREDValidationError):
            fetcher.fetch(options)

    def test_異常系_無効なシンボルでValidationError(self, fetcher: FREDFetcher) -> None:
        """無効なシンボルを含む場合 FREDValidationError が発生することを確認。"""
        options = FetchOptions(symbols=["GDP", "invalid", "CPIAUCSL"])

        with pytest.raises(FREDValidationError):
            fetcher.fetch(options)

    @patch("market.fred.fetcher.Fred")
    def test_異常系_APIエラー時にDataFetchError(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
    ) -> None:
        """API エラー発生時に FREDFetchError が発生することを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = Exception("API Error")
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(symbols=["GDP"])

        with pytest.raises(FREDFetchError) as exc_info:
            fetcher.fetch(options)

        assert "Failed to fetch FRED series GDP" in str(exc_info.value)

    @patch("market.fred.fetcher.Fred")
    def test_異常系_データが見つからない場合にDataFetchError(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
    ) -> None:
        """データが見つからない場合 FREDFetchError が発生することを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = pd.Series(dtype=float)
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(symbols=["INVALIDSERIES"])

        with pytest.raises(FREDFetchError) as exc_info:
            fetcher.fetch(options)

        assert "No data found" in str(exc_info.value)

    @patch("market.fred.fetcher.Fred")
    def test_異常系_無効なシリーズIDエラー時にDataFetchError(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
    ) -> None:
        """無効なシリーズ ID エラー時に FREDFetchError が発生することを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = ValueError("Invalid series ID")
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(symbols=["INVALIDSERIES"])

        with pytest.raises(FREDFetchError) as exc_info:
            fetcher.fetch(options)

        assert "Invalid FRED series ID" in str(exc_info.value)


# =============================================================================
# キャッシュのテスト
# =============================================================================


class TestFetchWithCache:
    """キャッシュ機能のテスト。"""

    @pytest.fixture
    def fetcher_with_cache(self, mock_api_key: str) -> FREDFetcher:
        """キャッシュ付き FREDFetcher インスタンスを作成。"""
        cache = SQLiteCache()  # インメモリキャッシュ
        return FREDFetcher(cache=cache)

    @patch("market.fred.fetcher.Fred")
    def test_正常系_キャッシュミス時にAPIからデータ取得(
        self,
        mock_fred_class: MagicMock,
        fetcher_with_cache: FREDFetcher,
        sample_series: pd.Series,
    ) -> None:
        """キャッシュミス時に API からデータを取得することを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = sample_series
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(
            symbols=["GDP"],
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        results = fetcher_with_cache.fetch(options)

        assert len(results) == 1
        assert results[0].from_cache is False

    @patch("market.fred.fetcher.Fred")
    def test_正常系_キャッシュヒット時にキャッシュからデータ取得(
        self,
        mock_fred_class: MagicMock,
        fetcher_with_cache: FREDFetcher,
        sample_series: pd.Series,
    ) -> None:
        """キャッシュヒット時にキャッシュからデータを取得することを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = sample_series
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(
            symbols=["GDP"],
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        # 1回目の取得 - キャッシュミス
        results1 = fetcher_with_cache.fetch(options)
        assert results1[0].from_cache is False

        # 2回目の取得 - キャッシュヒット
        results2 = fetcher_with_cache.fetch(options)
        assert results2[0].from_cache is True

        # API は1回だけ呼ばれるべき
        assert mock_fred.get_series.call_count == 1


# =============================================================================
# 日付処理のテスト
# =============================================================================


class TestDateFormatting:
    """日付フォーマット処理のテスト。"""

    @pytest.fixture
    def fetcher(self, mock_api_key: str) -> FREDFetcher:
        """テスト用 FREDFetcher インスタンスを作成。"""
        return FREDFetcher()

    @patch("market.fred.fetcher.Fred")
    def test_正常系_datetimeオブジェクトを文字列に変換(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
        sample_series: pd.Series,
    ) -> None:
        """datetime オブジェクトが正しく文字列に変換されることを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = sample_series
        mock_fred_class.return_value = mock_fred

        options = FetchOptions(
            symbols=["GDP"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        fetcher.fetch(options)

        mock_fred.get_series.assert_called_once()
        call_kwargs = mock_fred.get_series.call_args.kwargs
        assert call_kwargs["observation_start"] == "2024-01-01"
        assert call_kwargs["observation_end"] == "2024-12-31"


# =============================================================================
# シリーズ情報のテスト
# =============================================================================


class TestGetSeriesInfo:
    """get_series_info メソッドのテスト。"""

    @pytest.fixture
    def fetcher(self, mock_api_key: str) -> FREDFetcher:
        """テスト用 FREDFetcher インスタンスを作成。"""
        return FREDFetcher()

    @patch("market.fred.fetcher.Fred")
    def test_正常系_シリーズメタデータを取得(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
        sample_series_info: pd.Series,
    ) -> None:
        """シリーズメタデータを正常に取得できることを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series_info.return_value = sample_series_info
        mock_fred_class.return_value = mock_fred

        info = fetcher.get_series_info("GDP")

        assert info["id"] == "GDP"
        assert info["title"] == "Gross Domestic Product"

    @patch("market.fred.fetcher.Fred")
    def test_異常系_シリーズ情報取得失敗時にDataFetchError(
        self,
        mock_fred_class: MagicMock,
        fetcher: FREDFetcher,
    ) -> None:
        """シリーズ情報取得失敗時に FREDFetchError が発生することを確認。"""
        mock_fred = MagicMock()
        mock_fred.get_series_info.side_effect = Exception("API Error")
        mock_fred_class.return_value = mock_fred

        with pytest.raises(FREDFetchError):
            fetcher.get_series_info("INVALID")


# =============================================================================
# リトライ設定のテスト
# =============================================================================


class TestRetryConfig:
    """リトライ設定のテスト。"""

    def test_正常系_リトライ設定が適用される(self, mock_api_key: str) -> None:
        """リトライ設定が正しく適用されることを確認。"""
        retry_config = RetryConfig(max_attempts=5)
        fetcher = FREDFetcher(retry_config=retry_config)

        assert fetcher._retry_config == retry_config


# =============================================================================
# プリセット機能のテスト
# =============================================================================


class TestPresets:
    """プリセット機能のテスト。"""

    @pytest.fixture(autouse=True)
    def reset_presets(self) -> None:
        """各テスト前にプリセットキャッシュをリセット。"""
        FREDFetcher._presets = None
        FREDFetcher._presets_path = None

    def test_正常系_プリセットファイルを読み込む(self) -> None:
        """プリセットファイルを正常に読み込めることを確認。"""
        presets = FREDFetcher.load_presets()

        assert presets is not None
        assert "Interest Rates" in presets
        assert "Prices" in presets

    def test_正常系_カテゴリ一覧を取得(self) -> None:
        """カテゴリ一覧を取得できることを確認。"""
        FREDFetcher.load_presets()
        categories = FREDFetcher.get_preset_categories()

        assert "Interest Rates" in categories
        assert "Yield Spread" in categories
        assert "Population, Employment, & Labor Force" in categories

    def test_正常系_カテゴリ別シンボル取得(self) -> None:
        """カテゴリ別にシンボルを取得できることを確認。"""
        FREDFetcher.load_presets()
        symbols = FREDFetcher.get_preset_symbols("Interest Rates")

        assert "DGS10" in symbols
        assert "DGS2" in symbols
        assert "DGS30" in symbols

    def test_正常系_全シンボル取得(self) -> None:
        """全カテゴリのシンボルを取得できることを確認。"""
        FREDFetcher.load_presets()
        all_symbols = FREDFetcher.get_preset_symbols()

        assert len(all_symbols) > 10
        assert "DGS10" in all_symbols
        assert "GDPC1" in all_symbols  # Real GDP (US)
        assert "UNRATE" in all_symbols

    def test_正常系_シリーズ情報取得(self) -> None:
        """シリーズの詳細情報を取得できることを確認。"""
        FREDFetcher.load_presets()
        info = FREDFetcher.get_preset_info("DGS10")

        assert info is not None
        assert info["name_ja"] == "米国債10年物利回り"
        assert info["category_name"] == "Interest Rates"
        assert "frequency" in info
        assert "units" in info

    def test_正常系_存在しないシリーズでNone(self) -> None:
        """存在しないシリーズIDでNoneが返ることを確認。"""
        FREDFetcher.load_presets()
        info = FREDFetcher.get_preset_info("NONEXISTENT")

        assert info is None

    def test_異常系_プリセット未ロード時にRuntimeError(self) -> None:
        """プリセット未ロード時にRuntimeErrorが発生することを確認。"""
        with pytest.raises(RuntimeError, match="Presets not loaded"):
            FREDFetcher.get_preset_categories()

    def test_異常系_存在しないカテゴリでKeyError(self) -> None:
        """存在しないカテゴリ指定時にKeyErrorが発生することを確認。"""
        FREDFetcher.load_presets()

        with pytest.raises(KeyError, match="not found"):
            FREDFetcher.get_preset_symbols("Nonexistent Category")

    def test_正常系_キャッシュが効く(self) -> None:
        """2回目のload_presetsでキャッシュが使われることを確認。"""
        presets1 = FREDFetcher.load_presets()
        presets2 = FREDFetcher.load_presets()

        assert presets1 is presets2  # 同じオブジェクト

    def test_正常系_force_reloadでキャッシュ無視(self) -> None:
        """force_reload=Trueでキャッシュを無視して再読み込みすることを確認。"""
        presets1 = FREDFetcher.load_presets()
        presets2 = FREDFetcher.load_presets(force_reload=True)

        # 内容は同じだが、force_reloadで再読み込みされる
        assert presets1 is not presets2
        assert presets1 == presets2


# =============================================================================
# _get_default_presets_path のテスト
# =============================================================================


class TestGetDefaultPresetsPath:
    """_get_default_presets_path 関数のテスト。"""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """各テスト前に環境変数をクリア。"""
        monkeypatch.delenv("FRED_SERIES_ID_JSON", raising=False)
        monkeypatch.delenv("DATA_DIR", raising=False)

    def test_正常系_環境変数が設定されている場合はその値を返す(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """FRED_SERIES_ID_JSON 環境変数が設定されている場合、その値を返すことを確認。"""
        from market.fred.fetcher import _get_default_presets_path

        # 環境変数に一時ファイルのパスを設定
        env_path = tmp_path / "custom_fred_series.json"
        env_path.write_text('{"test": {}}', encoding="utf-8")
        monkeypatch.setenv("FRED_SERIES_ID_JSON", str(env_path))

        result = _get_default_presets_path()

        assert result == env_path

    def test_正常系_カレントディレクトリにdataがある場合はget_data_dir経由で解決(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """CWD に data/ が存在する場合、get_data_dir() 経由で config パスが解決されることを確認。"""
        from market.fred.fetcher import _get_default_presets_path

        # カレントディレクトリを一時ディレクトリに変更
        monkeypatch.chdir(tmp_path)

        # カレントディレクトリに data/config/fred_series.json を作成
        config_dir = tmp_path / "data" / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "fred_series.json"
        config_file.write_text('{"test": {}}', encoding="utf-8")

        result = _get_default_presets_path()

        # get_data_dir() が CWD/data を返すため、config/fred_series.json を付加したパスになる
        assert result == config_file

    def test_正常系_フォールバックとしてget_data_dirベースのパスを返す(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """環境変数が未設定の場合、get_data_dir() ベースのパスを返すことを確認。"""
        from market.fred.fetcher import _get_default_presets_path

        # カレントディレクトリを設定ファイルがない一時ディレクトリに変更
        monkeypatch.chdir(tmp_path)

        result = _get_default_presets_path()

        # get_data_dir() ベースのパスを返す
        from database.db.connection import get_data_dir

        expected = get_data_dir() / "config" / "fred_series.json"
        assert result == expected

    def test_正常系_環境変数が優先される(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """環境変数とカレントディレクトリの両方に設定がある場合、環境変数が優先されることを確認。"""
        from market.fred.fetcher import _get_default_presets_path

        # カレントディレクトリを一時ディレクトリに変更
        monkeypatch.chdir(tmp_path)

        # カレントディレクトリに設定ファイルを作成
        config_dir = tmp_path / "data" / "config"
        config_dir.mkdir(parents=True)
        cwd_config_file = config_dir / "fred_series.json"
        cwd_config_file.write_text('{"cwd": {}}', encoding="utf-8")

        # 環境変数に別のパスを設定
        env_path = tmp_path / "env_fred_series.json"
        env_path.write_text('{"env": {}}', encoding="utf-8")
        monkeypatch.setenv("FRED_SERIES_ID_JSON", str(env_path))

        result = _get_default_presets_path()

        # 環境変数の値が優先される
        assert result == env_path

    def test_正常系_戻り値はPathオブジェクト(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """戻り値が Path オブジェクトであることを確認。"""
        from market.fred.fetcher import _get_default_presets_path

        # カレントディレクトリを設定ファイルがない一時ディレクトリに変更
        monkeypatch.chdir(tmp_path)

        result = _get_default_presets_path()

        assert isinstance(result, Path)
