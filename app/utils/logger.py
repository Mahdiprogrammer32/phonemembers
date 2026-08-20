"""Lightweight logger that writes to a GUI panel and optionally to a file."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal


class LogLevel(Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Friendly colours per level (for future rich-text use)
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


class LogSignalEmitter(QObject):
    """Cross-thread signal emitter for log entries."""

    log_received = Signal(str, str)  # (level_name, formatted_message)


class Logger:
    """Application-wide logger.

    Emits ``log_received(level, message)`` so the GUI can update in real-time.
    """

    _instance: Optional["Logger"] = None

    def __init__(self) -> None:
        self._emitter = LogSignalEmitter()
        self._entries: list[LogEntry] = []
        self._file_path: Optional[Path] = None
        self._max_lines: int = 5000

        # Python stdlib logger for file output
        self._stdlib = logging.getLogger("app")
        self._stdlib.setLevel(logging.DEBUG)

    # -- singleton --------------------------------------------------------
    @classmethod
    def instance(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- configuration ----------------------------------------------------
    def set_file(self, path: Path, max_lines: int = 5000) -> None:
        self._file_path = path
        self._max_lines = max_lines
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        self._stdlib.addHandler(handler)

    # -- public API -------------------------------------------------------
    @property
    def signal(self) -> LogSignalEmitter:
        return self._emitter

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def log(self, level: LogLevel, message: str) -> None:
        entry = LogEntry(level, message)
        self._entries.append(entry)

        # Trim in-memory buffer
        if len(self._entries) > self._max_lines:
            self._entries = self._entries[-self._max_lines:]

        formatted = str(entry)
        self._emitter.log_received.emit(level.value, formatted)

        # Stdlib file logging
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
