"""Unit tests for horizons.config module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# We need to patch the module-level constants before importing Config
# to avoid side effects from the global config instance


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

        sources = [FollowSource(name="Feed", url="https://example.com")]
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

    def test_load_followees_from_json(self, tmp_path: Path) -> None:
        """Config should load followees from JSON file."""
        # Create temp config directory with followees.json
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        followees_data = {
            "test_followee": {
                "display_name": "Test Followee",
                "sources": [
                    {"name": "Test RSS", "url": "https://example.com/feed", "kind": "rss"}
                ],
            }
        }
        (config_dir / "followees.json").write_text(
            json.dumps(followees_data), encoding="utf-8"
        )

        # Create secrets.json
        secrets_data = {
            "qq_email": "test@qq.com",
            "qq_smtp_app_password": "pass",
            "glm_api_key": "key",
            "github_username": "user",
            "github_pat": "pat",
        }
        (config_dir / "secrets.json").write_text(
            json.dumps(secrets_data), encoding="utf-8"
        )

        # Patch the module constants
        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            from horizons.config import Config

            cfg = Config()
            assert "test_followee" in cfg.followees
            assert cfg.followees["test_followee"].display_name == "Test Followee"
            assert len(cfg.followees["test_followee"].sources) == 1

    def test_missing_secrets_raises_error(self, tmp_path: Path) -> None:
        """Config should raise RuntimeError when secrets.json is missing values."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create followees.json
        (config_dir / "followees.json").write_text("{}", encoding="utf-8")

        # Create secrets.json with empty values
        secrets_data = {
            "qq_email": "test@qq.com",
            "qq_smtp_app_password": "",  # Empty!
            "glm_api_key": "key",
            "github_username": "user",
            "github_pat": "pat",
        }
        (config_dir / "secrets.json").write_text(
            json.dumps(secrets_data), encoding="utf-8"
        )

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            from horizons.config import Config

            with pytest.raises(RuntimeError, match="missing value for qq_smtp_app_password"):
                Config()

    def test_creates_default_followees_if_missing(self, tmp_path: Path) -> None:
        """Config should create default followees.json if it doesn't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create secrets.json only
        secrets_data = {
            "qq_email": "test@qq.com",
            "qq_smtp_app_password": "pass",
            "glm_api_key": "key",
            "github_username": "user",
            "github_pat": "pat",
        }
        (config_dir / "secrets.json").write_text(
            json.dumps(secrets_data), encoding="utf-8"
        )

        followees_file = config_dir / "followees.json"

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", followees_file), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            from horizons.config import Config

            cfg = Config()

            # Default followees.json should be created
            assert followees_file.exists()
            # Should contain default minimax followee
            assert "minimax" in cfg.followees


class TestEnsureDirs:
    """Tests for ensure_dirs function."""

    def test_creates_directories(self, tmp_path: Path) -> None:
        """ensure_dirs should create config, data, and logs directories."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        log_dir = tmp_path / "logs"

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", data_dir), \
             patch("horizons.config.LOG_DIR", log_dir):

            from horizons.config import ensure_dirs

            ensure_dirs()

            assert config_dir.exists()
            assert data_dir.exists()
            assert log_dir.exists()
