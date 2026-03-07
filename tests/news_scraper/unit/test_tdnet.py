"""tdnet.py の単体テスト.

対象モジュール: src/news_scraper/tdnet.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from news_scraper.types import (
    TDNET_BASE_URL,
    TDNET_DEFAULT_CODES,
    Article,
    ScraperConfig,
)


class TestValidateCodes:
    """_validate_codes() のテスト."""

    def test_正常系_有効な4桁コードを受け付ける(self) -> None:
        """4桁の証券コードが有効として返されることを確認。"""
        from news_scraper.tdnet import _validate_codes

        result = _validate_codes(["7203", "6758", "9984"])
        assert result == ["7203", "6758", "9984"]

    def test_正常系_有効な5桁コードを受け付ける(self) -> None:
        """5桁の証券コード（ETF等）が有効として返されることを確認。"""
        from news_scraper.tdnet import _validate_codes

        result = _validate_codes(["13060"])
        assert result == ["13060"]

    def test_異常系_空リストでValueError(self) -> None:
        """空のコードリストで ValueError が発生することを確認。"""
        from news_scraper.tdnet import _validate_codes

        with pytest.raises(ValueError, match="codes must not be empty"):
            _validate_codes([])

    def test_異常系_全て無効なコードでValueError(self) -> None:
        """全て無効なコードの場合 ValueError が発生することを確認。"""
        from news_scraper.tdnet import _validate_codes

        with pytest.raises(ValueError, match="No valid stock codes"):
            _validate_codes(["abc", "12", "123456"])

    def test_正常系_無効コードをスキップして有効コードのみ返す(self) -> None:
        """無効なコードをスキップし、有効なコードのみ返すことを確認。"""
        from news_scraper.tdnet import _validate_codes

        result = _validate_codes(["7203", "abc", "6758", "12"])
        assert result == ["7203", "6758"]

    def test_正常系_前後の空白を除去して検証(self) -> None:
        """コードの前後空白を除去してから検証されることを確認。"""
        from news_scraper.tdnet import _validate_codes

        result = _validate_codes([" 7203 ", "6758"])
        assert result == ["7203", "6758"]


class TestBuildTdnetUrl:
    """_build_tdnet_url() のテスト."""

    def test_正常系_単一コードでURL構築(self) -> None:
        """単一のコードから正しい URL が構築されることを確認。"""
        from news_scraper.tdnet import _build_tdnet_url

        url = _build_tdnet_url(["7203"])
        assert url == f"{TDNET_BASE_URL}/7203.rss"

    def test_正常系_複数コードでカンマ区切りURL構築(self) -> None:
        """複数のコードがカンマ区切りで URL に含まれることを確認。"""
        from news_scraper.tdnet import _build_tdnet_url

        url = _build_tdnet_url(["7203", "6758", "9984"])
        assert url == f"{TDNET_BASE_URL}/7203,6758,9984.rss"


class TestExtractTickerFromTitle:
    """_extract_ticker_from_title() のテスト."""

    def test_正常系_タイトルにコードが含まれる場合(self) -> None:
        """タイトルに証券コードが含まれる場合に正しく抽出されることを確認。"""
        from news_scraper.tdnet import _extract_ticker_from_title

        result = _extract_ticker_from_title(
            "[7203] トヨタ自動車 決算短信", ["7203", "6758"]
        )
        assert result == "7203"

    def test_正常系_タイトルにコードが含まれない場合(self) -> None:
        """タイトルに証券コードが含まれない場合に空文字列を返すことを確認。"""
        from news_scraper.tdnet import _extract_ticker_from_title

        result = _extract_ticker_from_title("適時開示情報のお知らせ", ["7203", "6758"])
        assert result == ""

    def test_正常系_先頭のコードが優先される(self) -> None:
        """複数のコードが含まれる場合にリストの先頭が優先されることを確認。"""
        from news_scraper.tdnet import _extract_ticker_from_title

        result = _extract_ticker_from_title(
            "[7203][6758] 共同リリース", ["7203", "6758"]
        )
        assert result == "7203"


class TestFetchDisclosureFeed:
    """fetch_disclosure_feed() のテスト."""

    def test_正常系_デフォルトコードで取得(self) -> None:
        """codes=None でデフォルトコードを使用して取得することを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = fetch_disclosure_feed(mock_session)

        assert result == []
        called_url = mock_session.get.call_args[0][0]
        assert TDNET_BASE_URL in called_url

    def test_正常系_記事リストを返す(self) -> None:
        """RSS エントリから Article リストが正しく作成されることを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "[7203] トヨタ自動車 2026年3月期 決算短信",
            "link": "https://www.release.tdnet.info/inbs/140120260101000001.pdf",
            "published": "Wed, 01 Jan 2026 15:00:00 +0900",
            "summary": "決算短信の要約",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert len(result) == 1
        assert isinstance(result[0], Article)
        assert result[0].source == "tdnet"
        assert result[0].category == "disclosure"
        assert result[0].ticker == "7203"

    def test_正常系_tickerがタイトルから抽出される(self) -> None:
        """Article.ticker にタイトルから抽出された証券コードが設定されることを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "[6758] ソニーグループ 新製品発表",
            "link": "https://example.com/6758",
            "published": "",
            "summary": "",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = fetch_disclosure_feed(mock_session, codes=["7203", "6758"])

        assert result[0].ticker == "6758"

    def test_正常系_tickerが見つからない場合は空文字列(self) -> None:
        """タイトルに証券コードがない場合 ticker が空文字列になることを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "市場全体のお知らせ",
            "link": "https://example.com/general",
            "published": "",
            "summary": "",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert result[0].ticker == ""

    def test_正常系_URL構築が正しい(self) -> None:
        """コードリストから正しい URL が構築されることを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        mock_feed = MagicMock()
        mock_feed.entries = []

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            fetch_disclosure_feed(mock_session, codes=["7203", "6758"])

        called_url = mock_session.get.call_args[0][0]
        assert called_url == f"{TDNET_BASE_URL}/7203,6758.rss"

    def test_異常系_HTTPエラーで空リストを返す(self) -> None:
        """HTTP エラー時に空リストを返す graceful degradation を確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("503 Service Unavailable")

        result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert result == []

    def test_異常系_タイムアウトで空リストを返す(self) -> None:
        """タイムアウト時に空リストを返す graceful degradation を確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_session.get.side_effect = TimeoutError("Request timed out")

        result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert result == []

    def test_異常系_不正XMLで空リストを返す(self) -> None:
        """不正な XML レスポンスでも空リストを返す graceful degradation を確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "not xml at all"
        mock_session.get.return_value = mock_response

        # feedparser は不正 XML でも entries=[] を返すことが多いが、
        # 例外を送出するケースをテスト
        with patch(
            "news_scraper.tdnet.feedparser.parse",
            side_effect=Exception("XML parse error"),
        ):
            result = fetch_disclosure_feed(mock_session, codes=["7203"])

        assert result == []

    def test_異常系_空コードリストで空リストを返す(self) -> None:
        """空のコードリストで空リストを返す（graceful）ことを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        result = fetch_disclosure_feed(mock_session, codes=[])

        assert result == []

    def test_異常系_全て無効なコードで空リストを返す(self) -> None:
        """全て無効なコードの場合に空リストを返すことを確認。"""
        from news_scraper.tdnet import fetch_disclosure_feed

        mock_session = MagicMock()
        result = fetch_disclosure_feed(mock_session, codes=["abc", "xyz"])

        assert result == []


class TestAsyncFetchDisclosureFeed:
    """async_fetch_disclosure_feed() のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_記事リストを返す(self) -> None:
        """非同期で RSS エントリから Article リストが正しく作成されることを確認。"""
        from news_scraper.tdnet import async_fetch_disclosure_feed

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = "<rss/>"
        mock_session.get.return_value = mock_response

        entry = MagicMock()
        entry.get = lambda k, d="": {
            "title": "[7203] トヨタ自動車 決算発表",
            "link": "https://example.com/7203",
            "published": "Wed, 01 Jan 2026 15:00:00 +0900",
            "summary": "決算の要約",
        }.get(k, d)

        mock_feed = MagicMock()
        mock_feed.entries = [entry]

        with patch("news_scraper.tdnet.feedparser.parse", return_value=mock_feed):
            result = await async_fetch_disclosure_feed(mock_session, codes=["7203"])

        assert len(result) == 1
        assert result[0].source == "tdnet"
        assert result[0].ticker == "7203"

    @pytest.mark.asyncio
    async def test_異常系_HTTPエラーで空リストを返す(self) -> None:
        """非同期 HTTP エラー時に空リストを返すことを確認。"""
        from news_scraper.tdnet import async_fetch_disclosure_feed

        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("503 Service Unavailable")

        result = await async_fetch_disclosure_feed(mock_session, codes=["7203"])

        assert result == []

    @pytest.mark.asyncio
    async def test_異常系_空コードリストで空リストを返す(self) -> None:
        """非同期で空コードリストを渡した場合に空リストを返すことを確認。"""
        from news_scraper.tdnet import async_fetch_disclosure_feed

        mock_session = AsyncMock()
        result = await async_fetch_disclosure_feed(mock_session, codes=[])

        assert result == []


class TestFetchMultipleCodes:
    """fetch_multiple_codes() のテスト."""

    def test_正常系_デフォルトコードグループで取得(self) -> None:
        """code_groups=None でデフォルトコードを使用して取得することを確認。"""
        from news_scraper.tdnet import fetch_multiple_codes

        mock_session = MagicMock()

        with (
            patch("news_scraper.tdnet.fetch_disclosure_feed") as mock_fetch,
            patch("news_scraper.tdnet.time.sleep"),
        ):
            mock_fetch.return_value = [
                Article(
                    title="開示情報",
                    url="https://example.com/1",
                    source="tdnet",
                    category="disclosure",
                    ticker="7203",
                )
            ]
            df = fetch_multiple_codes(mock_session)

        assert not df.empty
        assert mock_fetch.call_count == 1

    def test_正常系_複数コードグループで取得(self) -> None:
        """複数のコードグループで取得することを確認。"""
        from news_scraper.tdnet import fetch_multiple_codes

        mock_session = MagicMock()

        with (
            patch("news_scraper.tdnet.fetch_disclosure_feed") as mock_fetch,
            patch("news_scraper.tdnet.time.sleep"),
        ):
            mock_fetch.return_value = [
                Article(
                    title="開示情報",
                    url="https://example.com/1",
                    source="tdnet",
                    category="disclosure",
                )
            ]
            df = fetch_multiple_codes(
                mock_session,
                code_groups=[["7203", "6758"], ["9984"]],
            )

        assert not df.empty
        assert mock_fetch.call_count == 2

    def test_正常系_エラーグループをスキップ(self) -> None:
        """個別グループの取得失敗をスキップすることを確認。"""
        from news_scraper.tdnet import fetch_multiple_codes

        mock_session = MagicMock()

        with (
            patch("news_scraper.tdnet.fetch_disclosure_feed") as mock_fetch,
            patch("news_scraper.tdnet.time.sleep"),
        ):
            mock_fetch.side_effect = Exception("Unexpected error")
            df = fetch_multiple_codes(
                mock_session,
                code_groups=[["7203"]],
            )

        assert df.empty


class TestAsyncFetchMultipleCodes:
    """async_fetch_multiple_codes() のテスト."""

    @pytest.mark.asyncio
    async def test_正常系_空コードグループで空DataFrameを返す(self) -> None:
        """空のコードグループリストで空 DataFrame を返すことを確認。"""
        from news_scraper.tdnet import async_fetch_multiple_codes

        mock_session = AsyncMock()
        df = await async_fetch_multiple_codes(mock_session, code_groups=[])

        assert df.empty

    @pytest.mark.asyncio
    async def test_正常系_指定コードグループで記事を取得(self) -> None:
        """指定コードグループの記事を非同期で取得することを確認。"""
        from news_scraper.tdnet import async_fetch_multiple_codes

        mock_session = AsyncMock()

        with patch("news_scraper.tdnet.async_fetch_disclosure_feed") as mock_fetch:
            mock_fetch.return_value = [
                Article(
                    title="非同期開示情報",
                    url="https://example.com/1",
                    source="tdnet",
                    category="disclosure",
                    ticker="7203",
                )
            ]
            df = await async_fetch_multiple_codes(
                mock_session,
                code_groups=[["7203"]],
                config=ScraperConfig(delay=0.0, max_concurrency=1),
            )

        assert not df.empty
        assert len(df) == 1
