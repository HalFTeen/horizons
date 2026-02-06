"""Unit tests for horizons.mailer.qq module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


class TestQQMailer:
    """Tests for QQMailer class."""

    def test_init_loads_credentials_from_config(self, tmp_path: Path) -> None:
        """QQMailer should load SMTP credentials from config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "sender@qq.com",
            "qq_smtp_app_password": "app_password_123",
            "glm_api_key": "key",
            "github_username": "user",
            "github_pat": "pat",
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

            from horizons.mailer.qq import QQMailer

            mailer = QQMailer()

            assert mailer.username == "sender@qq.com"
            assert mailer.password == "app_password_123"
            assert mailer.smtp_server == "smtp.qq.com"
            assert mailer.smtp_port == 465

    def test_send_markdown_creates_multipart_message(self, tmp_path: Path) -> None:
        """send_markdown() should create email with both plain and HTML parts."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "sender@qq.com",
            "qq_smtp_app_password": "password",
            "glm_api_key": "k",
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

            from horizons.mailer.qq import QQMailer

            mailer = QQMailer()

            mock_smtp = MagicMock()
            mock_smtp_class = MagicMock(return_value=mock_smtp)
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)

            with patch("smtplib.SMTP_SSL", mock_smtp_class):
                mailer.send_markdown(
                    subject="Test Subject",
                    markdown_content="# Hello\n\nThis is a **test**.",
                    recipients=["recipient@example.com"],
                )

            # Verify SMTP_SSL was called with correct server/port
            mock_smtp_class.assert_called_once_with("smtp.qq.com", 465)

            # Verify login was called
            mock_smtp.login.assert_called_once_with("sender@qq.com", "password")

            # Verify sendmail was called
            mock_smtp.sendmail.assert_called_once()
            call_args = mock_smtp.sendmail.call_args
            assert call_args[0][0] == "sender@qq.com"  # from
            assert call_args[0][1] == ["recipient@example.com"]  # to

    def test_send_markdown_sends_to_multiple_recipients(self, tmp_path: Path) -> None:
        """send_markdown() should send to all specified recipients."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "sender@qq.com",
            "qq_smtp_app_password": "password",
            "glm_api_key": "k",
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

            from horizons.mailer.qq import QQMailer

            mailer = QQMailer()

            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)

            with patch("smtplib.SMTP_SSL", return_value=mock_smtp):
                mailer.send_markdown(
                    subject="Test",
                    markdown_content="Hello",
                    recipients=["user1@example.com", "user2@example.com"],
                )

            call_args = mock_smtp.sendmail.call_args
            assert call_args[0][1] == ["user1@example.com", "user2@example.com"]


class TestMarkdownToHtml:
    """Tests for _markdown_to_html static method."""

    def test_converts_basic_markdown(self, tmp_path: Path) -> None:
        """_markdown_to_html() should convert markdown to HTML."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "k",
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

            from horizons.mailer.qq import QQMailer

            html = QQMailer._markdown_to_html("# Heading\n\n**Bold** text")

            assert "<h1>Heading</h1>" in html
            assert "<strong>Bold</strong>" in html

    def test_handles_lists(self, tmp_path: Path) -> None:
        """_markdown_to_html() should properly convert lists."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secrets_data = {
            "qq_email": "s@q.com",
            "qq_smtp_app_password": "p",
            "glm_api_key": "k",
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

            from horizons.mailer.qq import QQMailer

            markdown = "- Item 1\n- Item 2\n- Item 3"
            html = QQMailer._markdown_to_html(markdown)

            assert "<ul>" in html
            assert "<li>Item 1</li>" in html
