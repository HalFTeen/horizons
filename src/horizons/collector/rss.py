from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

import feedparser
import requests

from ..db import get_source_id, insert_item, upsert_sources
from ..config import config, Followee

logger = logging.getLogger(__name__)

USER_AGENT = "HorizonsBot/0.1 (+https://github.com/HalFTeen/horizons)"


@dataclass
class RSSRecord:
    followee_id: str
    source_url: str
    title: str
    link: str
    published: str | None
    summary: str | None


class RSSCollector:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.followees = config.followees
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def sync_followees(self) -> None:
        for followee in self.followees.values():
            sources = [
                {
                    "name": source.name,
                    "url": source.url,
                    "kind": source.kind,
                }
                for source in followee.sources
                if source.kind == "rss"
            ]
            if sources:
                upsert_sources(followee.id, sources)

    def fetch(self, followee: Followee) -> List[RSSRecord]:
        records: List[RSSRecord] = []
        for source in followee.sources:
            if source.kind != "rss":
                continue
            logger.info("Fetching RSS for %s from %s", followee.id, source.url)
            try:
                response = self.session.get(source.url, timeout=15, verify=True)
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("HTTP error for %s: %s", source.url, exc)
                continue
            feed = feedparser.parse(response.content)
            if feed.bozo:
                logger.warning("Failed to parse feed %s: %s", source.url, feed.bozo_exception)
                continue
            for entry in feed.entries:
                records.append(
                    RSSRecord(
                        followee_id=followee.id,
                        source_url=source.url,
                        title=getattr(entry, "title", "(untitled)"),
                        link=getattr(entry, "link", ""),
                        published=getattr(entry, "published", None),
                        summary=getattr(entry, "summary", None),
                    )
                )
        return records

    def ingest(self) -> int:
        inserted = 0
        self.sync_followees()
        for followee in self.followees.values():
            records = self.fetch(followee)
            for record in records:
                try:
                    source_id = get_source_id(record.followee_id, record.source_url)
                except LookupError as exc:
                    logger.error("Source missing in DB: %s", exc)
                    continue
                payload = {
                    "followee_id": record.followee_id,
                    "source_id": source_id,
                    "title": record.title,
                    "url": record.link,
                    "published_at": record.published,
                    "content": record.summary or "",
                }
                if insert_item(payload):
                    inserted += 1
        return inserted
