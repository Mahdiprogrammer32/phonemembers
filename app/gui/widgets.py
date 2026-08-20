"""Reusable custom widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.utils.logger import LOG_COLORS, LogLevel


# ======================================================================
# Log Panel
# ======================================================================
class LogPanel(QWidget):
    """Scrollable log panel with coloured output."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("📋 Log")
        header.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px;")
        layout.addWidget(header)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(5000)
        self._text.setFont(QFont("Cascadia Code,Consolas,monospace", 10))
        self._text.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 4px; padding: 6px; }"
        )
        layout.addWidget(self._text)

    def append(self, level_name: str, message: str) -> None:
        color = LOG_COLORS.get(LogLevel(level_name), "#cdd6f4")
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def clear(self) -> None:
        self._text.clear()


# ======================================================================
# Stats / Progress Bar
# ======================================================================
class StatsBar(QWidget):
    """Displays operation progress + statistics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p%  Processing …")
        self._progress.setStyleSheet(
            "QProgressBar { border: 1px solid #45475a; border-radius: 4px; "
            "text-align: center; height: 22px; background-color: #313244; }"
            "QProgressBar::chunk { background-color: #89b4fa; border-radius: 3px; }"
        )
        root.addWidget(self._progress)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        self._labels: dict[str, QLabel] = {}
        for key in ("Total", "Processed", "Success", "Failed", "Skipped"):
            lbl = QLabel(f"{key}: 0")
            lbl.setStyleSheet("font-size: 12px; color: #a6adc8;")
            stats_layout.addWidget(lbl)
            self._labels[key] = lbl
        stats_layout.addStretch()
        root.addLayout(stats_layout)

    # -- public API ------------------------------------------------------
    def update_stats(
        self, total: int, processed: int, success: int, failed: int, skipped: int
    ) -> None:
        self._labels["Total"].setText(f"Total: {total}")
        self._labels["Processed"].setText(f"Processed: {processed}")
        self._labels["Success"].setText(f"Success: {success}")
        self._labels["Failed"].setText(f"Failed: {failed}")
        self._labels["Skipped"].setText(f"Skipped: {skipped}")

        pct = int(processed / total * 100) if total else 0
        self._progress.setValue(pct)
        self._progress.setFormat(f"{pct}%  Processing …")

    def reset(self) -> None:
        self._progress.setValue(0)
        self._progress.setFormat("Ready")
        for key, lbl in self._labels.items():
            lbl.setText(f"{key}: 0")


# ======================================================================
# Styled Table
# ======================================================================
class StyledTable(QTableWidget):
    """A styled contact table with alternating row colours."""

    HEADERS = ["#", "Phone", "Name", "Source", "Status", "Created At"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setStyleSheet(
            "QTableWidget { background-color: #1e1e2e; color: #cdd6f4; "
            "gridline-color: #45475a; border: 1px solid #45475a; }"
            "QTableWidget::item:selected { background-color: #45475a; }"
            "QHeaderView::section { background-color: #313244; color: #cdd6f4; "
            "padding: 6px; border: 1px solid #45475a; font-weight: bold; }"
        )

    def load_data(self, rows: list[dict]) -> None:
        """Populate the table with a list of dicts (keys match HEADERS lowercased)."""
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.setItem(r, 0, QTableWidgetItem(str(r + 1)))
            self.setItem(r, 1, QTableWidgetItem(row.get("phone", "")))
            self.setItem(r, 2, QTableWidgetItem(row.get("generated_name", "")))
            self.setItem(r, 3, QTableWidgetItem(row.get("source", "")))
            self.setItem(r, 4, QTableWidgetItem(row.get("status", "")))
            self.setItem(r, 5, QTableWidgetItem(row.get("created_at", "")[:19]))
        self.resizeColumnsToContents()

    def get_selected_internal_ids(self) -> list[str]:
        """Return internal_ids of selected rows (stored as Qt.UserRole)."""
        ids: list[str] = []
        for idx in self.selectedIndexes():
            item = self.item(idx.row(), 0)
            if item:
                uid = item.data(Qt.ItemDataRole.UserRole)
                if uid:
                    ids.append(uid)
        return list(set(ids))

    def clear_table(self) -> None:
        self.setRowCount(0)


# ======================================================================
# Preview Table (read-only, lighter style)
# ======================================================================
class PreviewTable(QTableWidget):
    """Compact preview of generated numbers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["#", "Phone"])
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setMaximumHeight(200)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setStyleSheet(
            "QTableWidget { background-color: #1e1e2e; color: #a6adc8; "
            "gridline-color: #45475a; border: 1px solid #45475a; font-size: 11px; }"
            "QHeaderView::section { background-color: #313244; color: #cdd6f4; "
            "padding: 4px; border: 1px solid #45475a; font-weight: bold; }"
        )

    def load_numbers(self, phones: list[str], max_preview: int = 50) -> None:
        show = phones[:max_preview]
        self.setRowCount(len(show))
        for i, p in enumerate(show):
            self.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.setItem(i, 1, QTableWidgetItem(p))
        self.resizeColumnsToContents()
