"""academic キャッシュアダプタの単体テスト.

SQLiteCache ラッパーとキャッシュキー生成のテスト。
"""

from __future__ import annotations

from academic.cache import get_academic_cache, make_cache_key
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

    def test_正常系_SQLiteCacheインスタンスを返す(self) -> None:
        """get_academic_cache() が SQLiteCache インスタンスを返すことを確認。"""
        cache = get_academic_cache()
        assert cache is not None

    def test_正常系_デフォルトTTLが7日(self) -> None:
        """デフォルト TTL が 604800秒（7日）であることを確認。"""
        cache = get_academic_cache()
        assert cache.config.ttl_seconds == 604800

    def test_正常系_カスタム設定でTTLを変更できる(self) -> None:
        """AcademicConfig.cache_ttl でカスタム TTL を設定できることを確認。"""
        config = AcademicConfig(cache_ttl=3600)
        cache = get_academic_cache(config=config)
        assert cache.config.ttl_seconds == 3600

    def test_正常系_max_entriesが5000(self) -> None:
        """max_entries が 5000 であることを確認。"""
        cache = get_academic_cache()
        assert cache.config.max_entries == 5000


# ---------------------------------------------------------------------------
# TestCacheRoundTrip
# ---------------------------------------------------------------------------


class TestCacheRoundTrip:
    """キャッシュの set/get ラウンドトリップテスト."""

    def test_正常系_setとgetでラウンドトリップできる(self) -> None:
        """set で保存した値を get で取得できることを確認。"""
        cache = get_academic_cache()
        key = make_cache_key("2301.00001")
        data = {"title": "Test Paper", "authors": ["Alice"]}
        cache.set(key, data)

        result = cache.get(key)
        assert result is not None
        assert result["title"] == "Test Paper"
        assert result["authors"] == ["Alice"]

    def test_正常系_キャッシュミスでNoneを返す(self) -> None:
        """存在しないキーで get した場合 None が返ることを確認。"""
        cache = get_academic_cache()
        result = cache.get("academic:paper:nonexistent")
        assert result is None

    def test_正常系_TTL期限切れでNoneを返す(self) -> None:
        """TTL 期限切れの場合 None が返ることを確認。"""
        # TTL=1秒の短いキャッシュを作成
        config = AcademicConfig(cache_ttl=1)
        cache = get_academic_cache(config=config)
        key = make_cache_key("2301.00001")
        data = {"title": "Expiring Paper"}
        cache.set(key, data, ttl=0)  # TTL=0 で即時期限切れ

        # 期限切れなので None を返す
        result = cache.get(key)
        assert result is None
