"""Export contacts to TXT and CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from app.utils.logger import Logger


class ExportService:
    def __init__(self, logger: Logger | None = None) -> None:
        self.log = logger or Logger.instance()

    def export_txt(self, phones: list[str], path: Path) -> int:
        try:
            path.write_text("\n".join(phones) + ("\n" if phones else ""), encoding="utf-8")
            self.log.success(f"Exported {len(phones)} to {path.name}")
            return len(phones)
        except Exception as exc:
            self.log.error(f"TXT export failed: {exc}")
            return 0

    def export_csv(self, phones: list[str], path: Path) -> int:
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["phone"])
                for phone in phones:
                    writer.writerow([phone])
            self.log.success(f"Exported {len(phones)} to {path.name}")
            return len(phones)
        except Exception as exc:
            self.log.error(f"CSV export failed: {exc}")
            return 0
