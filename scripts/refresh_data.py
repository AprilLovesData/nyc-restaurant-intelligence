"""Refresh the whole pipeline from NYC Open Data through to Supabase.

Nothing in this project updates itself. The city republishes its inspection records
daily; everything downstream is a fixed copy until someone re-runs the chain. Doing
that by hand means four separate manual steps in the right order, which is exactly
the kind of thing that gets done wrong at 11pm three months from now.

    python3 scripts/refresh_data.py                 # download, rebuild, upload
    python3 scripts/refresh_data.py --skip-download # rebuild from the file on disk
    python3 scripts/refresh_data.py --dry-run       # show the plan, change nothing

The cleaning logic is NOT reimplemented here. This script re-executes notebooks 01
and 04, so the notebooks stay the single definition of how the data is cleaned and
modelled. If the two ever disagreed, the numbers in the report and the numbers in
the dashboard would quietly drift apart.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

import pandas as pd
import requests

PROJ = Path(__file__).resolve().parent.parent
RAW = PROJ / "data" / "raw"
PROCESSED = PROJ / "data" / "processed"
SECRETS = PROJ / ".streamlit" / "secrets.toml"

# NYC Open Data dataset identifiers. See data/raw/README.md.
SOURCES = {
    "DOHMH_New_York_City_Restaurant_Inspection_Results": "43nn-pn8j",
    "Borough_Boundaries": "gthc-hcne",
}

NOTEBOOKS = [
    "notebooks/01_data_quality_check.ipynb",   # audit + clean  -> data/cleaned/
    "notebooks/04_database_schema.ipynb",      # normalise      -> data/processed/
]

# Parents first: a child row is rejected while the row it points at is missing.
# Deleting runs in reverse for the same reason.
LOAD_ORDER = [
    ("neighborhoods", "nta_code"),
    ("violation_codes", "violation_id"),
    ("restaurants", "camis"),
    ("inspections", "inspection_id"),
    ("violations", "violation_row_id"),
]

BATCH = 2000


def log(step: str, message: str) -> None:
    print(f"[{step}] {message}", flush=True)


# --------------------------------------------------------------------- secrets


def read_secrets() -> dict:
    if not SECRETS.exists():
        sys.exit(f"Missing {SECRETS}. Copy secrets.toml.example and fill it in.")
    with SECRETS.open("rb") as handle:
        return tomllib.load(handle)


def supabase_config(secrets: dict) -> tuple[str, str]:
    """Return the project URL and a key that is allowed to write.

    The dashboard uses the anon key, which row level security restricts to reading.
    Writing needs the service role key, which bypasses those policies entirely —
    fine in a local admin script that never leaves this machine, catastrophic in
    anything that ships to a browser.
    """
    config = secrets.get("supabase", {})
    url = config.get("url", "").rstrip("/")
    key = config.get("service_key")
    if not url:
        sys.exit("secrets.toml is missing supabase.url")
    if not key:
        sys.exit(
            "secrets.toml is missing supabase.service_key.\n\n"
            "Add it under [supabase]:\n"
            '    service_key = "<the service_role key>"\n\n'
            "Find it in the Supabase dashboard under Project Settings -> API.\n"
            "It bypasses row level security, so it belongs only in this file — "
            "never in the deployed app's secrets."
        )
    return url, key


# -------------------------------------------------------------------- download


def download(dry_run: bool) -> None:
    stamp = date.today().strftime("%Y%m%d")
    RAW.mkdir(parents=True, exist_ok=True)

    for name, dataset_id in SOURCES.items():
        target = RAW / f"{name}_{stamp}.csv"
        url = (
            f"https://data.cityofnewyork.us/api/views/{dataset_id}/rows.csv"
            "?accessType=DOWNLOAD"
        )
        if dry_run:
            log("download", f"would fetch {dataset_id} -> {target.name}")
            continue
        if target.exists():
            log("download", f"{target.name} already exists, keeping it")
            continue

        log("download", f"fetching {dataset_id} (this is the slow part)…")
        with requests.get(url, stream=True, timeout=600) as response:
            response.raise_for_status()
            written = 0
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    handle.write(chunk)
                    written += len(chunk)
                    print(f"\r  {written / 1024**2:,.0f} MB", end="", flush=True)
        print()
        log("download", f"saved {target.name} ({target.stat().st_size / 1024**2:,.0f} MB)")


# --------------------------------------------------------------------- rebuild


def rebuild(dry_run: bool) -> None:
    for notebook in NOTEBOOKS:
        if dry_run:
            log("rebuild", f"would execute {notebook}")
            continue
        log("rebuild", f"executing {notebook} …")
        result = subprocess.run(
            [
                "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                "--ExecutePreprocessor.timeout=1800", notebook,
            ],
            cwd=PROJ, capture_output=True, text=True,
        )
        if result.returncode != 0:
            # The notebooks assert their own correctness, so a failure here means a
            # validation caught something — worth reading rather than retrying.
            print(result.stderr[-3000:], file=sys.stderr)
            sys.exit(f"{notebook} failed. Its assertions are the first place to look.")
        log("rebuild", f"{notebook} passed")


# ---------------------------------------------------------------------- upload


def upload(dry_run: bool) -> None:
    secrets = read_secrets()
    url, key = supabase_config(secrets)
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    tables = {}
    for table, _ in LOAD_ORDER:
        path = PROCESSED / f"{table}.csv"
        if not path.exists():
            sys.exit(f"Missing {path}. Run the rebuild step first.")
        tables[table] = pd.read_csv(path)

    log("upload", "row counts to load: "
        + ", ".join(f"{t}={len(df):,}" for t, df in tables.items()))
    if dry_run:
        log("upload", "would clear all five tables and re-insert the above")
        return

    # Clear children before parents, or the foreign keys refuse the delete.
    for table, primary_key in reversed(LOAD_ORDER):
        response = requests.delete(
            f"{url}/rest/v1/{table}",
            headers=headers,
            params={primary_key: "not.is.null"},
            timeout=180,
        )
        response.raise_for_status()
        log("upload", f"cleared {table}")

    for table, _ in LOAD_ORDER:
        frame = tables[table].where(pd.notna(tables[table]), None)
        rows = frame.to_dict("records")
        for start in range(0, len(rows), BATCH):
            chunk = rows[start:start + BATCH]
            response = requests.post(
                f"{url}/rest/v1/{table}",
                headers={**headers, "Prefer": "return=minimal"},
                json=chunk,
                timeout=180,
            )
            if not response.ok:
                sys.exit(f"{table} rejected rows {start}-{start + len(chunk)}: "
                         f"{response.text[:400]}")
            print(f"\r  {table}: {min(start + BATCH, len(rows)):,} / {len(rows):,}",
                  end="", flush=True)
        print()
        log("upload", f"loaded {table} ({len(rows):,} rows)")


# --------------------------------------------------------------------- verify


def verify() -> None:
    secrets = read_secrets()
    url, key = supabase_config(secrets)
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    print()
    log("verify", "comparing local files against the database")
    mismatch = False
    for table, _ in LOAD_ORDER:
        local = len(pd.read_csv(PROCESSED / f"{table}.csv"))
        response = requests.get(
            f"{url}/rest/v1/{table}",
            headers={**headers, "Prefer": "count=exact", "Range": "0-0"},
            timeout=60,
        )
        response.raise_for_status()
        remote = int(response.headers["content-range"].split("/")[-1])
        ok = local == remote
        mismatch |= not ok
        print(f"  {'OK ' if ok else 'BAD'} {table:18} local {local:>7,}  db {remote:>7,}")
    if mismatch:
        sys.exit("Row counts disagree — the load did not finish cleanly.")
    log("verify", "every table matches")


# ------------------------------------------------------------------------ main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-download", action="store_true",
                        help="reuse the source file already in data/raw/")
    parser.add_argument("--skip-rebuild", action="store_true",
                        help="reuse the tables already in data/processed/")
    parser.add_argument("--skip-upload", action="store_true",
                        help="rebuild locally without touching Supabase")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and change nothing")
    args = parser.parse_args()

    if not args.skip_download:
        download(args.dry_run)
    if not args.skip_rebuild:
        rebuild(args.dry_run)
    if not args.skip_upload:
        upload(args.dry_run)
        if not args.dry_run:
            verify()

    print()
    if args.dry_run:
        log("done", "dry run only — nothing was changed")
    else:
        log("done", "pipeline refreshed. Update SNAPSHOT_DATE in streamlit_app.py "
                    "so the dashboard states the right date.")


if __name__ == "__main__":
    main()
