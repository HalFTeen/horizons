"""Unit tests for horizons.collector.webpage module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestWebPageRecord:
    """Tests for WebPageRecord dataclass."""

    def test_all_fields(self) -> None:
        """WebPageRecord should store all webpage data."""
        from horizons.collector.webpage import WebPageRecord

        record = WebPageRecord(
            followee_id="test",
            source_url="https://example.com",
            url="https://example.com/article",
            title="Test Article",
            content="This is the article content.",
        )
        assert record.followee_id == "test"
        assert record.title == "Test Article"
        assert record.content == "This is the article content."


class TestWebPageCollector:
    """Tests for WebPageCollector class."""

    def test_fetch_single_extracts_content(self, sample_webpage_html: str) -> None:
        """fetch_single() should extract title and content from webpage."""
        from horizons.collector.webpage import WebPageCollector

        mock_response = MagicMock()
        mock_response.text = sample_webpage_html
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        # Mock trafilatura.extract to return structured data
        trafilatura_result = json.dumps({
            "title": "Interview with Test Person",
            "text": "This is the first paragraph of the interview content.\n\nThis is the second paragraph with more details.",
        })

        with patch("horizons.collector.webpage.trafilatura.extract", return_value=trafilatura_result):
            collector = WebPageCollector(session=mock_session)
            record = collector.fetch_single(
                followee_id="test",
                source_url="https://example.com",
                url="https://example.com/interview",
            )

        assert record is not None
        assert record.title == "Interview with Test Person"
        assert "first paragraph" in record.content

    def test_fetch_single_handles_http_error(self) -> None:
        """fetch_single() should return None on HTTP error."""
        import requests
        from horizons.collector.webpage import WebPageCollector

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.RequestException("Connection failed")

        collector = WebPageCollector(session=mock_session)
        record = collector.fetch_single("test", "https://example.com", "https://example.com/page")

        assert record is None

    def test_fetch_single_returns_none_on_no_content(self) -> None:
        """fetch_single() should return None when trafilatura extracts nothing."""
        from horizons.collector.webpage import WebPageCollector

        mock_response = MagicMock()
        mock_response.text = "<html><body>Empty</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        with patch("horizons.collector.webpage.trafilatura.extract", return_value=None):
            collector = WebPageCollector(session=mock_session)
            record = collector.fetch_single("test", "https://example.com", "https://example.com/empty")

        assert record is None

    def test_fetch_single_falls_back_to_html_title(self, sample_webpage_html: str) -> None:
        """fetch_single() should use HTML title if trafilatura doesn't extract one."""
        from horizons.collector.webpage import WebPageCollector

        mock_response = MagicMock()
        mock_response.text = sample_webpage_html
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        # trafilatura returns content but no title
        trafilatura_result = json.dumps({
            "title": None,  # No title
            "text": "Some content here.",
        })

        with patch("horizons.collector.webpage.trafilatura.extract", return_value=trafilatura_result):
            collector = WebPageCollector(session=mock_session)
            record = collector.fetch_single("test", "https://example.com", "https://example.com/page")

        assert record is not None
        assert record.title == "Test Interview"  # From HTML <title>


class TestWebPageCollectorStoreRecord:
    """Tests for WebPageCollector.store_record() method."""

    def test_store_record_inserts_item(self, tmp_path: Path) -> None:
        """store_record() should insert record into database."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "horizons.db"

        # Create config files
        followees_data = {
            "test": {
                "display_name": "Test",
                "sources": [{"name": "Manual", "url": "manual", "kind": "webpage"}],
            }
        }
        (config_dir / "followees.json").write_text(json.dumps(followees_data), encoding="utf-8")

        secrets_data = {
            "qq_email": "t@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "k",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")

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

            from horizons.db import initialize, upsert_sources
            from horizons.collector.webpage import WebPageCollector, WebPageRecord

            initialize()
            upsert_sources("test", [{"name": "Manual", "url": "manual", "kind": "webpage"}])

            collector = WebPageCollector()
            record = WebPageRecord(
                followee_id="test",
                source_url="manual",
                url="https://example.com/article",
                title="Test Article",
                content="Test content here.",
            )

            result = collector.store_record(record)

            assert result is True

            # Verify in database
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT title, content FROM items WHERE followee_id = 'test'")
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "Test Article"
            assert row[1] == "Test content here."

    def test_store_record_returns_false_for_missing_source(self, tmp_path: Path) -> None:
        """store_record() should return False when source doesn't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "horizons.db"

        followees_data = {"test": {"display_name": "Test", "sources": []}}
        (config_dir / "followees.json").write_text(json.dumps(followees_data), encoding="utf-8")

        secrets_data = {
            "qq_email": "t@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "k",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")

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
            from horizons.collector.webpage import WebPageCollector, WebPageRecord

            initialize()

            collector = WebPageCollector()
            record = WebPageRecord(
                followee_id="test",
                source_url="nonexistent",
                url="https://example.com/article",
                title="Test",
                content="Content",
            )

            result = collector.store_record(record)

            assert result is False
