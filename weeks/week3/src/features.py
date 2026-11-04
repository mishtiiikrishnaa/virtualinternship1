"""Feature engineering for the week 3 predictive models.

Two modelling targets share one cleaned extract:

* forecasting  -> daily shipment volume (regression, time series)
* classification -> whether an individual shipment is late (binary)

Every derived column is built from information available at or before the
shipment's ship_date. Columns that are *consequences* of the outcome
(delay_days, transit_days, delivery_date, anything computed from them) are
explicitly banned and never enter a feature matrix. The leakage test in
tests/ asserts this by name.

The city-to-city great-circle distance is computed once from the week 1 city
centroid table. It is a static property of the lane, so it carries no
future information.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Columns that describe the future or are consequences of the target. None of
# these may ever appear in a feature matrix. The leakage test enumerates them.
LEAKAGE_COLUMNS = [
    "delivery_date",
    "transit_days",
    "delay_days",
    "is_late",
]

# City centroids (lat, lon) reused from the week 1 source register. These are
# representative coordinates, not GPS telemetry; distance is therefore a lane
# property, not a shipment observation, and cannot leak the outcome.
CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "Abu Dhabi": (24.4539, 54.3773),
    "Amsterdam": (52.3676, 4.9041),
    "Bremen": (53.0793, 8.8017),
    "Chennai": (13.0827, 80.2707),
    "Chicago": (41.8781, -87.6298),
    "Dallas": (32.7767, -96.7970),
    "Delhi": (28.6139, 77.2090),
    "Dubai": (25.2048, 55.2708),
    "Felixstowe": (51.9612, 1.3522),
    "Frankfurt": (50.1109, 8.6821),
    "Guangzhou": (23.1291, 113.2644),
    "Hamburg": (53.5511, 9.9937),
    "Jebel Ali": (25.0393, 55.1177),
    "Jurong": (1.3052, 103.7041),
    "Long Beach": (33.7701, -118.1937),
    "London": (51.5074, -0.1278),
    "Manchester": (53.4808, -2.2374),
    "Mumbai": (19.0760, 72.8777),
    "Munich": (48.1351, 11.5820),
    "Newark": (40.7357, -74.1724),
    "Nhava Sheva": (18.9389, 72.9417),
    "Ningbo": (29.8683, 121.5440),
    "Rotterdam": (51.9244, 4.4777),
    "Savannah": (32.0809, -81.0912),
    "Shanghai": (31.2304, 121.4737),
    "Shenzhen": (22.5431, 114.0579),
    "Singapore": (1.3521, 103.8198),
    "Southampton": (50.9043, -1.4043),
    "Tilburg": (51.5555, 5.0913),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points on Earth, in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class FeatureSpec:
    """What each model needs, documented so the report can quote it."""

    id_cols: list[str]
    feature_cols: list[str]
    target_col: str
    date_col: str
    description: str


def load_clean() -> pd.DataFrame:
    """Load the week 1 cleaned extract and parse its date columns."""
    path = ROOT / "data" / "processed" / "shipments_clean.csv"
    frame = pd.read_csv(path, parse_dates=["order_date", "ship_date", "delivery_date"])
    return frame


def add_calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Calendar attributes of the ship_date only — nothing after it."""
    out = frame.copy()
    out["ship_dow"] = out["ship_date"].dt.dayofweek  # Monday = 0
    out["ship_month"] = out["ship_date"].dt.month
    out["is_weekend"] = (out["ship_dow"] >= 5).astype(int)
    out["order_to_ship_days"] = (out["ship_date"] - out["order_date"]).dt.days
    return out


def add_route_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Static lane attributes: distance, cross-border flag, mode.

    Distance is great-circle km between city centroids. Unknown cities fall
    back to the network median distance rather than being dropped.
    """
    out = frame.copy()

    def origin_latlon(city: str) -> tuple[float, float]:
        return CITY_CENTROIDS.get(city, (np.nan, np.nan))

    def dest_latlon(city: str) -> tuple[float, float]:
        return CITY_CENTROIDS.get(city, (np.nan, np.nan))

    o = out["origin_city"].map(origin_latlon).apply(pd.Series)
    d = out["dest_city"].map(dest_latlon).apply(pd.Series)
    o.columns = ["o_lat", "o_lon"]
    d.columns = ["d_lat", "d_lon"]
    geo = pd.concat([o, d], axis=1)

    dist = [
        _haversine_km(a, b, c, d_) if pd.notna(a) and pd.notna(c) else np.nan
        for a, b, c, d_ in zip(geo["o_lat"], geo["o_lon"], geo["d_lat"], geo["d_lon"])
    ]
    median_dist = float(np.nanmedian(dist))
    out["distance_km"] = pd.Series(dist, index=out.index).fillna(median_dist)

    out["cross_border"] = (out["origin_country"] != out["dest_country"]).astype(int)
    out["same_city"] = (out["origin_city"] == out["dest_city"]).astype(int)
    return out


def add_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Trailing daily aggregates for the forecast model.

    All lags and rolling windows end at t-1, so they never use the value being
    predicted. Shipments are counted per ship_date; dates with no activity are
    filled with zero before rolling.
    """
    daily = (
        frame.groupby(frame["ship_date"].dt.date)
        .size()
        .rename("daily_volume")
        .reset_index()
    )
    daily["ship_date"] = pd.to_datetime(daily["ship_date"])
    daily = daily.sort_values("ship_date").set_index("ship_date")
    full = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full, fill_value=0)

    # Strictly trailing: shift before rolling, so row t only sees up to t-1.
    daily["lag_1"] = daily["daily_volume"].shift(1)
    daily["lag_7"] = daily["daily_volume"].shift(7)
    daily["rolling_7_mean"] = daily["daily_volume"].shift(1).rolling(7, min_periods=1).mean()
    daily["rolling_14_mean"] = daily["daily_volume"].shift(1).rolling(14, min_periods=1).mean()
    daily["rolling_28_mean"] = daily["daily_volume"].shift(1).rolling(28, min_periods=1).mean()

    daily["dow"] = daily.index.dayofweek
    daily["month"] = daily.index.month
    daily["is_weekend"] = (daily["dow"] >= 5).astype(int)

    out = frame.copy()
    out["ship_date_only"] = out["ship_date"].dt.date
    daily2 = daily.reset_index()
    daily2["ship_date_only"] = daily2["ship_date"].dt.date
    out = out.merge(
        daily2[["ship_date_only", "lag_1", "lag_7", "rolling_7_mean",
                "rolling_14_mean", "rolling_28_mean", "dow", "month", "is_weekend"]],
        on="ship_date_only",
        how="left",
    )
    out = out.drop(columns=["ship_date_only"])
    return out, daily


def make_forecast_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to daily level and attach trailing features for forecasting."""
    daily = frame.groupby(frame["ship_date"].dt.date).agg(
        daily_volume=("shipment_id", "size"),
    ).reset_index()
    daily["ship_date"] = pd.to_datetime(daily["ship_date"])
    daily = daily.sort_values("ship_date").set_index("ship_date")
    full = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full, fill_value=0)

    daily["lag_1"] = daily["daily_volume"].shift(1)
    daily["lag_7"] = daily["daily_volume"].shift(7)
    daily["rolling_7_mean"] = daily["daily_volume"].shift(1).rolling(7, min_periods=1).mean()
    daily["rolling_14_mean"] = daily["daily_volume"].shift(1).rolling(14, min_periods=1).mean()
    daily["rolling_28_mean"] = daily["daily_volume"].shift(1).rolling(28, min_periods=1).mean()
    daily["dow"] = daily.index.dayofweek
    daily["month"] = daily.index.month
    daily["is_weekend"] = (daily["dow"] >= 5).astype(int)

    # leading indicators available before the forecast window: month-level
    # mode mix computed up to t-1
    mode_share = (
        frame.groupby([frame["ship_date"].dt.date, "mode"])
        .size()
        .unstack(fill_value=0)
    )
    mode_share.index = pd.to_datetime(mode_share.index)
    mode_share = mode_share.reindex(full, fill_value=0)
    mode_total = mode_share.sum(axis=1).replace(0, np.nan)
    for col in mode_share.columns:
        daily[f"mode_share_{col}"] = (mode_share[col] / mode_total).shift(1)

    daily = daily.reset_index().rename(columns={"index": "ship_date"})
    return daily


def make_classification_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-shipment feature matrix for the late-delivery classifier.

    All features are known at booking or ship time: calendar, route, mode,
    carrier, category, weight, quantity, cost. delay_days/transit_days are
    never used.
    """
    out = add_calendar_features(frame)
    out = add_route_features(out)
    out["weight_kg"] = out["weight_kg"].fillna(out["weight_kg"].median())
    out["freight_cost_usd"] = out["freight_cost_usd"].fillna(0.0)
    out["cost_imputed_flag"] = out["cost_imputed"].astype(int)
    out["weight_imputed_flag"] = out["weight_imputed"].astype(int)
    return out


def train_validation_test_split(
    daily: pd.DataFrame, val_days: int = 42, test_days: int = 28
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Time-ordered split for the forecast table. No shuffling, no overlap."""
    daily = daily.sort_values("ship_date").reset_index(drop=True)
    n = len(daily)
    test_start = n - test_days
    val_start = test_start - val_days
    train = daily.iloc[:val_start].copy()
    val = daily.iloc[val_start:test_start].copy()
    test = daily.iloc[test_start:].copy()
    return train, val, test


def classification_time_split(
    frame: pd.DataFrame, test_fraction: float = 0.2, val_fraction: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Time-ordered split for the classifier, with hard date boundaries so that
    no ship_date appears in more than one split (no train/test overlap)."""
    out = frame.sort_values("ship_date").reset_index(drop=True)
    counts_by_date = out.groupby("ship_date").size().sort_index()
    cumulative = counts_by_date.cumsum()
    n = len(out)
    val_target = int(n * (1 - test_fraction - val_fraction))
    test_target = int(n * (1 - test_fraction))

    val_boundary = next(
        (d for d, c in cumulative.items() if c >= val_target), counts_by_date.index[0]
    )
    test_boundary = next(
        (d for d, c in cumulative.items() if c >= test_target), counts_by_date.index[-1]
    )

    # cut at the date just before each boundary to avoid overlap
    val_start_date = val_boundary
    test_start_date = test_boundary
    if val_boundary == counts_by_date.index[0]:
        val_start_date = counts_by_date.index[min(1, len(counts_by_date) - 1)]
    # ensure strict separation: if boundaries collapse, push test to the next date
    distinct = list(counts_by_date.index)
    if distinct.index(test_boundary) <= distinct.index(val_boundary):
        test_boundary = distinct[min(distinct.index(val_boundary) + 1, len(distinct) - 1)]

    val_start_date = val_boundary
    test_start_date = test_boundary

    train = out[out["ship_date"] < val_start_date].copy()
    val = out[(out["ship_date"] >= val_start_date) & (out["ship_date"] < test_start_date)].copy()
    test = out[out["ship_date"] >= test_start_date].copy()
    return train, val, test


def forecast_feature_columns() -> list[str]:
    return [
        "lag_1", "lag_7", "rolling_7_mean", "rolling_14_mean",
        "rolling_28_mean", "dow", "month", "is_weekend",
    ] + [f"mode_share_{m}" for m in ("Air", "Ocean", "Road", "Rail")]


def classification_feature_columns() -> list[str]:
    return [
        "ship_dow", "ship_month", "is_weekend", "order_to_ship_days",
        "distance_km", "cross_border", "same_city",
        "weight_kg", "quantity", "freight_cost_usd",
        "cost_imputed_flag", "weight_imputed_flag",
    ] + [f"mode_{m}" for m in ("Air", "Ocean", "Road", "Rail")] \
        + [f"cat_{c}" for c in (
            "Electronics", "Apparel", "Pharmaceuticals",
            "Automotive Parts", "Consumer Goods", "Industrial Equipment",
            "Perishables",
        )]


def encode_classification(frame: pd.DataFrame, fit: pd.DataFrame | None = None) -> pd.DataFrame:
    """One-hot encode mode and category, aligned to a reference frame if given.
    Leakage columns (consequences of the outcome) are dropped first."""
    out = frame.copy()
    for col in LEAKAGE_COLUMNS:
        if col != "is_late" and col in out.columns:
            out = out.drop(columns=[col])
    cats = ["mode", "product_category"]
    if all(c in out.columns for c in cats):
        encoded = pd.get_dummies(out[cats], prefix=["mode", "cat"], dtype=int)
        out = pd.concat([out.drop(columns=cats), encoded], axis=1)

    if fit is not None:
        ref = encode_classification(fit)
        for col in ref.columns:
            if col not in out.columns:
                out[col] = 0
        out = out[[c for c in ref.columns if c in out.columns]]
    return out


def save_leakage_review(path: Path) -> None:
    """Document the banned columns so the review is reviewable, not verbal."""
    lines = [
        "# Leakage review — week 3",
        "",
        "The following columns are consequences of the outcome or describe the "
        "future relative to ship_date. They are banned from every feature "
        "matrix, in both models:",
        "",
    ]
    for col in LEAKAGE_COLUMNS:
        lines.append(f"- `{col}` — {_leakage_reason(col)}")
    lines += [
        "",
        "Lag and rolling features in the forecast model end at t-1: row t never "
        "sees its own value. The test in `tests/test_features.py` asserts that "
        "no leakage column appears in either feature list, and that the "
        "forecast split has no train/test date overlap.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _leakage_reason(col: str) -> str:
    reasons = {
        "delivery_date": "the outcome itself: when the shipment arrived",
        "transit_days": "derived from delivery_date minus ship_date",
        "delay_days": "derived from transit_days against the per-mode promise",
        "is_late": "derived from delay_days; the classification target",
    }
    return reasons.get(col, "future or outcome information")


def write_feature_manifest(path: Path, daily: pd.DataFrame, classified: pd.DataFrame) -> None:
    manifest = {
        "forecast_rows": int(len(daily)),
        "forecast_date_min": str(daily["ship_date"].min()),
        "forecast_date_max": str(daily["ship_date"].max()),
        "classification_rows": int(len(classified)),
        "late_count": int(classified["is_late"].sum()),
        "late_rate": float(classified["is_late"].mean()),
        "leakage_columns_banned": LEAKAGE_COLUMNS,
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
