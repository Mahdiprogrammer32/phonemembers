"""Export contacts to TXT and CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from app.utils.logger import Logger


class ExportService:
    """Write phone numbers / contacts to external files."""

    def __init__(self, logger: Logger | None = None) -> None:
        self.log = logger or Logger.instance()

    # ------------------------------------------------------------------
    # TXT export
    # ------------------------------------------------------------------
    def export_txt(self, phones: list[str], path: Path) -> int:
        """Write phones to a plain-text file. Returns count written."""
        try:
            path.write_text(
                "\n".join(phones) + ("\n" if phones else ""),
                encoding="utf-8",
            )
            self.log.success(f"Exported {len(phones)} numbers to {path.name}")
            return len(phones)
        except Exception as exc:
            self.log.error(f"TXT export failed: {exc}")
            return 0

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------
    def export_csv(self, phones: list[str], path: Path) -> int:
        """Write phones to a CSV file. Returns count written."""
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["phone"])
                for phone in phones:
                    writer.writerow([phone])
            self.log.success(f"Exported {len(phones)} numbers to {path.name}")
            return len(phones)
        except Exception as exc:
            self.log.error(f"CSV export failed: {exc}")
            return 0
