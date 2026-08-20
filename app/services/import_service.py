"""Import contacts from TXT and CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from app.utils.logger import Logger
from app.utils.phone import normalize_phone


class ImportService:
    """Read phone numbers from external files and normalize them."""

    def __init__(self, logger: Logger | None = None) -> None:
        self.log = logger or Logger.instance()

    # ------------------------------------------------------------------
    # TXT import
    # ------------------------------------------------------------------
    def import_txt(self, path: Path) -> list[str]:
        """Import phone numbers from a plain-text file (one per line).

        Returns a list of **normalized** phone numbers.
        """
        self.log.info(f"Importing TXT file: {path.name}")
        numbers: list[str] = []
        errors = 0

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            self.log.error(f"Failed to read file: {exc}")
            return []

        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            phone = normalize_phone(line)
            if phone is None:
                self.log.warning(f"Skipped invalid number on line {line_no}: {line}")
                errors += 1
                continue
            numbers.append(phone)

        self.log.success(
            f"TXT import complete: {len(numbers)} numbers, {errors} errors."
        )
        return numbers

    # ------------------------------------------------------------------
    # CSV import
    # ------------------------------------------------------------------
    def import_csv(self, path: Path) -> list[str]:
        """Import phone numbers from a CSV file.

        The service searches all columns for phone numbers.
        Returns a list of **normalized** phone numbers.
        """
        self.log.info(f"Importing CSV file: {path.name}")
        numbers: list[str] = []
        errors = 0

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                reader = csv.reader(fh)
                for row_no, row in enumerate(reader, 1):
                    for cell in row:
                        cell = cell.strip()
                        if not cell:
                            continue
                        phone = normalize_phone(cell)
                        if phone:
                            numbers.append(phone)
                        else:
                            # Only warn for cells that look like they might
                            # have been intended as phone numbers
                            if any(c.isdigit() for c in cell) and len(cell) >= 7:
                                self.log.warning(
                                    f"Skipped invalid number on row {row_no}: {cell}"
                                )
                                errors += 1
        except Exception as exc:
            self.log.error(f"Failed to read CSV: {exc}")
            return []

        self.log.success(
            f"CSV import complete: {len(numbers)} numbers, {errors} errors."
        )
        return numbers
