"""Unit tests for the Virtual Contact Manager."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Tests for phone normalization
# ---------------------------------------------------------------------------
from app.utils.phone import normalize_phone, validate_phone, format_display


class TestPhoneNormalization(unittest.TestCase):
    """Tests for app.utils.phone"""

    def test_zero_prefixed_local(self) -> None:
        result = normalize_phone("09121111111")
        self.assertEqual(result, "+989121111111")

    def test_plus_98_format(self) -> None:
        result = normalize_phone("+989121111111")
        self.assertEqual(result, "+989121111111")

    def test_double_zero_prefix(self) -> None:
        result = normalize_phone("00989121111111")
        self.assertEqual(result, "+989121111111")

    def test_short_local_number(self) -> None:
        result = normalize_phone("9121111111")
        self.assertEqual(result, "+989121111111")

    def test_with_dashes(self) -> None:
        result = normalize_phone("0912-111-1111")
        self.assertEqual(result, "+989121111111")

    def test_with_spaces(self) -> None:
        result = normalize_phone("0912 111 1111")
        self.assertEqual(result, "+989121111111")

    def test_empty_string(self) -> None:
        self.assertIsNone(normalize_phone(""))

    def test_invalid_short(self) -> None:
        self.assertIsNone(normalize_phone("123"))

    def test_letters_only(self) -> None:
        self.assertIsNone(normalize_phone("abcdefg"))

    def test_validate_valid(self) -> None:
        self.assertTrue(validate_phone("09121111111"))

    def test_validate_invalid(self) -> None:
        self.assertFalse(validate_phone("123"))

    def test_format_display_iranian(self) -> None:
        result = format_display("+989121111111")
        self.assertEqual(result, "+98 912 111 1111")

    def test_format_display_other(self) -> None:
        result = format_display("+12025551234")
        self.assertEqual(result, "+12025551234")


# ---------------------------------------------------------------------------
# Tests for number generation
# ---------------------------------------------------------------------------
from app.services.number_generator import generate_numbers


class TestNumberGeneration(unittest.TestCase):
    """Tests for app.services.number_generator"""

    def test_basic_generation(self) -> None:
        result = generate_numbers("09121111111", 5, step=1)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0], "+989121111111")
        self.assertEqual(result[1], "+989121111112")
        self.assertEqual(result[4], "+989121111115")

    def test_step_generation(self) -> None:
        result = generate_numbers("09121111111", 3, step=2)
        self.assertEqual(result[0], "+989121111111")
        self.assertEqual(result[1], "+989121111113")
        self.assertEqual(result[2], "+989121111115")

    def test_count_one(self) -> None:
        result = generate_numbers("09121111111", 1, step=1)
        self.assertEqual(len(result), 1)

    def test_invalid_start_raises(self) -> None:
        with self.assertRaises(ValueError):
            generate_numbers("123", 10)

    def test_empty_start_raises(self) -> None:
        with self.assertRaises(ValueError):
            generate_numbers("", 10)

    def test_large_count(self) -> None:
        result = generate_numbers("09121111111", 1000, step=1)
        self.assertEqual(len(result), 1000)
        self.assertEqual(result[-1], "+989121112110")


# ---------------------------------------------------------------------------
# Tests for validators
# ---------------------------------------------------------------------------
from app.utils.validators import (
    validate_count,
    validate_name_prefix,
    validate_start_number,
    validate_step,
)


class TestValidators(unittest.TestCase):

    def test_valid_count(self) -> None:
        ok, n, msg = validate_count("100")
        self.assertTrue(ok)
        self.assertEqual(n, 100)

    def test_zero_count(self) -> None:
        ok, n, msg = validate_count("0")
        self.assertFalse(ok)

    def test_negative_count(self) -> None:
        ok, n, msg = validate_count("-5")
        self.assertFalse(ok)

    def test_non_numeric_count(self) -> None:
        ok, n, msg = validate_count("abc")
        self.assertFalse(ok)

    def test_empty_count(self) -> None:
        ok, n, msg = validate_count("")
        self.assertFalse(ok)

    def test_valid_start_number(self) -> None:
        ok, msg = validate_start_number("09121111111")
        self.assertTrue(ok)

    def test_invalid_start_number(self) -> None:
        ok, msg = validate_start_number("123")
        self.assertFalse(ok)

    def test_valid_prefix(self) -> None:
        ok, msg = validate_name_prefix("Channel Member")
        self.assertTrue(ok)

    def test_empty_prefix(self) -> None:
        ok, msg = validate_name_prefix("")
        self.assertTrue(ok)

    def test_long_prefix(self) -> None:
        ok, msg = validate_name_prefix("x" * 200)
        self.assertFalse(ok)

    def test_valid_step(self) -> None:
        ok, n, msg = validate_step("5")
        self.assertTrue(ok)
        self.assertEqual(n, 5)

    def test_zero_step(self) -> None:
        ok, n, msg = validate_step("0")
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# Tests for database persistence & contact tracking
# ---------------------------------------------------------------------------
from app.database.database import Database
from app.database.models import Contact


class TestDatabase(unittest.TestCase):
    """Tests for the SQLite database layer."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.db = Database(Path(self._tmp) / "test.db")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_contact(self, phone: str, name: str = "Test") -> Contact:
        return Contact(phone=phone, generated_name=name)

    def test_insert_and_retrieve(self) -> None:
        c = self._make_contact("+989121111111", "Test 1")
        count = self.db.insert_contacts([c])
        self.assertEqual(count, 1)
        contacts = self.db.get_all_contacts()
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0].phone, "+989121111111")

    def test_phone_exists(self) -> None:
        c = self._make_contact("+989121111111")
        self.db.insert_contacts([c])
        self.assertTrue(self.db.phone_exists("+989121111111"))
        self.assertFalse(self.db.phone_exists("+989999999999"))

    def test_duplicate_insert_ignored(self) -> None:
        c = self._make_contact("+989121111111")
        self.db.insert_contacts([c])
        count = self.db.insert_contacts([c])
        self.assertEqual(count, 0)  # ignored

    def test_soft_delete(self) -> None:
        c = self._make_contact("+989121111111")
        self.db.insert_contacts([c])
        deleted = self.db.delete_contacts_by_ids([c.internal_id])
        self.assertEqual(deleted, 1)
        self.assertEqual(self.db.count_active_contacts(), 0)

    def test_delete_only_created_by_app(self) -> None:
        # App-created contact
        c1 = self._make_contact("+989121111111")
        c1.created_by_app = True
        self.db.insert_contacts([c1])

        # External contact
        c2 = self._make_contact("+989121111112")
        c2.created_by_app = False
        self.db.insert_contacts([c2])

        deleted = self.db.delete_contacts_by_ids([c1.internal_id, c2.internal_id])
        self.assertEqual(deleted, 1)  # only c1 should be deleted
        remaining = self.db.get_all_contacts()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].phone, "+989121111112")

    def test_delete_all_created(self) -> None:
        c1 = self._make_contact("+989121111111")
        c1.created_by_app = True
        c2 = self._make_contact("+989121111112")
        c2.created_by_app = True
        c3 = self._make_contact("+989121111113")
        c3.created_by_app = False
        self.db.insert_contacts([c1, c2, c3])

        deleted = self.db.delete_created_contacts()
        self.assertEqual(deleted, 2)
        remaining = self.db.get_all_contacts()
        self.assertEqual(len(remaining), 1)
        self.assertFalse(remaining[0].created_by_app)

    def test_count_contacts(self) -> None:
        for i in range(5):
            c = self._make_contact(f"+98912111111{i}")
            self.db.insert_contacts([c])
        self.assertEqual(self.db.count_active_contacts(), 5)

    def test_settings(self) -> None:
        self.db.set_setting("theme", "dark")
        self.assertEqual(self.db.get_setting("theme"), "dark")
        self.assertEqual(self.db.get_setting("missing", "default"), "default")


# ---------------------------------------------------------------------------
# Tests for import / export
# ---------------------------------------------------------------------------
from app.services.import_service import ImportService
from app.services.export_service import ExportService


class TestImportExport(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.import_svc = ImportService()
        self.export_svc = ExportService()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_import_txt(self) -> None:
        path = Path(self._tmp) / "phones.txt"
        path.write_text(
            "09121111111\n+989121111112\n0098912111113\n",
            encoding="utf-8",
        )
        result = self.import_svc.import_txt(path)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "+989121111111")
        self.assertEqual(result[1], "+989121111112")
        self.assertEqual(result[2], "+98912111113")

    def test_import_txt_with_invalid(self) -> None:
        path = Path(self._tmp) / "mixed.txt"
        path.write_text(
            "09121111111\nnot_a_number\n09121111113\n",
            encoding="utf-8",
        )
        result = self.import_svc.import_txt(path)
        self.assertEqual(len(result), 2)

    def test_import_txt_empty(self) -> None:
        path = Path(self._tmp) / "empty.txt"
        path.write_text("", encoding="utf-8")
        result = self.import_svc.import_txt(path)
        self.assertEqual(len(result), 0)

    def test_import_csv(self) -> None:
        path = Path(self._tmp) / "phones.csv"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "phone", "extra"])
            writer.writerow(["Alice", "09121111111", "x"])
            writer.writerow(["Bob", "+989121111112", "y"])
        result = self.import_svc.import_csv(path)
        self.assertEqual(len(result), 2)

    def test_export_txt(self) -> None:
        path = Path(self._tmp) / "out.txt"
        count = self.export_svc.export_txt(
            ["+98912111111", "+98912111112"], path
        )
        self.assertEqual(count, 2)
        content = path.read_text(encoding="utf-8")
        self.assertIn("+98912111111", content)

    def test_export_csv(self) -> None:
        path = Path(self._tmp) / "out.csv"
        count = self.export_svc.export_csv(
            ["+98912111111", "+98912111112"], path
        )
        self.assertEqual(count, 2)
        with open(path, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
        self.assertEqual(rows[0], ["phone"])
        self.assertEqual(len(rows), 3)  # header + 2 data rows


# ---------------------------------------------------------------------------
# Tests for contact service (integration)
# ---------------------------------------------------------------------------
from app.services.contact_service import ContactService
from app.utils.logger import Logger


class TestContactService(unittest.TestCase):
    """Integration tests for the contact service."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.db = Database(Path(self._tmp) / "test.db")
        self.svc = ContactService(self.db)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_create_contacts(self) -> None:
        phones = [f"+98912111111{i}" for i in range(10)]
        op = self.svc.create_contacts(phones, name_prefix="Test")
        self.assertEqual(op.success, 10)
        self.assertEqual(self.db.count_active_contacts(), 10)

    def test_create_contacts_skips_duplicates(self) -> None:
        phones = ["+989121111110", "+989121111111"]
        self.svc.create_contacts(phones)
        # Try creating again
        op = self.svc.create_contacts(phones)
        self.assertEqual(op.skipped, 2)

    def test_delete_created_contacts(self) -> None:
        phones = [f"+98912111111{i}" for i in range(5)]
        self.svc.create_contacts(phones)
        self.assertEqual(self.db.count_created_contacts(), 5)

        op = self.svc.delete_created_contacts()
        self.assertEqual(op.success, 5)
        self.assertEqual(self.db.count_active_contacts(), 0)

    def test_delete_preserves_external_contacts(self) -> None:
        # Add app-created contacts
        phones = [f"+98912111111{i}" for i in range(3)]
        self.svc.create_contacts(phones)

        # Add an external contact directly
        ext = Contact(
            phone="+989999999999",
            generated_name="External",
            source="imported",
            created_by_app=False,
        )
        self.db.insert_contacts([ext])

        self.svc.delete_created_contacts()
        remaining = self.db.get_all_contacts()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].phone, "+989999999999")


if __name__ == "__main__":
    unittest.main()
