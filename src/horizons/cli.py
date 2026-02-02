from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

import typer

from .config import config, ensure_dirs
from .db import DB_PATH, initialize
from .collector.rss import RSSCollector
from .collector.webpage import WebPageCollector
from .mailer.qq import QQMailer

app = typer.Typer(help="Horizons command line interface")

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
log_file = Path.cwd() / "logs" / "horizons.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[
    logging.FileHandler(log_file, encoding="utf-8"),
    logging.StreamHandler(),
])


@app.command()
def init_db() -> None:
    """Initialize the SQLite database."""
    ensure_dirs()
    initialize()
    typer.echo("Database initialized")


@app.command()
def ingest_rss() -> None:
    """Fetch RSS sources for all followees and store new items."""
    ensure_dirs()
    initialize()
    collector = RSSCollector()
    inserted = collector.ingest()
    typer.echo(f"Inserted {inserted} new items from RSS feeds")


@app.command()
def ingest_url(
    url: str = typer.Argument(..., help="The URL of the interview/article to ingest"),
    followee: str = typer.Option("minimax", "--followee", help="Followee identifier"),
    source_name: str = typer.Option("Manual", "--source-name", help="Friendly source name"),
    source_url: str = typer.Option("manual", "--source-url", help="Source identifier URL"),
) -> None:
    """Ingest a single webpage interview/article."""
    ensure_dirs()
    initialize()
    collector = WebPageCollector()
    collector.sync_followees()
    record = collector.fetch_single(followee, source_url or url, url)
    if not record:
        typer.echo("Failed to fetch content")
        raise typer.Exit(code=1)
    stored = collector.store_record(record)
    if stored:
        typer.echo(f"Stored item: {record.title}")
    else:
        typer.echo("Item already exists or failed to store")


@app.command()
def email_snippet(
    recipient: str = typer.Option(..., "--to", prompt=True, help="Recipient email address"),
    paragraphs: int = typer.Option(3, "--paragraphs", min=1, help="Number of paragraphs to include"),
) -> None:
    """Send the first N paragraphs of the latest item via email."""
    ensure_dirs()
    initialize()

    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT title, url, content, created_at FROM items ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if not row:
        typer.echo("No items found in database")
        raise typer.Exit(code=1)

    content = row["content"] or ""
    para_list = [p.strip() for p in content.split("\n\n") if p.strip()]
    snippet = "\n\n".join(para_list[:paragraphs])

    markdown_body = dedent(
        f"""
        # 访谈片段预览

        - 标题：{row['title']}
        - 原文链接：{row['url']}

        ---

        {snippet}
        """
    ).strip()

    subject = f"[Horizons] 访谈片段预览 - {row['title']}"
    mailer = QQMailer()
    mailer.send_markdown(subject=subject, markdown_content=markdown_body, recipients=[recipient])
    typer.echo(f"Snippet email sent to {recipient}")


if __name__ == "__main__":
    app()
