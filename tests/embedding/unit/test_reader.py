"""embedding.reader モジュールの単体テスト.

テストTODOリスト:
- [x] read_all_news_json: 存在しないディレクトリで FileNotFoundError
- [x] read_all_news_json: 空ディレクトリで空リストを返す
- [x] read_all_news_json: 正常な JSON ファイルを読み込める
- [x] read_all_news_json: 複数ソースのデータを読み込める
- [x] read_all_news_json: sources フィルタリングが機能する
- [x] read_all_news_json: 空の sources リストで空結果を返す
- [x] read_all_news_json: URL 重複除去が自動的に行われる
- [x] read_all_news_json: 不正 JSON はスキップされる
- [x] read_all_news_json: url なしのレコードはスキップされる
- [x] read_all_news_json: title なしのレコードはスキップされる
- [x] deduplicate_by_url: 重複 URL を排除する
- [x] deduplicate_by_url: 最初の出現を保持する
- [x] deduplicate_by_url: 空リストで空結果を返す
- [x] deduplicate_by_url: 重複なしのリストはそのまま返す
"""

import json
from pathlib import Path

import pytest

from embedding.reader import deduplicate_by_url, read_all_news_json
from embedding.types import ArticleRecord


class TestReadAllNewsJson:
    """read_all_news_json 関数のテスト."""

    def test_異常系_存在しないディレクトリでFileNotFoundError(
        self, tmp_path: Path
    ) -> None:
        """存在しないディレクトリを指定すると FileNotFoundError が発生することを確認。"""
        non_existent = tmp_path / "non_existent"

        with pytest.raises(FileNotFoundError, match="News directory not found"):
            read_all_news_json(non_existent)

    def test_正常系_空ディレクトリで空リストを返す(self, news_dir_empty: Path) -> None:
        """空のディレクトリを指定すると空リストを返すことを確認。"""
        result = read_all_news_json(news_dir_empty)
        assert result == []

    def test_正常系_JSONファイルを読み込みArticleRecordリストを返す(
        self, news_dir_with_data: Path
    ) -> None:
        """正常な JSON ファイルを読み込み ArticleRecord リストを返すことを確認。"""
        result = read_all_news_json(news_dir_with_data)

        assert len(result) == 3
        assert all(isinstance(r, ArticleRecord) for r in result)

    def test_正常系_複数ソースのデータを読み込める(
        self, news_dir_with_data: Path
    ) -> None:
        """複数ソースのデータを読み込めることを確認。"""
        result = read_all_news_json(news_dir_with_data)

        sources = {r.source for r in result}
        assert "cnbc" in sources
        assert "nasdaq" in sources

    def test_正常系_sourcesフィルタリングが機能する(
        self, news_dir_with_data: Path
    ) -> None:
        """sources パラメータでフィルタリングできることを確認。"""
        result = read_all_news_json(news_dir_with_data, sources=["cnbc"])

        assert len(result) == 2
        assert all(r.source == "cnbc" for r in result)

    def test_正常系_空のsourcesリストで空結果を返す(
        self, news_dir_with_data: Path
    ) -> None:
        """空の sources リストを指定すると空結果を返すことを確認。"""
        result = read_all_news_json(news_dir_with_data, sources=[])
        assert result == []

    def test_正常系_URL重複除去が自動的に行われる(self, tmp_path: Path) -> None:
        """同一 URL を持つ記事が重複除去されることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()

        # 重複 URL を含むデータ
        data = [
            {"url": "https://example.com/1", "title": "Article 1"},
            {"url": "https://example.com/1", "title": "Article 1 Duplicate"},
            {"url": "https://example.com/2", "title": "Article 2"},
        ]
        (source_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 2

    def test_正常系_不正JSONはスキップされる(self, tmp_path: Path) -> None:
        """不正な JSON ファイルはスキップされることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()

        # 不正 JSON ファイル
        (source_dir / "invalid.json").write_text("not valid json", encoding="utf-8")
        # 有効 JSON ファイル
        valid_data = [{"url": "https://example.com/1", "title": "Valid Article"}]
        (source_dir / "valid.json").write_text(json.dumps(valid_data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].url == "https://example.com/1"

    def test_正常系_urlなしのレコードはスキップされる(self, tmp_path: Path) -> None:
        """url フィールドがないレコードはスキップされることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()

        data = [
            {"url": "", "title": "No URL Article"},
            {"title": "Missing URL Article"},  # url キーなし
            {"url": "https://example.com/valid", "title": "Valid Article"},
        ]
        (source_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].url == "https://example.com/valid"

    def test_正常系_titleなしのレコードはスキップされる(self, tmp_path: Path) -> None:
        """title フィールドがないレコードはスキップされることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()

        data = [
            {"url": "https://example.com/1", "title": ""},
            {"url": "https://example.com/2"},  # title キーなし
            {"url": "https://example.com/valid", "title": "Valid Article"},
        ]
        (source_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].url == "https://example.com/valid"

    def test_正常系_JSON配列でないファイルはスキップされる(
        self, tmp_path: Path
    ) -> None:
        """JSON オブジェクト（配列でない）はスキップされることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()

        # JSON オブジェクト（配列でない）
        (source_dir / "object.json").write_text(
            json.dumps({"url": "https://example.com", "title": "Object"}),
            encoding="utf-8",
        )
        # 有効な配列
        (source_dir / "array.json").write_text(
            json.dumps([{"url": "https://example.com/valid", "title": "Array Item"}]),
            encoding="utf-8",
        )

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].url == "https://example.com/valid"

    def test_正常系_sourceフィールドが正しく設定される(self, tmp_path: Path) -> None:
        """ArticleRecord の source フィールドがディレクトリ名から設定されることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "my_source"
        source_dir.mkdir()

        data = [{"url": "https://example.com/1", "title": "Article"}]
        (source_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].source == "my_source"

    def test_正常系_json_fileフィールドにパスが設定される(self, tmp_path: Path) -> None:
        """ArticleRecord の json_file フィールドにファイルパスが設定されることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()
        json_file = source_dir / "2024-01-15.json"

        data = [{"url": "https://example.com/1", "title": "Article"}]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].json_file == str(json_file)

    def test_正常系_非dictアイテムはスキップされる(self, tmp_path: Path) -> None:
        """配列内の非 dict アイテムはスキップされることを確認。"""
        news_dir = tmp_path / "news"
        news_dir.mkdir()
        source_dir = news_dir / "cnbc"
        source_dir.mkdir()

        data = [
            "not a dict",
            42,
            None,
            {"url": "https://example.com/valid", "title": "Valid Article"},
        ]
        (source_dir / "data.json").write_text(json.dumps(data), encoding="utf-8")

        result = read_all_news_json(news_dir)
        assert len(result) == 1
        assert result[0].url == "https://example.com/valid"


class TestDeduplicateByUrl:
    """deduplicate_by_url 関数のテスト."""

    def test_正常系_空リストで空結果を返す(self) -> None:
        """空リストを入力すると空リストを返すことを確認。"""
        result = deduplicate_by_url([])
        assert result == []

    def test_正常系_重複なしのリストはそのまま返す(self) -> None:
        """重複がないリストはそのまま返すことを確認。"""
        articles = [
            ArticleRecord(url="https://example.com/1", title="Article 1"),
            ArticleRecord(url="https://example.com/2", title="Article 2"),
            ArticleRecord(url="https://example.com/3", title="Article 3"),
        ]
        result = deduplicate_by_url(articles)
        assert len(result) == 3

    def test_正常系_重複URLを排除する(self) -> None:
        """重複する URL を持つ記事を排除することを確認。"""
        articles = [
            ArticleRecord(url="https://example.com/1", title="Article 1"),
            ArticleRecord(url="https://example.com/1", title="Article 1 Dup"),
            ArticleRecord(url="https://example.com/2", title="Article 2"),
        ]
        result = deduplicate_by_url(articles)
        assert len(result) == 2

    def test_正常系_最初の出現を保持する(self) -> None:
        """重複がある場合、最初の出現を保持することを確認。"""
        articles = [
            ArticleRecord(url="https://example.com/1", title="First"),
            ArticleRecord(url="https://example.com/1", title="Second"),
        ]
        result = deduplicate_by_url(articles)
        assert len(result) == 1
        assert result[0].title == "First"

    def test_正常系_出現順序を維持する(self) -> None:
        """重複除去後も出現順序が維持されることを確認。"""
        articles = [
            ArticleRecord(url="https://example.com/3", title="C"),
            ArticleRecord(url="https://example.com/1", title="A"),
            ArticleRecord(url="https://example.com/2", title="B"),
        ]
        result = deduplicate_by_url(articles)
        assert [r.url for r in result] == [
            "https://example.com/3",
            "https://example.com/1",
            "https://example.com/2",
        ]

    def test_正常系_全て重複の場合1件のみ返す(self) -> None:
        """全て同じ URL の場合、1件のみ返すことを確認。"""
        articles = [
            ArticleRecord(url="https://example.com/same", title="First"),
            ArticleRecord(url="https://example.com/same", title="Second"),
            ArticleRecord(url="https://example.com/same", title="Third"),
        ]
        result = deduplicate_by_url(articles)
        assert len(result) == 1
        assert result[0].title == "First"
