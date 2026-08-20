"""Sequential phone number generator."""

from __future__ import annotations

from app.utils.phone import normalize_phone


def generate_numbers(start_number: str, count: int, step: int = 1) -> list[str]:
    """Generate sequential phone numbers.

    Returns a list of normalized phone strings.
    """
    normalized = normalize_phone(start_number)
    if normalized is None:
        raise ValueError(f"Invalid start number: {start_number}")

    base_digits = int(normalized.lstrip("+"))
    results: list[str] = []

    for i in range(count):
        num = base_digits + i * step
        if len(str(num)) > 15:
            break
        results.append(f"+{num}")

    return results
