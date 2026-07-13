#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SCHEMA_VERSION = "system_a_kqxs_archive_schema_v1"
QUARTER_RE = re.compile(r"^(?P<year>20\d{2})-Q(?P<quarter>[1-4])$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")
MANIFEST_KEYS = {"archive_id", "quarter_id", "schema_version", "sha256", "sqlite_bytes", "row_counts"}
ROW_COUNT_KEYS = {"lottery_draws", "lottery_results"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("download_url and manifest_url must be credential-free HTTPS URLs")


def download(url, target):
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "c1-quarter-archive-publisher/1"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as output:
        if response.status != 200:
            raise ValueError(f"download failed with HTTP {response.status}")
        shutil.copyfileobj(response, output)


def manifest_counts(manifest):
    counts = manifest.get("row_counts")
    if not isinstance(counts, dict) or set(counts) != ROW_COUNT_KEYS:
        raise ValueError("manifest row_counts must contain exactly lottery_draws and lottery_results")
    draws, results = counts["lottery_draws"], counts["lottery_results"]
    if not isinstance(draws, int) or not isinstance(results, int) or draws < 0 or results < 0:
        raise ValueError("manifest must contain non-negative draw and result row counts")
    return draws, results


def inspect_sqlite(path):
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if quick != "ok" or integrity != "ok":
            raise ValueError("SQLite integrity check failed")
        version_row = connection.execute(
            "SELECT version, name FROM archive_schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if not version_row or version_row[1] != SCHEMA_VERSION:
            raise ValueError("SQLite schema version mismatch")
        draws = connection.execute("SELECT COUNT(*) FROM lottery_draws").fetchone()[0]
        results = connection.execute("SELECT COUNT(*) FROM lottery_results").fetchone()[0]
        return draws, results
    except sqlite3.DatabaseError as error:
        raise ValueError("invalid or corrupt SQLite archive") from error
    finally:
        if "connection" in locals():
            connection.close()


def publish_local(sqlite_path, manifest_path, repo, archive_id, quarter_id, expected_sha):
    match = QUARTER_RE.fullmatch(quarter_id)
    if not match or not ID_RE.fullmatch(archive_id) or not SHA_RE.fullmatch(expected_sha):
        raise ValueError("invalid archive_id, quarter_id, or sha256")
    expected_sha = expected_sha.lower()
    actual_sha = sha256(sqlite_path)
    if actual_sha != expected_sha:
        raise ValueError("SQLite SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise ValueError("manifest must contain exactly the canonical V1 fields")
    if manifest.get("archive_id") != archive_id or manifest.get("quarter_id") != quarter_id:
        raise ValueError("manifest identity mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("manifest schema version mismatch")
    manifest_sha = manifest.get("sha256")
    if not isinstance(manifest_sha, str) or not SHA_RE.fullmatch(manifest_sha) or manifest_sha != expected_sha:
        raise ValueError("manifest SHA-256 mismatch")
    byte_size = manifest.get("sqlite_bytes")
    if not isinstance(byte_size, int) or byte_size < 1 or byte_size != sqlite_path.stat().st_size:
        raise ValueError("manifest byte size mismatch")
    expected_counts = manifest_counts(manifest)
    if inspect_sqlite(sqlite_path) != expected_counts:
        raise ValueError("manifest row counts do not match SQLite")
    year, quarter = match.group("year"), match.group("quarter")
    destination = repo / "archives" / year / f"Q{quarter}"
    archive_target = destination / f"kqxs_{year}_Q{quarter}.sqlite"
    manifest_target = destination / "manifest.json"
    canonical_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    archive_exists, manifest_exists = archive_target.exists(), manifest_target.exists()
    if archive_exists or manifest_exists:
        if not archive_exists or not manifest_exists:
            raise ValueError("PUBLIC_CONFLICT: archive pair is incomplete")
        if sha256(archive_target) != expected_sha or manifest_target.read_bytes() != canonical_bytes:
            raise ValueError("PUBLIC_CONFLICT: existing archive pair does not match")
        return "idempotent"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sqlite_path, archive_target)
    manifest_target.write_bytes(canonical_bytes)
    return "published"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    import os
    values = {name: os.environ.get(name, "") for name in
              ("ARCHIVE_ID", "QUARTER_ID", "DOWNLOAD_URL", "MANIFEST_URL", "EXPECTED_SHA256")}
    if not all(values.values()):
        raise SystemExit("missing required repository_dispatch payload field")
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        sqlite_path, manifest_path = temp / "archive.sqlite", temp / "manifest.json"
        download(values["DOWNLOAD_URL"], sqlite_path)
        download(values["MANIFEST_URL"], manifest_path)
        print(publish_local(sqlite_path, manifest_path, args.repo.resolve(),
                            values["ARCHIVE_ID"], values["QUARTER_ID"], values["EXPECTED_SHA256"]))


if __name__ == "__main__":
    main()
