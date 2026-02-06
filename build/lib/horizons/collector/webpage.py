from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests
import json

import trafilatura
from bs4 import BeautifulSoup

from ..config import config
from ..db import get_source_id, insert_item, upsert_sources

logger = logging.getLogger(__name__)

USER_AGENT = "HorizonsBot/0.1 (+https://github.com/HalFTeen/horizons)"


@dataclass
class WebPageRecord:
    followee_id: str
    source_url: str
    url: str
    title: str
    content: str


class WebPageCollector:
    def __init__(self, session: Optional[requests.Session] = None) -> None:
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
                if source.kind in {"webpage", "article"}
            ]
            if sources:
                upsert_sources(followee.id, sources)

    def fetch_single(self, followee_id: str, source_url: str, url: str) -> Optional[WebPageRecord]:
        logger.info("Fetching webpage for followee=%s url=%s", followee_id, url)
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None
        downloaded = trafilatura.extract(response.text, output_format="json")
        if not downloaded:
            logger.warning("No content extracted for %s", url)
            return None
        try:
            data = json.loads(downloaded)
        except json.JSONDecodeError:
            logger.warning("Failed to parse trafilatura JSON for %s", url)
            return None
        title = data.get("title")
        if not title:
            soup = BeautifulSoup(response.text, "lxml")
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else "(untitled)"
        content = data.get("text") or ""
        return WebPageRecord(
            followee_id=followee_id,
            source_url=source_url,
            url=url,
            title=title.strip(),
            content=content.strip(),
        )

    def store_record(self, record: WebPageRecord) -> bool:
        try:
            source_id = get_source_id(record.followee_id, record.source_url)
        except LookupError as exc:
            logger.error("Source missing: %s", exc)
            return False
        payload = {
            "followee_id": record.followee_id,
            "source_id": source_id,
            "title": record.title,
            "url": record.url,
            "published_at": None,
            "content": record.content,
        }
        return insert_item(payload) is not None
