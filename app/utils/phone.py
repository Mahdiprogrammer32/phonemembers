"""Phone number normalization and validation utilities."""

from __future__ import annotations

import re
from typing import Optional


def normalize_phone(raw: str) -> Optional[str]:
    """Normalize a phone number to a standard format.

    Accepted inputs:
      09121111111       → +989121111111
      +989121111111     → +989121111111
      00989121111111    → +989121111111
      9121111111        → +989121111111

    Returns ``None`` if the number is invalid.
    """
    digits = re.sub(r"[^\d]", "", raw)

    if not digits:
        return None

    # Strip leading zeros (country dial prefix)
    while len(digits) > 2 and digits.startswith("00"):
        digits = digits[2:]

    # Iranian numbers
    if digits.startswith("0") and len(digits) == 11:
        # 09121111111 → 989121111111
        digits = "98" + digits[1:]
    elif digits.startswith("98") and len(digits) == 12:
        pass  # already in +98 format
    elif len(digits) == 10 and digits.startswith("9"):
        # 9121111111 → 989121111111 (10-digit without leading 0)
        digits = "98" + digits
    else:
        # Generic: keep as-is if between 7-15 digits (E.164 range)
        if len(digits) < 7 or len(digits) > 15:
            return None

    return "+" + digits


def validate_phone(raw: str) -> bool:
    """Return True if the raw value normalizes to a valid phone."""
    return normalize_phone(raw) is not None


def format_display(phone: str) -> str:
    """Pretty-print a normalized phone for the UI.

    ``+989121111111`` → ``+98 912 111 1111``
    """
    if phone.startswith("+98") and len(phone) == 13:
        local = phone[3:]
        return f"+98 {local[:3]} {local[3:6]} {local[6:]}"
    return phone
