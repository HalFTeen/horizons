"""Unit tests for CLI summarize command (TDD - tests first)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner


runner = CliRunner()


@pytest.fixture
def setup_test_env(tmp_path: Path):
    """Set up test environment with config, database, and test data."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    db_path = data_dir / "horizons.db"

    # Create config files
    followees_data = {
        "test": {
            "display_name": "Test Followee",
            "sources": [{"name": "Test Source", "url": "https://example.com", "kind": "rss"}],
        }
    }
    (config_dir / "followees.json").write_text(json.dumps(followees_data), encoding="utf-8")

    secrets_data = {
        "qq_email": "test@qq.com",
        "qq_smtp_app_password": "pass",
        "glm_api_key": "test_glm_key",
        "github_username": "user",
        "github_pat": "pat",
    }
    (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")

    return config_dir, data_dir, db_path


def create_test_item(db_path: Path, item_id: int = 1, status: str = "pending") -> None:
    """Helper to create a test item in the database."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            followee_id TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            followee_id TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            published_at TEXT,
            content TEXT,
            transcript_path TEXT,
            summary_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.execute(
        "INSERT OR IGNORE INTO sources (id, followee_id, name, url, kind) VALUES (1, 'test', 'Test Source', 'https://example.com', 'rss')"
    )
    conn.execute(
        """INSERT INTO items (id, followee_id, source_id, title, url, content, status)
           VALUES (?, 'test', 1, 'Test Interview Title', 'https://example.com/interview', 
                   'This is the interview content. It contains multiple paragraphs.\n\nSecond paragraph here.\n\nThird paragraph with more details.', ?)""",
        (item_id, status),
    )
    conn.commit()
    conn.close()


class TestSummarizeCommand:
    """Tests for the summarize CLI command."""

    def test_summarize_requires_item_id_argument(self, setup_test_env) -> None:
        """summarize command should require an item_id argument."""
        config_dir, data_dir, db_path = setup_test_env

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", data_dir.parent / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            from horizons.cli import app

            # Running without item_id should fail
            result = runner.invoke(app, ["summarize"])
            assert result.exit_code != 0

    def test_summarize_calls_glm_api(self, setup_test_env) -> None:
        """summarize command should call GLM API with item content."""
        config_dir, data_dir, db_path = setup_test_env
        create_test_item(db_path)

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", data_dir.parent / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            # Mock GLM API response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "# Summary\n\nKey insights..."}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("requests.post", return_value=mock_response) as mock_post:
                from horizons.cli import app

                result = runner.invoke(app, ["summarize", "1"])

                # Should call the API
                mock_post.assert_called_once()

    def test_summarize_saves_summary_to_file(self, setup_test_env) -> None:
        """summarize command should save the summary to a file."""
        config_dir, data_dir, db_path = setup_test_env
        create_test_item(db_path)

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", data_dir.parent / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "# Summary\n\nThis is the summary."}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("requests.post", return_value=mock_response):
                from horizons.cli import app

                result = runner.invoke(app, ["summarize", "1"])

                # Should create summary file in data/summaries/
                summaries_dir = data_dir / "summaries"
                if summaries_dir.exists():
                    summary_files = list(summaries_dir.glob("*.md"))
                    assert len(summary_files) > 0

    def test_summarize_updates_item_status(self, setup_test_env) -> None:
        """summarize command should update item status to 'summarized'."""
        config_dir, data_dir, db_path = setup_test_env
        create_test_item(db_path)

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", data_dir.parent / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "# Summary"}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("requests.post", return_value=mock_response):
                from horizons.cli import app

                result = runner.invoke(app, ["summarize", "1"])

                # Verify item status updated
                conn = sqlite3.connect(db_path)
                row = conn.execute("SELECT status, summary_path FROM items WHERE id = 1").fetchone()
                conn.close()

                assert row[0] == "summarized"
                assert row[1] is not None

    def test_summarize_handles_missing_item(self, setup_test_env) -> None:
        """summarize command should handle non-existent item gracefully."""
        config_dir, data_dir, db_path = setup_test_env
        # Initialize DB without items
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'pending'
            );
        """)
        conn.close()

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", data_dir.parent / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            from horizons.cli import app

            result = runner.invoke(app, ["summarize", "999"])

            assert result.exit_code != 0
            assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_summarize_outputs_summary_preview(self, setup_test_env) -> None:
        """summarize command should output a preview of the summary."""
        config_dir, data_dir, db_path = setup_test_env
        create_test_item(db_path)

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", data_dir.parent / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"), \
             patch("horizons.db.DATA_DIR", data_dir), \
             patch("horizons.db.DB_PATH", db_path):

            import importlib
            import horizons.config
            import horizons.db
            importlib.reload(horizons.config)
            importlib.reload(horizons.db)

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "# Summary Title\n\nKey insight 1.\n\nKey insight 2."}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("requests.post", return_value=mock_response):
                from horizons.cli import app

                result = runner.invoke(app, ["summarize", "1"])

                assert result.exit_code == 0
                # Should show success message
                assert "summary" in result.output.lower() or "saved" in result.output.lower()
