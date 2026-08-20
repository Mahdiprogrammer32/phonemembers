"""Reusable dialog windows."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QWidget,
)


def confirm_delete_all(parent: QWidget) -> bool:
    """Show a confirmation dialog for deleting all created contacts.

    Returns ``True`` if the user confirmed.
    """
    box = QMessageBox(parent)
    box.setWindowTitle("Confirm Delete")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText(
        "Are you sure you want to delete ALL contacts created by this application?"
    )
    box.setInformativeText(
        "This operation cannot be undone. "
        "Only contacts that were created by this app will be removed. "
        "Your original contacts will NOT be affected."
    )
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes


def confirm_delete_selected(parent: QWidget, count: int) -> bool:
    """Confirmation for deleting selected contacts."""
    box = QMessageBox(parent)
    box.setWindowTitle("Confirm Delete")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText(f"Delete {count} selected contact(s)?")
    box.setInformativeText(
        "Only contacts created by this application will be removed."
    )
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes


def pick_import_file(parent: QWidget, file_type: str = "txt") -> str | None:
    """Open a file dialog and return the selected file path (or None)."""
    if file_type == "csv":
        filt = "CSV Files (*.csv);;All Files (*)"
    else:
        filt = "Text Files (*.txt);;All Files (*)"
    path, _ = QFileDialog.getOpenFileName(
        parent, "Import Contacts", "", filt
    )
    return path or None


def pick_export_file(parent: QWidget, file_type: str = "txt") -> str | None:
    """Open a save-file dialog and return the selected path (or None)."""
    if file_type == "csv":
        filt = "CSV Files (*.csv);;All Files (*)"
    else:
        filt = "Text Files (*.txt);;All Files (*)"
    path, _ = QFileDialog.getSaveFileName(
        parent, "Export Contacts", "", filt
    )
    return path or None


def show_info(parent: QWidget, title: str, message: str) -> None:
    """Show an information message box."""
    QMessageBox.information(parent, title, message)


def show_error(parent: QWidget, title: str, message: str) -> None:
    """Show an error message box."""
    QMessageBox.critical(parent, title, message)
