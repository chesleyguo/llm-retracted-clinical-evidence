"""Step 01: download the Retraction Watch database (distributed by Crossref).

Saves the CSV to data/raw/retraction_watch_<YYYY-MM-DD>.csv and appends one
provenance record (URL, time, size, SHA-256, row count) to
results/01_download_log.jsonl.

Raw data is never modified: if a snapshot already exists, the script stops
without downloading. Pass --new to take an additional, newer snapshot.

Usage:
    python scripts/01_download_retraction_watch.py [--new]
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
LOG_PATH = ROOT / "results" / "01_download_log.jsonl"

# Crossref asks for a contact email as the query string.
URL_TEMPLATE = "https://api.labs.crossref.org/data/retractionwatch?{email}"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path):
    # Use the csv module rather than counting lines: quoted fields may contain
    # line breaks, so lines != records.
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", action="store_true",
                        help="download a new snapshot even if one exists")
    args = parser.parse_args()

    existing = sorted(RAW_DIR.glob("retraction_watch_*.csv"))
    if existing and not args.new:
        print("Snapshot already exists, skipping download:")
        for p in existing:
            print(f"  {p.relative_to(ROOT)}")
        print("Run with --new to take an additional snapshot.")
        return

    load_dotenv(ROOT / ".env")
    email = os.getenv("CONTACT_EMAIL")
    if not email:
        sys.exit("CONTACT_EMAIL is not set in .env")

    now = datetime.now(timezone.utc)
    out_path = RAW_DIR / f"retraction_watch_{now:%Y-%m-%d}.csv"
    if out_path.exists():
        sys.exit(f"{out_path.relative_to(ROOT)} already exists; not overwriting.")

    # Download to a temporary .part file and rename only when complete, so an
    # interrupted download never leaves a partial file that looks finished.
    part_path = out_path.with_suffix(".csv.part")
    print(f"Downloading to {out_path.relative_to(ROOT)} ...")
    with requests.get(URL_TEMPLATE.format(email=email), stream=True, timeout=120) as r:
        r.raise_for_status()
        last_modified = r.headers.get("Last-Modified")
        with open(part_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    part_path.rename(out_path)

    record = {
        "file": str(out_path.relative_to(ROOT)),
        # The email is masked so the committed log does not contain it.
        "url": URL_TEMPLATE.format(email="<CONTACT_EMAIL>"),
        "downloaded_at_utc": now.isoformat(timespec="seconds"),
        "server_last_modified": last_modified,
        "size_bytes": out_path.stat().st_size,
        "sha256": sha256_of(out_path),
        "n_records": count_rows(out_path),
    }
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    for k, v in record.items():
        print(f"  {k}: {v}")
    print(f"Logged to {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
