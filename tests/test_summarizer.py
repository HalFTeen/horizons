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

    def test_init_loads_api_key_from_config(self) -> None:
        """GLMSummarizer should load API key from config."""
        from horizons.summarizer.glm import GLMSummarizer

        summarizer = GLMSummarizer()

        assert summarizer.api_key == "test_glm_key"
        assert summarizer.model == "glm-4-plus"

    def test_init_accepts_custom_model(self) -> None:
        """GLMSummarizer should accept custom model name."""
        from horizons.summarizer.glm import GLMSummarizer

        summarizer = GLMSummarizer(model="glm-4-flash")

        assert summarizer.model == "glm-4-flash"

    def test_summarize_calls_api_correctly(self) -> None:
        """summarize() should call GLM API with correct parameters."""
        from horizons.summarizer.glm import GLMSummarizer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Test summary"}}]}

        with patch("requests.post", return_value=mock_response) as mock_post:
            summarizer = GLMSummarizer()
            result = summarizer.summarize(
                title="Test Title",
                url="https://example.com/article",
                content="This is test content.",
            )

            assert result == "Test summary"
            mock_post.assert_called_once()
            # requests.post(url, headers=..., json=...) uses positional arguments
            call_args = mock_post.call_args.args
            assert call_args[0] == "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            call_kwargs = mock_post.call_args.kwargs
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test_glm_key"
            assert "model" in call_kwargs["json"]
            assert call_kwargs["json"]["model"] == "glm-4-plus"
            assert len(call_kwargs["json"]["messages"]) == 2  # system + user

    def test_summarize_raises_on_invalid_response(self) -> None:
        """summarize() should raise RuntimeError on unexpected API response."""
        from horizons.summarizer.glm import GLMSummarizer

        summarizer = GLMSummarizer()

        # Mock invalid API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Failed to parse GLM response"):
                summarizer.summarize("Title", "URL", "Content")

    def test_summarize_handles_http_error(self) -> None:
        """summarize() should propagate HTTP errors."""
        import requests
        from horizons.summarizer.glm import GLMSummarizer

        summarizer = GLMSummarizer()

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                summarizer.summarize("Title", "URL", "Content")
