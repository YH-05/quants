"""Tests for market.cache module.

このモジュールは市場データ用のSQLiteベースキャッシュ機能をテストします。

テスト対象:
- generate_cache_key: キャッシュキーの生成
- SQLiteCache: SQLiteベースのキャッシュクラス
- get_cache/reset_cache: グローバルキャッシュ管理
- create_persistent_cache: 永続キャッシュの作成
"""

import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from market.cache import (
    DEFAULT_CACHE_DB_PATH,
    PERSISTENT_CACHE_CONFIG,
    CacheConfig,
    SQLiteCache,
    create_persistent_cache,
    generate_cache_key,
    get_cache,
    reset_cache,
)
from market.cache.cache import _resolve_cache_db_path


class TestGenerateCacheKey:
    """generate_cache_key関数のテスト。

    キャッシュキー生成の一貫性、一意性、形式を検証します。
    """

    def test_正常系_同じ入力で一貫したキー生成(self) -> None:
        """同じパラメータで呼び出すと同じキーが生成されることを確認。"""
        key1 = generate_cache_key("AAPL", "2024-01-01", "2024-12-31")
        key2 = generate_cache_key("AAPL", "2024-01-01", "2024-12-31")
        assert key1 == key2

    def test_正常系_異なるシンボルで異なるキー生成(self) -> None:
        """異なるシンボルでは異なるキーが生成されることを確認。"""
        key1 = generate_cache_key("AAPL", "2024-01-01", "2024-12-31")
        key2 = generate_cache_key("GOOGL", "2024-01-01", "2024-12-31")
        assert key1 != key2

    def test_正常系_キー長が64文字のSHA256ハッシュ(self) -> None:
        """生成されたキーがSHA256ハッシュ（64文字）であることを確認。"""
        key = generate_cache_key("AAPL")
        assert len(key) == 64


class TestSQLiteCache:
    """SQLiteCacheクラスのテスト。

    SQLiteベースのキャッシュの基本操作、TTL処理、エントリ管理を検証します。
    """

    @pytest.fixture
    def cache(self) -> Generator[SQLiteCache, None, None]:
        """テスト用のインメモリキャッシュインスタンスを作成。"""
        config = CacheConfig(
            enabled=True,
            ttl_seconds=3600,
            max_entries=100,
            db_path=None,  # In-memory
        )
        cache_instance = SQLiteCache(config)
        yield cache_instance
        cache_instance.close()

    # =========================================================================
    # 基本操作テスト
    # =========================================================================

    def test_正常系_存在しないキーでNone返却(self, cache: SQLiteCache) -> None:
        """存在しないキーに対してgetがNoneを返すことを確認。"""
        assert cache.get("nonexistent") is None

    def test_正常系_setとgetの基本操作(self, cache: SQLiteCache) -> None:
        """setした値をgetで取得できることを確認。"""
        cache.set("key1", {"price": 150.0})
        result = cache.get("key1")
        assert result == {"price": 150.0}

    def test_正常系_リストのシリアライズとデシリアライズ(
        self, cache: SQLiteCache
    ) -> None:
        """リスト値の保存と取得が正しく動作することを確認。"""
        cache.set("key1", [1, 2, 3])
        result = cache.get("key1")
        assert result == [1, 2, 3]

    def test_正常系_DataFrameのシリアライズとデシリアライズ(
        self, cache: SQLiteCache
    ) -> None:
        """DataFrameの保存と取得が正しく動作することを確認。"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        cache.set("df_key", df)
        result = cache.get("df_key")
        pd.testing.assert_frame_equal(result, df)

    # =========================================================================
    # TTL（有効期限）テスト
    # =========================================================================

    def test_正常系_TTL期限切れでNone返却(self) -> None:
        """TTL期限切れ後にgetがNoneを返すことを確認。"""
        config = CacheConfig(ttl_seconds=1)  # 1秒のTTL
        with SQLiteCache(config) as cache:
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

            time.sleep(1.1)  # 期限切れを待つ
            assert cache.get("key1") is None

    # =========================================================================
    # 削除操作テスト
    # =========================================================================

    def test_正常系_deleteでエントリ削除(self, cache: SQLiteCache) -> None:
        """deleteでエントリが削除されることを確認。"""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.get("key1") is None

    def test_正常系_存在しないキーのdeleteでFalse(self, cache: SQLiteCache) -> None:
        """存在しないキーに対するdeleteがFalseを返すことを確認。"""
        deleted = cache.delete("nonexistent")
        assert deleted is False

    def test_正常系_clearで全エントリ削除(self, cache: SQLiteCache) -> None:
        """clearで全エントリが削除されることを確認。"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        count = cache.clear()
        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_正常系_cleanup_expiredで期限切れエントリのみ削除(self) -> None:
        """cleanup_expiredが期限切れエントリのみを削除することを確認。"""
        config = CacheConfig(ttl_seconds=1)
        with SQLiteCache(config) as cache:
            cache.set("key1", "value1")
            time.sleep(1.1)  # key1を期限切れにする
            cache.set("key2", "value2", ttl=3600)  # key2は長いTTL

            removed = cache.cleanup_expired()
            assert removed == 1
            assert cache.get("key1") is None
            assert cache.get("key2") == "value2"

    # =========================================================================
    # エントリ制限テスト
    # =========================================================================

    def test_正常系_max_entries超過で古いエントリ削除(self) -> None:
        """max_entries超過時に古いエントリが削除されることを確認。"""
        config = CacheConfig(max_entries=3)
        with SQLiteCache(config) as cache:
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            cache.set("key3", "value3")
            cache.set("key4", "value4")  # クリーンアップをトリガー

            stats = cache.get_stats()
            assert stats["total_entries"] <= 3

    # =========================================================================
    # 統計情報テスト
    # =========================================================================

    def test_正常系_get_statsで正しい統計情報返却(self, cache: SQLiteCache) -> None:
        """get_statsが正しい統計情報を返すことを確認。"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["expired_entries"] == 0
        assert "max_entries" in stats

    # =========================================================================
    # コンテキストマネージャテスト
    # =========================================================================

    def test_正常系_コンテキストマネージャとして動作(self) -> None:
        """withステートメントでキャッシュが正常に動作することを確認。"""
        with SQLiteCache() as cache:
            cache.set("key", "value")
            assert cache.get("key") == "value"


class TestGlobalCache:
    """グローバルキャッシュ関数のテスト。

    get_cacheとreset_cacheのシングルトンパターンを検証します。
    """

    def teardown_method(self) -> None:
        """各テスト後にグローバルキャッシュをリセット。"""
        reset_cache()

    def test_正常系_get_cacheでシングルトン取得(self) -> None:
        """get_cacheが同じインスタンスを返すことを確認。"""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_正常系_reset_cacheで新インスタンス作成(self) -> None:
        """reset_cache後に新しいインスタンスが作成されることを確認。"""
        cache1 = get_cache()
        cache1.set("key", "value")

        reset_cache()
        cache2 = get_cache()

        assert cache1 is not cache2
        assert cache2.get("key") is None


class TestPersistentCache:
    """永続キャッシュ機能のテスト。

    ファイルベースの永続キャッシュ作成と設定を検証します。
    """

    def test_正常系_create_persistent_cacheでファイルベースキャッシュ作成(
        self, tmp_path: Path
    ) -> None:
        """create_persistent_cacheがファイルベースのキャッシュを作成することを確認。"""
        cache = create_persistent_cache(db_path=tmp_path / "test_cache.db")

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        cache.close()

    def test_正常系_カスタムTTL設定(self, tmp_path: Path) -> None:
        """create_persistent_cacheでカスタムTTLを設定できることを確認。"""
        cache = create_persistent_cache(
            db_path=tmp_path / "test_cache.db",
            ttl_seconds=7200,
        )

        assert cache.config.ttl_seconds == 7200
        cache.close()

    def test_正常系_親ディレクトリ自動作成(self, tmp_path: Path) -> None:
        """create_persistent_cacheが親ディレクトリを自動作成することを確認。"""
        cache_path = tmp_path / "subdir" / "nested" / "cache.db"
        cache = create_persistent_cache(db_path=cache_path)

        cache.set("key", "value")
        assert cache_path.parent.exists()
        cache.close()

    def test_正常系_PERSISTENT_CACHE_CONFIGの値確認(self) -> None:
        """PERSISTENT_CACHE_CONFIGが正しい値を持つことを確認。"""
        assert PERSISTENT_CACHE_CONFIG.enabled is True
        assert PERSISTENT_CACHE_CONFIG.ttl_seconds == 86400  # 24時間
        assert PERSISTENT_CACHE_CONFIG.max_entries == 10000
        assert PERSISTENT_CACHE_CONFIG.db_path is not None

    def test_正常系_DEFAULT_CACHE_DB_PATHの値確認(self) -> None:
        """DEFAULT_CACHE_DB_PATHが正しく設定されていることを確認。"""
        assert DEFAULT_CACHE_DB_PATH.name == "market_data.db"
        assert "cache" in DEFAULT_CACHE_DB_PATH.parts

    def test_正常系_resolve_cache_db_pathがDATA_DIR環境変数を反映(
        self, tmp_path: Path
    ) -> None:
        """_resolve_cache_db_path() が DATA_DIR 環境変数を反映すること。"""
        custom_data_dir = tmp_path / "custom_data"
        custom_data_dir.mkdir()

        with patch(
            "market.cache.cache.get_data_dir",
            return_value=custom_data_dir,
        ):
            result = _resolve_cache_db_path()

        assert result == custom_data_dir / "cache" / "market_data.db"
