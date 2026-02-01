from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

from .config import DATA_DIR

DB_PATH = DATA_DIR / "horizons.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    followee_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    kind TEXT NOT NULL,
    UNIQUE(followee_id, url)
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    followee_id TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    content TEXT,
    transcript_path TEXT,
    summary_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(followee_id, title)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    message TEXT
);
"""


def initialize() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def upsert_sources(followee_id: str, sources: Iterable[dict]) -> None:
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO sources (followee_id, name, url, kind)
            VALUES (:followee_id, :name, :url, :kind)
            """,
            [dict(followee_id=followee_id, **src) for src in sources],
        )
        conn.commit()


def insert_item(record: dict) -> Optional[int]:
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO items (followee_id, source_id, title, url, published_at, content)
                VALUES (:followee_id, :source_id, :title, :url, :published_at, :content)
                """,
                record,
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_item(item_id: int, **fields: str) -> None:
    set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
    values = list(fields.values()) + [item_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE items SET {set_clause} WHERE id = ?", values)
        conn.commit()


def fetch_pending_items() -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT items.*, sources.name AS source_name, sources.kind AS source_kind
            FROM items
            JOIN sources ON items.source_id = sources.id
            WHERE items.status = 'pending'
            ORDER BY items.published_at DESC NULLS LAST, items.created_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]
