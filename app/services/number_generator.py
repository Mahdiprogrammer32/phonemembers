"""Sequential phone number generator."""

from __future__ import annotations

from app.utils.phone import normalize_phone


def generate_numbers(
    start_number: str,
    count: int,
    step: int = 1,
) -> list[str]:
    """Generate a list of sequential phone numbers.

    The *start_number* is parsed to its digit form and numbers are generated
    by adding *step* to the numeric value.

    Returns a list of **normalized** phone strings.
    """
    normalized = normalize_phone(start_number)
    if normalized is None:
        raise ValueError(f"Invalid start number: {start_number}")

    # Extract digits (without leading +)
    base_digits = int(normalized.lstrip("+"))
    results: list[str] = []

    for i in range(count):
        num = base_digits + i * step
        phone = f"+{num}"
        # Validate length (E.164 allows max 15 digits)
        if len(str(num)) > 15:
            break
        results.append(phone)

    return results
