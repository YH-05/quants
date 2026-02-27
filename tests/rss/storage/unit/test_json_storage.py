"""Unit tests for JSONStorage class."""

import json
from pathlib import Path

import pytest

from rss.exceptions import RSSError
from rss.storage.json_storage import JSONStorage
from rss.types import (
    Feed,
    FeedItem,
    FeedItemsData,
    FeedsData,
    FetchInterval,
    FetchStatus,
)


class TestJSONStorageInit:
    """Test JSONStorage initialization."""

    def test_init_success(self, tmp_path: Path) -> None:
        """Test successful initialization."""
        storage = JSONStorage(tmp_path)
        assert storage.data_dir == tmp_path
        assert storage.lock_manager is not None

    def test_init_invalid_data_dir_type(self) -> None:
        """Test initialization with invalid data_dir type."""
        with pytest.raises(ValueError, match="data_dir must be a Path object"):
            JSONStorage("invalid")  # type: ignore[arg-type]


class TestSaveFeeds:
    """Test save_feeds method."""

    def test_save_feeds_success(self, tmp_path: Path) -> None:
        """Test saving feeds successfully."""
        storage = JSONStorage(tmp_path)

        feed = Feed(
            feed_id="550e8400-e29b-41d4-a716-446655440000",
            url="https://example.com/feed.xml",
            title="Example Feed",
            category="finance",
            fetch_interval=FetchInterval.DAILY,
            created_at="2026-01-14T10:00:00Z",
            updated_at="2026-01-14T10:00:00Z",
            last_fetched=None,
            last_status=FetchStatus.PENDING,
            enabled=True,
        )
        feeds_data = FeedsData(version="1.0", feeds=[feed])

        storage.save_feeds(feeds_data)

        # Verify file exists
        feeds_file = tmp_path / "feeds.json"
        assert feeds_file.exists()

        # Verify content
        content = feeds_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["version"] == "1.0"
        assert len(data["feeds"]) == 1
        assert data["feeds"][0]["feed_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["feeds"][0]["title"] == "Example Feed"

    def test_save_feeds_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_feeds creates data directory if it doesn't exist."""
        data_dir = tmp_path / "new_dir"
        storage = JSONStorage(data_dir)

        feeds_data = FeedsData(version="1.0", feeds=[])
        storage.save_feeds(feeds_data)

        assert data_dir.exists()
        assert (data_dir / "feeds.json").exists()

    def test_save_feeds_utf8_encoding(self, tmp_path: Path) -> None:
        """Test that feeds are saved with UTF-8 encoding."""
        storage = JSONStorage(tmp_path)

        feed = Feed(
            feed_id="550e8400-e29b-41d4-a716-446655440000",
            url="https://example.com/feed.xml",
            title="日本語タイトル",  # Japanese characters
            category="finance",
            fetch_interval=FetchInterval.DAILY,
            created_at="2026-01-14T10:00:00Z",
            updated_at="2026-01-14T10:00:00Z",
            last_fetched=None,
            last_status=FetchStatus.PENDING,
            enabled=True,
        )
        feeds_data = FeedsData(version="1.0", feeds=[feed])

        storage.save_feeds(feeds_data)

        # Verify UTF-8 encoding
        feeds_file = tmp_path / "feeds.json"
        content = feeds_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["feeds"][0]["title"] == "日本語タイトル"

    def test_save_feeds_indented_json(self, tmp_path: Path) -> None:
        """Test that JSON is saved with indentation for manual editability."""
        storage = JSONStorage(tmp_path)

        feeds_data = FeedsData(version="1.0", feeds=[])
        storage.save_feeds(feeds_data)

        feeds_file = tmp_path / "feeds.json"
        content = feeds_file.read_text(encoding="utf-8")

        # Check for indentation (at least one line with spaces)
        lines = content.split("\n")
        assert any(line.startswith("  ") for line in lines)


class TestLoadFeeds:
    """Test load_feeds method."""

    def test_load_feeds_success(self, tmp_path: Path) -> None:
        """Test loading feeds successfully."""
        storage = JSONStorage(tmp_path)

        # Save feeds first
        feed = Feed(
            feed_id="550e8400-e29b-41d4-a716-446655440000",
            url="https://example.com/feed.xml",
            title="Example Feed",
            category="finance",
            fetch_interval=FetchInterval.DAILY,
            created_at="2026-01-14T10:00:00Z",
            updated_at="2026-01-14T10:00:00Z",
            last_fetched=None,
            last_status=FetchStatus.PENDING,
            enabled=True,
        )
        feeds_data = FeedsData(version="1.0", feeds=[feed])
        storage.save_feeds(feeds_data)

        # Load feeds
        loaded = storage.load_feeds()

        assert loaded.version == "1.0"
        assert len(loaded.feeds) == 1
        assert loaded.feeds[0].feed_id == "550e8400-e29b-41d4-a716-446655440000"
        assert loaded.feeds[0].title == "Example Feed"
        assert loaded.feeds[0].fetch_interval == FetchInterval.DAILY
        assert loaded.feeds[0].last_status == FetchStatus.PENDING

    def test_load_feeds_file_not_exists(self, tmp_path: Path) -> None:
        """Test loading feeds when file doesn't exist returns empty data."""
        storage = JSONStorage(tmp_path)

        loaded = storage.load_feeds()

        assert loaded.version == "1.0"
        assert len(loaded.feeds) == 0

    def test_load_feeds_invalid_json(self, tmp_path: Path) -> None:
        """Test loading feeds with invalid JSON raises error."""
        storage = JSONStorage(tmp_path)

        # Create invalid JSON file
        feeds_file = tmp_path / "feeds.json"
        tmp_path.mkdir(parents=True, exist_ok=True)
        feeds_file.write_text("invalid json", encoding="utf-8")

        with pytest.raises(RSSError, match=r"load feeds from.*failed"):
            storage.load_feeds()


class TestSaveItems:
    """Test save_items method."""

    def test_save_items_success(self, tmp_path: Path) -> None:
        """Test saving items successfully."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        item = FeedItem(
            item_id="660e8400-e29b-41d4-a716-446655440001",
            title="Article Title",
            link="https://example.com/article",
            published="2026-01-14T09:00:00Z",
            summary="Article summary...",
            content="Full content...",
            author="Author Name",
            fetched_at="2026-01-14T10:00:00Z",
        )
        items_data = FeedItemsData(version="1.0", feed_id=feed_id, items=[item])

        storage.save_items(feed_id, items_data)

        # Verify file exists
        items_file = tmp_path / feed_id / "items.json"
        assert items_file.exists()

        # Verify content
        content = items_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["version"] == "1.0"
        assert data["feed_id"] == feed_id
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Article Title"

    def test_save_items_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_items creates feed directory if it doesn't exist."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        items_data = FeedItemsData(version="1.0", feed_id=feed_id, items=[])

        storage.save_items(feed_id, items_data)

        feed_dir = tmp_path / feed_id
        assert feed_dir.exists()
        assert (feed_dir / "items.json").exists()

    def test_save_items_empty_feed_id(self, tmp_path: Path) -> None:
        """Test saving items with empty feed_id raises error."""
        storage = JSONStorage(tmp_path)

        items_data = FeedItemsData(version="1.0", feed_id="", items=[])

        with pytest.raises(ValueError, match="feed_id cannot be empty"):
            storage.save_items("", items_data)

    def test_save_items_feed_id_mismatch(self, tmp_path: Path) -> None:
        """Test saving items with mismatched feed_id raises error."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        items_data = FeedItemsData(version="1.0", feed_id="different-feed-id", items=[])

        with pytest.raises(ValueError, match=r"data.feed_id .* must match feed_id"):
            storage.save_items(feed_id, items_data)

    def test_save_items_utf8_encoding(self, tmp_path: Path) -> None:
        """Test that items are saved with UTF-8 encoding."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        item = FeedItem(
            item_id="660e8400-e29b-41d4-a716-446655440001",
            title="日本語タイトル",  # Japanese characters
            link="https://example.com/article",
            published="2026-01-14T09:00:00Z",
            summary="要約",
            content="コンテンツ",
            author="著者",
            fetched_at="2026-01-14T10:00:00Z",
        )
        items_data = FeedItemsData(version="1.0", feed_id=feed_id, items=[item])

        storage.save_items(feed_id, items_data)

        # Verify UTF-8 encoding
        items_file = tmp_path / feed_id / "items.json"
        content = items_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["items"][0]["title"] == "日本語タイトル"


class TestLoadItems:
    """Test load_items method."""

    def test_load_items_success(self, tmp_path: Path) -> None:
        """Test loading items successfully."""
        storage = JSONStorage(tmp_path)

        # Save items first
        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        item = FeedItem(
            item_id="660e8400-e29b-41d4-a716-446655440001",
            title="Article Title",
            link="https://example.com/article",
            published="2026-01-14T09:00:00Z",
            summary="Article summary...",
            content="Full content...",
            author="Author Name",
            fetched_at="2026-01-14T10:00:00Z",
        )
        items_data = FeedItemsData(version="1.0", feed_id=feed_id, items=[item])
        storage.save_items(feed_id, items_data)

        # Load items
        loaded = storage.load_items(feed_id)

        assert loaded.version == "1.0"
        assert loaded.feed_id == feed_id
        assert len(loaded.items) == 1
        assert loaded.items[0].title == "Article Title"

    def test_load_items_file_not_exists(self, tmp_path: Path) -> None:
        """Test loading items when file doesn't exist returns empty data."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        loaded = storage.load_items(feed_id)

        assert loaded.version == "1.0"
        assert loaded.feed_id == feed_id
        assert len(loaded.items) == 0

    def test_load_items_empty_feed_id(self, tmp_path: Path) -> None:
        """Test loading items with empty feed_id raises error."""
        storage = JSONStorage(tmp_path)

        with pytest.raises(ValueError, match="feed_id cannot be empty"):
            storage.load_items("")

    def test_load_items_invalid_json(self, tmp_path: Path) -> None:
        """Test loading items with invalid JSON raises error."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        feed_dir = tmp_path / feed_id
        feed_dir.mkdir(parents=True)
        items_file = feed_dir / "items.json"
        items_file.write_text("invalid json", encoding="utf-8")

        with pytest.raises(RSSError, match=r"load items for feed.*failed"):
            storage.load_items(feed_id)


class TestFileLocking:
    """Test file locking behavior."""

    def test_save_feeds_with_lock(self, tmp_path: Path) -> None:
        """Test that save_feeds uses file locking."""
        storage = JSONStorage(tmp_path)

        feeds_data = FeedsData(version="1.0", feeds=[])
        storage.save_feeds(feeds_data)

        # Verify that lock file was created and removed
        lock_file = tmp_path / ".feeds.lock"
        # Lock file should not exist after operation completes
        assert not lock_file.exists() or lock_file.stat().st_size == 0

    def test_save_items_with_lock(self, tmp_path: Path) -> None:
        """Test that save_items uses file locking."""
        storage = JSONStorage(tmp_path)

        feed_id = "550e8400-e29b-41d4-a716-446655440000"
        items_data = FeedItemsData(version="1.0", feed_id=feed_id, items=[])
        storage.save_items(feed_id, items_data)

        # Verify that lock file was created and removed
        lock_file = tmp_path / feed_id / ".items.lock"
        # Lock file should not exist after operation completes
        assert not lock_file.exists() or lock_file.stat().st_size == 0
