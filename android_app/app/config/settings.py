"""Application configuration — Android-aware.

On Android the database and logs live in the app's user-data directory
(provided by ``platform``).  On desktop they live next to the project root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _user_data_dir() -> Path:
    """Return a writable data directory.

    On Android we rely on ``platform`` (Buildozer injects it).  Fallback to
    a local ``data/`` folder for desktop testing.
    """
    try:
        import platform  # type: ignore[import-not-found]
        return Path(platform.user_data_dir("vcm"))
    except Exception:
        return Path(__file__).resolve().parent.parent.parent / "data"


@dataclass(frozen=True)
class DatabaseSettings:
    path: Path = field(default_factory=lambda: _user_data_dir() / "contacts.db")

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app_name: str = "VCM"
    version: str = "1.0.0"
    log_max_lines: int = 5000
    batch_size: int = 50


settings = Settings()
