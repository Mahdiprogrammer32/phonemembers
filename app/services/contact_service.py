"""Service layer for contact operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.database.database import Database
from app.database.models import Contact, Operation
from app.utils.logger import Logger


class ContactService:
    """High-level contact operations backed by the Database layer."""

    def __init__(self, db: Database, logger: Logger | None = None) -> None:
        self.db = db
        self.log = logger or Logger.instance()

    # ------------------------------------------------------------------
    # Creating
    # ------------------------------------------------------------------
    def create_contacts(
        self,
        phones: list[str],
        name_prefix: str = "Channel Member",
        batch_size: int = 50,
        progress_callback=None,
    ) -> Operation:
        """Create contacts for the given phone list.

        *progress_callback(total, processed, success, failed, skipped)* is
        called after each batch so the GUI can update progress.
        """
        op = Operation(operation_type="add", total=len(phones))
        self.db.insert_operation(op)
        self.log.info(f"Starting to create {len(phones)} contacts …")

        idx = 0
        for phone in phones:
            if self._is_cancelled(op):
                op.status = "cancelled"
                self.db.update_operation(op)
                self.log.warning("Contact creation cancelled by user.")
                return op

            # Skip duplicates
            if self.db.phone_exists(phone):
                op.skipped += 1
                idx += 1
                self._maybe_report(op, progress_callback, batch_size, idx)
                continue

            contact = Contact(
                internal_id=str(uuid.uuid4()),
                phone=phone,
                generated_name=(
                    f"{name_prefix} {idx + 1:03d}" if name_prefix else ""
                ),
                created_at=datetime.now().isoformat(),
                source="generated",
                status="active",
                created_by_app=True,
            )
            count = self.db.insert_contacts([contact])
            if count > 0:
                op.success += 1
            else:
                op.failed += 1
            op.processed += 1
            idx += 1
            self._maybe_report(op, progress_callback, batch_size, idx)

        op.status = "completed"
        self.db.update_operation(op)
        self.log.success(
            f"Contact creation finished: {op.success} created, "
            f"{op.failed} failed, {op.skipped} skipped."
        )
        return op

    # ------------------------------------------------------------------
    # Deleting
    # ------------------------------------------------------------------
    def delete_created_contacts(self, batch_size: int = 50, progress_callback=None) -> Operation:
        """Soft-delete all contacts that were created by this application."""
        created = self.db.get_created_contacts()
        op = Operation(operation_type="delete", total=len(created))
        self.db.insert_operation(op)
        self.log.info(f"Deleting {len(created)} application-created contacts …")

        ids = [c.internal_id for c in created]
        deleted = self.db.delete_contacts_by_ids(ids)
        op.processed = len(ids)
        op.success = deleted
        op.skipped = len(ids) - deleted
        op.status = "completed"
        self.db.update_operation(op)
        self.log.success(f"Deleted {deleted} contacts.")
        return op

    def delete_selected_contacts(self, internal_ids: list[str]) -> int:
        """Soft-delete specific contacts (only created-by-app ones are removed)."""
        if not internal_ids:
            return 0
        deleted = self.db.delete_contacts_by_ids(internal_ids)
        self.log.success(f"Deleted {deleted} selected contact(s).")
        return deleted

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def get_all_contacts(self) -> list[Contact]:
        return self.db.get_all_contacts(active_only=True)

    def get_created_count(self) -> int:
        return self.db.count_created_contacts()

    def get_total_count(self) -> int:
        return self.db.count_active_contacts()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_cancelled(op: Operation) -> bool:
        return op.status == "cancelled"

    def _maybe_report(
        self,
        op: Operation,
        progress_callback,
        batch_size: int,
        idx: int,
    ) -> None:
        if progress_callback and idx % batch_size == 0:
            progress_callback(op.total, op.processed, op.success, op.failed, op.skipped)
