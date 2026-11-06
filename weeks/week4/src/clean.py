"""Cleaning audit for week 4.

Week 4 re-runs the week 1 cleaning implementation (the authoritative version,
unchanged) over the week 1 raw extract, so that the before/after numbers in the
week 4 report come from the same code that produced the week 1 quality report,
and not from a second, drifted copy. The week 1 modules are loaded by file path
and are otherwise untouched.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
WEEK1_SRC = REPO_ROOT / "weeks" / "week1" / "src"


def _load(name: str):
    path = WEEK1_SRC / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"week1_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"week1_{name}"] = module
    spec.loader.exec_module(module)
    return module


week1_clean = _load("clean")
week1_ingest = _load("ingest")
week1_validate = _load("validate")


def load_week1_raw():
    return week1_ingest.read_raw(
        REPO_ROOT / "weeks" / "week1" / "data" / "raw" / "shipments_raw.csv"
    )


def load_week1_cleaned_frame() -> pd.DataFrame:
    """Run the week 1 cleaning implementation over the week 1 raw extract."""
    raw = load_week1_raw()
    cleaned, log = week1_clean.clean(raw)
    return cleaned


def cleaning_audit() -> dict:
    raw = load_week1_raw()
    cleaned, log = week1_clean.clean(raw)
    checks = week1_validate.run_checks(cleaned)
    summary = week1_validate.summarise(checks)

    before_missing = raw.isna().sum().sum() / max(raw.size, 1)
    after_cols = [c for c in cleaned.columns if c not in
                  ("delivery_date", "on_time", "transit_days", "delay_days",
                   "cost_per_kg", "cost_per_km", "speed_km_per_day")]
    after_missing = cleaned[after_cols].isna().sum().sum() / max(cleaned[after_cols].size, 1)

    return {
        "source_raw_file": "weeks/week1/data/raw/shipments_raw.csv",
        "rows_before_cleaning": int(len(raw)),
        "rows_published": int(len(cleaned)),
        "columns_before": int(raw.shape[1]),
        "columns_published": int(cleaned.shape[1]),
        "cleaning_log": [s for s in log.steps],
        "validation": {
            "total_checks": int(summary["total"]),
            "failed_checks": int(summary["failed"]),
            "critical_failures": int(summary["critical_failures"]),
            "checks": [c.as_dict() for c in checks],
        },
        "missing_share_before_cleaning": float(before_missing),
        "missing_share_after_cleaning": float(after_missing),
        "headline": {
            "median_weight_kg": float(cleaned["weight_kg"].median()),
            "median_freight_cost_usd": float(cleaned["freight_cost_usd"].median()),
            "median_transit_days": float(cleaned["transit_days"].median()),
            "late_share": float((cleaned["delay_days"].fillna(0) > 0).mean()),
            "weight_imputed_share": float(cleaned["weight_imputed"].mean()),
            "cost_imputed_share": float(cleaned["cost_imputed"].mean()),
        },
    }
