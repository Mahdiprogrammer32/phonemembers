"""Generic validation helpers."""

from __future__ import annotations

import re
from typing import Optional


def validate_name_prefix(prefix: str) -> tuple[bool, Optional[str]]:
    prefix = prefix.strip()
    if not prefix:
        return True, None
    if len(prefix) > 100:
        return False, "Name prefix must be 100 characters or fewer."
    if re.search(r"[<>\"';\x00]", prefix):
        return False, "Name prefix contains forbidden characters."
    return True, None


def validate_count(value: str) -> tuple[bool, int, Optional[str]]:
    value = value.strip()
    if not value:
        return False, 0, "Count is required."
    if not value.isdigit():
        return False, 0, "Count must be a positive integer."
    n = int(value)
    if n <= 0:
        return False, 0, "Count must be greater than zero."
    if n > 100_000:
        return False, 0, "Count cannot exceed 100 000."
    return True, n, None


def validate_start_number(value: str) -> tuple[bool, Optional[str]]:
    from app.utils.phone import normalize_phone

    value = value.strip()
    if not value:
        return False, "Start number is required."
    if normalize_phone(value) is None:
        return False, "Invalid phone number format."
    return True, None


def validate_step(value: str) -> tuple[bool, int, Optional[str]]:
    value = value.strip()
    if not value:
        return False, 0, "Step is required."
    if not value.isdigit():
        return False, 0, "Step must be a positive integer."
    n = int(value)
    if n <= 0:
        return False, 0, "Step must be greater than zero."
    return True, n, None
