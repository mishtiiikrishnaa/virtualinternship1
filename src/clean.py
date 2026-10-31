"""Cleaning transforms.

Every function is pure apart from the `CleaningLog`, which records what was
changed and how many rows it touched. Two rules shape the whole module:

1. Coerce or reject, never guess silently. A weight that cannot be parsed
   becomes null with a flag, not a zero.
2. Keep the original alongside the derived value where a human will need to
   adjudicate (currency, unit, country alias).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

LB_TO_KG = 0.45359237
MAX_PLAUSIBLE_KG = 250_000.0

# Pinned conversion snapshot. A production job would call the ECB reference
# rate API daily and store the response; a pinned table keeps the published
# numbers stable and the reasoning auditable.
FX_TO_USD: dict[str, float] = {"USD": 1.0, "EUR": 1.09, "GBP": 1.27, "INR": 0.012}

COUNTRY_LOOKUP: dict[str, str] = {
    "us": "United States",
    "usa": "United States",
    "united states": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "great britain": "United Kingdom",
    "de": "Germany",
    "germany": "Germany",
    "deutschland": "Germany",
    "nl": "Netherlands",
    "netherlands": "Netherlands",
    "the netherlands": "Netherlands",
    "holland": "Netherlands",
    "in": "India",
    "india": "India",
    "bharat": "India",
    "cn": "China",
    "china": "China",
    "pr china": "China",
    "prc": "China",
    "p r china": "China",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "sg": "Singapore",
    "singapore": "Singapore",
}

MODE_LOOKUP: dict[str, str] = {
    "air": "Air",
    "air freight": "Air",
    "airfreight": "Air",
    "ocean": "Ocean",
    "sea": "Ocean",
    "sea freight": "Ocean",
    "seafreight": "Ocean",
    "vessel": "Ocean",
    "road": "Road",
    "truck": "Road",
    "lorry": "Road",
    "rail": "Rail",
    "train": "Rail",
}

CATEGORY_LOOKUP: dict[str, str] = {
    "electronics": "Electronics",
    "apparel": "Apparel",
    "clothing": "Apparel",
    "pharmaceuticals": "Pharmaceuticals",
    "pharma": "Pharmaceuticals",
    "automotive parts": "Automotive Parts",
    "auto parts": "Automotive Parts",
    "consumer goods": "Consumer Goods",
    "fmcg": "Consumer Goods",
    "industrial equipment": "Industrial Equipment",
    "perishables": "Perishables",
    "cold chain": "Perishables",
}

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%Y/%m/%d", "%d-%m-%Y")

_UNIT_TO_KG = {
    "kg": 1.0,
    "kgs": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "lb": LB_TO_KG,
    "lbs": LB_TO_KG,
    "pound": LB_TO_KG,
    "pounds": LB_TO_KG,
    "t": 1000.0,
    "tonne": 1000.0,
    "tonnes": 1000.0,
}

_CURRENCY_SYMBOL = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}
_CURRENCY_CODE = re.compile(r"\b(USD|EUR|GBP|INR)\b", re.IGNORECASE)


@dataclass
class CleaningLog:
    steps: list[dict[str, object]] = field(default_factory=list)

    def add(self, step: str, detail: str, rows: int) -> None:
        self.steps.append({"step": step, "detail": detail, "rows_affected": int(rows)})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.steps, columns=["step", "detail", "rows_affected"])

    def summary(self) -> str:
        return "\n".join(
            f"- **{s['step']}** — {s['detail']} ({s['rows_affected']:,} rows)"
            for s in self.steps
        )


def _key(value: str) -> str:
    """Normalise a label to a lookup key: no case, dots, punctuation or padding."""
    text = str(value).strip().lower()
    text = text.replace("&", " and ")
    # dots are deleted rather than replaced: "U.S.A." and "USA" must land on
    # the same key, while "U.A.E." must not become "u a e"
    text = text.replace(".", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonicalise(series: pd.Series, lookup: dict[str, str], log: CleaningLog, label: str) -> pd.Series:
    keys = series.map(lambda v: _key(v) if pd.notna(v) else None)
    mapped = keys.map(lookup.get)
    unknown = series[mapped.isna() & series.notna()].unique()
    if len(unknown):
        log.add(
            f"unmapped {label}",
            "left null for manual review: " + ", ".join(map(str, sorted(unknown, key=str)[:10])),
            int((mapped.isna() & series.notna()).sum()),
        )
    return mapped


def parse_mixed_dates(series: pd.Series, log: CleaningLog, label: str) -> pd.Series:
    """Try each known format in turn, keeping the first that succeeds.

    `dayfirst` puzzles are avoided entirely by never asking pandas to guess:
    an explicit format list is boring, correct and reviewable.
    """
    out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    source = series.astype("string").str.strip()
    for fmt in DATE_FORMATS:
        pending = out.isna() & source.notna()
        if not pending.any():
            break
        out.loc[pending] = pd.to_datetime(source[pending], format=fmt, errors="coerce")
    failed = int((out.isna() & source.notna()).sum())
    log.add(f"parse {label}", f"formats tried: {', '.join(DATE_FORMATS)}", failed)
    return out


def _numeric(text: str) -> float:
    """Parse a money or measure string, tolerating thousands separators.

    Handles both 1,234.56 and 1.234,56, and keeps the sign that the source put
    somewhere in the string (before the symbol, after it, or both).
    """
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return float("nan")
    raw = str(text).strip()
    if raw == "":
        return float("nan")
    negative = "-" in raw or (raw.startswith("(") and raw.endswith(")"))
    cleaned = re.sub(r"[^0-9.,]", "", raw)
    if not cleaned:
        return float("nan")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        head, _, tail = cleaned.rpartition(",")
        cleaned = f"{head.replace(',', '')}.{tail}" if len(tail) == 2 else cleaned.replace(",", "")
    value = float(cleaned)
    return -value if negative else value


def parse_weight(frame: pd.DataFrame, log: CleaningLog) -> pd.Series:
    values = frame["weight_value"].map(_numeric)
    units = frame["weight_unit"].map(lambda u: _UNIT_TO_KG.get(_key(u), np.nan) if pd.notna(u) else np.nan)

    unknown_units = int((units.isna() & frame["weight_unit"].notna()).sum())
    if unknown_units:
        log.add("unknown weight unit", "rows rejected rather than assumed to be kg", unknown_units)

    kg = values * units
    sentinel = kg > MAX_PLAUSIBLE_KG
    zero = kg <= 0
    log.add(
        "reject implausible weight",
        f"sentinel values above {MAX_PLAUSIBLE_KG:,.0f} kg and non-positive weights set to null",
        int(sentinel.sum() + zero.sum()),
    )
    kg = kg.mask(sentinel | zero)
    return kg.rename("weight_kg")


def parse_money(frame: pd.DataFrame, log: CleaningLog) -> tuple[pd.Series, pd.Series]:
    """Return (amount_in_usd, currency_used)."""
    text = frame["freight_cost"]
    amount = text.map(_numeric)
    declared = frame["currency"].map(lambda c: str(c).strip().upper() if pd.notna(c) else None)

    from_string = text.map(
        lambda t: (
            _CURRENCY_CODE.search(str(t)).group(1).upper()
            if _CURRENCY_CODE.search(str(t))
            else next((code for symbol, code in _CURRENCY_SYMBOL.items() if symbol in str(t)), None)
        )
    )
    # a code printed in the amount beats the separate currency column, because
    # the amount travelled with the money
    currency = from_string.fillna(declared).fillna("USD")
    rate = currency.map(FX_TO_USD)
    missing_rate = int(rate.isna().sum())
    if missing_rate:
        log.add("unknown currency", "converted at par, flagged for review", missing_rate)
    rate = rate.fillna(1.0)

    negatives = int((amount < 0).sum())
    if negatives:
        log.add("negative freight cost", "kept as credit notes, excluded from cost aggregates", negatives)

    return (amount * rate).rename("freight_cost_usd"), currency.rename("currency_resolved")


def deduplicate(frame: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Keep the last occurrence of each shipment key.

    Shipping systems emit a row per status change, so "keep first" would keep
    the least complete version of the record. The last row is the most recent
    state of the world.
    """
    before = len(frame)
    exact = int(frame.duplicated().sum())
    frame = frame.drop_duplicates()
    conflicting = int(frame.duplicated(subset=["shipment_id"]).sum())
    frame = frame.drop_duplicates(subset=["shipment_id"], keep="last")
    log.add(
        "deduplicate",
        f"{exact} byte-identical rows removed, {conflicting} conflicting shipment keys resolved by latest state",
        before - len(frame),
    )
    return frame.reset_index(drop=True)


def impute_weight(frame: pd.DataFrame, log: CleaningLog) -> pd.Series:
    """Median within mode × category, then mode, then global.

    Median rather than mean: freight weights are log-normal, so the mean is
    dragged upward by a single mis-scaled pallet. Each level is a fallback for
    thin cells, and every filled row is flagged.
    """
    kg = frame["weight_kg"]
    by_cell = frame.groupby(["mode", "product_category"], observed=True)["weight_kg"].transform("median")
    by_mode = frame.groupby("mode", observed=True)["weight_kg"].transform("median")
    global_median = kg.median()
    filled = kg.fillna(by_cell).fillna(by_mode).fillna(global_median)
    missing = int(kg.isna().sum())
    log.add(
        "impute weight",
        f"grouped median (mode x category -> mode -> global {global_median:,.1f} kg), flag added",
        missing,
    )
    return filled.rename("weight_kg")


def impute_cost(frame: pd.DataFrame, weight: pd.Series, log: CleaningLog) -> pd.Series:
    """Fill missing cost from the mode-level median cost per kilogram.

    Cost is roughly proportional to billed weight, so a rate is a better
    estimator than a flat median — an ocean consignment and an air consignment
    of the same mass do not cost the same.
    """
    cost = frame["freight_cost_usd"].clip(lower=0)
    rate = (cost / weight).groupby(frame["mode"], observed=True).transform("median")
    estimate = (weight * rate).round(2)
    filled = cost.fillna(estimate)
    log.add(
        "impute cost",
        "mode-level median USD per kg applied to missing costs, flag added",
        int(frame["freight_cost_usd"].isna().sum()),
    )
    return filled.rename("freight_cost_usd")


def winsorise(series: pd.Series, log: CleaningLog, label: str, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    lo, hi = series.quantile([lower, upper])
    clipped = int(((series < lo) | (series > hi)).sum())
    log.add(
        f"winsorise {label}",
        f"clipped to p{lower * 100:g}={lo:,.2f} / p{upper * 100:g}={hi:,.2f}",
        clipped,
    )
    return series.clip(lower=lo, upper=hi)


def add_transit_features(frame: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    frame = frame.copy()
    frame["transit_days"] = (frame["delivery_date"] - frame["ship_date"]).dt.days
    impossible = frame["transit_days"] < 0
    frame.loc[impossible, "transit_days"] = pd.NA

    # carrier promise = 90th percentile of observed transit for that mode; in a
    # real engagement this comes from the contract table, not the data
    promise = frame.groupby("mode", observed=True)["transit_days"].transform(
        lambda s: s.quantile(0.90)
    )
    frame["delay_days"] = frame["transit_days"].astype("Float64") - promise
    log.add(
        "derive transit features",
        "transit_days from ship/delivery dates; delay_days against p90 promise per mode",
        int(impossible.sum()),
    )
    return frame


def clean(frame: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    log = CleaningLog()

    # 1. typing and hygiene -------------------------------------------------
    frame = frame.copy()
    for col in ("shipment_id", "order_id", "carrier", "origin_city", "dest_city"):
        frame[col] = frame[col].astype("string").str.strip()
    frame.loc[frame["carrier"] == "", "carrier"] = pd.NA
    frame = frame.dropna(subset=["shipment_id"])
    log.add("trim text", "whitespace stripped from keys, cities and carriers", len(frame))

    # 2. controlled vocabularies -------------------------------------------
    frame["origin_country"] = canonicalise(frame["origin_country"], COUNTRY_LOOKUP, log, "origin_country")
    frame["dest_country"] = canonicalise(frame["dest_country"], COUNTRY_LOOKUP, log, "dest_country")
    frame["mode"] = canonicalise(frame["mode"], MODE_LOOKUP, log, "mode")
    frame["product_category"] = canonicalise(frame["product_category"], CATEGORY_LOOKUP, log, "product_category")

    # 3. temporal parsing ---------------------------------------------------
    for col in ("order_date", "ship_date", "delivery_date"):
        frame[col] = parse_mixed_dates(frame[col], log, col)
    backwards = (frame["ship_date"] < frame["order_date"]) | (frame["delivery_date"] < frame["ship_date"])
    log.add("date ordering", "rows where ship<order or delivery<ship nulled out", int(backwards.sum()))
    frame.loc[backwards, ["ship_date", "delivery_date"]] = pd.NaT

    # 4. measures -----------------------------------------------------------
    quantity = pd.to_numeric(frame["quantity"], errors="coerce")
    bad_qty = quantity.isna() | (quantity < 1)
    log.add("reject quantity", "non-numeric or below one set to null", int(bad_qty.sum()))
    frame["quantity"] = quantity.mask(bad_qty).astype("Int64")

    frame["weight_kg"] = parse_weight(frame, log)
    frame["freight_cost_usd"], frame["currency_resolved"] = parse_money(frame, log)

    # 5. identity -----------------------------------------------------------
    frame = deduplicate(frame, log)

    # 6. missingness --------------------------------------------------------
    raw_missing = frame["weight_kg"].isna()
    frame["weight_kg"] = impute_weight(frame, log)
    frame["weight_imputed"] = raw_missing.to_numpy()
    cost_missing = frame["freight_cost_usd"].isna()
    frame["freight_cost_usd"] = impute_cost(frame, frame["weight_kg"], log)
    frame["cost_imputed"] = cost_missing.to_numpy()

    # 7. extremes -----------------------------------------------------------
    frame["weight_kg"] = winsorise(frame["weight_kg"], log, "weight_kg", 0.001, 0.999)
    frame["freight_cost_usd"] = winsorise(frame["freight_cost_usd"], log, "freight_cost_usd")

    # 8. features -----------------------------------------------------------
    frame = add_transit_features(frame, log)

    # 9. terminal shaping ---------------------------------------------------
    frame["quantity"] = frame["quantity"].fillna(1).astype("int64")
    for col in ("origin_country", "dest_country", "mode", "product_category"):
        frame[col] = frame[col].astype("string").astype("category")
    frame["carrier"] = frame["carrier"].astype("string")
    frame["weight_kg"] = frame["weight_kg"].astype("float64")
    frame["freight_cost_usd"] = frame["freight_cost_usd"].astype("float64")
    frame["transit_days"] = frame["transit_days"].astype("Int64")
    frame["delay_days"] = frame["delay_days"].round(2)

    ordered = [
        "shipment_id", "order_id", "order_date", "ship_date", "delivery_date",
        "origin_city", "origin_country", "dest_city", "dest_country",
        "mode", "carrier", "product_category", "quantity",
        "weight_kg", "weight_imputed", "freight_cost_usd", "cost_imputed",
        "currency_resolved", "transit_days", "delay_days",
    ]
    frame = frame[ordered].sort_values("shipment_id").reset_index(drop=True)
    log.add("emit curated table", f"{len(frame):,} rows, {frame.shape[1]} columns", len(frame))
    return frame, log
