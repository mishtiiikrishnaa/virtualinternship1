"""Generate a deliberately messy shipment extract for pipeline development.

The numbers here are synthetic. Carrier names are invented on purpose: no real
firm is described, so the repository can be published without a licensing or
defamation headache. The *defects* however are modelled on the ones that show
up in genuine freight extracts — mixed date formats, unit drift, country
aliases, currency symbols pasted into numeric columns, duplicated shipment
keys and placeholder weights such as 999999.

Run with a fixed seed to reproduce byte-identical output:

    python -m src.make_sample_data
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260131
N_ROWS = 4200
RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "shipments_raw.csv"

# canonical country -> plausible ways a clerk, a portal export or a customs
# form might write it
COUNTRY_ALIASES: dict[str, list[str]] = {
    "United States": ["USA", "U.S.A.", "United States", "united states", "US", " US "],
    "United Kingdom": ["UK", "U.K.", "United Kingdom", "united kingdom", "Great Britain"],
    "Germany": ["DE", "Germany", "germany", "Deutschland"],
    "Netherlands": ["NL", "Netherlands", "the netherlands", "Holland"],
    "India": ["IN", "India", "india", "Bharat"],
    "China": ["CN", "China", "china", "P.R. China"],
    "United Arab Emirates": ["UAE", "U.A.E.", "United Arab Emirates", "uae"],
    "Singapore": ["SG", "Singapore", "singapore"],
}

CITIES: dict[str, list[str]] = {
    "United States": ["Newark", "Long Beach", "Chicago", "Savannah", "Dallas"],
    "United Kingdom": ["Felixstowe", "Southampton", "London", "Manchester"],
    "Germany": ["Hamburg", "Bremen", "Frankfurt", "Munich"],
    "Netherlands": ["Rotterdam", "Amsterdam", "Tilburg"],
    "India": ["Nhava Sheva", "Chennai", "Mumbai", "Delhi"],
    "China": ["Shanghai", "Shenzhen", "Ningbo", "Guangzhou"],
    "United Arab Emirates": ["Jebel Ali", "Dubai", "Abu Dhabi"],
    "Singapore": ["Singapore", "Jurong"],
}

MODE_ALIASES: dict[str, list[str]] = {
    "Air": ["Air", "AIR", "air freight", "Air Freight"],
    "Ocean": ["Ocean", "OCEAN", "Sea", "sea freight"],
    "Road": ["Road", "road", "Truck", "TRUCK"],
    "Rail": ["Rail", "rail", "RAIL"],
}

CATEGORIES: dict[str, list[str]] = {
    "Electronics": ["Electronics", "electronics", "ELECTRONICS"],
    "Apparel": ["Apparel", "apparel", "Apparel "],
    "Pharmaceuticals": ["Pharmaceuticals", "pharmaceuticals", "Pharma"],
    "Automotive Parts": ["Automotive Parts", "automotive parts", "Auto Parts"],
    "Consumer Goods": ["Consumer Goods", "consumer goods", "FMCG"],
    "Industrial Equipment": ["Industrial Equipment", "industrial equipment"],
    "Perishables": ["Perishables", "perishables", "Cold Chain"],
}

# invented carriers; roughly one per mode so that joins stay plausible
CARRIERS: dict[str, list[str]] = {
    "Air": ["Nimbus Air Cargo", "Vantage Skyfreight"],
    "Ocean": ["Poseidon Line", "Kestrel Container Co"],
    "Road": ["Atlas Roadways", "Northstar Haulage"],
    "Rail": ["Vulcan Rail Freight"],
}

# typical transit windows in days, used to build a promised vs actual delay flag
TRANSIT_DAYS: dict[str, tuple[int, int]] = {
    "Air": (2, 6),
    "Ocean": (18, 38),
    "Road": (2, 9),
    "Rail": (7, 16),
}

# USD per kilogram, only to make synthetic costs look sane
RATE_PER_KG: dict[str, float] = {
    "Air": 4.10,
    "Ocean": 0.35,
    "Road": 0.80,
    "Rail": 0.55,
}

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%Y/%m/%d")


def _pick(rng: np.random.Generator, mapping: dict[str, list[str]], n: int) -> list[str]:
    keys = list(mapping)
    chosen = rng.choice(keys, size=n, p=_weights(len(keys)))
    return [rng.choice(mapping[k]) for k in chosen]


def _weights(k: int) -> np.ndarray:
    w = np.linspace(1.6, 0.6, k)
    return w / w.sum()


def _messy_date(value: pd.Timestamp, rng: np.random.Generator) -> str:
    fmt = DATE_FORMATS[rng.integers(len(DATE_FORMATS))]
    return value.strftime(fmt)


def build() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    modes = _pick(rng, MODE_ALIASES, N_ROWS)
    canonical_mode = {alias: name for name, aliases in MODE_ALIASES.items() for alias in aliases}
    categories = _pick(rng, CATEGORIES, N_ROWS)
    canonical_country = {
        alias: name for name, aliases in COUNTRY_ALIASES.items() for alias in aliases
    }
    origins = _pick(rng, COUNTRY_ALIASES, N_ROWS)
    dests = _pick(rng, COUNTRY_ALIASES, N_ROWS)
    origin_keys = [canonical_country[o] for o in origins]
    dest_keys = [canonical_country[d] for d in dests]

    # origin and destination should not collide
    for i, (o, d) in enumerate(zip(origin_keys, dest_keys, strict=True)):
        if o == d:
            dest_keys[i] = "Germany" if o != "Germany" else "India"

    order_dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(
        rng.integers(0, 360, N_ROWS), unit="D"
    )
    ship_lag = rng.integers(0, 7, N_ROWS)
    ship_dates = order_dates + pd.to_timedelta(ship_lag, unit="D")

    transit = np.array(
        [rng.integers(*TRANSIT_DAYS[canonical_mode[m]]) for m in modes], dtype="int64"
    )
    delivery_dates = ship_dates + pd.to_timedelta(transit, unit="D")

    base_weight = rng.lognormal(mean=5.2, sigma=0.9, size=N_ROWS)  # ~180 kg median
    weight_unit = rng.choice(["kg", "KG", "Kilograms", "lb", "lbs"], N_ROWS,
                             p=[0.55, 0.15, 0.05, 0.20, 0.05])
    # pounds carry a bigger number for the same physical mass
    weight_value = np.where(
        np.isin(weight_unit, ["lb", "lbs"]), base_weight / 0.45359237, base_weight
    )
    weight_value = np.round(weight_value, 2)
    weight_text = weight_value.astype(str)

    cost_usd = weight_value * np.array([RATE_PER_KG[canonical_mode[m]] for m in modes])
    cost_usd *= rng.lognormal(mean=0.0, sigma=0.25, size=N_ROWS)
    currency = rng.choice(["USD", "EUR", "GBP", "INR"], N_ROWS, p=[0.62, 0.2, 0.1, 0.08])
    fx = {"USD": 1.0, "EUR": 1.09, "GBP": 1.27, "INR": 0.012}
    symbol = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}
    local_cost = cost_usd / np.array([fx[c] for c in currency])
    cost_text = [
        f"{symbol[c]}{v:,.2f}" if i % 2 == 0 else f"{c} {v:,.2f}"
        for i, (c, v) in enumerate(zip(currency, local_cost, strict=True))
    ]

    df = pd.DataFrame(
        {
            "shipment_id": [f"SHP-{i:05d}" for i in range(1, N_ROWS + 1)],
            "order_id": [f"ORD-{i:05d}" for i in rng.permutation(N_ROWS) + 1],
            "order_date": [_messy_date(d, rng) for d in order_dates],
            "ship_date": [_messy_date(d, rng) for d in ship_dates],
            "delivery_date": [_messy_date(d, rng) for d in delivery_dates],
            "origin_city": [rng.choice(CITIES[o]) for o in origin_keys],
            "origin_country": origins,
            "dest_city": [rng.choice(CITIES[d]) for d in dest_keys],
            "dest_country": dests,
            "mode": modes,
            "carrier": [rng.choice(CARRIERS[canonical_mode[m]]) for m in modes],
            "product_category": categories,
            "quantity": rng.integers(1, 40, N_ROWS),
            "weight_value": weight_text,
            "weight_unit": weight_unit,
            "freight_cost": cost_text,
            "currency": currency,
        }
    )

    df = _inject_defects(df, rng)
    return df


def _inject_defects(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    df = df.copy()

    # --- text hygiene -------------------------------------------------------
    city_noise = rng.random(n) < 0.12
    df.loc[city_noise, "origin_city"] = (
        df.loc[city_noise, "origin_city"].str.upper() + " "
    )
    postcode_noise = rng.random(n) < 0.06
    df.loc[postcode_noise, "dest_city"] = (
        df.loc[postcode_noise, "dest_city"] + " " + rng.integers(1000, 99999, postcode_noise.sum()).astype(str)
    )

    # --- missingness that reflects reality, not entropy ---------------------
    df.loc[rng.random(n) < 0.08, "weight_value"] = np.nan
    df.loc[rng.random(n) < 0.05, "freight_cost"] = np.nan
    df.loc[rng.random(n) < 0.04, "delivery_date"] = np.nan
    df.loc[rng.random(n) < 0.02, "carrier"] = np.nan

    # --- values that parse as numbers but mean nothing ----------------------
    sentinel = rng.random(n) < 0.01
    df.loc[sentinel, "weight_value"] = "999999"
    zeros = rng.random(n) < 0.01
    df.loc[zeros, "weight_value"] = "0"

    # --- negative money, which freight systems occasionally emit ------------
    neg = rng.random(n) < 0.008
    idx = df.index[neg]
    df.loc[idx, "freight_cost"] = df.loc[idx, "freight_cost"].str.replace(
        r"([-]?)([$€£₹]|[A-Z]{3}) ?", r"\1\2-", regex=True
    )

    # --- duplicated extracts ------------------------------------------------
    exact_dupes = df.sample(n=120, random_state=SEED).copy()
    stale_dupes = df.sample(n=60, random_state=SEED + 1).copy()
    stale_dupes["freight_cost"] = stale_dupes["freight_cost"].astype(str) + "0"

    df = pd.concat([df, exact_dupes, stale_dupes], ignore_index=True)
    return df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)


def main() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = build()
    frame.to_csv(RAW_PATH, index=False)
    print(f"wrote {len(frame):,} rows x {frame.shape[1]} columns to {RAW_PATH}")


if __name__ == "__main__":
    main()
