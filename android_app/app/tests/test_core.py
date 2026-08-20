"""Unit tests for the Virtual Contact Manager — Android edition."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from app.utils.phone import normalize_phone, validate_phone, format_display
from app.services.number_generator import generate_numbers
from app.utils.validators import (
    validate_count,
    validate_name_prefix,
    validate_start_number,
    validate_step,
)
from app.database.database import Database
from app.database.models import Contact
from app.services.contact_service import ContactService
from app.services.import_service import ImportService
from app.services.export_service import ExportService


# ======================================================================
# Phone normalization
# ======================================================================
class TestPhoneNormalization(unittest.TestCase):
    def test_zero_prefixed_local(self):
        self.assertEqual(normalize_phone("09121111111"), "+989121111111")

    def test_plus_98_format(self):
        self.assertEqual(normalize_phone("+989121111111"), "+989121111111")

    def test_double_zero_prefix(self):
        self.assertEqual(normalize_phone("00989121111111"), "+989121111111")

    def test_short_local_number(self):
        self.assertEqual(normalize_phone("9121111111"), "+989121111111")

    def test_with_dashes(self):
        self.assertEqual(normalize_phone("0912-111-1111"), "+989121111111")

    def test_with_spaces(self):
        self.assertEqual(normalize_phone("0912 111 1111"), "+989121111111")

    def test_empty_string(self):
        self.assertIsNone(normalize_phone(""))

    def test_invalid_short(self):
        self.assertIsNone(normalize_phone("123"))

    def test_validate_valid(self):
        self.assertTrue(validate_phone("09121111111"))

    def test_validate_invalid(self):
        self.assertFalse(validate_phone("123"))

    def test_format_display_iranian(self):
        self.assertEqual(format_display("+989121111111"), "+98 912 111 1111")


# ======================================================================
# Number generation
# ======================================================================
class TestNumberGeneration(unittest.TestCase):
    def test_basic(self):
        result = generate_numbers("09121111111", 5, step=1)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0], "+989121111111")
        self.assertEqual(result[4], "+989121111115")

    def test_step(self):
        result = generate_numbers("09121111111", 3, step=2)
        self.assertEqual(result, ["+989121111111", "+989121111113", "+989121111115"])

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            generate_numbers("123", 10)


# ======================================================================
# Validators
# ======================================================================
class TestValidators(unittest.TestCase):
    def test_valid_count(self):
        ok, n, _ = validate_count("100")
        self.assertTrue(ok and n == 100)

    def test_zero_count(self):
        ok, _, _ = validate_count("0")
        self.assertFalse(ok)

    def test_valid_start(self):
        ok, _ = validate_start_number("09121111111")
        self.assertTrue(ok)

    def test_invalid_start(self):
        ok, _ = validate_start_number("123")
        self.assertFalse(ok)

    def test_valid_step(self):
        ok, n, _ = validate_step("5")
        self.assertTrue(ok and n == 5)

    def test_empty_prefix(self):
        ok, _ = validate_name_prefix("")
        self.assertTrue(ok)


# ======================================================================
# Database
# ======================================================================
class TestDatabase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.db = Database(Path(self._tmp) / "test.db")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _contact(self, phone, name="Test"):
        return Contact(phone=phone, generated_name=name)

    def test_insert_and_retrieve(self):
        c = self._contact("+989121111111")
        self.db.insert_contacts([c])
        self.assertEqual(len(self.db.get_all_contacts()), 1)

    def test_duplicate_ignored(self):
        c = self._contact("+989121111111")
        self.assertEqual(self.db.insert_contacts([c]), 1)
        self.assertEqual(self.db.insert_contacts([c]), 0)

    def test_phone_exists(self):
        self.db.insert_contacts([self._contact("+989121111111")])
        self.assertTrue(self.db.phone_exists("+989121111111"))
        self.assertFalse(self.db.phone_exists("+989999999999"))

    def test_soft_delete(self):
        c = self._contact("+989121111111")
        self.db.insert_contacts([c])
        self.db.delete_contacts_by_ids([c.internal_id])
        self.assertEqual(self.db.count_active_contacts(), 0)

    def test_delete_only_created_by_app(self):
        c1 = self._contact("+989121111111")
        c1.created_by_app = True
        c2 = self._contact("+989121111112")
        c2.created_by_app = False
        self.db.insert_contacts([c1, c2])
        deleted = self.db.delete_contacts_by_ids([c1.internal_id, c2.internal_id])
        self.assertEqual(deleted, 1)
        self.assertEqual(len(self.db.get_all_contacts()), 1)

    def test_delete_all_created(self):
        c1 = self._contact("+989121111111")
        c1.created_by_app = True
        c2 = self._contact("+989121111112")
        c2.created_by_app = True
        c3 = self._contact("+989121111113")
        c3.created_by_app = False
        self.db.insert_contacts([c1, c2, c3])
        deleted = self.db.delete_created_contacts()
        self.assertEqual(deleted, 2)
        self.assertEqual(len(self.db.get_all_contacts()), 1)


# ======================================================================
# Import / Export
# ======================================================================
class TestImportExport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.import_svc = ImportService()
        self.export_svc = ExportService()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_import_txt(self):
        path = Path(self._tmp) / "phones.txt"
        path.write_text("09121111111\n+989121111112\n", encoding="utf-8")
        result = self.import_svc.import_txt(path)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "+989121111111")

    def test_import_csv(self):
        path = Path(self._tmp) / "phones.csv"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "phone"])
            writer.writerow(["Alice", "09121111111"])
        result = self.import_svc.import_csv(path)
        self.assertEqual(len(result), 1)

    def test_export_txt(self):
        path = Path(self._tmp) / "out.txt"
        count = self.export_svc.export_txt(["+98912111111"], path)
        self.assertEqual(count, 1)
        self.assertIn("+98912111111", path.read_text())

    def test_export_csv(self):
        path = Path(self._tmp) / "out.csv"
        count = self.export_svc.export_csv(["+98912111111"], path)
        self.assertEqual(count, 1)


# ======================================================================
# Contact service integration
# ======================================================================
class TestContactService(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.db = Database(Path(self._tmp) / "test.db")
        self.svc = ContactService(self.db)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_create_contacts(self):
        phones = [f"+98912111111{i}" for i in range(10)]
        op = self.svc.create_contacts(phones, name_prefix="Test")
        self.assertEqual(op.success, 10)
        self.assertEqual(self.db.count_active_contacts(), 10)

    def test_skips_duplicates(self):
        phones = ["+989121111110", "+989121111111"]
        self.svc.create_contacts(phones)
        op = self.svc.create_contacts(phones)
        self.assertEqual(op.skipped, 2)

    def test_delete_created(self):
        phones = [f"+98912111111{i}" for i in range(5)]
        self.svc.create_contacts(phones)
        op = self.svc.delete_created_contacts()
        self.assertEqual(op.success, 5)
        self.assertEqual(self.db.count_active_contacts(), 0)

    def test_delete_preserves_external(self):
        phones = [f"+98912111111{i}" for i in range(3)]
        self.svc.create_contacts(phones)
        ext = Contact(phone="+989999999999", source="imported", created_by_app=False)
        self.db.insert_contacts([ext])
        self.svc.delete_created_contacts()
        remaining = self.db.get_all_contacts()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].phone, "+989999999999")


if __name__ == "__main__":
    unittest.main()
