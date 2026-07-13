# Quarterly KQXS SQLite archives

This public repository contains completed historical KQXS data, one immutable SQLite file per quarter. Archives use schema `system_a_kqxs_archive_schema_v1` and preserve result numbers as text.

## Layout

`archives/YYYY/QN/kqxs_YYYY_QN.sqlite` and `archives/YYYY/QN/manifest.json`

Example download and verification:

```sh
curl -LO https://raw.githubusercontent.com/itgi8vn/quarterly-kqxs-archives/main/archives/2026/Q2/kqxs_2026_Q2.sqlite
curl -LO https://raw.githubusercontent.com/itgi8vn/quarterly-kqxs-archives/main/archives/2026/Q2/manifest.json
sha256sum kqxs_2026_Q2.sqlite
python -c "import json; print(json.load(open('manifest.json'))['sha256'])"
sqlite3 kqxs_2026_Q2.sqlite 'PRAGMA quick_check; PRAGMA integrity_check;'
```

The computed checksum must equal the manifest `sha256`. Consumers should also confirm `schema_version`, row counts, and SQLite integrity before use. Published quarter paths are immutable: retrying the same checksum succeeds; a different checksum is rejected.
