"""Shared pytest fixtures for Horizons tests."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Create a shared test base directory before any imports
# This ensures HORIZONS_BASE_DIR is set before horizons modules are imported
_TEST_BASE_DIR = Path(tempfile.gettempdir()) / "horizons_test_shared"
_TEST_BASE_DIR.mkdir(exist_ok=True, parents=True)
os.environ["HORIZONS_BASE_DIR"] = str(_TEST_BASE_DIR)


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Create a temporary config directory with test fixtures."""
    config_dir = _TEST_BASE_DIR / "config"
    config_dir.mkdir(exist_ok=True)

    # Create test followees.json
    followees = {
        "test_followee": {
            "display_name": "Test Followee",
            "sources": [
                {
                    "name": "Test RSS",
                    "url": "https://example.com/feed.xml",
                    "kind": "rss",
                }
            ],
        }
    }
    (config_dir / "followees.json").write_text(
        json.dumps(followees, indent=2), encoding="utf-8"
    )

    # Create test secrets.json
    secrets = {
        "qq_email": "test@qq.com",
        "qq_smtp_app_password": "test_password",
        "glm_api_key": "test_glm_key",
        "github_username": "test_user",
        "github_pat": "test_pat",
    }
    (config_dir / "secrets.json").write_text(
        json.dumps(secrets, indent=2), encoding="utf-8"
    )

    yield config_dir


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_db_path(temp_data_dir: Path) -> Path:
    """Return path to a temporary database."""
    return temp_data_dir / "test_horizons.db"


@pytest.fixture
def sample_rss_content() -> str:
    """Sample RSS feed content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test feed</description>
    <item>
      <title>Test Article 1</title>
      <link>https://example.com/article1</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <description>This is the first test article.</description>
    </item>
    <item>
      <title>Test Article 2</title>
      <link>https://example.com/article2</link>
      <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
      <description>This is the second test article.</description>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_webpage_html() -> str:
    """Sample webpage HTML content for testing."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Interview</title>
</head>
<body>
    <article>
        <h1>Interview with Test Person</h1>
        <p>This is the first paragraph of the interview content.</p>
        <p>This is the second paragraph with more details.</p>
        <p>This is the third paragraph concluding the interview.</p>
    </article>
</body>
</html>"""
