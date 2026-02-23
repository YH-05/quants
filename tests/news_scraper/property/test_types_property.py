"""types.py のプロパティベーステスト.

Article.to_dict() の不変条件と get_delay() の範囲をプロパティテストで検証する。
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from news_scraper.types import Article, ScraperConfig, get_delay


class TestArticleToDict:
    """Article.to_dict() のプロパティテスト."""

    @given(
        title=st.text(min_size=0, max_size=500),
        url=st.text(min_size=0, max_size=500),
        published=st.text(min_size=0, max_size=100),
        summary=st.text(min_size=0, max_size=1000),
        category=st.text(min_size=0, max_size=100),
        source=st.text(min_size=0, max_size=100),
        content=st.text(min_size=0, max_size=5000),
        ticker=st.text(min_size=0, max_size=20),
        author=st.text(min_size=0, max_size=200),
        article_id=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=50)
    def test_プロパティ_任意の文字列でArticle生成とto_dict変換が成功する(
        self,
        title: str,
        url: str,
        published: str,
        summary: str,
        category: str,
        source: str,
        content: str,
        ticker: str,
        author: str,
        article_id: str,
    ) -> None:
        """任意の文字列フィールドで Article を生成して to_dict() が成功することを確認。"""
        article = Article(
            title=title,
            url=url,
            published=published,
            summary=summary,
            category=category,
            source=source,
            content=content,
            ticker=ticker,
            author=author,
            article_id=article_id,
        )
        result = article.to_dict()

        assert isinstance(result, dict)

    @given(
        title=st.text(min_size=0, max_size=200),
        url=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=100)
    def test_プロパティ_to_dictは元の値を保持する(
        self,
        title: str,
        url: str,
    ) -> None:
        """to_dict() が元のフィールド値を保持することを確認。"""
        article = Article(title=title, url=url)
        result = article.to_dict()

        assert result["title"] == title
        assert result["url"] == url

    @given(
        title=st.text(min_size=0, max_size=200),
        url=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=50)
    def test_プロパティ_to_dictは常に11個のキーを返す(
        self,
        title: str,
        url: str,
    ) -> None:
        """to_dict() が常に 11 個のキーを返すことを確認。"""
        article = Article(title=title, url=url)
        result = article.to_dict()

        assert len(result) == 11

    @given(
        title=st.text(min_size=0, max_size=200),
        url=st.text(min_size=0, max_size=200),
        metadata=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(min_size=0, max_size=100),
                st.integers(),
                st.booleans(),
                st.none(),
            ),
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_プロパティ_metadataが任意の辞書を保持する(
        self,
        title: str,
        url: str,
        metadata: dict,
    ) -> None:
        """任意の metadata 辞書が to_dict() で保持されることを確認。"""
        article = Article(title=title, url=url, metadata=metadata)
        result = article.to_dict()

        assert result["metadata"] == metadata

    @given(
        title=st.text(min_size=0, max_size=200),
        url=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=50)
    def test_プロパティ_to_dictが冪等である(
        self,
        title: str,
        url: str,
    ) -> None:
        """to_dict() を複数回呼んでも同じ結果が返されることを確認（冪等性）。"""
        article = Article(title=title, url=url)

        result1 = article.to_dict()
        result2 = article.to_dict()

        assert result1 == result2

    @given(
        title=st.text(min_size=0, max_size=200),
        url=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=50)
    def test_プロパティ_to_dictが必要なキーを全て含む(
        self,
        title: str,
        url: str,
    ) -> None:
        """to_dict() が全ての必要なキーを含むことを確認。"""
        article = Article(title=title, url=url)
        result = article.to_dict()

        required_keys = {
            "title",
            "url",
            "published",
            "summary",
            "category",
            "source",
            "content",
            "ticker",
            "author",
            "article_id",
            "metadata",
        }
        assert required_keys == set(result.keys())


class TestGetDelayProperty:
    """get_delay() のプロパティベーステスト."""

    @given(
        delay=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
        jitter=st.floats(min_value=0.0, max_value=50.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_プロパティ_get_delayが期待範囲内の値を返す(
        self,
        delay: float,
        jitter: float,
    ) -> None:
        """get_delay() が delay ± jitter の範囲内の値を返すことを確認。"""
        config = ScraperConfig(delay=delay, jitter=jitter)
        result = get_delay(config)

        assert delay - jitter <= result <= delay + jitter

    @given(
        delay=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_プロパティ_jitter_0の場合はdelayと等しい(
        self,
        delay: float,
    ) -> None:
        """jitter が 0.0 の場合、get_delay() が delay と等しい値を返すことを確認。"""
        config = ScraperConfig(delay=delay, jitter=0.0)

        result = get_delay(config)

        assert abs(result - delay) < 1e-10  # 浮動小数点誤差を許容

    @given(
        delay=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
        jitter=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_プロパティ_get_delayが浮動小数点を返す(
        self,
        delay: float,
        jitter: float,
    ) -> None:
        """get_delay() が浮動小数点数を返すことを確認。"""
        config = ScraperConfig(delay=delay, jitter=jitter)
        result = get_delay(config)

        assert isinstance(result, float)
