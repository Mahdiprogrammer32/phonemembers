"""Main KivyMD application for Android."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.lang import Builder

from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDFillRoundFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, TwoLineListItem, MDList
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.bottomsheet import MDGridBottomSheet

from app.config.settings import settings
from app.database.database import Database
from app.services.contact_service import ContactService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.services.number_generator import generate_numbers
from app.utils.logger import Logger
from app.utils.phone import normalize_phone
from app.utils.validators import validate_count, validate_name_prefix, validate_start_number, validate_step

# ============================================================================
# KV Language — defines the entire UI layout
# ============================================================================

KV = """
#:import get_color_from_hex kivy.utils.get_color_from_hex

<HoverCard@MDCard>
    padding: dp(12)
    spacing: dp(8)
    elevation: 2
    radius: [dp(8)]
    md_bg_color: get_color_from_hex("#1E1E2E")

<DarkTextField@MDTextField>
    mode: "rectangle"
    line_color_normal: get_color_from_hex("#45475A")
    line_color_focus: get_color_from_hex("#89B4FA")
    text_color_normal: get_color_from_hex("#CDD6F4")
    text_color_focus: get_color_from_hex("#CDD6F4")
    fill_color_normal: get_color_from_hex("#313244")
    fill_color_focus: get_color_from_hex("#313244")
    hint_text_color: get_color_from_hex("#6C7086")

<DarkButton@MDFillRoundFlatButton>
    md_bg_color: get_color_from_hex("#89B4FA")
    text_color: get_color_from_hex("#1E1E2E")
    font_size: sp(14)

<DangerButton@MDFillRoundFlatButton>
    md_bg_color: get_color_from_hex("#F38BA8")
    text_color: get_color_from_hex("#1E1E2E")
    font_size: sp(14)

<SuccessButton@MDFillRoundFlatButton>
    md_bg_color: get_color_from_hex("#A6E3A1")
    text_color: get_color_from_hex("#1E1E2E")
    font_size: sp(14)

<FlatButton@MDFlatButton>
    text_color: get_color_from_hex("#89B4FA")

MDScreenManager:
    id: screen_manager

    MDScreen:
        name: "main"
        MDBoxLayout:
            orientation: "vertical"
            md_bg_color: get_color_from_hex("#11111B")

            MDTopAppBar:
                title: "📱 Virtual Contact Manager"
                md_bg_color: get_color_from_hex("#181825")
                specific_text_color: get_color_from_hex("#CDD6F4")
                elevation: 4

            ScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    spacing: dp(12)
                    padding: dp(16)
                    size_hint_y: None
                    height: self.minimum_height

                    # ── Number Generation Card ──
                    HoverCard:
                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: dp(8)
                            size_hint_y: None
                            height: self.minimum_height

                            MDLabel:
                                text: "🔧 Number Generation"
                                font_style: "H6"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#CDD6F4")
                                size_hint_y: None
                                height: dp(32)

                            DarkTextField:
                                id: start_number
                                hint_text: "Start Number (e.g. 09121111111)"
                                text: "09121111111"
                                size_hint_y: None
                                height: dp(48)

                            DarkTextField:
                                id: count
                                hint_text: "Count"
                                text: "1000"
                                input_filter: "int"
                                size_hint_y: None
                                height: dp(48)

                            DarkTextField:
                                id: name_prefix
                                hint_text: "Name Prefix"
                                text: "Channel Member"
                                size_hint_y: None
                                height: dp(48)

                            DarkTextField:
                                id: step
                                hint_text: "Step"
                                text: "1"
                                input_filter: "int"
                                size_hint_y: None
                                height: dp(48)

                            MDBoxLayout:
                                spacing: dp(8)
                                size_hint_y: None
                                height: dp(48)

                                DarkButton:
                                    text: "👁 Preview"
                                    on_release: app.preview_numbers()
                                    size_hint_x: 0.5

                                DarkButton:
                                    text: "⚡ Generate"
                                    on_release: app.generate_contacts()
                                    size_hint_x: 0.5

                    # ── Preview Card ──
                    HoverCard:
                        id: preview_card
                        size_hint_y: None
                        height: dp(200)

                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: dp(4)

                            MDLabel:
                                text: "Preview"
                                font_style: "Subtitle1"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#A6ADC8")
                                size_hint_y: None
                                height: dp(24)

                            ScrollView:
                                MDList:
                                    id: preview_list

                    # ── Operations Card ──
                    HoverCard:
                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: dp(8)
                            size_hint_y: None
                            height: self.minimum_height

                            MDLabel:
                                text: "👥 Operations"
                                font_style: "H6"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#CDD6F4")
                                size_hint_y: None
                                height: dp(32)

                            MDProgressBar:
                                id: progress_bar
                                value: 0
                                color: get_color_from_hex("#89B4FA")
                                size_hint_y: None
                                height: dp(8)

                            MDLabel:
                                id: progress_label
                                text: "Ready"
                                font_style: "Caption"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#A6ADC8")
                                size_hint_y: None
                                height: dp(20)

                            MDGridLayout:
                                cols: 2
                                spacing: dp(8)
                                size_hint_y: None
                                height: self.minimum_height

                                SuccessButton:
                                    text: "➕ Add Contacts"
                                    on_release: app.generate_contacts()
                                    size_hint_x: 1

                                DangerButton:
                                    text: "🗑 Delete Created"
                                    on_release: app.delete_created_contacts()
                                    size_hint_x: 1

                                DangerButton:
                                    text: "✂ Delete Selected"
                                    on_release: app.delete_selected_contacts()
                                    size_hint_x: 1

                                FlatButton:
                                    text: "🔄 Refresh"
                                    on_release: app.refresh_contacts()
                                    size_hint_x: 1

                            MDGridLayout:
                                cols: 3
                                spacing: dp(8)
                                size_hint_y: None
                                height: dp(48)

                                FlatButton:
                                    text: "📄 Import TXT"
                                    on_release: app.import_contacts("txt")
                                    size_hint_x: 0.33

                                FlatButton:
                                    text: "📊 Import CSV"
                                    on_release: app.import_contacts("csv")
                                    size_hint_x: 0.33

                                FlatButton:
                                    text: "📤 Export"
                                    on_release: app.show_export_dialog()
                                    size_hint_x: 0.34

                    # ── Contact List Card ──
                    HoverCard:
                        size_hint_y: None
                        height: dp(300)

                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: dp(4)

                            MDBoxLayout:
                                size_hint_y: None
                                height: dp(32)

                                MDLabel:
                                    id: contacts_title
                                    text: "👥 Contacts (0)"
                                    font_style: "H6"
                                    theme_text_color: "Custom"
                                    text_color: get_color_from_hex("#CDD6F4")

                            ScrollView:
                                MDList:
                                    id: contact_list

                    # ── Log Card ──
                    HoverCard:
                        size_hint_y: None
                        height: dp(220)

                        MDBoxLayout:
                            orientation: "vertical"
                            spacing: dp(4)

                            MDLabel:
                                text: "📋 Log"
                                font_style: "Subtitle1"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#A6ADC8")
                                size_hint_y: None
                                height: dp(24)

                            ScrollView:
                                id: log_scroll
                                MDList:
                                    id: log_list
"""


# ============================================================================
# Main Application
# ============================================================================

class VCMApp(MDApp):
    """Virtual Contact Manager — Android Edition."""

    contact_items = ListProperty([])
    log_items = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Database(settings.db.path)
        self.logger = Logger.instance()
        self.logger.set_file(settings.db.path.parent / "app.log")
        self.contact_svc = ContactService(self.db, self.logger)
        self.import_svc = ImportService(self.logger)
        self.export_svc = ExportService(self.logger)
        self._generated_phones: list[str] = []
        self._worker_thread: Optional[threading.Thread] = None
        self._cancel_flag = False

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.title = settings.app_name
        return Builder.load_string(KV)

    def on_start(self):
        # Register log callback
        self.logger.add_callback(self._on_log_message)
        self.refresh_contacts()
        self.logger.info("Application started")

    # ==================================================================
    # Number Generation
    # ==================================================================
    def preview_numbers(self):
        start = self.root.ids.start_number.text.strip()
        count_s = self.root.ids.count.text.strip()
        step_s = self.root.ids.step.text.strip()

        ok, msg = validate_start_number(start)
        if not ok:
            self._show_error(msg or "Invalid start number")
            return
        ok, count_val, msg = validate_count(count_s)
        if not ok:
            self._show_error(msg or "Invalid count")
            return
        ok, step_val, msg = validate_step(step_s)
        if not ok:
            self._show_error(msg or "Invalid step")
            return

        try:
            phones = generate_numbers(start, count_val, step_val)
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self._generated_phones = phones
        self._update_preview_list(phones[:100])
        self.logger.info(f"Preview: {len(phones)} numbers")

    def _update_preview_list(self, phones: list[str]):
        preview_list = self.root.ids.preview_list
        preview_list.clear_widgets()
        for i, phone in enumerate(phones):
            preview_list.add_widget(
                OneLineListItem(text=f"{i+1}. {phone}")
            )

    def generate_contacts(self):
        if not self._generated_phones:
            self.preview_numbers()
            if not self._generated_phones:
                return

        prefix = self.root.ids.name_prefix.text.strip()
        ok, msg = validate_name_prefix(prefix)
        if not ok:
            self._show_error(msg)
            return

        self._set_buttons_enabled(False)
        self._cancel_flag = False
        self.root.ids.progress_bar.value = 0

        def _work():
            phones = self._generated_phones
            total = len(phones)
            batch = settings.batch_size

            op = self.contact_svc.create_contacts(
                phones,
                name_prefix=prefix,
                batch_size=batch,
                progress_callback=lambda t, p, s, f, sk: Clock.schedule_once(
                    lambda dt: self._update_progress(t, p, s, f, sk), 0
                ),
            )
            Clock.schedule_once(lambda dt: self._on_operation_done(op), 0)

        self._worker_thread = threading.Thread(target=_work, daemon=True)
        self._worker_thread.start()

    def _update_progress(self, total, processed, success, failed, skipped):
        pct = int(processed / total * 100) if total else 0
        self.root.ids.progress_bar.value = pct
        self.root.ids.progress_label.text = (
            f"Processed: {processed}/{total}  ✅ {success}  ❌ {failed}  ⏭ {skipped}"
        )

    def _on_operation_done(self, op):
        self._set_buttons_enabled(True)
        self.refresh_contacts()
        self.root.ids.progress_label.text = (
            f"Done — ✅ {op.success}  ❌ {op.failed}  ⏭ {op.skipped}"
        )

    # ==================================================================
    # Delete
    # ==================================================================
    def delete_created_contacts(self):
        count = self.contact_svc.get_created_count()
        if count == 0:
            self._show_info("No application-created contacts to delete.")
            return
        self._show_confirm(
            f"Delete ALL {count} contacts created by this application?\n\n"
            "This cannot be undone. Your original contacts will NOT be affected.",
            self._do_delete_created,
        )

    def _do_delete_created(self):
        self._set_buttons_enabled(False)

        def _work():
            op = self.contact_svc.delete_created_contacts(
                progress_callback=lambda t, p, s, f, sk: Clock.schedule_once(
                    lambda dt: self._update_progress(t, p, s, f, sk), 0
                ),
            )
            Clock.schedule_once(lambda dt: self._on_operation_done(op), 0)

        self._worker_thread = threading.Thread(target=_work, daemon=True)
        self._worker_thread.start()

    def delete_selected_contacts(self):
        # On mobile, selection is via long-press — simplified: delete all with confirmation
        self.delete_created_contacts()

    # ==================================================================
    # Import / Export
    # ==================================================================
    def import_contacts(self, file_type: str):
        """Import from app's download directory (Android)."""
        from jnius import autoclass  # type: ignore[import-not-found]

        Environment = autoclass("android.os.Environment")
        downloads = Path(str(Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS
        )))

        if file_type == "csv":
            pattern = "*.csv"
            files = sorted(downloads.glob(pattern))
        else:
            pattern = "*.txt"
            files = sorted(downloads.glob(pattern))

        if not files:
            self._show_info(f"No {file_type.upper()} files found in Downloads folder.")
            return

        # Show file picker dialog
        items = []
        for f in files[:20]:  # limit
            items.append(
                OneLineListItem(
                    text=f.name,
                    on_release=lambda x, path=f: self._do_import(path),
                )
            )
        self._import_dialog = MDDialog(
            title=f"Select {file_type.upper()} file",
            type="simple",
            items=items,
            buttons=[MDFlatButton(text="Cancel", on_release=lambda x: self._import_dialog.dismiss())],
        )
        self._import_dialog.open()

    def _do_import(self, path: Path):
        if hasattr(self, "_import_dialog"):
            self._import_dialog.dismiss()

        if path.suffix.lower() == ".csv":
            phones = self.import_svc.import_csv(path)
        else:
            phones = self.import_svc.import_txt(path)

        if phones:
            self._generated_phones = phones
            self._update_preview_list(phones[:100])
            self._show_info(f"Imported {len(phones)} numbers from {path.name}")
        else:
            self._show_info("No valid phone numbers found.")

    def show_export_dialog(self):
        """Export contacts to Downloads."""
        contacts = self.contact_svc.get_all_contacts()
        if not contacts:
            self._show_info("No contacts to export.")
            return

        phones = [c.phone for c in contacts]

        from jnius import autoclass  # type: ignore[import-not-found]

        Environment = autoclass("android.os.Environment")
        downloads = Path(str(Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS
        )))
        ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = downloads / f"contacts_{ts}.txt"
        csv_path = downloads / f"contacts_{ts}.csv"

        items = [
            OneLineListItem(
                text=f"📄 Export as TXT ({len(phones)} contacts)",
                on_release=lambda x: self._do_export(phones, txt_path, "txt"),
            ),
            OneLineListItem(
                text=f"📊 Export as CSV ({len(phones)} contacts)",
                on_release=lambda x: self._do_export(phones, csv_path, "csv"),
            ),
        ]
        self._export_dialog = MDDialog(
            title="Export Contacts",
            type="simple",
            items=items,
            buttons=[MDFlatButton(text="Cancel", on_release=lambda x: self._export_dialog.dismiss())],
        )
        self._export_dialog.open()

    def _do_export(self, phones, path, fmt):
        if hasattr(self, "_export_dialog"):
            self._export_dialog.dismiss()
        if fmt == "csv":
            count = self.export_svc.export_csv(phones, path)
        else:
            count = self.export_svc.export_txt(phones, path)
        if count:
            self._show_info(f"Exported {count} contacts to:\n{path.name}")

    # ==================================================================
    # Refresh contacts
    # ==================================================================
    def refresh_contacts(self):
        contacts = self.contact_svc.get_all_contacts()
        contact_list = self.root.ids.contact_list
        contact_list.clear_widgets()

        total = len(contacts)
        created = self.contact_svc.get_created_count()
        self.root.ids.contacts_title.text = f"👥 Contacts ({total} total, {created} by app)"

        for c in contacts:
            item = TwoLineListItem(
                text=c.phone if c.phone else c.generated_name,
                secondary_text=f"{c.generated_name}  •  {c.source}",
            )
            contact_list.add_widget(item)

    # ==================================================================
    # Helpers
    # ==================================================================
    def _set_buttons_enabled(self, enabled: bool):
        """Enable/disable buttons during operations."""
        # KivyMD doesn't have a simple way to disable all buttons,
        # so we rely on the cancel flag
        pass

    def _on_log_message(self, level_name: str, message: str):
        """Called from logger on every log entry."""
        color_map = {
            "INFO": "#3b82f6",
            "SUCCESS": "#22c55e",
            "WARNING": "#eab308",
            "ERROR": "#ef4444",
        }
        color = color_map.get(level_name, "#CDD6F4")

        def _add():
            log_list = self.root.ids.log_list
            log_list.add_widget(
                OneLineListItem(text=message)
            )
            # Auto-scroll
            scroll = self.root.ids.log_scroll
            scroll.scroll_y = 0

        Clock.schedule_once(lambda dt: _add(), 0)

    def _show_error(self, msg: str):
        dialog = MDDialog(
            title="Error",
            text=msg,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()

    def _show_info(self, msg: str):
        dialog = MDDialog(
            title="Info",
            text=msg,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()

    def _show_confirm(self, msg: str, on_yes):
        def _yes(x):
            dialog.dismiss()
            on_yes()

        dialog = MDDialog(
            title="Confirm",
            text=msg,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(text="Confirm", on_release=_yes),
            ],
        )
        dialog.open()
