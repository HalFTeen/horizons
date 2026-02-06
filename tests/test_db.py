"""Unit tests for horizons.db module."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


class TestInitialize:
    """Tests for database initialization."""

    def test_creates_database_file(self, tmp_path: Path) -> None:
        """initialize() should create the database file."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize

            initialize()

            assert db_path.exists()

    def test_creates_required_tables(self, tmp_path: Path) -> None:
        """initialize() should create sources, items, and runs tables."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize

            initialize()

            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            assert "sources" in tables
            assert "items" in tables
            assert "runs" in tables


class TestUpsertSources:
    """Tests for upsert_sources function."""

    def test_inserts_new_sources(self, tmp_path: Path) -> None:
        """upsert_sources() should insert new source records."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources

            initialize()

            sources = [
                {"name": "Test RSS", "url": "https://example.com/feed", "kind": "rss"},
                {"name": "Test Blog", "url": "https://example.com/blog", "kind": "webpage"},
            ]
            upsert_sources("test_followee", sources)

            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT followee_id, name, url, kind FROM sources")
            rows = cursor.fetchall()
            conn.close()

            assert len(rows) == 2
            assert rows[0] == ("test_followee", "Test RSS", "https://example.com/feed", "rss")

    def test_ignores_duplicate_sources(self, tmp_path: Path) -> None:
        """upsert_sources() should ignore duplicates (same followee_id + url)."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources

            initialize()

            sources = [{"name": "Test RSS", "url": "https://example.com/feed", "kind": "rss"}]
            upsert_sources("test_followee", sources)
            upsert_sources("test_followee", sources)  # Insert again

            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM sources")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 1


class TestGetSourceId:
    """Tests for get_source_id function."""

    def test_returns_source_id(self, tmp_path: Path) -> None:
        """get_source_id() should return the ID of an existing source."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources, get_source_id

            initialize()

            sources = [{"name": "Test RSS", "url": "https://example.com/feed", "kind": "rss"}]
            upsert_sources("test_followee", sources)

            source_id = get_source_id("test_followee", "https://example.com/feed")

            assert source_id == 1

    def test_raises_on_missing_source(self, tmp_path: Path) -> None:
        """get_source_id() should raise LookupError for missing source."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, get_source_id

            initialize()

            with pytest.raises(LookupError, match="Source not found"):
                get_source_id("nonexistent", "https://example.com")


class TestInsertItem:
    """Tests for insert_item function."""

    def test_inserts_new_item(self, tmp_path: Path) -> None:
        """insert_item() should insert a new item and return its ID."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources, get_source_id, insert_item

            initialize()

            upsert_sources("test", [{"name": "Feed", "url": "https://example.com", "kind": "rss"}])
            source_id = get_source_id("test", "https://example.com")

            record = {
                "followee_id": "test",
                "source_id": source_id,
                "title": "Test Article",
                "url": "https://example.com/article",
                "published_at": "2024-01-01",
                "content": "Test content",
            }
            item_id = insert_item(record)

            assert item_id is not None
            assert item_id > 0

    def test_returns_none_on_duplicate(self, tmp_path: Path) -> None:
        """insert_item() should return None when inserting duplicate (same followee_id + title)."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources, get_source_id, insert_item

            initialize()

            upsert_sources("test", [{"name": "Feed", "url": "https://example.com", "kind": "rss"}])
            source_id = get_source_id("test", "https://example.com")

            record = {
                "followee_id": "test",
                "source_id": source_id,
                "title": "Duplicate Article",
                "url": "https://example.com/article",
                "published_at": None,
                "content": "",
            }
            first_id = insert_item(record)
            second_id = insert_item(record)

            assert first_id is not None
            assert second_id is None


class TestUpdateItem:
    """Tests for update_item function."""

    def test_updates_item_fields(self, tmp_path: Path) -> None:
        """update_item() should update specified fields."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources, get_source_id, insert_item, update_item

            initialize()

            upsert_sources("test", [{"name": "Feed", "url": "https://example.com", "kind": "rss"}])
            source_id = get_source_id("test", "https://example.com")

            record = {
                "followee_id": "test",
                "source_id": source_id,
                "title": "Test",
                "url": "https://example.com",
                "published_at": None,
                "content": "",
            }
            item_id = insert_item(record)

            update_item(item_id, status="processed", transcript_path="/path/to/transcript")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT status, transcript_path FROM items WHERE id = ?", (item_id,)).fetchone()
            conn.close()

            assert row["status"] == "processed"
            assert row["transcript_path"] == "/path/to/transcript"


class TestFetchPendingItems:
    """Tests for fetch_pending_items function."""

    def test_returns_pending_items_only(self, tmp_path: Path) -> None:
        """fetch_pending_items() should only return items with status='pending'."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, upsert_sources, get_source_id, insert_item, update_item, fetch_pending_items

            initialize()

            upsert_sources("test", [{"name": "Feed", "url": "https://example.com", "kind": "rss"}])
            source_id = get_source_id("test", "https://example.com")

            # Insert two items
            for i, title in enumerate(["Pending Article", "Processed Article"]):
                record = {
                    "followee_id": "test",
                    "source_id": source_id,
                    "title": title,
                    "url": f"https://example.com/{i}",
                    "published_at": None,
                    "content": "",
                }
                item_id = insert_item(record)
                if title == "Processed Article":
                    update_item(item_id, status="processed")

            pending = fetch_pending_items()

            assert len(pending) == 1
            assert pending[0]["title"] == "Pending Article"
            assert pending[0]["source_name"] == "Feed"

    def test_returns_empty_list_when_no_pending(self, tmp_path: Path) -> None:
        """fetch_pending_items() should return empty list when no pending items."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            from horizons.db import initialize, fetch_pending_items

            initialize()

            pending = fetch_pending_items()

            assert pending == []
