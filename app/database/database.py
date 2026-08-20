"""SQLite database access layer."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from app.database.models import Contact, Operation


class Database:
    """SQLite wrapper for the application."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path), check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    internal_id   TEXT PRIMARY KEY,
                    phone         TEXT NOT NULL,
                    generated_name TEXT NOT NULL DEFAULT '',
                    created_at    TEXT NOT NULL,
                    source        TEXT NOT NULL DEFAULT 'generated',
                    status        TEXT NOT NULL DEFAULT 'active',
                    created_by_app INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id   TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    total          INTEGER NOT NULL DEFAULT 0,
                    processed      INTEGER NOT NULL DEFAULT 0,
                    success        INTEGER NOT NULL DEFAULT 0,
                    failed         INTEGER NOT NULL DEFAULT 0,
                    skipped        INTEGER NOT NULL DEFAULT 0,
                    status         TEXT NOT NULL DEFAULT 'pending',
                    created_at     TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp  TEXT NOT NULL,
                    level      TEXT NOT NULL,
                    message    TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # Indexes
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_created_by_app ON contacts(created_by_app)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status)"
            )

    # ------------------------------------------------------------------
    # Contacts CRUD
    # ------------------------------------------------------------------
    def insert_contacts(self, contacts: list[Contact]) -> int:
        """Bulk-insert contacts. Returns count of successfully inserted rows."""
        count = 0
        with self._cursor() as cur:
            for c in contacts:
                try:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO contacts
                        (internal_id, phone, generated_name, created_at, source, status, created_by_app)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            c.internal_id,
                            c.phone,
                            c.generated_name,
                            c.created_at,
                            c.source,
                            c.status,
                            int(c.created_by_app),
                        ),
                    )
                    count += cur.rowcount
                except sqlite3.IntegrityError:
                    pass
        return count

    def get_all_contacts(self, active_only: bool = True) -> list[Contact]:
        with self._cursor() as cur:
            if active_only:
                cur.execute(
                    "SELECT * FROM contacts WHERE status='active' ORDER BY created_at"
                )
            else:
                cur.execute("SELECT * FROM contacts ORDER BY created_at")
            return [self._row_to_contact(row) for row in cur.fetchall()]

    def get_created_contacts(self) -> list[Contact]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM contacts WHERE created_by_app=1 AND status='active'"
            )
            return [self._row_to_contact(row) for row in cur.fetchall()]

    def delete_contacts_by_ids(self, internal_ids: list[str]) -> int:
        """Soft-delete contacts by their internal IDs."""
        if not internal_ids:
            return 0
        count = 0
        with self._cursor() as cur:
            # Process in chunks to avoid parameter limits
            chunk_size = 500
            for i in range(0, len(internal_ids), chunk_size):
                chunk = internal_ids[i : i + chunk_size]
                placeholders = ",".join("?" * len(chunk))
                cur.execute(
                    f"UPDATE contacts SET status='deleted' WHERE internal_id IN ({placeholders}) AND created_by_app=1",
                    chunk,
                )
                count += cur.rowcount
        return count

    def delete_created_contacts(self) -> int:
        """Soft-delete all contacts created by the application."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE contacts SET status='deleted' WHERE created_by_app=1 AND status='active'"
            )
            return cur.rowcount

    def count_active_contacts(self) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM contacts WHERE status='active'"
            )
            return cur.fetchone()[0]

    def count_created_contacts(self) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM contacts WHERE created_by_app=1 AND status='active'"
            )
            return cur.fetchone()[0]

    def phone_exists(self, phone: str) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM contacts WHERE phone=? AND status='active'",
                (phone,),
            )
            return cur.fetchone() is not None

    def refresh_contact(self) -> None:
        """Force a refresh of the connection's view."""
        self._get_conn().commit()

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------
    def insert_operation(self, op: Operation) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO operations
                (operation_id, operation_type, total, processed, success, failed, skipped, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    op.operation_id,
                    op.operation_type,
                    op.total,
                    op.processed,
                    op.success,
                    op.failed,
                    op.skipped,
                    op.status,
                    op.created_at,
                ),
            )

    def update_operation(self, op: Operation) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                UPDATE operations SET
                    total=?, processed=?, success=?, failed=?, skipped=?, status=?
                WHERE operation_id=?
                """,
                (
                    op.total,
                    op.processed,
                    op.success,
                    op.failed,
                    op.skipped,
                    op.status,
                    op.operation_id,
                ),
            )

    # ------------------------------------------------------------------
    # Logs (persisted)
    # ------------------------------------------------------------------
    def insert_log(self, level: str, message: str) -> None:
        from datetime import datetime

        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), level, message),
            )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key: str, default: str = "") -> str:
        with self._cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_contact(row: sqlite3.Row) -> Contact:
        return Contact(
            internal_id=row["internal_id"],
            phone=row["phone"],
            generated_name=row["generated_name"],
            created_at=row["created_at"],
            source=row["source"],
            status=row["status"],
            created_by_app=bool(row["created_by_app"]),
        )
