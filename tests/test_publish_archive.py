import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
from publish_archive import SCHEMA_VERSION, publish_local
from build_full_schema_fixture import build, DB, MANIFEST

EXPECTED_TABLES = {"archive_schema_version","archive_manifest","archive_checksums","regions","lottery_provinces","lottery_schedules","prize_specs","lottery_draws","lottery_results","archive_row_provenance"}

class PublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.db = Path(self.temp.name) / "fixture.sqlite"
        self.manifest = Path(self.temp.name) / "manifest.json"
        self.db.write_bytes(DB.read_bytes())
        self.manifest.write_bytes(MANIFEST.read_bytes())
        self.digest = hashlib.sha256(self.db.read_bytes()).hexdigest()

    def tearDown(self): self.temp.cleanup()

    def publish(self, digest=None, quarter="2026-Q2"):
        return publish_local(self.db,self.manifest,self.repo,"kqxs-2026-Q2-v1",quarter,digest or self.digest)

    def test_full_schema_fixture(self):
        con=sqlite3.connect(self.db)
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(EXPECTED_TABLES <= tables)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM lottery_results").fetchone()[0],27)
        con.close()

    def test_success(self): self.assertEqual(self.publish(),"published")
    def test_wrong_hash(self):
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"): self.publish("0"*64)
    def test_corrupt_sqlite(self):
        self.db.write_bytes(b"not sqlite")
        digest=hashlib.sha256(self.db.read_bytes()).hexdigest()
        data=json.loads(self.manifest.read_text()); data["sha256"]=digest; data["sqlite_bytes"]=len(b"not sqlite")
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"invalid or corrupt"): self.publish(digest)
    def test_noncanonical_quarter(self):
        with self.assertRaisesRegex(ValueError,"invalid"): self.publish(quarter="2026Q2")
    def test_extra_manifest_field(self):
        data=json.loads(self.manifest.read_text()); data["generated_at"]="no"
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"canonical V1"): self.publish()
    def test_duplicate_same_pair(self):
        self.assertEqual(self.publish(),"published"); self.assertEqual(self.publish(),"idempotent")
    def test_missing_manifest_conflict(self):
        self.publish(); (self.repo/"archives/2026/Q2/manifest.json").unlink()
        with self.assertRaisesRegex(ValueError,"PUBLIC_CONFLICT"): self.publish()
    def test_manifest_mismatch_conflict(self):
        self.publish(); (self.repo/"archives/2026/Q2/manifest.json").write_text("{}")
        with self.assertRaisesRegex(ValueError,"PUBLIC_CONFLICT"): self.publish()
    def test_duplicate_different_hash(self):
        self.publish(); (self.repo/"archives/2026/Q2/kqxs_2026_Q2.sqlite").write_bytes(b"different")
        with self.assertRaisesRegex(ValueError,"PUBLIC_CONFLICT"): self.publish()

if __name__ == "__main__": unittest.main()
