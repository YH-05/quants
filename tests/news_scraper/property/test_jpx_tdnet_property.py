"""JPX・TDnet スクレイパー プロパティテスト.

JPX Article 変換の不変条件:
- Article.source が "jpx" 固定
- URL が文字列型
- タイトルが非空（entry にタイトルがある場合）
- エントリ数と記事数が一致

TDnet URL 構築の不変条件:
- 任意のコード数で正しい URL 生成
- TDNET_BASE_URL で始まる
- .rss で終わる
- コード数 >= 1 のとき URL にコードが含まれる
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from news_scraper.types import JPX_FEEDS, TDNET_BASE_URL, Article


def _make_feed_entry(title: str, link: str, published: str, summary: str) -> MagicMock:
    """テスト用の feedparser entry モックを作成する."""
    entry = MagicMock()
    entry.get = lambda k, d="": {
        "title": title,
        "link": link,
        "published": published,
        "summary": summary,
    }.get(k, d)
    return entry


def _make_mock_session_and_feed(
    entries: list[MagicMock],
) -> tuple[MagicMock, MagicMock]:
    """モック session と feed を作成する."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "<rss/>"
    mock_session.get.return_value = mock_response

    mock_feed = MagicMock()
    mock_feed.entries = entries
    return mock_session, mock_feed


# 日本語テキストを含む文字列戦略（サロゲートペア Cs を除外）
jp_text_strategy = st.text(
    alphabet=st.characters(
        categories=("L", "N", "P", "Z"),
    ),
    min_size=1,
    max_size=200,
)

url_strategy = st.from_regex(r"https?://[a-z0-9.]+/[a-z0-9/-]+", fullmatch=True)

# 4-5桁の証券コード戦略
stock_code_strategy = st.from_regex(r"\d{4,5}", fullmatch=True)


class TestJpxProperty:
    """JPX スクレイパーのプロパティテスト."""

    @given(
        title=jp_text_strategy,
        link=url_strategy,
        published=st.text(min_size=0, max_size=50),
        summary=st.text(min_size=0, max_size=500),
        category=st.sampled_from(list(JPX_FEEDS.keys())),
    )
    @settings(max_examples=30)
    def test_プロパティ_Article_sourceが固定値jpx(
        self,
        title: str,
        link: str,
        published: str,
        summary: str,
        category: str,
    ) -> None:
        """任意の entry データから変換された Article.source が "jpx" であること。"""
        from news_scraper.jpx import fetch_rss_feed

        entry = _make_feed_entry(title, link, published, summary)
        mock_session, mock_feed = _make_mock_session_and_feed([entry])

        with patch("news_scraper.jpx.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, category)

        assert len(result) == 1
        assert result[0].source == "jpx"
        assert isinstance(result[0].url, str)
        assert isinstance(result[0].title, str)
        assert len(result[0].title) > 0

    @given(
        titles=st.lists(jp_text_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=20)
    def test_プロパティ_エントリ数と記事数が一致(self, titles: list[str]) -> None:
        """feedparser エントリ数と返却 Article 数が常に一致すること。"""
        from news_scraper.jpx import fetch_rss_feed

        entries = [
            _make_feed_entry(t, f"https://www.jpx.co.jp/{i}", "", "")
            for i, t in enumerate(titles)
        ]
        mock_session, mock_feed = _make_mock_session_and_feed(entries)

        with patch("news_scraper.jpx.feedparser.parse", return_value=mock_feed):
            result = fetch_rss_feed(mock_session, "news_release")

        assert len(result) == len(titles)


class TestTdnetUrlProperty:
    """TDnet URL 構築のプロパティテスト."""

    @given(
        codes=st.lists(stock_code_strategy, min_size=1, max_size=20),
    )
    @settings(max_examples=50)
    def test_プロパティ_URLがBASE_URLで始まりrssで終わる(
        self, codes: list[str]
    ) -> None:
        """任意のコードリストで構築された URL が正しい形式であること。"""
        from news_scraper.tdnet import _build_tdnet_url

        url = _build_tdnet_url(codes)

        assert url.startswith(TDNET_BASE_URL)
        assert url.endswith(".rss")

    @given(
        codes=st.lists(stock_code_strategy, min_size=1, max_size=20),
    )
    @settings(max_examples=50)
    def test_プロパティ_URLに全コードが含まれる(self, codes: list[str]) -> None:
        """構築された URL に全ての証券コードが含まれること。"""
        from news_scraper.tdnet import _build_tdnet_url

        url = _build_tdnet_url(codes)

        for code in codes:
            assert code in url

    @given(
        codes=st.lists(stock_code_strategy, min_size=2, max_size=10),
    )
    @settings(max_examples=30)
    def test_プロパティ_URLのコード区切りがカンマ(self, codes: list[str]) -> None:
        """構築された URL のコード部分がカンマ区切りであること。"""
        from news_scraper.tdnet import _build_tdnet_url

        url = _build_tdnet_url(codes)

        # URL の最後の部分（/codes.rss）からコード部分を抽出
        path_part = url.split("/")[-1]  # "7203,6758,9984.rss"
        codes_part = path_part.replace(".rss", "")  # "7203,6758,9984"
        extracted_codes = codes_part.split(",")

        assert extracted_codes == codes


class TestTdnetArticleProperty:
    """TDnet Article 変換のプロパティテスト."""

    @given(
        title=jp_text_strategy,
        link=url_strategy,
        published=st.text(min_size=0, max_size=50),
        summary=st.text(min_size=0, max_size=500),
    )
    @settings(max_examples=30)
    def test_プロパティ_Article_sourceが固定値tdnet(
        self,
        title: str,
        link: str,
        published: str,
        summary: str,
    ) -> None:
        """任意の entry データから変換された Article.source が "tdnet" であること。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        entry = _make_feed_entry(title, link, published, summary)
        mock_session, mock_feed = _make_mock_session_and_feed([entry])

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert len(result) == 1
        assert result[0].source == "tdnet"
        assert result[0].category == "disclosure"
        assert isinstance(result[0].url, str)
        assert isinstance(result[0].title, str)

    @given(
        titles=st.lists(jp_text_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=20)
    def test_プロパティ_エントリ数と記事数が一致(self, titles: list[str]) -> None:
        """feedparser エントリ数と返却 Article 数が常に一致すること。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        entries = [
            _make_feed_entry(t, f"https://example.com/tdnet/{i}", "", "")
            for i, t in enumerate(titles)
        ]
        mock_session, mock_feed = _make_mock_session_and_feed(entries)

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert len(result) == len(titles)
