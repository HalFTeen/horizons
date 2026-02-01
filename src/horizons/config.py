from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
SECRETS_FILE = CONFIG_DIR / "secrets.json"
FOLLOWEES_FILE = CONFIG_DIR / "followees.json"

load_dotenv(CONFIG_DIR / ".env")


def ensure_dirs() -> None:
    for path in (CONFIG_DIR, DATA_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


@dataclass
class FollowSource:
    name: str
    url: str
    kind: str = "rss"  # rss | webpage | youtube | bilibili | x
    notes: Optional[str] = None


@dataclass
class Followee:
    id: str
    display_name: str
    sources: List[FollowSource] = field(default_factory=list)


@dataclass
class Secrets:
    qq_email: str
    qq_smtp_app_password: str
    glm_api_key: str
    github_username: str
    github_pat: str


@dataclass
class Settings:
    timezone: str = "Asia/Shanghai"
    schedule_cron: str = "0 6 */2 * *"  # every two days at 06:00
    history_days: int = 7


class Config:
    def __init__(self) -> None:
        ensure_dirs()
        self._followees = self._load_followees()
        self._secrets = self._load_secrets()
        self.settings = Settings()

    @staticmethod
    def _load_followees() -> Dict[str, Followee]:
        if not FOLLOWEES_FILE.exists():
            default = {
                "minimax": {
                    "display_name": "MiniMax",
                    "sources": [
                        {
                            "name": "MiniMax Official Blog",
                            "url": "https://www.minimax.space/feed",
                            "kind": "rss",
                        }
                    ],
                }
            }
            FOLLOWEES_FILE.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
        data = json.loads(FOLLOWEES_FILE.read_text(encoding="utf-8"))
        followees: Dict[str, Followee] = {}
        for followee_id, payload in data.items():
            sources = [FollowSource(**src) for src in payload.get("sources", [])]
            followees[followee_id] = Followee(
                id=followee_id,
                display_name=payload.get("display_name", followee_id),
                sources=sources,
            )
        return followees

    @staticmethod
    def _load_secrets() -> Secrets:
        if not SECRETS_FILE.exists():
            empty = {
                "qq_email": "example@qq.com",
                "qq_smtp_app_password": "",
                "glm_api_key": "",
                "github_username": "",
                "github_pat": "",
            }
            SECRETS_FILE.write_text(json.dumps(empty, indent=2, ensure_ascii=False), encoding="utf-8")
            raise RuntimeError("secrets.json missing required credentials; fill in config/secrets.json")
        payload = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
        required = ["qq_email", "qq_smtp_app_password", "glm_api_key", "github_username", "github_pat"]
        for key in required:
            if not payload.get(key):
                raise RuntimeError(f"secrets.json missing value for {key}")
        return Secrets(**payload)

    @property
    def followees(self) -> Dict[str, Followee]:
        return self._followees

    @property
    def secrets(self) -> Secrets:
        return self._secrets


config = Config()
