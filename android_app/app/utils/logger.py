"""Lightweight logger — Qt-free version for Kivy/Android."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


class LogLevel(Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


LOG_COLORS = {
    LogLevel.INFO: "#3b82f6",
    LogLevel.SUCCESS: "#22c55e",
    LogLevel.WARNING: "#eab308",
    LogLevel.ERROR: "#ef4444",
}


class LogEntry:
    __slots__ = ("timestamp", "level", "message")

    def __init__(self, level: LogLevel, message: str) -> None:
        self.timestamp: str = datetime.now().strftime("%H:%M:%S")
        self.level: LogLevel = level
        self.message: str = message

    def __str__(self) -> str:
        return f"[{self.timestamp}] [{self.level.value}] {self.message}"


class Logger:
    """Application-wide logger with callback-based observer pattern."""

    _instance: Optional["Logger"] = None

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []
        self._callbacks: list[Callable[[str, str], None]] = []
        self._file_path: Optional[Path] = None
        self._max_lines: int = 5000
        self._stdlib = logging.getLogger("app")
        self._stdlib.setLevel(logging.DEBUG)

    @classmethod
    def instance(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- observer pattern ------------------------------------------------
    def add_callback(self, cb: Callable[[str, str], None]) -> None:
        """Register a callback ``(level_name, formatted_message) -> None``."""
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable) -> None:
        self._callbacks = [c for c in self._callbacks if c is not cb]

    # -- configuration ---------------------------------------------------
    def set_file(self, path: Path, max_lines: int = 5000) -> None:
        self._file_path = path
        self._max_lines = max_lines
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        self._stdlib.addHandler(handler)

    # -- public API ------------------------------------------------------
    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def log(self, level: LogLevel, message: str) -> None:
        entry = LogEntry(level, message)
        self._entries.append(entry)
        if len(self._entries) > self._max_lines:
            self._entries = self._entries[-self._max_lines:]

        formatted = str(entry)
        for cb in self._callbacks:
            try:
                cb(level.value, formatted)
            except Exception:
                pass

        stdlib_map = {
            LogLevel.INFO: logging.INFO,
            LogLevel.SUCCESS: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
        }
        self._stdlib.log(stdlib_map.get(level, logging.INFO), message)

    def info(self, message: str) -> None:
        self.log(LogLevel.INFO, message)

    def success(self, message: str) -> None:
        self.log(LogLevel.SUCCESS, message)

    def warning(self, message: str) -> None:
        self.log(LogLevel.WARNING, message)

    def error(self, message: str) -> None:
        self.log(LogLevel.ERROR, message)

    def clear(self) -> None:
        self._entries.clear()
