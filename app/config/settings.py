"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve project root (two levels up from this file)
# ---------------------------------------------------------------------------
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# Load .env from project root if it exists
load_dotenv(_PROJECT_ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class DatabaseSettings:
    path: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "data" / "contacts.db"
    )

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app_name: str = "Virtual Contact Manager"
    version: str = "1.0.0"
    log_max_lines: int = 5000
    batch_size: int = 50  # contacts per batch during create/delete


settings = Settings()
