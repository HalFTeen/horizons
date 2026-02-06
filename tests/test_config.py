"""Unit tests for horizons.config module."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with test fixtures."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

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
        json.dumps(followees, indent=2, ensure_ascii=False), encoding="utf-8"
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
        json.dumps(secrets, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return config_dir


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


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
      <description>This is first test article.</description>
    </item>
    <item>
      <title>Test Article 2</title>
      <link>https://example.com/article2</link>
      <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
      <description>This is second test article.</description>
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
        <p>This is first paragraph of interview content.</p>
        <p>This is second paragraph with more details.</p>
        <p>This is third paragraph concluding the interview.</p>
    </article>
</body>
</html>"""


class TestFollowSource:
    """Tests for FollowSource dataclass."""

    def test_default_kind_is_rss(self) -> None:
        """FollowSource should default to 'rss' kind."""
        from horizons.config import FollowSource

        source = FollowSource(name="Test", url="https://example.com")
        assert source.kind == "rss"
        assert source.notes is None

    def test_all_fields(self) -> None:
        """FollowSource should accept all fields."""
        from horizons.config import FollowSource

        source = FollowSource(
            name="Test Feed",
            url="https://example.com/feed",
            kind="youtube",
            notes="Test note",
        )
        assert source.name == "Test Feed"
        assert source.url == "https://example.com/feed"
        assert source.kind == "youtube"
        assert source.notes == "Test note"


class TestFollowee:
    """Tests for Followee dataclass."""

    def test_empty_sources_by_default(self) -> None:
        """Followee should have empty sources list by default."""
        from horizons.config import Followee

        followee = Followee(id="test", display_name="Test")
        assert followee.sources == []

    def test_with_sources(self) -> None:
        """Followee should accept sources list."""
        from horizons.config import Followee, FollowSource

        sources = [FollowSource(name="Feed", url="https://example.com", kind="rss")]
        followee = Followee(id="test", display_name="Test", sources=sources)
        assert len(followee.sources) == 1
        assert followee.sources[0].name == "Feed"


class TestSecrets:
    """Tests for Secrets dataclass."""

    def test_all_fields_required(self) -> None:
        """Secrets should require all fields."""
        from horizons.config import Secrets

        secrets = Secrets(
            qq_email="test@qq.com",
            qq_smtp_app_password="pass",
            glm_api_key="key",
            github_username="user",
            github_pat="pat",
        )
        assert secrets.qq_email == "test@qq.com"
        assert secrets.glm_api_key == "key"


class TestSettings:
    """Tests for Settings dataclass."""

    def test_defaults(self) -> None:
        """Settings should have sensible defaults."""
        from horizons.config import Settings

        settings = Settings()
        assert settings.timezone == "Asia/Shanghai"
        assert settings.schedule_cron == "0 6 */2 * *"
        assert settings.history_days == 7


class TestConfigLoading:
    """Tests for Config class file loading behavior."""

    def test_load_followees_from_json(self, temp_config_dir: Path) -> None:
        """Config should load followees from JSON file."""
        from unittest.mock import patch
        import importlib

        # Patch all module-level paths with absolute Path objects
        with patch("horizons.config.BASE_DIR", temp_config_dir), \
             patch("horizons.config.CONFIG_DIR", temp_config_dir / "config"), \
             patch("horizons.config.DATA_DIR", temp_config_dir / "data"), \
             patch("horizons.config.LOG_DIR", temp_config_dir / "logs"), \
             patch("horizons.config.SECRETS_FILE", temp_config_dir / "config" / "secrets.json"), \
             patch("horizons.config.FOLLOWEES_FILE", temp_config_dir / "config" / "followees.json"):

            # Force module reload to get fresh module state
            importlib.import_module('horizons.config')
            
            # Need to import Config from freshly reloaded module
            from horizons.config import Config

            cfg = Config()
            assert "test_followee" in cfg.followees
            assert cfg.followees["test_followee"].display_name == "Test Followee"
            assert len(cfg.followees["test_followee"].sources) == 1

    def test_missing_secrets_raises_error(self, temp_config_dir: Path) -> None:
        """Config should raise RuntimeError when secrets.json is missing values."""
        from horizons.config import Config, ensure_dirs

        # Create followees.json
        followees = {"test": {"display_name": "Test", "sources": []}}
        (temp_config_dir / "followees.json").write_text(
            json.dumps(followees), encoding="utf-8"
        )

        # Create secrets.json with MISSING values (empty password to trigger error)
        secrets_data = {
            "qq_email": "test@qq.com",
            "qq_smtp_app_password": "",  # Empty! Should trigger error
            "glm_api_key": "test_glm_key",
            "github_username": "test_user",
            "github_pat": "test_pat",
        }
        (temp_config_dir / "secrets.json").write_text(
            json.dumps(secrets_data), encoding="utf-8"
        )

        ensure_dirs()

        with pytest.raises(RuntimeError, match="secrets.json missing value for qq_smtp_app_password"):
            Config()

    def test_creates_default_followees_if_missing(self, temp_config_dir: Path) -> None:
        """Config should create default followees.json if it doesn't exist."""
        from unittest.mock import patch

        # Patch all module-level paths
        with patch("horizons.config.BASE_DIR", temp_config_dir), \
             patch("horizons.config.CONFIG_DIR", temp_config_dir / "config"), \
             patch("horizons.config.DATA_DIR", temp_config_dir / "data"), \
             patch("horizons.config.LOG_DIR", temp_config_dir / "logs"), \
             patch("horizons.config.SECRETS_FILE", temp_config_dir / "config" / "secrets.json"), \
             patch("horizons.config.FOLLOWEES_FILE", temp_config_dir / "config" / "followees.json"):
            
            from horizons.config import Config, FOLLOWEES_FILE, ensure_dirs

            # Force module reload after patching
            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            ensure_dirs()

            # Remove both files
            for f in [FOLLOWEES_FILE, temp_config_dir / "config" / "secrets.json"]:
                file_path = f if isinstance(f, Path) else temp_config_dir / f
                if file_path.exists():
                    file_path.unlink()

            # Create secrets.json with valid data to avoid _load_secrets error
            secrets_data = {
                "qq_email": "s@q.com",
                "qq_smtp_app_password": "p",
                "glm_api_key": "k",
                "github_username": "u",
                "github_pat": "p",
            }
            (temp_config_dir / "secrets.json").write_text(
                json.dumps(secrets_data), encoding="utf-8"
            )

            assert not FOLLOWEES_FILE.exists()

            cfg = Config()

            # Default followees.json should be created
            assert FOLLOWEES_FILE.exists()
            assert "minimax" in cfg.followees

    def test_creates_default_followees_if_missing(self, temp_config_dir: Path) -> None:
        """Config should create default followees.json if it doesn't exist."""
        from unittest.mock import patch

        # Patch all module-level paths
        with patch("horizons.config.BASE_DIR", temp_config_dir), \
             patch("horizons.config.CONFIG_DIR", temp_config_dir / "config"), \
             patch("horizons.config.DATA_DIR", temp_config_dir / "data"), \
             patch("horizons.config.LOG_DIR", temp_config_dir / "logs"), \
             patch("horizons.config.SECRETS_FILE", temp_config_dir / "config" / "secrets.json"), \
             patch("horizons.config.FOLLOWEES_FILE", temp_config_dir / "config" / "followees.json"):

            # Force module reload after patching
            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            from horizons.config import Config, FOLLOWEES_FILE

            ensure_dirs()

            # Remove both files to ensure clean state
            for f in [FOLLOWEES_FILE, temp_config_dir / "config" / "secrets.json"]:
                file_path = f if isinstance(f, Path) else temp_config_dir / f
                if file_path.exists():
                    file_path.unlink()

            # Create secrets.json with valid data to avoid _load_secrets error
            secrets_data = {
                "qq_email": "s@q.com",
                "qq_smtp_app_password": "p",
                "glm_api_key": "k",
                "github_username": "u",
                "github_pat": "p",
            }
            (temp_config_dir / "secrets.json").write_text(
                json.dumps(secrets_data), encoding="utf-8"
            )

            assert not FOLLOWEES_FILE.exists()

            cfg = Config()

            # Default followees.json should be created
            assert FOLLOWEES_FILE.exists()
            assert "minimax" in cfg.followees


class TestEnsureDirs:
    """Tests for ensure_dirs function."""

    def test_creates_directories(self, tmp_path: Path) -> None:
        """ensure_dirs should create config, data, and logs directories."""
        from horizons.config import ensure_dirs

        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        log_dir = tmp_path / "logs"

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", log_dir):

            ensure_dirs()

            assert config_dir.exists()
            assert data_dir.exists()
            assert log_dir.exists()
