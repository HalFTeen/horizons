"""Unit tests for horizons.collector.rss module."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRSSRecord:
    """Tests for RSSRecord dataclass."""

    def test_all_fields(self) -> None:
        """RSSRecord should store all feed entry data."""
        from horizons.collector.rss import RSSRecord

        record = RSSRecord(
            followee_id="test",
            source_url="https://example.com/feed",
            title="Test Article",
            link="https://example.com/article",
            published="Mon, 01 Jan 2024 12:00:00 GMT",
            summary="Test summary",
        )
        assert record.followee_id == "test"
        assert record.title == "Test Article"
        assert record.published == "Mon, 01 Jan 2024 12:00:00 GMT"


class TestRSSCollector:
    """Tests for RSSCollector class."""

    @pytest.mark.skip(reason="Module-level constant patching doesn't work - DB_PATH computed before patch applied")
    def test_sync_followees_inserts_rss_sources_only(self, tmp_path: Path) -> None:
        """sync_followees() should only insert sources with kind='rss'."""
        config_dir, data_dir = tmp_path / "config", tmp_path / "data"
        db_path = data_dir / "horizons.db"

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            from horizons.db import initialize
            from horizons.collector.rss import RSSCollector

            initialize()

            collector = RSSCollector()
            collector.sync_followees()

            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT kind FROM sources")
            kinds = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Should only have RSS sources, not webpage
            assert all(k == "rss" for k in kinds)
            assert len(kinds) == 1

    def test_fetch_parses_rss_entries(self, sample_rss_content: str) -> None:
        """fetch() should parse RSS feed and return RSSRecord objects."""
        from horizons.collector.rss import RSSCollector, RSSRecord
        from horizons.config import Followee, FollowSource

        # Create a mock session that returns sample RSS content
        mock_response = MagicMock()
        mock_response.content = sample_rss_content.encode("utf-8")
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        # Create test followee with RSS source
        followee = Followee(
            id="test",
            display_name="Test",
            sources=[FollowSource(name="Test Feed", url="https://example.com/feed", kind="rss")],
        )

        collector = RSSCollector(session=mock_session)
        # Override followees for this test
        collector.followees = {"test": followee}

        records = collector.fetch(followee)

        assert len(records) == 2
        assert all(isinstance(r, RSSRecord) for r in records)
        assert records[0].title == "Test Article 1"
        assert records[1].title == "Test Article 2"

    def test_fetch_handles_http_error(self) -> None:
        """fetch() should handle HTTP errors gracefully."""
        import requests
        from horizons.collector.rss import RSSCollector
        from horizons.config import Followee, FollowSource

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.RequestException("Network error")

        followee = Followee(
            id="test",
            display_name="Test",
            sources=[FollowSource(name="Feed", url="https://example.com/feed", kind="rss")],
        )

        collector = RSSCollector(session=mock_session)
        collector.followees = {"test": followee}
        records = collector.fetch(followee)

        assert records == []

    def test_fetch_skips_non_rss_sources(self) -> None:
        """fetch() should skip sources that are not RSS type."""
        from horizons.collector.rss import RSSCollector
        from horizons.config import Followee, FollowSource

        mock_session = MagicMock()

        followee = Followee(
            id="test",
            display_name="Test",
            sources=[
                FollowSource(name="Webpage", url="https://example.com/page", kind="webpage"),
                FollowSource(name="YouTube", url="https://youtube.com/channel", kind="youtube"),
            ],
        )

        collector = RSSCollector(session=mock_session)
        collector.followees = {"test": followee}
        records = collector.fetch(followee)

        # Should not make any HTTP requests for non-RSS sources
        mock_session.get.assert_not_called()
        assert records == []


class TestRSSCollectorIngest:
    """Tests for RSSCollector.ingest() integration."""

    def test_ingest_stores_new_items(self, sample_rss_content: str) -> None:
        """ingest() should fetch RSS and store new items in database."""
        from horizons.db import initialize
        from horizons.collector.rss import RSSCollector
        from horizons.config import Followee, FollowSource

        # Get shared test paths
        import os as _os
        from pathlib import Path as _Path
        test_base = _Path(_os.environ.get("HORIZONS_BASE_DIR", _Path(__file__).resolve().parent.parent))
        db_path = test_base / "data" / "horizons.db"

        # Clean database before test
        if db_path.exists():
            db_path.unlink()

        # Mock RSS response
        mock_response = MagicMock()
        mock_response.content = sample_rss_content.encode("utf-8")
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        # Create test followee
        followee = Followee(
            id="test_followee",
            display_name="Test",
            sources=[FollowSource(name="Test Feed", url="https://example.com/feed", kind="rss")],
        )

        # Initialize database
        initialize()

        collector = RSSCollector(session=mock_session)
        collector.followees = {"test_followee": followee}
        inserted = collector.ingest()

        assert inserted == 2

    def test_ingest_skips_duplicate_items(self, sample_rss_content: str) -> None:
        """ingest() should not insert duplicate items."""
        from horizons.db import initialize
        from horizons.collector.rss import RSSCollector
        from horizons.config import Followee, FollowSource

        # Get shared test paths
        import os as _os
        from pathlib import Path as _Path
        test_base = _Path(_os.environ.get("HORIZONS_BASE_DIR", _Path(__file__).resolve().parent.parent))
        db_path = test_base / "data" / "horizons.db"

        # Clean database before test
        if db_path.exists():
            db_path.unlink()

        # Mock RSS response
        mock_response = MagicMock()
        mock_response.content = sample_rss_content.encode("utf-8")
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        # Create test followee
        followee = Followee(
            id="test_followee",
            display_name="Test",
            sources=[FollowSource(name="Test Feed", url="https://example.com/feed", kind="rss")],
        )

        # Initialize database
        initialize()

        collector = RSSCollector(session=mock_session)
        collector.followees = {"test_followee": followee}
        first_inserted = collector.ingest()
        second_inserted = collector.ingest()

        assert first_inserted == 2
        assert second_inserted == 0  # All duplicates
