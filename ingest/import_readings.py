"""Hourly AMR import: SFTP -> Supabase.

Run by .github/workflows/hourly-import.yml every hour. Can also be run
locally:  python -m ingest.import_readings

Required environment variables:
    SFTP_HOST, SFTP_PORT (default 22), SFTP_USERNAME, SFTP_PASSWORD
    SFTP_DIR              directory on the SFTP server holding the .csv exports
    SUPABASE_URL          https://<project>.supabase.co
    SUPABASE_SERVICE_KEY  service_role key (Settings > API) — never the anon key
Optional:
    SFTP_FILE_PATTERN     glob-style pattern, default "*.csv"
    SFTP_LOOKBACK_FILES   only consider the N most recent files, default 200

Behaviour:
    * Syncs the meter register from data/Summer_Ridge_Master_Sheet.xlsx into
      the `meters` table (so the DB always mirrors the Excel in the repo).
    * Lists CSV files on the SFTP server, skips any already in `import_log`.
    * Parses each new file and upserts rows into `readings`. The unique
      constraint on (meter_serial, reading_ts) makes this idempotent — a meter
      that has not produced a new reading since the last export is skipped.
    * Values are stored raw: gas in litres, elec in kWh. Unit conversion
      (litres -> m3) happens in the app, never in the database.
"""
from __future__ import annotations

import fnmatch
import io
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import paramiko
from supabase import create_client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.master import load_master  # noqa: E402

BATCH = 500


def clean(records: list[dict]) -> list[dict]:
    """Make records JSON-safe: NaN/NaT/inf -> None, numpy types -> python."""
    out = []
    for rec in records:
        fixed = {}
        for k, v in rec.items():
            if v is None:
                fixed[k] = None
            elif isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
                fixed[k] = None
            elif hasattr(v, "item"):  # numpy scalar
                v = v.item()
                fixed[k] = None if (isinstance(v, float) and v != v) else v
            elif pd.isna(v):
                fixed[k] = None
            else:
                fixed[k] = v
        out.append(fixed)
    return out


def env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        print(f"ERROR: missing required environment variable {name}")
        sys.exit(1)
    return val


# ---------------------------------------------------------------- parsing
# READING_DATE:  '10/07/2026 10:25:00 GMT+2'  (dd/mm/yyyy)
# CURRENT_DATE:  '2026-07-10 11:50:01 GMT+2'  (yyyy-mm-dd)
TS_DMY = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*(?:GMT([+-]\d{1,2}))?\s*$")
TS_YMD = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})\s*(?:GMT([+-]\d{1,2}))?\s*$")


def parse_ts(raw: str) -> datetime | None:
    """Parse a CSV timestamp (either format above) to an aware datetime."""
    if not isinstance(raw, str):
        return None
    m = TS_DMY.match(raw)
    if m:
        d, mo, y, h, mi, s, off = m.groups()
    else:
        m = TS_YMD.match(raw)
        if not m:
            return None
        y, mo, d, h, mi, s, off = m.groups()
    tz = timezone(timedelta(hours=int(off))) if off else timezone.utc
    try:
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), tzinfo=tz)
    except ValueError:
        return None


def parse_csv(content: bytes, file_name: str) -> tuple[list[dict], int]:
    df = pd.read_csv(io.BytesIO(content), dtype=str)
    df.columns = [c.strip().upper() for c in df.columns]
    rows: list[dict] = []
    for _, r in df.iterrows():
        serial = str(r.get("METER_ADDRESS", "")).strip()
        ts = parse_ts(r.get("READING_DATE", ""))
        try:
            value = float(r.get("READING_VALUE"))
            if pd.isna(value):
                value = None
        except (TypeError, ValueError):
            value = None
        if not serial or ts is None or value is None:
            continue

        def num(col: str):
            v = r.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            v = str(v).strip()
            if v in ("", "nan", "None"):
                return None
            try:
                return float(v)
            except ValueError:
                return None

        rows.append(
            {
                "meter_serial": serial,
                "reading_ts": ts.isoformat(),
                "reading_value": value,
                "peak": num("PEAK"),
                "std": num("STD"),
                "offpeak": num("OFFPEAK"),
                "md": num("MD"),
                "low_battery": str(r.get("LOW_BATTERY", "0")).strip() in ("1", "true", "True"),
                "exported_at": (parse_ts(r.get("CURRENT_DATE", "")) or datetime.now(timezone.utc)).isoformat(),
                "source_file": file_name,
            }
        )
    return rows, len(df)


# ---------------------------------------------------------------- main
def main() -> None:
    sb = create_client(env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY"))

    # 1. Sync meter register from the repo's master sheet
    print("[stage] syncing meter register from master sheet ...")
    master = load_master()
    meter_rows = clean(
        master.assign(updated_at=datetime.now(timezone.utc).isoformat()).to_dict("records")
    )
    for i in range(0, len(meter_rows), BATCH):
        sb.table("meters").upsert(meter_rows[i : i + BATCH], on_conflict="serial").execute()
    print(f"Synced {len(meter_rows)} meters from master sheet.")

    # 2. Connect to SFTP and list candidate files
    host = env("SFTP_HOST")
    port = int(env("SFTP_PORT", "22"))
    pattern = env("SFTP_FILE_PATTERN", "*.csv")
    lookback = int(env("SFTP_LOOKBACK_FILES", "200"))
    sftp_dir = env("SFTP_DIR")

    transport = paramiko.Transport((host, port))
    print(f"[stage] connecting to SFTP {host}:{port} ...")
    transport.connect(username=env("SFTP_USERNAME"), password=env("SFTP_PASSWORD"))
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.chdir(sftp_dir)

    entries = [e for e in sftp.listdir_attr() if fnmatch.fnmatch(e.filename, pattern)]
    entries.sort(key=lambda e: e.st_mtime or 0, reverse=True)
    entries = entries[:lookback]
    print(f"Found {len(entries)} file(s) matching {pattern} in {sftp_dir}.")

    processed = {
        row["file_name"]
        for row in (sb.table("import_log").select("file_name").execute().data or [])
    }
    new_files = [e.filename for e in entries if e.filename not in processed]
    print(f"{len(new_files)} new file(s) to import.")

    for fname in sorted(new_files):
        try:
            print(f"[stage] importing {fname} ...")
            with sftp.open(fname, "rb") as fh:
                content = fh.read()
            rows, rows_in_file = parse_csv(content, fname)
            rows = clean(rows)

            inserted = 0
            for i in range(0, len(rows), BATCH):
                chunk = rows[i : i + BATCH]
                sb.table("readings").upsert(
                    chunk, on_conflict="meter_serial,reading_ts", ignore_duplicates=True
                ).execute()
                inserted += len(chunk)

            sb.table("import_log").upsert(
                {
                    "file_name": fname,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "rows_in_file": rows_in_file,
                    "rows_inserted": inserted,
                    "rows_skipped": rows_in_file - len(rows),
                    "status": "ok",
                },
                on_conflict="file_name",
            ).execute()
            print(f"  {fname}: {inserted} rows upserted ({rows_in_file} in file).")
        except Exception as exc:  # log and continue with the next file
            sb.table("import_log").upsert(
                {
                    "file_name": fname,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error_detail": str(exc)[:500],
                },
                on_conflict="file_name",
            ).execute()
            print(f"  {fname}: FAILED — {exc}")

    sftp.close()
    transport.close()
    print("Import complete.")


if __name__ == "__main__":
    main()