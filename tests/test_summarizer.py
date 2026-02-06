"""Unit tests for horizons.summarizer.glm module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBuildPrompt:
    """Tests for build_prompt function."""

    def test_includes_all_fields(self) -> None:
        """build_prompt() should include title, url, and content in prompt."""
        from horizons.summarizer.glm import build_prompt

        prompt = build_prompt(
            title="Test Interview",
            url="https://example.com/interview",
            content="Interview content here.",
        )

        assert "Test Interview" in prompt
        assert "https://example.com/interview" in prompt
        assert "Interview content here." in prompt

    def test_includes_task_instructions(self) -> None:
        """build_prompt() should include summarization task instructions."""
        from horizons.summarizer.glm import build_prompt

        prompt = build_prompt(title="T", url="U", content="C")

        # Should contain key instruction elements
        assert "核心观点" in prompt or "关键洞察" in prompt
        assert "Markdown" in prompt


class TestGLMSummarizer:
    """Tests for GLMSummarizer class."""

    def test_init_loads_api_key_from_config(self, tmp_path: Path) -> None:
        """GLMSummarizer should load API key from config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "test_glm_api_key_123",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")
        (config_dir / "followees.json").write_text("{}", encoding="utf-8")

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            from horizons.summarizer.glm import GLMSummarizer

            summarizer = GLMSummarizer()

            assert summarizer.api_key == "test_glm_api_key_123"
            assert summarizer.model == "glm-4-plus"

    def test_init_accepts_custom_model(self, tmp_path: Path) -> None:
        """GLMSummarizer should accept custom model name."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "key",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")
        (config_dir / "followees.json").write_text("{}", encoding="utf-8")

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            from horizons.summarizer.glm import GLMSummarizer

            summarizer = GLMSummarizer(model="glm-4-flash")

            assert summarizer.model == "glm-4-flash"

    def test_summarize_calls_api_correctly(self, tmp_path: Path) -> None:
        """summarize() should call GLM API with correct payload."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "test_api_key",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")
        (config_dir / "followees.json").write_text("{}", encoding="utf-8")

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            from horizons.summarizer.glm import GLMSummarizer

            summarizer = GLMSummarizer()

            # Mock the API response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "# Summary\n\nThis is the summary."
                        }
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("requests.post", return_value=mock_response) as mock_post:
                result = summarizer.summarize(
                    title="Test Interview",
                    url="https://example.com",
                    content="Interview content here.",
                )

            # Verify API was called correctly
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]

            assert call_kwargs["headers"]["Authorization"] == "Bearer test_api_key"
            assert call_kwargs["json"]["model"] == "glm-4-plus"
            assert len(call_kwargs["json"]["messages"]) == 2  # system + user

            # Verify result
            assert result == "# Summary\n\nThis is the summary."

    def test_summarize_raises_on_invalid_response(self, tmp_path: Path) -> None:
        """summarize() should raise RuntimeError on unexpected API response."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "key",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")
        (config_dir / "followees.json").write_text("{}", encoding="utf-8")

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            from horizons.summarizer.glm import GLMSummarizer

            summarizer = GLMSummarizer()

            # Mock invalid API response
            mock_response = MagicMock()
            mock_response.json.return_value = {"error": "Invalid request"}
            mock_response.raise_for_status = MagicMock()

            with patch("requests.post", return_value=mock_response):
                with pytest.raises(RuntimeError, match="Failed to parse GLM response"):
                    summarizer.summarize("Title", "URL", "Content")

    def test_summarize_handles_http_error(self, tmp_path: Path) -> None:
        """summarize() should propagate HTTP errors."""
        import requests

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "key",
            "github_username": "u",
            "github_pat": "p",
        }
        (config_dir / "secrets.json").write_text(json.dumps(secrets_data), encoding="utf-8")
        (config_dir / "followees.json").write_text("{}", encoding="utf-8")

        with patch("horizons.config.CONFIG_DIR", config_dir), \
             patch("horizons.config.DATA_DIR", tmp_path / "data"), \
             patch("horizons.config.LOG_DIR", tmp_path / "logs"), \
             patch("horizons.config.FOLLOWEES_FILE", config_dir / "followees.json"), \
             patch("horizons.config.SECRETS_FILE", config_dir / "secrets.json"):

            import importlib
            import horizons.config
            importlib.reload(horizons.config)

            from horizons.summarizer.glm import GLMSummarizer

            summarizer = GLMSummarizer()

            # Mock HTTP error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

            with patch("requests.post", return_value=mock_response):
                with pytest.raises(requests.HTTPError):
                    summarizer.summarize("Title", "URL", "Content")
