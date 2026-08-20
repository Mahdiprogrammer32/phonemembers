"""Contact management service."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.database.database import Database
from app.database.models import Contact, Operation
from app.utils.logger import Logger


class ContactService:
    def __init__(self, db: Database, logger: Logger | None = None) -> None:
        self.db = db
        self.log = logger or Logger.instance()

    def create_contacts(
        self,
        phones: list[str],
        name_prefix: str = "Channel Member",
        batch_size: int = 50,
        progress_callback=None,
    ) -> Operation:
        op = Operation(operation_type="add", total=len(phones))
        self.db.insert_operation(op)
        self.log.info(f"Starting to create {len(phones)} contacts …")

        for idx, phone in enumerate(phones):
            if self.db.phone_exists(phone):
                op.skipped += 1
                op.processed += 1
                if progress_callback and idx % batch_size == 0:
                    progress_callback(op.total, op.processed, op.success, op.failed, op.skipped)
                continue

            contact = Contact(
                internal_id=str(uuid.uuid4()),
                phone=phone,
                generated_name=f"{name_prefix} {idx + 1:03d}" if name_prefix else "",
                created_at=datetime.now().isoformat(),
                source="generated",
                status="active",
                created_by_app=True,
            )
            count = self.db.insert_contacts([contact])
            op.success += count
            op.failed += 1 - count
            op.processed += 1

            if progress_callback and idx % batch_size == 0:
                progress_callback(op.total, op.processed, op.success, op.failed, op.skipped)

        op.status = "completed"
        self.db.update_operation(op)
        self.log.success(f"Created {op.success}, failed {op.failed}, skipped {op.skipped}")
        return op

    def delete_created_contacts(self, batch_size: int = 50, progress_callback=None) -> Operation:
        created = self.db.get_created_contacts()
        op = Operation(operation_type="delete", total=len(created))
        self.db.insert_operation(op)

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
        if not internal_ids:
            return 0
        deleted = self.db.delete_contacts_by_ids(internal_ids)
        self.log.success(f"Deleted {deleted} selected contact(s).")
        return deleted

    def get_all_contacts(self) -> list[Contact]:
        return self.db.get_all_contacts(active_only=True)

    def get_created_count(self) -> int:
        return self.db.count_created_contacts()

    def get_total_count(self) -> int:
        return self.db.count_active_contacts()
