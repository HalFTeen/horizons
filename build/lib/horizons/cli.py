from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

import typer

from .config import get_config, ensure_dirs, DATA_DIR
from .db import DB_PATH, initialize, update_item
from .collector.rss import RSSCollector
from .collector.webpage import WebPageCollector
from .mailer.qq import QQMailer
from .summarizer.glm import GLMSummarizer

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


@app.command()
def summarize(
    item_id: int = typer.Argument(..., help="ID of the item to summarize"),
) -> None:
    """Summarize a stored item using GLM API and save the result."""
    ensure_dirs()
    initialize()

    import sqlite3
    from datetime import datetime

    # Fetch the item from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, title, url, content FROM items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()

    if not row:
        typer.echo(f"Error: Item with ID {item_id} not found")
        raise typer.Exit(code=1)

    title = row["title"]
    url = row["url"]
    content = row["content"] or ""

    if not content.strip():
        typer.echo(f"Error: Item {item_id} has no content to summarize")
        raise typer.Exit(code=1)

    typer.echo(f"Summarizing: {title}")

    # Call GLM API
    summarizer = GLMSummarizer()
    try:
        summary = summarizer.summarize(title=title, url=url, content=content)
    except Exception as exc:
        typer.echo(f"Error calling GLM API: {exc}")
        raise typer.Exit(code=1)

    # Save summary to file
    summaries_dir = DATA_DIR / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in title[:50])
    summary_filename = f"{timestamp}_{safe_title}.md"
    summary_path = summaries_dir / summary_filename

    summary_path.write_text(summary, encoding="utf-8")

    # Update item in database
    update_item(item_id, status="summarized", summary_path=str(summary_path))

    typer.echo(f"Summary saved to: {summary_path}")
    typer.echo("---")
    # Show first few lines as preview
    preview_lines = summary.split("\n")[:10]
    typer.echo("\n".join(preview_lines))
    if len(summary.split("\n")) > 10:
        typer.echo("...")


if __name__ == "__main__":
    app()
