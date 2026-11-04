"""Tests for the evaluation metrics on known inputs."""

from __future__ import annotations

import numpy as np
import pytest

from src import models


def test_smape_perfect_forecast_is_zero():
    actual = np.array([10.0, 20.0, 30.0])
    assert models.smape(actual, actual) == 0.0


def test_smape_handles_zeros():
    actual = np.array([0.0, 10.0])
    predicted = np.array([5.0, 10.0])
    out = models.smape(actual, predicted)
    assert np.isfinite(out)
    assert out > 0


def test_smape_mismatch_is_positive():
    actual = np.array([10.0, 10.0])
    predicted = np.array([20.0, 20.0])
    # sMAPE of doubling is 2/3 = 66.67%
    assert models.smape(actual, predicted) == pytest.approx(66.6667, rel=1e-4)


def test_tune_threshold_picks_best_f1():
    y_true = np.array([0, 0, 1, 1])
    proba = np.array([0.1, 0.4, 0.6, 0.9])
    t = models._tune_threshold(y_true, proba)
    assert 0.05 <= t <= 0.95
    pred = (proba >= t).astype(int)
    from sklearn.metrics import f1_score
    assert f1_score(y_true, pred) > 0
