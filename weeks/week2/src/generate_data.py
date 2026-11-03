"""Generate a seeded, representative simulation of shipment-level logistics data.

The simulation is the primary dataset for the week 2 EDA. It is built with a
fixed seed so every run reproduces the same file, and it deliberately embeds
ten effects that the analysis is expected to recover. Those effects are
recorded in ``results/planted_effects.json`` so that section 6.10 can compare
"what was planted" with "what the EDA found" instead of asserting quality.

Nothing here is presented as real-world data. Every table and figure that uses
it is labelled "simulated".
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_SIM = ROOT / "data" / "simulated"
RESULTS = ROOT / "results"

SEED = 42
N_SHIPMENTS = 50_000
START = "2024-01-01"
END = "2025-12-31"

# name: (latitude, longitude, country)
HUBS = {
    "Shanghai": (31.2304, 121.4737, "CN"),
    "Shenzhen": (22.5431, 114.0579, "CN"),
    "Ningbo": (29.8683, 121.5440, "CN"),
    "Busan": (35.1796, 129.0756, "KR"),
    "Singapore": (1.3521, 103.8198, "SG"),
    "Mumbai": (19.0760, 72.8777, "IN"),
    "Chennai": (13.0827, 80.2707, "IN"),
    "Rotterdam": (51.9244, 4.4777, "NL"),
    "Hamburg": (53.5511, 9.9937, "DE"),
    "Los Angeles": (34.0522, -118.2437, "US"),
    "Long Beach": (33.7701, -118.1937, "US"),
    "Chicago": (41.8781, -87.6298, "US"),
    "Dallas": (32.7767, -96.7970, "US"),
    "Atlanta": (33.7490, -84.3880, "US"),
    "Memphis": (35.1495, -90.0490, "US"),
    "New York": (40.7128, -74.0060, "US"),
    "Seattle": (47.6062, -122.3321, "US"),
    "Miami": (25.7617, -80.1918, "US"),
    "Columbus": (39.9612, -82.9988, "US"),
}
ORIGINS = ["Shanghai", "Shenzhen", "Ningbo", "Busan", "Singapore", "Mumbai",
           "Chennai", "Rotterdam", "Hamburg", "Chicago", "Dallas", "Atlanta"]
DESTINATIONS = ["Los Angeles", "Long Beach", "Chicago", "Dallas", "Atlanta",
                "Memphis", "New York", "Seattle", "Miami", "Columbus"]

# carrier: (served modes, share within mode, on-time penalty in days)
CARRIERS = {
    "Atlas Freight": (["Road", "Rail"], 1.6, 0.00),
    "Beacon Logistics": (["Road", "Air"], 1.5, 0.05),
    "Cobalt Lines": (["Sea", "Road"], 1.2, 1.55),      # planted weak carrier
    "Dunmore Cargo": (["Road", "Rail"], 1.1, 0.10),
    "Eastwind Shipping": (["Sea"], 1.4, 0.00),
    "Falcon Air Cargo": (["Air"], 1.5, -0.10),
    "Granite Haulage": (["Road"], 1.3, 0.15),
    "Harborlink": (["Sea", "Road"], 1.0, 0.20),
    "Ironline Rail": (["Rail"], 1.6, 0.05),
    "Jetstream Express": (["Air"], 1.6, -0.05),
    "Keystone Freight": (["Road", "Rail"], 1.2, 0.10),
    "Northwind Cargo": (["Road", "Air", "Sea"], 0.9, 2.20),  # planted weak carrier
}
BAD_CARRIERS = {"Northwind Cargo": 2.20, "Cobalt Lines": 2.10}

MODE_BASE_DAYS = {"Air": 0.9, "Road": 4.4, "Rail": 8.2, "Sea": 17.5}
MODE_SIGMA = {"Air": 0.34, "Road": 0.30, "Rail": 0.24, "Sea": 0.26}
MODE_DIST_SLOPE = {"Air": 0.55, "Road": 0.95, "Rail": 0.75, "Sea": 1.15}
MODE_COST_K = {"Air": 8.8, "Road": 3.4, "Rail": 1.85, "Sea": 1.15}

Q4_MONTHS = (10, 11, 12)
DISRUPTION_MONTH = "2025-02"
DISRUPTION_DAYS = {"Sea": 2.6, "Road": 1.4, "Rail": 0.7, "Air": 0.3}

MODE_MIX = {"Road": 0.52, "Rail": 0.16, "Air": 0.18, "Sea": 0.14}
MODE_SHARE_DOMESTIC = {"Road": 0.72, "Rail": 0.22, "Air": 0.06}

PRIORITY_MIX = {"High": 0.22, "Standard": 0.63, "Low": 0.15}
PRIORITY_TRANSIT = {"High": 0.88, "Standard": 1.00, "Low": 1.12}
PRIORITY_COST = {"High": 1.18, "Standard": 1.00, "Low": 0.92}

WEIGHT_MEDIAN = {"Air": 120.0, "Road": 260.0, "Rail": 2400.0, "Sea": 1200.0}


def haversine(lat1, lon1, lat2, lon2):
    radius = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(a))


def draw_dates(rng: np.random.Generator, n: int) -> pd.Series:
    """Order dates with a Q4 peak and a quiet January."""
    weights = {1: 0.86, 2: 0.93, 3: 1.00, 4: 1.00, 5: 1.02, 6: 1.00,
               7: 0.97, 8: 1.00, 9: 1.06, 10: 1.36, 11: 1.38, 12: 1.30}
    months = pd.period_range(START, END, freq="M")
    w = np.array([weights[m.month] for m in months], dtype=float)
    w = w / w.sum()
    pick = rng.choice(len(months), size=n, p=w)
    days_in_month = months.days_in_month.values
    day = (rng.random(n) * days_in_month[pick]).astype(int) + 1
    return pd.Series([pd.Timestamp(y, m, d) for y, m, d in
                      zip(months.year[pick], months.month[pick], day)])


def main() -> None:
    rng = np.random.default_rng(SEED)
    n = N_SHIPMENTS

    order_date = draw_dates(rng, n).sort_values().reset_index(drop=True)

    # --- geography and mode -------------------------------------------------
    domestic = rng.random(n) < 0.38
    origin = np.where(domestic,
                      rng.choice(["Chicago", "Dallas", "Atlanta"], n),
                      rng.choice(ORIGINS, n,
                                 p=np.array([0.22, 0.14, 0.11, 0.07, 0.07, 0.14,
                                             0.07, 0.09, 0.06, 0.01, 0.01, 0.01])))
    destination = rng.choice(DESTINATIONS, n,
                             p=np.array([0.24, 0.02, 0.18, 0.14, 0.10, 0.07,
                                         0.12, 0.06, 0.04, 0.03]))
    # a shipment cannot terminate at its own origin
    clash = destination == origin
    while clash.any():
        destination[clash] = rng.choice(DESTINATIONS, int(clash.sum()),
                                        p=np.array([0.24, 0.02, 0.18, 0.14, 0.10, 0.07,
                                                    0.12, 0.06, 0.04, 0.03]))
        clash = destination == origin

    mode = np.empty(n, dtype=object)
    for i in range(n):
        if domestic[i]:
            mode[i] = rng.choice(list(MODE_SHARE_DOMESTIC),
                                 p=list(MODE_SHARE_DOMESTIC.values()))
        else:
            options = ["Sea", "Air"] if HUBS[origin[i]][2] != "US" else ["Road", "Rail", "Air"]
            probs = [0.62, 0.38] if HUBS[origin[i]][2] != "US" else [0.7, 0.24, 0.06]
            mode[i] = rng.choice(options, p=probs)

    lat1 = np.array([HUBS[o][0] for o in origin])
    lon1 = np.array([HUBS[o][1] for o in origin])
    lat2 = np.array([HUBS[d][0] for d in destination])
    lon2 = np.array([HUBS[d][1] for d in destination])
    great_circle = haversine(lat1, lon1, lat2, lon2)
    route_factor = np.where(mode == "Sea", 1.45,
                            np.where(mode == "Rail", 1.22,
                                     np.where(mode == "Road", 1.18, 1.03)))
    distance_km = np.maximum(35.0, great_circle * route_factor *
                             rng.lognormal(0.0, 0.07, n))

    # --- carrier ------------------------------------------------------------
    carrier = np.empty(n, dtype=object)
    names = list(CARRIERS)
    for m in MODE_BASE_DAYS:
        idx = np.where(mode == m)[0]
        candidates = [c for c in names if m in CARRIERS[c][0]]
        w = np.array([CARRIERS[c][1] for c in candidates], dtype=float)
        carrier[idx] = rng.choice(candidates, size=len(idx), p=w / w.sum())

    priority = rng.choice(list(PRIORITY_MIX), n, p=list(PRIORITY_MIX.values()))

    # --- transit time -------------------------------------------------------
    base = np.array([MODE_BASE_DAYS[m] for m in mode])
    sigma = np.array([MODE_SIGMA[m] for m in mode])
    slope = np.array([MODE_DIST_SLOPE[m] for m in mode])
    nominal = (base + distance_km / 4000.0 * slope) * np.exp(rng.normal(0.0, sigma, n))

    priority_transit = np.array([PRIORITY_TRANSIT[p] for p in priority])
    carrier_penalty = np.array([BAD_CARRIERS.get(c, 0.0) for c in carrier])
    month_key = order_date.dt.strftime("%Y-%m")
    disruption = np.array([DISRUPTION_DAYS[m] if k == DISRUPTION_MONTH else 0.0
                           for m, k in zip(mode, month_key)])

    transit_days = nominal * priority_transit + carrier_penalty + disruption
    transit_days = np.maximum(0.6, transit_days)

    # Promised days behave like a mode-level service commitment calibrated to
    # the 87th percentile of nominal transit, then rounded and jittered.
    promise = {}
    reliable = ~np.isin(carrier, list(BAD_CARRIERS))
    for m in MODE_BASE_DAYS:
        mask = (mode == m) & reliable
        promise[m] = float(np.quantile(np.ceil(transit_days[mask]), 0.88))
    promised_days = np.array([promise[m] for m in mode]) + rng.normal(0, 0.25, n)
    promised_days = np.clip(np.round(promised_days), 1, 60).astype(int)

    ship_lag = rng.integers(0, 3, n)
    ship_date = order_date + pd.to_timedelta(ship_lag, unit="D")
    delivery_date = ship_date + pd.to_timedelta(np.ceil(transit_days).astype(int), unit="D")

    # --- physical and commercial -------------------------------------------
    weight_median = np.array([WEIGHT_MEDIAN[m] for m in mode])
    weight_kg = weight_median * rng.lognormal(0.0, 1.05, n)
    density = rng.normal(165.0, 28.0, n)                      # kg per m3
    volume_m3 = np.maximum(0.002, weight_kg / density *
                           rng.lognormal(0.0, 0.18, n))

    cost_k = np.array([MODE_COST_K[m] for m in mode])
    priority_cost = np.array([PRIORITY_COST[p] for p in priority])
    q4_cost = np.where(order_date.dt.month.isin(Q4_MONTHS), 1.05, 1.0)
    carrier_cost = np.array([1.0 + 0.04 * (i % 3) for i in
                             [names.index(c) for c in carrier]])
    freight_cost = (cost_k * distance_km * weight_kg ** 0.82 / 1000.0 *
                    np.exp(rng.normal(0.0, 0.18, n)) *
                    priority_cost * q4_cost * carrier_cost)

    # --- planted outliers (1.4%) -------------------------------------------
    outlier_mask = rng.random(n) < 0.014
    outlier_kind = rng.choice(["cost", "weight", "transit"], outlier_mask.sum(),
                              p=[0.5, 0.3, 0.2])
    idx = np.where(outlier_mask)[0]
    for j, i in enumerate(idx):
        if outlier_kind[j] == "cost":
            freight_cost[i] *= rng.uniform(5, 12)
        elif outlier_kind[j] == "weight":
            weight_kg[i] *= rng.uniform(8, 20)
            volume_m3[i] *= rng.uniform(4, 8)
        else:
            extra = rng.uniform(18, 40)
            transit_days[i] += extra
            delivery_date[i] = ship_date[i] + pd.Timedelta(
                days=int(np.ceil(transit_days[i])))

    status = np.where(transit_days <= promised_days, "Delivered", "Delayed")
    late_window = order_date >= pd.Timestamp("2025-12-12")
    in_transit = late_window & (rng.random(n) < 0.45)
    status = np.where(in_transit, "In Transit", status)
    cancelled = (~in_transit) & (rng.random(n) < 0.007)
    status = np.where(cancelled, "Cancelled", status)

    frame = pd.DataFrame({
        "shipment_id": [f"SHP-{i:06d}" for i in range(1, n + 1)],
        "order_date": order_date,
        "ship_date": ship_date,
        "delivery_date": delivery_date,
        "origin": origin,
        "destination": destination,
        "lane": [f"{o} -> {d}" for o, d in zip(origin, destination)],
        "mode": mode,
        "carrier": carrier,
        "weight_kg": weight_kg.round(2),
        "volume_m3": volume_m3.round(3),
        "distance_km": distance_km.round(1),
        "freight_cost_usd": freight_cost.round(2),
        "promised_days": promised_days,
        "status": status,
        "priority": priority,
    })

    truth = frame[["shipment_id", "mode", "carrier", "weight_kg",
                   "freight_cost_usd", "distance_km"]].copy()
    truth["transit_days_true"] = (delivery_date - ship_date).dt.days
    truth["planted_outlier"] = outlier_mask
    truth["planted_disruption"] = month_key == DISRUPTION_MONTH

    dirty = frame.copy()
    dirty = inject_quality_defects(dirty, rng)

    DATA_SIM.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    dirty.to_csv(DATA_SIM / "shipments_raw.csv", index=False)
    truth.to_csv(DATA_SIM / "shipments_ground_truth.csv", index=False)

    planted = {
        "seed": SEED,
        "rows_generated": int(n),
        "window": [START, END],
        "q4_multiplier": 1.35,
        "q4_months": list(Q4_MONTHS),
        "mode_base_days": MODE_BASE_DAYS,
        "weak_carriers": BAD_CARRIERS,
        "disruption_month": DISRUPTION_MONTH,
        "disruption_penalty_days": DISRUPTION_DAYS,
        "cost_weight_elasticity": 0.82,
        "cost_distance_elasticity": 1.0,
        "outlier_share": 0.014,
        "duplicate_rows": int(round(n * 0.012)),
        "missing_share_target": 0.045,
        "realised": {
            "on_time_rate": float(frame.loc[frame["status"].isin(
                ["Delivered", "Delayed"]), "status"].eq("Delivered").mean()),
            "median_transit_days_by_mode": frame.loc[frame["status"].isin(
                ["Delivered", "Delayed"])].assign(
                    t=(frame["delivery_date"] - frame["ship_date"]).dt.days)
                .groupby("mode")["t"].median().to_dict(),
            "on_time_rate_by_carrier": frame.loc[frame["status"].isin(
                ["Delivered", "Delayed"])].assign(
                    ok=(frame["status"] == "Delivered").astype(int))
                .groupby("carrier")["ok"].mean().round(4).to_dict(),
            "median_cost_per_kg_by_mode": (frame.assign(
                cpk=frame["freight_cost_usd"] / frame["weight_kg"])
                .groupby("mode")["cpk"].median().round(3).to_dict()),
            "monthly_rows": frame["order_date"].dt.to_period("M").astype(str)
                                 .value_counts().sort_index().to_dict(),
        },
    }
    (RESULTS / "planted_effects.json").write_text(json.dumps(planted, indent=2) + "\n")
    print(json.dumps({k: v for k, v in planted.items() if k != "realised"}, indent=2))
    print("on-time overall:", round(planted["realised"]["on_time_rate"], 4))
    print(pd.Series(planted["realised"]["on_time_rate_by_carrier"]).sort_values().to_string())
    print(planted["realised"]["median_transit_days_by_mode"])


def inject_quality_defects(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Sprinkle the defects a real export would contain, and record their size."""
    dirty = frame.copy()
    n = len(dirty)
    log: dict[str, int] = {}

    # inconsistent categorical labels
    mode_variants = {"Road": ["road", "Road ", "ROAD", "Road"],
                     "Rail": ["Rail", "rail", "RAIL ", "Rail"],
                     "Air": ["Air", "air freight", "AIR", "Air"],
                     "Sea": ["Sea", "sea", "Ocean", "SEA "]}
    pick = rng.random(n) < 0.08
    dirty.loc[pick, "mode"] = [rng.choice(mode_variants[m]) for m in dirty.loc[pick, "mode"]]
    log["mode_label_variants"] = int(pick.sum())

    carrier_pick = rng.random(n) < 0.05
    dirty.loc[carrier_pick, "carrier"] = dirty.loc[carrier_pick, "carrier"].str.lower() + " "
    log["carrier_label_variants"] = int(carrier_pick.sum())

    # unit drift: some rows exported in pounds and litres
    dirty["weight_unit"] = "kg"
    dirty["volume_unit"] = "m3"
    lb = rng.random(n) < 0.02
    dirty.loc[lb, "weight_kg"] = (dirty.loc[lb, "weight_kg"] * 2.20462).round(2)
    dirty.loc[lb, "weight_unit"] = rng.choice(["lb", "lbs", "LBS"], int(lb.sum()))
    lit = rng.random(n) < 0.015
    dirty.loc[lit, "volume_m3"] = (dirty.loc[lit, "volume_m3"] * 1000).round(1)
    dirty.loc[lit, "volume_unit"] = "L"
    log["weight_rows_in_pounds"] = int(lb.sum())
    log["volume_rows_in_litres"] = int(lit.sum())

    # mixed date formats
    ship_fmt = rng.random(n) < 0.04
    dirty["ship_date"] = dirty["ship_date"].dt.strftime("%Y-%m-%d")
    dirty.loc[ship_fmt, "ship_date"] = dirty.loc[ship_fmt, "ship_date"].apply(
        lambda s: pd.Timestamp(s).strftime("%d/%m/%Y"))
    order_fmt = rng.random(n) < 0.03
    dirty["order_date"] = dirty["order_date"].dt.strftime("%Y-%m-%d")
    dirty.loc[order_fmt, "order_date"] = dirty.loc[order_fmt, "order_date"].apply(
        lambda s: pd.Timestamp(s).strftime("%Y/%m/%d"))
    dirty["delivery_date"] = dirty["delivery_date"].dt.strftime("%Y-%m-%d")
    log["ship_date_dmy_rows"] = int(ship_fmt.sum())
    log["order_date_slash_rows"] = int(order_fmt.sum())

    # unparseable dates
    bad_delivery = rng.choice(n, 45, replace=False)
    dirty.loc[bad_delivery, "delivery_date"] = "not recorded"
    bad_ship = rng.choice(np.setdiff1d(np.arange(n), bad_delivery), 20, replace=False)
    dirty.loc[bad_ship, "ship_date"] = "not recorded"
    log["unparseable_dates"] = int(len(bad_delivery) + len(bad_ship))

    # impossible values
    neg_w = rng.choice(n, 15, replace=False)
    dirty.loc[neg_w, "weight_kg"] = -dirty.loc[neg_w, "weight_kg"].abs()
    zero_d = rng.choice(n, 8, replace=False)
    dirty.loc[zero_d, "distance_km"] = 0.0
    neg_c = rng.choice(n, 20, replace=False)
    dirty.loc[neg_c, "freight_cost_usd"] = -dirty.loc[neg_c, "freight_cost_usd"].abs()
    log["impossible_values"] = int(len(neg_w) + len(zero_d) + len(neg_c))

    # missingness, with freight cost missing not at random
    p_cost = np.where(dirty["mode"].isin(["Air", "Sea"]), 0.075, 0.012)
    high_value = dirty["freight_cost_usd"] > dirty["freight_cost_usd"].quantile(0.90)
    p_cost = np.where(high_value, 0.10, p_cost)
    cost_missing = rng.random(len(dirty)) < p_cost
    dirty.loc[cost_missing, "freight_cost_usd"] = np.nan
    log["freight_cost_missing"] = int(cost_missing.sum())

    for column, share in [("weight_kg", 0.011), ("volume_m3", 0.008),
                          ("priority", 0.005), ("promised_days", 0.003),
                          ("destination", 0.002)]:
        mask = rng.random(len(dirty)) < share
        dirty.loc[mask, column] = np.nan
        log[f"{column}_missing"] = int(mask.sum())

    unk = rng.random(len(dirty)) < 0.004
    dirty.loc[unk, "carrier"] = rng.choice(["unknown", "", "N/A"], int(unk.sum()))
    log["carrier_unknown"] = int(unk.sum())

    # exact duplicate rows, exported twice at the end of the extract
    dup = dirty.sample(n=int(round(n * 0.012)), random_state=SEED)
    dirty = pd.concat([dirty, dup], ignore_index=True)
    log["duplicate_rows_added"] = len(dup)

    total_cells = dirty.shape[0] * dirty.shape[1]
    log["missing_cell_share"] = round(float(dirty.isna().sum().sum() / total_cells), 4)
    (RESULTS / "dirt_injected.json").write_text(json.dumps(log, indent=2) + "\n")
    return dirty


if __name__ == "__main__":
    main()
