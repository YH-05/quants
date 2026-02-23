"""types.py の単体テスト.

Article, ScraperConfig, get_delay の動作を検証する。
"""

from __future__ import annotations

import pytest

from news_scraper.types import Article, ScraperConfig, get_delay


class TestArticle:
    """Article データクラスのテスト."""

    def test_正常系_必須フィールドのみでインスタンス生成(self) -> None:
        """title と url のみで Article を作成できることを確認。"""
        article = Article(title="Test Article", url="https://example.com/article")

        assert article.title == "Test Article"
        assert article.url == "https://example.com/article"

    def test_正常系_デフォルト値でインスタンス生成(self) -> None:
        """オプションフィールドが正しいデフォルト値を持つことを確認。"""
        article = Article(title="Test", url="https://example.com/")

        assert article.published == ""
        assert article.summary == ""
        assert article.category == ""
        assert article.source == ""
        assert article.content == ""
        assert article.ticker == ""
        assert article.author == ""
        assert article.article_id == ""
        assert article.metadata == {}

    def test_正常系_全フィールドでインスタンス生成(self) -> None:
        """全フィールドを指定して Article を作成できることを確認。"""
        article = Article(
            title="Full Article",
            url="https://example.com/full",
            published="2026-02-23T12:00:00+00:00",
            summary="Summary text",
            category="economy",
            source="cnbc",
            content="Full content",
            ticker="AAPL",
            author="John Doe",
            article_id="cnbc-001",
            metadata={"key": "value"},
        )

        assert article.title == "Full Article"
        assert article.url == "https://example.com/full"
        assert article.published == "2026-02-23T12:00:00+00:00"
        assert article.summary == "Summary text"
        assert article.category == "economy"
        assert article.source == "cnbc"
        assert article.content == "Full content"
        assert article.ticker == "AAPL"
        assert article.author == "John Doe"
        assert article.article_id == "cnbc-001"
        assert article.metadata == {"key": "value"}

    def test_エッジケース_空文字列のフィールド(self) -> None:
        """全フィールドを空文字列で設定できることを確認。"""
        article = Article(
            title="",
            url="",
            published="",
            summary="",
            category="",
            source="",
        )

        assert article.title == ""
        assert article.url == ""
        assert article.published == ""

    def test_エッジケース_metadataが独立したインスタンスを持つ(self) -> None:
        """各インスタンスが独立した metadata dict を持つことを確認。"""
        article1 = Article(title="A1", url="https://a1.com")
        article2 = Article(title="A2", url="https://a2.com")

        article1.metadata["key"] = "value"
        assert "key" not in article2.metadata

    def test_正常系_to_dictで辞書に変換できる(self) -> None:
        """to_dict() が全フィールドを含む辞書を返すことを確認。"""
        article = Article(
            title="Test",
            url="https://example.com/test",
            published="2026-02-23",
            source="cnbc",
        )
        result = article.to_dict()

        assert result["title"] == "Test"
        assert result["url"] == "https://example.com/test"
        assert result["published"] == "2026-02-23"
        assert result["source"] == "cnbc"

    def test_正常系_to_dictの戻り値が正しいキーを持つ(self) -> None:
        """to_dict() が全必要なキーを返すことを確認。"""
        article = Article(title="T", url="https://example.com")
        result = article.to_dict()

        expected_keys = {
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
        assert set(result.keys()) == expected_keys

    def test_正常系_to_dictがmetadataをコピーする(self) -> None:
        """to_dict() が metadata の参照を返すことを確認。"""
        metadata = {"test": 123}
        article = Article(title="T", url="https://example.com", metadata=metadata)
        result = article.to_dict()

        assert result["metadata"] == metadata

    def test_エッジケース_日本語タイトル(self) -> None:
        """日本語タイトルを設定できることを確認。"""
        article = Article(
            title="テストニュース記事タイトル",
            url="https://example.com/jp",
        )
        assert article.title == "テストニュース記事タイトル"
        result = article.to_dict()
        assert result["title"] == "テストニュース記事タイトル"


class TestScraperConfig:
    """ScraperConfig データクラスのテスト."""

    def test_正常系_デフォルト値でインスタンス生成(self) -> None:
        """デフォルト値で ScraperConfig を作成できることを確認。"""
        config = ScraperConfig()

        assert config.impersonate == "chrome131"
        assert config.proxy is None
        assert config.delay == 1.0
        assert config.jitter == 0.5
        assert config.timeout == 30
        assert config.include_content is False
        assert config.use_playwright is True
        assert config.max_concurrency == 5
        assert config.max_concurrency_content == 3
        assert config.max_retries == 3

    def test_正常系_全フィールドを指定してインスタンス生成(self) -> None:
        """全フィールドを指定して ScraperConfig を作成できることを確認。"""
        config = ScraperConfig(
            impersonate="safari",
            proxy="http://proxy.example.com:8080",
            delay=2.0,
            jitter=1.0,
            timeout=60,
            include_content=True,
            use_playwright=False,
            max_concurrency=10,
            max_concurrency_content=5,
            max_retries=5,
        )

        assert config.impersonate == "safari"
        assert config.proxy == "http://proxy.example.com:8080"
        assert config.delay == 2.0
        assert config.jitter == 1.0
        assert config.timeout == 60
        assert config.include_content is True
        assert config.use_playwright is False
        assert config.max_concurrency == 10
        assert config.max_concurrency_content == 5
        assert config.max_retries == 5

    def test_正常系_impersonate_chromeを設定できる(self) -> None:
        """impersonate に chrome を設定できることを確認。"""
        config = ScraperConfig(impersonate="chrome")
        assert config.impersonate == "chrome"

    def test_正常系_proxyがNoneのデフォルト(self) -> None:
        """proxy のデフォルト値が None であることを確認。"""
        config = ScraperConfig()
        assert config.proxy is None

    def test_エッジケース_delay_0で設定できる(self) -> None:
        """delay を 0.0 で設定できることを確認。"""
        config = ScraperConfig(delay=0.0, jitter=0.0)
        assert config.delay == 0.0
        assert config.jitter == 0.0


class TestGetDelay:
    """get_delay() 関数のテスト."""

    def test_正常系_delay範囲内の値を返す(self) -> None:
        """get_delay() が delay ± jitter の範囲内の値を返すことを確認。"""
        config = ScraperConfig(delay=1.0, jitter=0.5)
        result = get_delay(config)

        assert 0.5 <= result <= 1.5

    def test_正常系_jitter_0の場合はdelayと等しい(self) -> None:
        """jitter が 0 の場合、get_delay() が delay と等しい値を返すことを確認。"""
        config = ScraperConfig(delay=2.0, jitter=0.0)
        result = get_delay(config)

        assert result == pytest.approx(2.0)

    def test_正常系_delay_0の場合は0付近の値を返す(self) -> None:
        """delay が 0 でも get_delay() が適切な値を返すことを確認。"""
        config = ScraperConfig(delay=0.0, jitter=0.5)
        result = get_delay(config)

        assert -0.5 <= result <= 0.5

    def test_正常系_複数回呼ぶと異なる値になりうる(self) -> None:
        """jitter が 0 以外のとき、複数回の呼び出しで異なる値になりうることを確認。"""
        config = ScraperConfig(delay=1.0, jitter=0.5)
        results = {get_delay(config) for _ in range(50)}

        # 50回呼べば少なくとも2種類の値が出るはず（確率的）
        assert len(results) >= 2

    def test_正常系_大きなjitterでも範囲内(self) -> None:
        """大きな jitter を設定しても範囲内の値を返すことを確認。"""
        config = ScraperConfig(delay=5.0, jitter=4.0)
        for _ in range(20):
            result = get_delay(config)
            assert 1.0 <= result <= 9.0
