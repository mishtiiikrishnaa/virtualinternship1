"""Clean and preprocess the simulated shipment extract.

Every step is counted and written to ``results/cleaning.json`` so the report's
before/after table is generated from the run rather than typed by hand.

Order matters: duplicates and unparseable dates are removed first because they
corrupt every downstream count; labels and units are standardised next so that
grouping keys are consistent; missing values are handled after that so that
imputation can use the corrected categories.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "simulated" / "shipments_raw.csv"
OUT = ROOT / "data" / "processed" / "shipments_clean.csv"
RESULTS = ROOT / "results"

MODE_MAP = {
    "road": "Road", "road ": "Road", "road": "Road",
    "rail": "Rail", "rail ": "Rail",
    "air": "Air", "air freight": "Air", "air ": "Air",
    "sea": "Sea", "sea ": "Sea", "ocean": "Sea",
}
CARRIER_ALIASES = {"": "Unassigned", "unknown": "Unassigned", "n/a": "Unassigned",
                   "na": "Unassigned", "nan": "Unassigned"}
LB_PER_KG = 2.20462


def parse_dates(series: pd.Series, formats: list[str]) -> tuple[pd.Series, int]:
    """Parse a column that contains more than one date format.

    Formats are tried in order of specificity, so an ambiguous string such as
    05/02/2025 is only read as day-first when the ISO attempt has already
    failed. Strings that match no format become NaT and are counted.
    """
    out = pd.to_datetime(series, format=formats[0], errors="coerce")
    for fmt in formats[1:]:
        todo = out.isna() & series.notna()
        if not todo.any():
            break
        out.loc[todo] = pd.to_datetime(series.loc[todo], format=fmt, errors="coerce")
    failed = int((out.isna() & series.notna()).sum())
    return out, failed


def standardise_labels(frame: pd.DataFrame, log: dict) -> pd.DataFrame:
    raw_mode = frame["mode"].copy()
    frame["mode"] = (frame["mode"].astype("string").str.strip().str.lower()
                     .map(MODE_MAP))
    log["mode_labels_rewritten"] = int((frame["mode"] != raw_mode).sum())

    frame["carrier"] = (frame["carrier"].astype("string").str.strip().str.lower()
                        .replace(CARRIER_ALIASES))
    frame["carrier"] = frame["carrier"].str.title()
    frame.loc[frame["carrier"].isin(["Nan", "None", "<Na>"]), "carrier"] = "Unassigned"

    frame["priority"] = frame["priority"].astype("string").str.strip().str.title()
    frame["priority"] = frame["priority"].fillna("Unspecified")
    frame["status"] = frame["status"].astype("string").str.strip()
    return frame


def normalise_units(frame: pd.DataFrame, log: dict) -> pd.DataFrame:
    lb = frame["weight_unit"].astype("string").str.lower().isin(["lb", "lbs"])
    frame.loc[lb, "weight_kg"] = frame.loc[lb, "weight_kg"] / LB_PER_KG
    log["weight_rows_converted_from_lb"] = int(lb.sum())

    litre = frame["volume_unit"].astype("string").str.lower().isin(["l", "litre", "liter"])
    frame.loc[litre, "volume_m3"] = frame.loc[litre, "volume_m3"] / 1000.0
    log["volume_rows_converted_from_litres"] = int(litre.sum())

    frame["weight_unit"] = "kg"
    frame["volume_unit"] = "m3"
    return frame


def add_derived(frame: pd.DataFrame) -> pd.DataFrame:
    frame["transit_days"] = (frame["delivery_date"] - frame["ship_date"]).dt.days
    frame["delay_days"] = frame["transit_days"] - frame["promised_days"]
    eligible = frame["status"].isin(["Delivered", "Delayed"])
    frame["on_time"] = np.where(eligible, (frame["delay_days"] <= 0), np.nan)
    frame["on_time"] = pd.to_numeric(frame["on_time"], errors="coerce")
    frame["cost_per_kg"] = frame["freight_cost_usd"] / frame["weight_kg"]
    frame["cost_per_km"] = frame["freight_cost_usd"] / frame["distance_km"]
    frame["speed_km_per_day"] = frame["distance_km"] / frame["transit_days"]
    frame["month"] = frame["order_date"].dt.to_period("M").astype(str)
    frame["month_start"] = frame["order_date"].dt.to_period("M").dt.to_timestamp()
    frame["quarter"] = frame["order_date"].dt.quarter
    frame["year"] = frame["order_date"].dt.year
    frame["weekday"] = frame["order_date"].dt.day_name()
    frame["week"] = frame["order_date"].dt.isocalendar().week.astype(int)
    frame["is_q4"] = frame["quarter"].eq(4)
    frame["lane_type"] = np.where(
        frame["origin"].isin(["Chicago", "Dallas", "Atlanta"]), "Domestic", "International")
    return frame


def main() -> None:
    raw = pd.read_csv(RAW, dtype={"promised_days": "float"})
    log: dict = {"rows_raw": int(len(raw)), "cols_raw": int(raw.shape[1])}
    steps = [{"step": "0. Raw extract", "rows_in": len(raw), "rows_out": len(raw),
              "removed": 0, "detail": "18 columns, mixed formats and units"}]

    # --- 1. exact duplicates -------------------------------------------------
    before = len(raw)
    frame = raw.drop_duplicates(keep="first").copy()
    log["duplicates_removed"] = before - len(frame)
    steps.append({"step": "1. Remove exact duplicate rows", "rows_in": before,
                  "rows_out": len(frame), "removed": before - len(frame),
                  "detail": "same shipment_id exported twice"})

    # --- 2. dates ------------------------------------------------------------
    before = len(frame)
    frame["order_date"], f1 = parse_dates(frame["order_date"], ["%Y-%m-%d", "%Y/%m/%d"])
    frame["ship_date"], f2 = parse_dates(frame["ship_date"], ["%Y-%m-%d", "%d/%m/%Y"])
    frame["delivery_date"], f3 = parse_dates(frame["delivery_date"], ["%Y-%m-%d"])
    log["unparseable_date_strings"] = f1 + f2 + f3
    # a delivered shipment with no readable delivery date cannot be scored
    undated_delivery = frame["delivery_date"].isna() & frame["status"].isin(
        ["Delivered", "Delayed"])
    frame = frame.loc[~(frame["order_date"].isna() | frame["ship_date"].isna() |
                        undated_delivery)].copy()
    log["rows_dropped_unparseable"] = before - len(frame)
    steps.append({"step": "2. Parse dates, drop unreadable rows", "rows_in": before,
                  "rows_out": len(frame), "removed": before - len(frame),
                  "detail": f"{f1 + f2 + f3} strings matched no accepted format"})

    # --- 3. impossible values ------------------------------------------------
    voided = {}
    for column in ["weight_kg", "volume_m3", "distance_km",
                   "freight_cost_usd", "promised_days"]:
        bad = frame[column] <= 0
        voided[column] = int(bad.sum())
        frame.loc[bad, column] = np.nan
    log["impossible_values_set_missing"] = int(sum(voided.values()))
    log["impossible_values_detail"] = voided
    steps.append({"step": "3. Void impossible values", "rows_in": len(frame),
                  "rows_out": len(frame), "removed": 0,
                  "detail": "negative weights, zero distance, negative cost set to missing"})

    # --- 4. labels and units -------------------------------------------------
    frame = standardise_labels(frame, log)
    frame = normalise_units(frame, log)
    steps.append({"step": "4. Standardise labels and units", "rows_in": len(frame),
                  "rows_out": len(frame), "removed": 0,
                  "detail": f"{log['mode_labels_rewritten']} mode labels; "
                            f"{log['weight_rows_converted_from_lb']} lb rows"})

    # --- 5. recover destination from lane -----------------------------------
    missing_dest = frame["destination"].isna()
    recovered = frame.loc[missing_dest, "lane"].str.split(" -> ").str[-1]
    frame.loc[missing_dest, "destination"] = recovered
    log["destination_recovered_from_lane"] = int(missing_dest.sum() - frame["destination"].isna().sum())

    # --- 6. missing values ---------------------------------------------------
    miss_before = frame.isna().mean().round(4).to_dict()
    log["missing_share_before"] = round(float(frame.isna().sum().sum() /
                                              frame.size), 4)
    weight_by_mode = frame.groupby("mode")["weight_kg"].median()
    volume_by_mode = frame.groupby("mode")["volume_m3"].median()
    promise_by_mode = frame.groupby("mode")["promised_days"].median()

    frame["weight_imputed"] = frame["weight_kg"].isna()
    frame["cost_missing"] = frame["freight_cost_usd"].isna()
    frame["weight_kg"] = frame["weight_kg"].fillna(
        frame["mode"].map(weight_by_mode)).round(2)
    frame["volume_m3"] = frame["volume_m3"].fillna(
        frame["mode"].map(volume_by_mode)).round(3)
    log["promised_imputed_rows"] = int(frame["promised_days"].isna().sum())
    frame["promised_days"] = frame["promised_days"].fillna(
        frame["mode"].map(promise_by_mode)).round(0)
    log["weight_imputed_rows"] = int(frame["weight_imputed"].sum())
    log["volume_imputed_rows"] = int(round(miss_before.get("volume_m3", 0) * len(frame)))
    frame["priority"] = frame["priority"].fillna("Unspecified")
    frame["carrier"] = frame["carrier"].fillna("Unassigned")
    log["freight_cost_left_missing_rows"] = int(frame["cost_missing"].sum())
    log["on_time_eligible_rows"] = int(
        frame["status"].isin(["Delivered", "Delayed"]).sum())

    # in-transit and cancelled shipments carry no delivery date by definition
    frame.loc[~frame["status"].isin(["Delivered", "Delayed"]), "delivery_date"] = pd.NaT
    steps.append({"step": "5-6. Impute where defensible", "rows_in": len(frame),
                  "rows_out": len(frame), "removed": 0,
                  "detail": "weight/volume/promise by mode median; cost kept missing"})

    # --- 7. derived features -------------------------------------------------
    frame = add_derived(frame)

    # --- 8. outliers: flag, do not delete -----------------------------------
    q1, q3 = frame["freight_cost_usd"].quantile([0.25, 0.75])
    iqr = q3 - q1
    frame["outlier_cost_iqr"] = frame["freight_cost_usd"].gt(q3 + 1.5 * iqr)
    log["cost_outliers_flagged"] = int(frame["outlier_cost_iqr"].sum())
    log["rows_clean"] = int(len(frame))
    log["cols_clean"] = int(frame.shape[1])
    log["missing_share_after"] = round(float(
        frame.drop(columns=["delivery_date", "on_time", "transit_days",
                            "delay_days", "cost_per_kg", "cost_per_km",
                            "speed_km_per_day"]).isna().sum().sum() /
        frame.drop(columns=["delivery_date", "on_time", "transit_days",
                            "delay_days", "cost_per_kg", "cost_per_km",
                            "speed_km_per_day"]).size), 4)
    log["missing_by_column"] = {
        column: {"count": int(frame[column].isna().sum()),
                 "share": round(float(frame[column].isna().mean()), 4)}
        for column in frame.columns
    }
    log["steps"] = steps
    log["date_min"] = str(frame["order_date"].min().date())
    log["date_max"] = str(frame["order_date"].max().date())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT, index=False)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    log["output_sha256"] = digest
    log["output_bytes"] = OUT.stat().st_size
    (RESULTS / "cleaning.json").write_text(json.dumps(log, indent=2, default=float) + "\n")

    print(json.dumps({k: v for k, v in log.items()
                      if k not in ("missing_by_column", "steps")}, indent=2))
    print(pd.DataFrame(steps).to_string(index=False))


if __name__ == "__main__":
    main()
