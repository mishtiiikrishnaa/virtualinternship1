"""Download the public BTS Border Crossing dataset used as Dataset B.

Source : U.S. Bureau of Transportation Statistics / U.S. Customs and Border
         Protection, "Border Crossing Entry Data", dataset id keg4-3bc2.
Licence: Public Domain (Socrata licenceId PUBLIC_DOMAIN).
API    : https://data.transportation.gov/resource/keg4-3bc2.json

Only the truck measure is pulled (the freight-relevant one for a logistics
report). The request is paginated because the SODA 2.1 endpoint returns at
most 50,000 rows per call. The script is idempotent: it rewrites the snapshot
only when the row count changes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.transportation.gov/resource/keg4-3bc2.json"
DATASET_ID = "keg4-3bc2"
DATASET_NAME = "Border Crossing Entry Data"
PAGE = 50_000
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "external"
CSV_PATH = OUT_DIR / "bts_border_trucks.csv.gz"
META_PATH = OUT_DIR / "bts_border_trucks.meta.json"

FIELDS = ["port_name", "state", "port_code", "border", "date", "measure",
          "value", "latitude", "longitude"]


def fetch(measure: str = "Trucks") -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    offset = 0
    while True:
        params = {
            "$select": ",".join(FIELDS),
            "$where": f"measure='{measure}'",
            "$order": "date,port_code",
            "$limit": PAGE,
            "$offset": offset,
        }
        response = requests.get(BASE, params=params, timeout=120)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        frames.append(pd.DataFrame(batch))
        offset += PAGE
        if len(batch) < PAGE:
            break
    frame = pd.concat(frames, ignore_index=True)
    for column in ("value", "latitude", "longitude"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def snapshot_is_current() -> bool:
    """True when the committed gzip exists and still matches its recorded hash."""
    if not (CSV_PATH.exists() and META_PATH.exists()):
        return False
    try:
        meta = json.loads(META_PATH.read_text())
    except json.JSONDecodeError:
        return False
    digest = hashlib.sha256(CSV_PATH.read_bytes()).hexdigest()
    return digest == meta.get("sha256_gz")


def main(force: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not force and snapshot_is_current():
        print(f"snapshot current: {CSV_PATH.relative_to(OUT_DIR.parents[1])} "
              f"({CSV_PATH.stat().st_size} bytes, sha256 verified); "
              "pass --force to refetch")
        return
    frame = fetch()
    frame = frame.sort_values(["date", "port_code"]).reset_index(drop=True)
    frame.to_csv(CSV_PATH, index=False, compression="gzip")

    digest = hashlib.sha256(CSV_PATH.read_bytes()).hexdigest()
    meta = {
        "dataset": DATASET_NAME,
        "dataset_id": DATASET_ID,
        "publisher": "U.S. Bureau of Transportation Statistics (BTS); "
                     "data collected by U.S. Customs and Border Protection (CBP)",
        "landing_page": f"https://data.transportation.gov/d/{DATASET_ID}",
        "api_endpoint": BASE,
        "licence": "Public Domain (Socrata licenceId PUBLIC_DOMAIN)",
        "attribution": "U.S. Department of Homeland Security, Customs and Border Protection",
        "measure_filter": "Trucks",
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "date_min": str(frame["date"].min().date()),
        "date_max": str(frame["date"].max().date()),
        "ports": int(frame["port_code"].nunique()),
        "states": int(frame["state"].nunique()),
        "accessed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256_gz": digest,
        "bytes_gz": CSV_PATH.stat().st_size,
        "retrieved_by": "src/fetch_real_data.py",
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="refetch even when the committed snapshot verifies")
    main(force=parser.parse_args().force)
