from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from ..config import config


class QQMailer:
    def __init__(self) -> None:
        secrets = config.secrets
        self.smtp_server = "smtp.qq.com"
        self.smtp_port = 465
        self.username = secrets.qq_email
        self.password = secrets.qq_smtp_app_password

    def send_markdown(self, subject: str, markdown_content: str, recipients: List[str]) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.username
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        markdown_part = MIMEText(markdown_content, "plain", "utf-8")
        html_part = MIMEText(self._markdown_to_html(markdown_content), "html", "utf-8")
        msg.attach(markdown_part)
        msg.attach(html_part)

        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.username, self.password)
            server.sendmail(self.username, recipients, msg.as_string())

    @staticmethod
    def _markdown_to_html(markdown_content: str) -> str:
        from markdown import markdown  # lazy import

        return markdown(markdown_content, extensions=["extra", "sane_lists"]) 
