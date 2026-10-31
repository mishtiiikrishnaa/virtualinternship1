"""Unit tests for the cleaning layer.

The tests are deliberately boring and specific. A test that asserts "cleaning
works" protects nothing; one that asserts 1 lb is 0.45359237 kg protects the
conversion table six months after everyone has forgotten why it exists.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import clean, validate


def test_country_aliases_land_on_one_canonical_value():
    log = clean.CleaningLog()
    series = pd.Series(["U.S.A.", "USA", "usa", " US ", "united states"])
    out = clean.canonicalise(series, clean.COUNTRY_LOOKUP, log, "country")
    assert out.dropna().unique().tolist() == ["United States"]
    assert out.notna().all()


def test_dotted_abbreviations_survive_punctuation_stripping():
    log = clean.CleaningLog()
    out = clean.canonicalise(pd.Series(["U.K.", "UAE", "P.R. China"]), clean.COUNTRY_LOOKUP, log, "country")
    assert out.tolist() == ["United Kingdom", "United Arab Emirates", "China"]


def test_unmapped_values_are_nulled_and_logged():
    log = clean.CleaningLog()
    out = clean.canonicalise(pd.Series(["Atlantis"]), clean.COUNTRY_LOOKUP, log, "country")
    assert out.isna().all()
    assert log.steps[0]["step"] == "unmapped country"


def test_mode_and_category_aliases():
    log = clean.CleaningLog()
    modes = clean.canonicalise(pd.Series(["Sea", "air freight", "TRUCK"]), clean.MODE_LOOKUP, log, "mode")
    cats = clean.canonicalise(pd.Series(["Pharma", "FMCG"]), clean.CATEGORY_LOOKUP, log, "product_category")
    assert modes.tolist() == ["Ocean", "Air", "Road"]
    assert cats.tolist() == ["Pharmaceuticals", "Consumer Goods"]


def test_mixed_date_formats_all_parse():
    log = clean.CleaningLog()
    series = pd.Series(["2025-03-04", "04/03/2025", "March 4, 2025", "2025/03/04"])
    out = clean.parse_mixed_dates(series, log, "order_date")
    assert out.nunique() == 1
    assert out.iloc[0] == pd.Timestamp("2025-03-04")


def test_unparseable_dates_are_counted_not_invented():
    log = clean.CleaningLog()
    out = clean.parse_mixed_dates(pd.Series(["2025-03-04", "not a date", "31/02/2025"]), log, "order_date")
    assert out.isna().sum() == 2
    assert log.steps[0]["rows_affected"] == 2


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$1,240.50", 1240.50),
        ("₹9,052.19", 9052.19),
        ("EUR 890.00", 890.00),
        ("1.234,56", 1234.56),
        ("€-42.10", -42.10),
        ("(1,000.00)", -1000.00),
        ("", np.nan),
    ],
)
def test_numeric_parser_handles_freight_notation(raw, expected):
    value = clean._numeric(raw)
    if np.isnan(expected):
        assert np.isnan(value)
    else:
        assert value == pytest.approx(expected)


def test_weight_conversion_uses_exact_pound():
    frame = pd.DataFrame({"weight_value": ["100", "100", "1"], "weight_unit": ["kg", "lb", "t"]})
    log = clean.CleaningLog()
    out = clean.parse_weight(frame, log)
    assert out.iloc[0] == pytest.approx(100.0)
    assert out.iloc[1] == pytest.approx(45.359237)
    assert out.iloc[2] == pytest.approx(1000.0)


def test_sentinel_and_zero_weights_are_rejected():
    frame = pd.DataFrame(
        {"weight_value": ["999999", "0", "12.5"], "weight_unit": ["kg", "kg", "kg"]}
    )
    log = clean.CleaningLog()
    out = clean.parse_weight(frame, log)
    assert out.isna().sum() == 2
    assert log.steps[0]["rows_affected"] == 2


def test_currency_printed_on_the_amount_beats_the_column():
    frame = pd.DataFrame({"freight_cost": ["$500.00", "500.00"], "currency": ["EUR", "EUR"]})
    log = clean.CleaningLog()
    usd, resolved = clean.parse_money(frame, log)
    assert resolved.tolist() == ["USD", "EUR"]
    assert usd.iloc[0] == pytest.approx(500.0)
    assert usd.iloc[1] == pytest.approx(545.0)


def test_deduplicate_keeps_the_latest_state_of_a_shipment():
    frame = pd.DataFrame(
        {
            "shipment_id": ["SHP-00001", "SHP-00001", "SHP-00002"],
            "freight_cost": ["100", "150", "200"],
            "currency": ["USD", "USD", "USD"],
        }
    )
    out = clean.deduplicate(frame, clean.CleaningLog())
    assert len(out) == 2
    assert float(out.loc[out["shipment_id"] == "SHP-00001", "freight_cost"].iloc[0]) == 150.0


def test_imputation_flags_every_filled_value():
    frame = pd.DataFrame(
        {
            "mode": pd.Series(["Air"] * 4, dtype="category"),
            "product_category": pd.Series(["Apparel"] * 4, dtype="category"),
            "weight_kg": [100.0, 110.0, 120.0, np.nan],
        }
    )
    log = clean.CleaningLog()
    filled = clean.impute_weight(frame, log)
    assert filled.isna().sum() == 0
    assert filled.iloc[-1] == pytest.approx(110.0)
    assert log.steps[0]["rows_affected"] == 1


def test_validation_catches_duplicate_keys():
    frame = pd.DataFrame(
        {
            "shipment_id": ["SHP-00001", "SHP-00001"],
            "order_id": ["ORD-1", "ORD-2"],
            "order_date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "ship_date": pd.to_datetime(["2025-01-02", "2025-01-03"]),
            "delivery_date": pd.to_datetime(["2025-01-05", "2025-01-06"]),
            "origin_city": ["Newark", "Newark"],
            "dest_city": ["Hamburg", "Hamburg"],
            "origin_country": pd.Series(["United States"] * 2, dtype="category"),
            "dest_country": pd.Series(["Germany"] * 2, dtype="category"),
            "mode": pd.Series(["Air"] * 2, dtype="category"),
            "product_category": pd.Series(["Apparel"] * 2, dtype="category"),
            "quantity": [1, 2],
            "weight_kg": [10.0, 12.0],
            "weight_imputed": [False, False],
            "freight_cost_usd": [100.0, 120.0],
            "cost_imputed": [False, False],
            "transit_days": pd.array([3, 4], dtype="Int64"),
        }
    )
    checks = {c.name: c for c in validate.run_checks(frame)}
    assert not checks["unique shipment_id"].passed
    assert checks["unique shipment_id"].severity == "critical"
    assert checks["weight positive"].passed
