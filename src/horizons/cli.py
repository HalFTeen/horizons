from __future__ import annotations

import logging
from pathlib import Path

import typer

from .config import config, ensure_dirs
from .db import initialize
from .collector.rss import RSSCollector
from .collector.webpage import WebPageCollector

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


if __name__ == "__main__":
    app()
