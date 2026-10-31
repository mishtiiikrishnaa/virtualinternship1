"""Landing-zone helpers: read the extract, fingerprint it, profile it.

Nothing here mutates data. That is deliberate — the raw file is treated as
immutable evidence, and every later step derives from it. If a cleaning rule
turns out to be wrong, we re-run from this layer rather than patching a
half-cleaned copy.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path: Path) -> dict[str, object]:
    """Return a provenance record for a landed file.

    A checksum is the cheapest way to answer the question every reviewer asks
    eventually: "is this the same file you analysed?"
    """
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stat = path.stat()
    return {
        "file": path.name,
        "bytes": stat.st_size,
        "sha256": digest,
        "landed_at_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "recorded_at_utc": datetime.now(tz=timezone.utc).isoformat(),
    }


def read_raw(path: Path) -> pd.DataFrame:
    """Read everything as text.

    Deliberately no dtype inference. Numeric inference is where a leading zero
    disappears from a consignment code and a two-decimal price silently becomes
    a float32. Parsing is the cleaning layer's job, where it is logged.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=True, na_values=["", "NA", "N/A", "null", "-"])


def profile(frame: pd.DataFrame) -> dict[str, object]:
    """Cheap, deterministic profile of the landing table."""
    return {
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "null_fraction": {
            col: round(float(frame[col].isna().mean()), 4) for col in frame.columns
        },
        "distinct": {col: int(frame[col].nunique(dropna=True)) for col in frame.columns},
    }


def write_manifest(path: Path, record: dict[str, object], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / f"{path.stem}.manifest.json"
    manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return manifest
