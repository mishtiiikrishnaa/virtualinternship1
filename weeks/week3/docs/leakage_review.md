# Leakage review — week 3

The following columns are consequences of the outcome or describe the future relative to ship_date. They are banned from every feature matrix, in both models:

- `delivery_date` — the outcome itself: when the shipment arrived
- `transit_days` — derived from delivery_date minus ship_date
- `delay_days` — derived from transit_days against the per-mode promise
- `is_late` — derived from delay_days; the classification target

Lag and rolling features in the forecast model end at t-1: row t never sees its own value. The test in `tests/test_features.py` asserts that no leakage column appears in either feature list, and that the forecast split has no train/test date overlap.
