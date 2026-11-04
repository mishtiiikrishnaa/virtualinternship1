"""Tests for model reproducibility and behaviour under the fixed seed."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import features, models


@pytest.fixture
def classified():
    frame = features.load_clean()
    out = features.make_classification_features(frame)
    out["is_late"] = (out["delay_days"].fillna(0) > 0).astype(int)
    return out


def test_forecast_reproducible_under_seed():
    frame = features.load_clean()
    daily = features.make_forecast_features(frame)
    train, val, test = features.train_validation_test_split(daily, val_days=42, test_days=28)
    r1 = models.train_forecast_models(train, val, test)
    r2 = models.train_forecast_models(train, val, test)
    for name in r1:
        a = r1[name].predictions
        b = r2[name].predictions
        assert np.allclose(a, b), f"{name} not reproducible"


def test_classification_reproducible_under_seed(classified):
    train, val, test = features.classification_time_split(classified)
    train_enc = features.encode_classification(train)
    val_enc = features.encode_classification(val, fit=train)
    test_enc = features.encode_classification(test, fit=train)
    cols = [c for c in train_enc.columns if c not in ("shipment_id", "order_id",
        "order_date", "ship_date", "delivery_date", "origin_city", "origin_country",
        "dest_city", "dest_country", "mode", "carrier", "product_category",
        "currency_resolved", "weight_imputed", "cost_imputed", "transit_days",
        "delay_days", "is_late")]
    r1 = models.tune_classification_models(train_enc, val_enc, test_enc)
    r2 = models.tune_classification_models(train_enc, val_enc, test_enc)
    for name in r1:
        assert r1[name].f1 == pytest.approx(r2[name].f1)
        assert np.allclose(r1[name].y_proba, r2[name].y_proba)


def test_gradient_boosting_beats_naive_on_test(classified):
    frame = features.load_clean()
    daily = features.make_forecast_features(frame)
    train, val, test = features.train_validation_test_split(daily, val_days=42, test_days=28)
    results = models.train_forecast_models(train, val, test)
    naive = results["naive"].test_mae
    gb = results["gradient_boosting"].test_mae
    assert gb < naive, f"gradient boosting {gb:.2f} did not beat naive {naive:.2f}"
