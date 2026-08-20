"""Main application window."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import settings
from app.database.database import Database
from app.gui.dialogs import (
    confirm_delete_all,
    confirm_delete_selected,
    pick_export_file,
    pick_import_file,
    show_error,
    show_info,
)
from app.gui.widgets import LogPanel, PreviewTable, StatsBar, StyledTable
from app.services.contact_service import ContactService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.services.number_generator import generate_numbers
from app.utils.logger import Logger
from app.utils.phone import normalize_phone
from app.utils.validators import (
    validate_count,
    validate_name_prefix,
    validate_start_number,
    validate_step,
)


# ======================================================================
# Background worker thread
# ======================================================================
class WorkerThread(QThread):
    """Generic worker that runs a callable in a background thread."""

    finished = Signal(object)  # result
    error = Signal(str)
    progress = Signal(int, int, int, int, int)  # total, processed, success, failed, skipped

    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._cancelled = False
        self._result = None

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self._result = result
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ======================================================================
# Main Window
# ======================================================================
class MainWindow(QMainWindow):
    """The main application window."""

    DARK_STYLE = """
    QMainWindow, QWidget {
        background-color: #11111b;
        color: #cdd6f4;
        font-family: 'Segoe UI', 'SF Pro', sans-serif;
        font-size: 13px;
    }
    QGroupBox {
        border: 1px solid #45475a;
        border-radius: 6px;
        margin-top: 12px;
        padding: 12px 8px 8px 8px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }
    QLineEdit, QComboBox {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 13px;
    }
    QLineEdit:focus { border: 1px solid #89b4fa; }
    QPushButton {
        background-color: #45475a;
        color: #cdd6f4;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #585b70; }
    QPushButton:pressed { background-color: #313244; }
    QPushButton:disabled {
        background-color: #1e1e2e;
        color: #585b70;
    }
    QPushButton#primary {
        background-color: #89b4fa;
        color: #1e1e2e;
    }
    QPushButton#primary:hover { background-color: #b4d0fb; }
    QPushButton#danger {
        background-color: #f38ba8;
        color: #1e1e2e;
    }
    QPushButton#danger:hover { background-color: #f5a0bc; }
    QPushButton#success {
        background-color: #a6e3a1;
        color: #1e1e2e;
    }
    QPushButton#success:hover { background-color: #c0f0c0; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{settings.app_name} v{settings.version}")
        self.setMinimumSize(1100, 750)
        self.resize(1280, 850)
        self.setStyleSheet(self.DARK_STYLE)

        # ---- Core services ------------------------------------------------
        self.db = Database(settings.db.path)
        self.logger = Logger.instance()
        self.logger.set_file(settings.db.path.parent / "app.log")
        self.contact_svc = ContactService(self.db, self.logger)
        self.import_svc = ImportService(self.logger)
        self.export_svc = ExportService(self.logger)

        # ---- State --------------------------------------------------------
        self._generated_phones: list[str] = []
        self._worker: Optional[WorkerThread] = None

        # ---- Build UI -----------------------------------------------------
        self._build_ui()
        self._connect_signals()
        self._refresh_table()
        self._log("Application started", "INFO")

    # ==================================================================
    # UI Construction
    # ==================================================================
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 8, 12, 8)

        # Top area: config + contacts in a splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter, stretch=5)

        # ---- Upper: two-column layout
        upper = QWidget()
        upper_layout = QHBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(upper)

        # Left column — Generation config
        left_col = self._build_generation_panel()
        upper_layout.addWidget(left_col, stretch=1)

        # Right column — Contacts table + actions
        right_col = self._build_contacts_panel()
        upper_layout.addWidget(right_col, stretch=2)

        # ---- Lower: log + stats
        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 4, 0, 0)

        self._stats_bar = StatsBar()
        lower_layout.addWidget(self._stats_bar)

        self._log_panel = LogPanel()
        lower_layout.addWidget(self._log_panel, stretch=1)

        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)

    # -- Generation panel (left) ----------------------------------------
    def _build_generation_panel(self) -> QWidget:
        grp = QGroupBox("🔧 Number Generation")
        layout = QVBoxLayout(grp)

        form = QGridLayout()
        form.setSpacing(8)

        lbl_style = "font-size: 12px; color: #a6adc8;"

        # Start Number
        lbl = QLabel("Start Number:")
        lbl.setStyleSheet(lbl_style)
        form.addWidget(lbl, 0, 0)
        self._inp_start = QLineEdit("09121111111")
        self._inp_start.setPlaceholderText("e.g. 09121111111")
        form.addWidget(self._inp_start, 0, 1)

        # Count
        lbl = QLabel("Count:")
        lbl.setStyleSheet(lbl_style)
        form.addWidget(lbl, 1, 0)
        self._inp_count = QLineEdit("1000")
        form.addWidget(self._inp_count, 1, 1)

        # Name Prefix
        lbl = QLabel("Name Prefix:")
        lbl.setStyleSheet(lbl_style)
        form.addWidget(lbl, 2, 0)
        self._inp_prefix = QLineEdit("Channel Member")
        form.addWidget(self._inp_prefix, 2, 1)

        # Country Code  (informational — normalization handles it)
        lbl = QLabel("Country Code:")
        lbl.setStyleSheet(lbl_style)
        form.addWidget(lbl, 3, 0)
        self._lbl_country = QLabel("+98 (Iran)")
        self._lbl_country.setStyleSheet("color: #89b4fa; font-weight: bold;")
        form.addWidget(self._lbl_country, 3, 1)

        # Step
        lbl = QLabel("Step:")
        lbl.setStyleSheet(lbl_style)
        form.addWidget(lbl, 4, 0)
        self._inp_step = QLineEdit("1")
        form.addWidget(self._inp_step, 4, 1)

        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_preview = QPushButton("👁 Preview")
        self._btn_preview.setObjectName("primary")
        btn_row.addWidget(self._btn_preview)

        self._btn_generate = QPushButton("⚡ Generate")
        self._btn_generate.setObjectName("primary")
        btn_row.addWidget(self._btn_generate)

        layout.addLayout(btn_row)

        # Preview table
        self._preview_table = PreviewTable()
        layout.addWidget(self._preview_table)

        return grp

    # -- Contacts panel (right) -----------------------------------------
    def _build_contacts_panel(self) -> QWidget:
        grp = QGroupBox("👥 Contact Management")
        layout = QVBoxLayout(grp)

        # Table
        self._contact_table = StyledTable()
        layout.addWidget(self._contact_table, stretch=1)

        # Action buttons row 1
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._btn_add = QPushButton("➕ Add Contacts")
        self._btn_add.setObjectName("success")
        row1.addWidget(self._btn_add)

        self._btn_del_created = QPushButton("🗑 Delete Created Contacts")
        self._btn_del_created.setObjectName("danger")
        row1.addWidget(self._btn_del_created)

        self._btn_del_selected = QPushButton("✂ Delete Selected")
        self._btn_del_selected.setObjectName("danger")
        row1.addWidget(self._btn_del_selected)

        self._btn_refresh = QPushButton("🔄 Refresh")
        row1.addWidget(self._btn_refresh)

        layout.addLayout(row1)

        # Action buttons row 2 (import / export)
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        row2.addWidget(QLabel("Import:"))
        self._btn_import_txt = QPushButton("TXT")
        row2.addWidget(self._btn_import_txt)
        self._btn_import_csv = QPushButton("CSV")
        row2.addWidget(self._btn_import_csv)

        row2.addSpacing(20)

        row2.addWidget(QLabel("Export:"))
        self._btn_export_txt = QPushButton("TXT")
        row2.addWidget(self._btn_export_txt)
        self._btn_export_csv = QPushButton("CSV")
        row2.addWidget(self._btn_export_csv)

        row2.addStretch()

        self._btn_clear = QPushButton("🧹 Clear Preview")
        row2.addWidget(self._btn_clear)

        # Cancel button (hidden by default)
        self._btn_cancel = QPushButton("⛔ Cancel")
        self._btn_cancel.setObjectName("danger")
        self._btn_cancel.setVisible(False)
        row2.addWidget(self._btn_cancel)

        layout.addLayout(row2)

        # Status label
        self._lbl_status = QLabel("Ready")
        self._lbl_status.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 4px;")
        layout.addWidget(self._lbl_status)

        return grp

    # ==================================================================
    # Signal connections
    # ==================================================================
    def _connect_signals(self) -> None:
        # Generation
        self._btn_preview.clicked.connect(self._on_preview)
        self._btn_generate.clicked.connect(self._on_generate)

        # Contact operations
        self._btn_add.clicked.connect(self._on_add_contacts)
        self._btn_del_created.clicked.connect(self._on_delete_created)
        self._btn_del_selected.clicked.connect(self._on_delete_selected)
        self._btn_refresh.clicked.connect(self._refresh_table)

        # Import / Export
        self._btn_import_txt.clicked.connect(lambda: self._on_import("txt"))
        self._btn_import_csv.clicked.connect(lambda: self._on_import("csv"))
        self._btn_export_txt.clicked.connect(lambda: self._on_export("txt"))
        self._btn_export_csv.clicked.connect(lambda: self._on_export("csv"))

        # Clear
        self._btn_clear.clicked.connect(self._on_clear_preview)

        # Cancel
        self._btn_cancel.clicked.connect(self._on_cancel)

        # Logger signal
        self.logger.signal.log_received.connect(self._on_log_received)

    # ==================================================================
    # Actions
    # ==================================================================

    # -- Preview --------------------------------------------------------
    @Slot()
    def _on_preview(self) -> None:
        start = self._inp_start.text().strip()
        count_s = self._inp_count.text().strip()
        step_s = self._inp_step.text().strip()

        ok, msg = validate_start_number(start)
        if not ok:
            show_error(self, "Validation Error", msg or "Invalid start number")
            return
        ok, count, msg = validate_count(count_s)
        if not ok:
            show_error(self, "Validation Error", msg or "Invalid count")
            return
        ok, step, msg = validate_step(step_s)
        if not ok:
            show_error(self, "Validation Error", msg or "Invalid step")
            return

        try:
            phones = generate_numbers(start, count, step)
        except ValueError as exc:
            show_error(self, "Generation Error", str(exc))
            return

        self._generated_phones = phones
        self._preview_table.load_numbers(phones)
        self._log(f"Preview: {len(phones)} numbers generated", "INFO")
        self._lbl_status.setText(f"Previewing {len(phones)} numbers")

    # -- Generate (create in DB) ----------------------------------------
    @Slot()
    def _on_generate(self) -> None:
        if not self._generated_phones:
            show_error(self, "Error", "Please preview numbers first.")
            return

        ok, prefix, msg = validate_name_prefix(self._inp_prefix.text().strip())
        if not ok:
            show_error(self, "Validation Error", msg or "Invalid prefix")
            return

        self._set_buttons_enabled(False)
        self._btn_cancel.setVisible(True)
        self._stats_bar.reset()

        def _work():
            return self.contact_svc.create_contacts(
                self._generated_phones,
                name_prefix=prefix,
                batch_size=settings.batch_size,
                progress_callback=lambda t, p, s, f, sk: self._stats_bar.update_stats(t, p, s, f, sk),
            )

        self._worker = WorkerThread(_work)
        self._worker.finished.connect(self._on_generate_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_generate_done(self, result) -> None:
        self._set_buttons_enabled(True)
        self._btn_cancel.setVisible(False)
        self._stats_bar.update_stats(
            result.total, result.processed, result.success, result.failed, result.skipped
        )
        self._refresh_table()
        self._log(f"Generation complete: {result.success} created", "SUCCESS")

    # -- Add contacts (same as generate, using current preview) --------
    @Slot()
    def _on_add_contacts(self) -> None:
        """Alias: adds the previewed numbers to the database."""
        self._on_generate()

    # -- Delete created -------------------------------------------------
    @Slot()
    def _on_delete_created(self) -> None:
        count = self.contact_svc.get_created_count()
        if count == 0:
            show_info(self, "Info", "No application-created contacts to delete.")
            return

        if not confirm_delete_all(self):
            return

        self._set_buttons_enabled(False)
        self._btn_cancel.setVisible(True)
        self._stats_bar.reset()

        def _work():
            return self.contact_svc.delete_created_contacts(
                batch_size=settings.batch_size,
                progress_callback=lambda t, p, s, f, sk: self._stats_bar.update_stats(t, p, s, f, sk),
            )

        self._worker = WorkerThread(_work)
        self._worker.finished.connect(self._on_delete_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_delete_done(self, result) -> None:
        self._set_buttons_enabled(True)
        self._btn_cancel.setVisible(False)
        self._stats_bar.update_stats(
            result.total, result.processed, result.success, result.failed, result.skipped
        )
        self._refresh_table()
        self._log(f"Delete complete: {result.success} removed", "SUCCESS")

    # -- Delete selected ------------------------------------------------
    @Slot()
    def _on_delete_selected(self) -> None:
        ids = self._contact_table.get_selected_internal_ids()
        if not ids:
            show_info(self, "Info", "No contacts selected.")
            return

        if not confirm_delete_selected(self, len(ids)):
            return

        deleted = self.contact_svc.delete_selected_contacts(ids)
        self._refresh_table()
        self._log(f"Deleted {deleted} selected contact(s)", "SUCCESS")

    # -- Import ---------------------------------------------------------
    @Slot()
    def _on_import(self, file_type: str) -> None:
        path = pick_import_file(self, file_type)
        if not path:
            return

        p = Path(path)
        if file_type == "csv":
            phones = self.import_svc.import_csv(p)
        else:
            phones = self.import_svc.import_txt(p)

        if not phones:
            show_info(self, "Import", "No valid phone numbers found.")
            return

        self._generated_phones = phones
        self._preview_table.load_numbers(phones)
        self._log(f"Imported {len(phones)} numbers from {p.name}", "SUCCESS")

    # -- Export ---------------------------------------------------------
    @Slot()
    def _on_export(self, file_type: str) -> None:
        path = pick_export_file(self, file_type)
        if not path:
            return

        contacts = self.contact_svc.get_all_contacts()
        phones = [c.phone for c in contacts]

        if not phones:
            show_info(self, "Export", "No contacts to export.")
            return

        p = Path(path)
        if file_type == "csv":
            count = self.export_svc.export_csv(phones, p)
        else:
            count = self.export_svc.export_txt(phones, p)

        if count:
            show_info(self, "Export", f"Exported {count} contacts to {p.name}")

    # -- Clear preview --------------------------------------------------
    @Slot()
    def _on_clear_preview(self) -> None:
        self._generated_phones.clear()
        self._preview_table.load_numbers([])
        self._lbl_status.setText("Preview cleared")

    # -- Cancel ---------------------------------------------------------
    @Slot()
    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._log("Operation cancelled by user", "WARNING")

    # ==================================================================
    # Helpers
    # ==================================================================
    def _refresh_table(self) -> None:
        contacts = self.contact_svc.get_all_contacts()
        rows = []
        for c in contacts:
            rows.append({
                "phone": c.phone,
                "generated_name": c.generated_name,
                "source": c.source,
                "status": c.status,
                "created_at": c.created_at,
                "_id": c.internal_id,
            })
        self._contact_table.load_data(rows)

        # Re-attach internal_id as UserRole on the first column
        for r, c in enumerate(contacts):
            item = self._contact_table.item(r, 0)
            if item:
                item.setData(Qt.ItemDataRole.UserRole, c.internal_id)

        total = self.contact_svc.get_total_count()
        created = self.contact_svc.get_created_count()
        self._lbl_status.setText(
            f"Total: {total}  |  Created by app: {created}"
        )

    def _set_buttons_enabled(self, enabled: bool) -> None:
        """Enable/disable action buttons during long operations."""
        for btn in (
            self._btn_preview,
            self._btn_generate,
            self._btn_add,
            self._btn_del_created,
            self._btn_del_selected,
            self._btn_import_txt,
            self._btn_import_csv,
            self._btn_export_txt,
            self._btn_export_csv,
        ):
            btn.setEnabled(enabled)

    def _log(self, message: str, level: str = "INFO") -> None:
        self.logger.log(
            __import__("app.utils.logger", fromlist=["LogLevel"]).LogLevel(level),
            message,
        )

    @Slot(str, str)
    def _on_log_received(self, level_name: str, message: str) -> None:
        self._log_panel.append(level_name, message)

    def _on_worker_error(self, msg: str) -> None:
        self._set_buttons_enabled(True)
        self._btn_cancel.setVisible(False)
        self._log(f"Error: {msg}", "ERROR")
        show_error(self, "Error", msg)
