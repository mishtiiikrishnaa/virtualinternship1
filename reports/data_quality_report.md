# Data quality report — shipment table

Generated 2026-10-31 11:28 UTC by `src/run_pipeline.py`. This file is an artefact, not a
document: it is regenerated on every run and its numbers are the numbers the
cleaned table actually contains.

## Run provenance

| property | value |
|---|---|
| source file | `shipments_raw.csv` |
| source sha256 | `4cc084a7f947b374…` |
| source size | 682,599 bytes |
| rows before cleaning | 4,380 |
| rows published | 4,200 |
| output sha256 | `923540152f546997…` |
| checks | 13 total, 0 failed, 0 critical |

## Cleaning steps

| step                       | detail                                                                                 | rows_affected |
|----------------------------|----------------------------------------------------------------------------------------|---------------|
| trim text                  | whitespace stripped from keys, cities and carriers                                     | 4380          |
| parse order_date           | formats tried: %Y-%m-%d, %d/%m/%Y, %B %d, %Y, %Y/%m/%d, %d-%m-%Y                       | 0             |
| parse ship_date            | formats tried: %Y-%m-%d, %d/%m/%Y, %B %d, %Y, %Y/%m/%d, %d-%m-%Y                       | 0             |
| parse delivery_date        | formats tried: %Y-%m-%d, %d/%m/%Y, %B %d, %Y, %Y/%m/%d, %d-%m-%Y                       | 0             |
| date ordering              | rows where ship<order or delivery<ship nulled out                                      | 0             |
| reject quantity            | non-numeric or below one set to null                                                   | 0             |
| reject implausible weight  | sentinel values above 250,000 kg and non-positive weights set to null                  | 86            |
| negative freight cost      | kept as credit notes, excluded from cost aggregates                                    | 43            |
| deduplicate                | 122 byte-identical rows removed, 58 conflicting shipment keys resolved by latest state | 180           |
| impute weight              | grouped median (mode x category -> mode -> global 181.9 kg), flag added                | 382           |
| impute cost                | mode-level median USD per kg applied to missing costs, flag added                      | 220           |
| winsorise weight_kg        | clipped to p0.1=14.07 / p99.9=3,044.12                                                 | 10            |
| winsorise freight_cost_usd | clipped to p1=3.99 / p99=6,131.60                                                      | 84            |
| derive transit features    | transit_days from ship/delivery dates; delay_days against p90 promise per mode         | 0             |
| emit curated table         | 4,200 rows, 20 columns                                                                 | 4200          |

## Validation

| check                              | severity | result | detail                                                                                                                                                  |
|------------------------------------|----------|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| unique shipment_id                 | critical | pass   | 0 duplicate keys                                                                                                                                        |
| key columns populated              | critical | pass   | {'shipment_id': 0, 'order_id': 0, 'order_date': 0, 'ship_date': 0, 'origin_city': 0, 'origin_country': 0, 'dest_city': 0, 'dest_country': 0, 'mode': 0} |
| origin_country within vocabulary   | critical | pass   | unexpected values: none                                                                                                                                 |
| dest_country within vocabulary     | critical | pass   | unexpected values: none                                                                                                                                 |
| mode within vocabulary             | critical | pass   | unexpected values: none                                                                                                                                 |
| product_category within vocabulary | critical | pass   | unexpected values: none                                                                                                                                 |
| weight positive                    | critical | pass   | 0 non-positive weights                                                                                                                                  |
| cost non-negative                  | critical | pass   | 0 negative costs                                                                                                                                        |
| ship not before order              | critical | pass   | 0 violations                                                                                                                                            |
| transit non-negative               | warning  | pass   | 0 negative transits                                                                                                                                     |
| imputation share                   | warning  | pass   | 9.10% of weights imputed (limit 15%)                                                                                                                    |
| cost per kg plausible              | warning  | pass   | median $0.91 per kg                                                                                                                                     |
| row count in expected band         | warning  | pass   | 4,200 rows                                                                                                                                              |

## Column profile

| column            | dtype          | nulls | distinct |
|-------------------|----------------|-------|----------|
| shipment_id       | string         | 0     | 4200     |
| order_id          | string         | 0     | 4200     |
| order_date        | datetime64[ns] | 0     | 360      |
| ship_date         | datetime64[ns] | 0     | 363      |
| delivery_date     | datetime64[ns] | 147   | 385      |
| origin_city       | string         | 0     | 58       |
| origin_country    | category       | 0     | 8        |
| dest_city         | string         | 0     | 296      |
| dest_country      | category       | 0     | 8        |
| mode              | category       | 0     | 4        |
| carrier           | string         | 88    | 7        |
| product_category  | category       | 0     | 7        |
| quantity          | int64          | 0     | 39       |
| weight_kg         | float64        | 0     | 3735     |
| weight_imputed    | bool           | 0     | 2        |
| freight_cost_usd  | float64        | 0     | 4059     |
| cost_imputed      | bool           | 0     | 2        |
| currency_resolved | str            | 0     | 4        |
| transit_days      | Int64          | 147   | 34       |
| delay_days        | Float64        | 147   | 20       |

## Headline figures

- median weight: 182.5 kg
- median freight cost: $209.36
- median transit: 6.0 days
- share of rows with late delivery (> 0 delay days): 1.7%
- weights imputed: 9.10%
- costs imputed: 5.24%
