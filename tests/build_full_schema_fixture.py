#!/usr/bin/env python3
import hashlib
import json
import sqlite3
from pathlib import Path

SCHEMA_VERSION = "system_a_kqxs_archive_schema_v1"
ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures"
DB = FIXTURES / "kqxs_2026_Q2.sqlite"
MANIFEST = FIXTURES / "manifest.json"
CONFLICT_DB = FIXTURES / "conflict_kqxs_2026_Q2.sqlite"
CONFLICT_MANIFEST = FIXTURES / "conflict_manifest.json"

DDL = """
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;
CREATE TABLE archive_schema_version(version INTEGER PRIMARY KEY, name TEXT NOT NULL, generated_at TEXT NOT NULL, ddl_sha256 TEXT NOT NULL);
CREATE TABLE archive_manifest(archive_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL REFERENCES archive_schema_version(version), source_system TEXT NOT NULL, source_label TEXT, export_started_at TEXT, export_completed_at TEXT NOT NULL, min_draw_date TEXT, max_draw_date TEXT, checksum_algorithm TEXT NOT NULL DEFAULT 'sha256', row_counts_json TEXT NOT NULL, checksum_manifest_json TEXT NOT NULL, notes TEXT);
CREATE TABLE archive_checksums(archive_id TEXT NOT NULL REFERENCES archive_manifest(archive_id) ON DELETE CASCADE, artifact TEXT NOT NULL, row_count INTEGER NOT NULL CHECK(row_count >= 0), sha256 TEXT NOT NULL, PRIMARY KEY(archive_id, artifact));
CREATE TABLE regions(code TEXT PRIMARY KEY CHECK(code IN ('MB','MT','MN')), name TEXT NOT NULL);
CREATE TABLE lottery_provinces(code TEXT PRIMARY KEY, region_code TEXT NOT NULL REFERENCES regions(code), name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)));
CREATE TABLE lottery_schedules(province_code TEXT NOT NULL REFERENCES lottery_provinces(code), weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6), draw_time TEXT NOT NULL, region_code TEXT NOT NULL REFERENCES regions(code), PRIMARY KEY(province_code, weekday));
CREATE TABLE prize_specs(region_code TEXT NOT NULL REFERENCES regions(code), prize_code TEXT NOT NULL, expected_count INTEGER NOT NULL CHECK(expected_count > 0), width INTEGER NOT NULL CHECK(width > 0), sort_order INTEGER NOT NULL, PRIMARY KEY(region_code, prize_code));
CREATE TABLE lottery_draws(draw_key TEXT PRIMARY KEY, draw_date TEXT NOT NULL, province_code TEXT NOT NULL REFERENCES lottery_provinces(code), region_code TEXT NOT NULL REFERENCES regions(code), source_system TEXT, source_label TEXT, source_row_ref TEXT, UNIQUE(draw_date, province_code));
CREATE TABLE lottery_results(result_key TEXT PRIMARY KEY, draw_key TEXT NOT NULL REFERENCES lottery_draws(draw_key) ON DELETE CASCADE, prize_code TEXT NOT NULL CHECK(prize_code IN ('DB','G1','G2','G3','G4','G5','G6','G7','G8')), prize_order INTEGER NOT NULL CHECK(prize_order >= 0), result_number TEXT NOT NULL, source_row_ref TEXT, UNIQUE(draw_key, prize_code, prize_order));
CREATE TABLE archive_row_provenance(archive_id TEXT NOT NULL REFERENCES archive_manifest(archive_id) ON DELETE CASCADE, target_table TEXT NOT NULL, target_key TEXT NOT NULL, source_system TEXT, source_label TEXT, source_row_ref TEXT, row_sha256 TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('exported','accepted','rejected')), reason TEXT, PRIMARY KEY(archive_id, target_table, target_key));
CREATE INDEX idx_archive_provinces_region ON lottery_provinces(region_code, code);
CREATE INDEX idx_archive_schedules_weekday ON lottery_schedules(weekday, region_code, province_code);
CREATE INDEX idx_archive_draws_date ON lottery_draws(draw_date, region_code, province_code);
CREATE INDEX idx_archive_results_draw_prize ON lottery_results(draw_key, prize_code, prize_order);
CREATE INDEX idx_archive_provenance_status ON archive_row_provenance(archive_id, status);
"""

MB_SPECS = [("G7",4,2,20),("G6",3,3,30),("G5",6,4,40),("G4",4,4,50),("G3",6,5,60),("G2",2,5,70),("G1",1,5,80),("DB",1,5,90)]

def build():
    FIXTURES.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    connection = sqlite3.connect(DB)
    connection.executescript(DDL)
    ddl_sha = hashlib.sha256(DDL.encode()).hexdigest()
    connection.execute("INSERT INTO archive_schema_version VALUES(1,?,?,?)", (SCHEMA_VERSION, "2026-07-13T00:00:00Z", ddl_sha))
    connection.executemany("INSERT INTO regions VALUES(?,?)", [("MB","Mien Bac"),("MT","Mien Trung"),("MN","Mien Nam")])
    connection.execute("INSERT INTO lottery_provinces VALUES('HN','MB','Ha Noi','ha-noi',1)")
    connection.execute("INSERT INTO lottery_schedules VALUES('HN',1,'18:10:00','MB')")
    connection.executemany("INSERT INTO prize_specs VALUES('MB',?,?,?,?)", MB_SPECS)
    draw_key = "2026-04-06:HN"
    connection.execute("INSERT INTO lottery_draws VALUES(?,?,?,?,?,?,?)", (draw_key,"2026-04-06","HN","MB","synthetic_fixture","c1-public-test","fixture-draw-1"))
    n = 1
    for prize, count, width, _ in MB_SPECS:
        for order in range(count):
            value = str(n).zfill(width)[-width:]
            key = f"{draw_key}:{prize}:{order}"
            connection.execute("INSERT INTO lottery_results VALUES(?,?,?,?,?,?)", (key,draw_key,prize,order,value,f"fixture-result-{n}"))
            n += 1
    connection.execute("INSERT INTO archive_manifest VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", ("kqxs-2026-Q2-v1",1,"synthetic_fixture","c1-public-test",None,"2026-07-13T00:00:00Z","2026-04-06","2026-04-06","sha256",'{"lottery_draws":1,"lottery_results":27}','{}',"Synthetic public workflow fixture"))
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    digest = hashlib.sha256(DB.read_bytes()).hexdigest()
    manifest = {"archive_id":"kqxs-2026-Q2-v1","quarter_id":"2026-Q2","schema_version":SCHEMA_VERSION,"sha256":digest,"sqlite_bytes":DB.stat().st_size,"row_counts":{"lottery_draws":1,"lottery_results":27}}
    MANIFEST.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    CONFLICT_DB.write_bytes(DB.read_bytes())
    conflict = sqlite3.connect(CONFLICT_DB)
    conflict.execute("UPDATE lottery_results SET result_number='99' WHERE result_key='2026-04-06:HN:G7:0'")
    conflict.commit()
    conflict.execute("VACUUM")
    conflict.close()
    conflict_digest = hashlib.sha256(CONFLICT_DB.read_bytes()).hexdigest()
    conflict_manifest = dict(manifest)
    conflict_manifest["sha256"] = conflict_digest
    conflict_manifest["sqlite_bytes"] = CONFLICT_DB.stat().st_size
    CONFLICT_MANIFEST.write_text(json.dumps(conflict_manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")

if __name__ == "__main__":
    build()
