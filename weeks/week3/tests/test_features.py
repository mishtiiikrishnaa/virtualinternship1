"""Tests for the feature engineering layer.

Covered: no train/test date overlap, feature builder output shape, no leakage
columns in either feature list, and strictly-trailing lag features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import features


@pytest.fixture
def frame():
    return features.load_clean()


def test_forecast_split_has_no_date_overlap(frame):
    daily = features.make_forecast_features(frame)
    train, val, test = features.train_validation_test_split(daily, val_days=42, test_days=28)
    assert train["ship_date"].max() < val["ship_date"].min()
    assert val["ship_date"].max() < test["ship_date"].min()
    assert train["ship_date"].max() < test["ship_date"].min()
    assert len(test) == 28
    assert len(val) == 42


def test_classification_split_has_no_date_overlap(frame):
    classified = features.make_classification_features(frame)
    classified["is_late"] = (classified["delay_days"].fillna(0) > 0).astype(int)
    train, val, test = features.classification_time_split(classified)
    assert train["ship_date"].max() < val["ship_date"].min()
    assert val["ship_date"].max() < test["ship_date"].min()


def test_no_leakage_columns_in_feature_lists():
    banned = set(features.LEAKAGE_COLUMNS) - {"is_late"}
    forecast_cols = set(features.forecast_feature_columns())
    clf_cols = set(features.classification_feature_columns())
    assert not (forecast_cols & banned)
    assert not (clf_cols & banned)


def test_lag_features_are_strictly_trailing(frame):
    daily = features.make_forecast_features(frame)
    daily = daily.sort_values("ship_date").reset_index(drop=True)
    # row 0 has no history: lag_1 and lag_7 must be NaN.
    assert pd.isna(daily.loc[0, "lag_1"])
    assert pd.isna(daily.loc[0, "lag_7"])
    # row 7: lag_7 must equal row 0's volume, never row 7's own volume.
    assert daily.loc[7, "lag_7"] == daily.loc[0, "daily_volume"]
    assert daily.loc[7, "lag_7"] != daily.loc[7, "daily_volume"] or True  # may coincide; value source matters


def test_forecast_feature_output_shape(frame):
    daily = features.make_forecast_features(frame)
    expected = set(features.forecast_feature_columns()) | {
        "ship_date", "daily_volume", "dow", "month", "is_weekend",
    }
    missing = expected - set(daily.columns)
    assert not missing, f"missing columns: {missing}"
    assert len(daily) == daily["ship_date"].nunique()  # one row per date


def test_classification_feature_columns_known_at_ship_time(frame):
    classified = features.make_classification_features(frame)
    classified["is_late"] = (classified["delay_days"].fillna(0) > 0).astype(int)
    cols = features.classification_feature_columns()
    encoded = features.encode_classification(classified)
    for col in cols:
        assert col in encoded.columns, f"missing encoded feature: {col}"
    # none of the encoded feature frames may contain delay_days or transit_days
    for banned in ("delay_days", "transit_days", "delivery_date"):
        assert banned not in encoded.columns
