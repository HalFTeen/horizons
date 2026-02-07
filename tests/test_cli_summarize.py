"""Unit tests for horizons.summarize.glm module."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

runner = CliRunner()


def get_shared_test_paths() -> tuple[Path, Path]:
    """Get paths to shared test config and data directories."""
    import os as _os
    from pathlib import Path as _Path
    test_base = _Path(_os.environ.get("HORIZONS_BASE_DIR", _Path(__file__).resolve().parent.parent))
    return test_base / "config", test_base / "data"


def create_test_item(item_id: int = 1, status: str = "pending") -> None:
    """Helper to create a test item in shared database."""
    config_dir, data_dir = get_shared_test_paths()
    db_path = data_dir / "horizons.db"

    # Initialize database schema if needed
    from horizons.db import initialize
    initialize()

    conn = sqlite3.connect(db_path)
    # First insert source, then item
    conn.execute(
        "INSERT OR REPLACE INTO sources (id, followee_id, name, url, kind) VALUES (1, 'test', 'Test Source', 'https://example.com', 'rss')"
    )
    conn.execute(
        """INSERT OR REPLACE INTO items (id, followee_id, source_id, title, url, content, status)
               VALUES (?, 'test', 1, 'Test Interview Title', 'https://example.com/interview',
                      'This is the interview content. It has multiple paragraphs.\n\nSecond paragraph here.\n\nThird paragraph with more details.', ?)""",
        (item_id, status),
    )
    conn.commit()
    conn.close()


class TestSummarizeCommand:
    """Tests for summarize CLI command."""

    def test_summarize_requires_item_id_argument(self) -> None:
        """summarize command should require an item_id argument."""
        from horizons.cli import app

        # Running without item_id should fail
        result = runner.invoke(app, ["summarize"])
        assert result.exit_code != 0

    def test_summarize_calls_glm_api(self) -> None:
        """summarize command should call GLM API with item content."""
        create_test_item()

        # Mock GLM API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "# Summary\n\nKey insights..."}}]
        }
        mock_response.raise_for_status = MagicMock()

        from unittest.mock import patch
        with patch("requests.post", return_value=mock_response) as mock_post:
            from horizons.cli import app

            result = runner.invoke(app, ["summarize", "1"])

            # Should call API
            mock_post.assert_called_once()

    def test_summarize_saves_summary_to_file(self) -> None:
        """summarize command should save summary to a file."""
        create_test_item()

        config_dir, data_dir = get_shared_test_paths()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "# Summary\n\nTest content..."}}]
        }
        mock_response.raise_for_status = MagicMock()

        from unittest.mock import patch
        with patch("requests.post", return_value=mock_response):
            from horizons.cli import app

            result = runner.invoke(app, ["summarize", "1"])

            # Should create summary file
            summary_files = list((data_dir / "summaries").glob("*.md"))
            assert len(summary_files) > 0

    def test_summarize_updates_item_status(self) -> None:
        """summarize command should update item status to 'summarized'."""
        create_test_item(item_id=2)

        config_dir, data_dir = get_shared_test_paths()
        db_path = data_dir / "horizons.db"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "# Summary"}}]
        }
        mock_response.raise_for_status = MagicMock()

        from unittest.mock import patch
        with patch("requests.post", return_value=mock_response):
            from horizons.cli import app

            result = runner.invoke(app, ["summarize", "2"])

            # Verify item status updated
            conn = sqlite3.connect(db_path)
            row = conn.execute("SELECT status, summary_path FROM items WHERE id = 2").fetchone()
            conn.close()

            assert row[0] == "summarized", f"Expected 'summarized', got '{row[0]}'"
            assert row[1] is not None

    def test_summarize_handles_missing_item(self) -> None:
        """summarize command should handle non-existent item gracefully."""
        from horizons.cli import app

        result = runner.invoke(app, ["summarize", "999"])
        assert "not found" in result.stdout.lower()
        assert result.exit_code != 0

    def test_summarize_outputs_summary_preview(self) -> None:
        """summarize command should output summary preview."""
        create_test_item()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nLine 10\nLine 11"}}]
        }
        mock_response.raise_for_status = MagicMock()

        from unittest.mock import patch
        with patch("requests.post", return_value=mock_response):
            from horizons.cli import app

            result = runner.invoke(app, ["summarize", "1"])

            # Should show preview (first 10 lines)
            assert "Line 10" in result.stdout
            assert "..." in result.stdout
            assert result.exit_code == 0


class TestBuildPrompt:
    """Tests for build_prompt static function."""

    def test_includes_all_fields(self) -> None:
        """Prompt should include title, URL and content."""
        from horizons.summarizer.glm import build_prompt

        prompt = build_prompt(
            title="Test Title",
            url="https://example.com/article",
            content="Test content here."
        )

        assert "Test Title" in prompt
        assert "https://example.com/article" in prompt
        assert "Test content here." in prompt

    def test_includes_task_instructions(self) -> None:
        """Prompt should include task instructions."""
        from horizons.summarizer.glm import build_prompt

        prompt = build_prompt(
            title="Title",
            url="URL",
            content="Content"
        )

        assert "总结" in prompt or "summarize" in prompt.lower()
