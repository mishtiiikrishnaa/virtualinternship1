# Data dictionary — `shipments_clean.csv`

One row per `shipment_id`. Produced by `src/run_pipeline.py` from
`data/raw/shipments_raw.csv`. If this file and the pipeline disagree, the
pipeline is right and this file is a bug.

| column | type | description | rule applied |
|---|---|---|---|
| `shipment_id` | string | shipment key as issued by the source system | trimmed; duplicates resolved by latest state; must match `^SHP-\d{5}$` |
| `order_id` | string | originating order reference | trimmed, not validated against an order table (none was supplied) |
| `order_date` | datetime64 | date the order was placed | parsed against an explicit format list; unparseable → null |
| `ship_date` | datetime64 | date the consignment left origin | must be ≥ `order_date`, otherwise nulled |
| `delivery_date` | datetime64 | date of delivery, null while in transit | must be ≥ `ship_date` |
| `origin_city` | string | city of origin as free text | whitespace trimmed, case preserved, postcodes stripped when detected |
| `origin_country` | category | ISO-style country name | alias table, 30+ spellings → 8 canonical values |
| `dest_city` | string | destination city as free text | as above |
| `dest_country` | category | ISO-style country name | as above |
| `mode` | category | transport mode | alias table → Air / Ocean / Road / Rail |
| `carrier` | string | carrier name | trimmed; null preserved rather than guessed |
| `product_category` | category | commodity group | alias table → 7 canonical values |
| `quantity` | int64 | units shipped | non-numeric or < 1 → null, then filled with 1 and counted |
| `weight_kg` | float64 | gross weight in kilograms | lb → kg at 0.45359237; sentinel and non-positive values rejected; missing values imputed by grouped median |
| `weight_imputed` | bool | true where `weight_kg` was filled | set before imputation so it cannot be lost downstream |
| `freight_cost_usd` | float64 | freight charge converted to USD | symbol/code parsed from the amount; FX snapshot applied; negatives kept as credits then clipped at zero; winsorised at p1/p99 |
| `cost_imputed` | bool | true where cost was filled | mode-level median USD per kg |
| `currency_resolved` | string | currency actually used for conversion | code printed in the amount outranks the currency column |
| `transit_days` | Int64 | `delivery_date - ship_date` in days | negative transit → null |
| `delay_days` | Float64 | `transit_days` minus the p90 promise for that mode | positive means late; null where delivery is unknown |

## Derived / dropped columns

| column | fate |
|---|---|
| `weight_value`, `weight_unit` | consumed into `weight_kg`, not republished |
| `freight_cost`, `currency` | consumed into `freight_cost_usd` and `currency_resolved` |

## Conventions

- Money is stored as a float in USD. Currency is *not* implicit: the
  `currency_resolved` column records what was converted, so a reviewer can
  re-convert at a different rate.
- Dates are naive dates. A real deployment over multiple time zones needs
  `tz`-aware timestamps at origin and destination; that is listed in the
  decision log as deferred rather than silently ignored.
- Null means *unknown*. It never means zero, and it never means "not
  applicable". Where "not applicable" was intended, a flag column exists.
