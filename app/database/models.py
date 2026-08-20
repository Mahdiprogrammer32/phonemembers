"""Data models used across the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class Contact:
    """Represents a single contact record in the database."""

    internal_id: str = field(default_factory=_uuid)
    phone: str = ""
    generated_name: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    source: str = "generated"  # "generated" | "imported"
    status: str = "active"  # "active" | "deleted"
    created_by_app: bool = True


@dataclass
class Operation:
    """Records an operation performed by the application."""

    operation_id: str = field(default_factory=_uuid)
    operation_type: str = ""  # "generate" | "add" | "delete" | "import"
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    status: str = "pending"  # "pending" | "running" | "completed" | "cancelled"
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
