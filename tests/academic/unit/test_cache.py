"""academic キャッシュアダプタの単体テスト.

SQLiteCache ラッパーとキャッシュキー生成のテスト。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from academic.cache import (
    ACADEMIC_CACHE_DB_PATH,
    ACADEMIC_CACHE_MAX_ENTRIES,
    ACADEMIC_CACHE_TTL,
    get_academic_cache,
    make_cache_key,
)
from academic.types import AcademicConfig

# ---------------------------------------------------------------------------
# TestMakeCacheKey
# ---------------------------------------------------------------------------


class TestMakeCacheKey:
    """make_cache_key() のテスト."""

    def test_正常系_キャッシュキーが正しい形式で生成される(self) -> None:
        """arxiv_id から 'academic:paper:{id}' 形式のキーが生成されることを確認。"""
        key = make_cache_key("2301.00001")
        assert key == "academic:paper:2301.00001"

    def test_正常系_異なるIDで異なるキーが生成される(self) -> None:
        """異なる arxiv_id で異なるキャッシュキーが生成されることを確認。"""
        key1 = make_cache_key("2301.00001")
        key2 = make_cache_key("2301.00002")
        assert key1 != key2

    def test_正常系_バージョン付きIDでもキーが生成される(self) -> None:
        """バージョン付き arxiv_id でもキーが生成されることを確認。"""
        key = make_cache_key("2301.00001v2")
        assert key == "academic:paper:2301.00001v2"


# ---------------------------------------------------------------------------
# TestGetAcademicCache
# ---------------------------------------------------------------------------


class TestGetAcademicCache:
    """get_academic_cache() のテスト."""

    @patch("academic.cache.create_persistent_cache")
    def test_正常系_デフォルト引数でcreate_persistent_cacheを呼ぶ(
        self,
        mock_create: MagicMock,
    ) -> None:
        """デフォルト設定で create_persistent_cache が正しい引数で呼ばれることを確認。"""
        mock_cache = MagicMock()
        mock_create.return_value = mock_cache

        result = get_academic_cache()

        mock_create.assert_called_once_with(
            db_path=ACADEMIC_CACHE_DB_PATH,
            ttl_seconds=ACADEMIC_CACHE_TTL,
            max_entries=ACADEMIC_CACHE_MAX_ENTRIES,
        )
        assert result is mock_cache

    @patch("academic.cache.create_persistent_cache")
    def test_正常系_カスタムTTLでcreate_persistent_cacheを呼ぶ(
        self,
        mock_create: MagicMock,
    ) -> None:
        """AcademicConfig.cache_ttl でカスタム TTL が渡されることを確認。"""
        mock_cache = MagicMock()
        mock_create.return_value = mock_cache

        config = AcademicConfig(cache_ttl=3600)
        result = get_academic_cache(config=config)

        mock_create.assert_called_once_with(
            db_path=ACADEMIC_CACHE_DB_PATH,
            ttl_seconds=3600,
            max_entries=ACADEMIC_CACHE_MAX_ENTRIES,
        )
        assert result is mock_cache

    @patch("academic.cache.create_persistent_cache")
    def test_正常系_Noneの場合デフォルト設定を使用(
        self,
        mock_create: MagicMock,
    ) -> None:
        """config=None でデフォルト TTL が使用されることを確認。"""
        mock_cache = MagicMock()
        mock_create.return_value = mock_cache

        get_academic_cache(config=None)

        mock_create.assert_called_once_with(
            db_path=ACADEMIC_CACHE_DB_PATH,
            ttl_seconds=ACADEMIC_CACHE_TTL,
            max_entries=ACADEMIC_CACHE_MAX_ENTRIES,
        )
