"""Import contacts from TXT and CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from app.utils.logger import Logger
from app.utils.phone import normalize_phone


class ImportService:
    def __init__(self, logger: Logger | None = None) -> None:
        self.log = logger or Logger.instance()

    def import_txt(self, path: Path) -> list[str]:
        self.log.info(f"Importing TXT: {path.name}")
        numbers: list[str] = []
        errors = 0
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            self.log.error(f"Read failed: {exc}")
            return []
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            phone = normalize_phone(line)
            if phone is None:
                self.log.warning(f"Skipped line {line_no}: {line}")
                errors += 1
                continue
            numbers.append(phone)
        self.log.success(f"TXT: {len(numbers)} numbers, {errors} errors")
        return numbers

    def import_csv(self, path: Path) -> list[str]:
        self.log.info(f"Importing CSV: {path.name}")
        numbers: list[str] = []
        errors = 0
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for row_no, row in enumerate(csv.reader(fh), 1):
                    for cell in row:
                        cell = cell.strip()
                        if not cell:
                            continue
                        phone = normalize_phone(cell)
                        if phone:
                            numbers.append(phone)
                        elif any(c.isdigit() for c in cell) and len(cell) >= 7:
                            self.log.warning(f"Skipped row {row_no}: {cell}")
                            errors += 1
        except Exception as exc:
            self.log.error(f"CSV read failed: {exc}")
            return []
        self.log.success(f"CSV: {len(numbers)} numbers, {errors} errors")
        return numbers
