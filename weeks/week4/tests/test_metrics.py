"""Tests for the week 4 extended metrics."""

from __future__ import annotations

import numpy as np
import pytest

from src import metrics


def test_confusion_counts():
    stats = metrics.confusion_stats(
        np.array([0, 0, 1, 1]), np.array([0, 1, 0, 1]))
    assert stats["counts"]["true_positive"] == 1
    assert stats["counts"]["false_negative"] == 1
    assert stats["counts"]["false_positive"] == 1
    assert stats["counts"]["true_negative"] == 1


def test_confusion_row_normalised_sums_to_one():
    stats = metrics.confusion_stats(
        np.array([0, 0, 1, 1]), np.array([0, 1, 0, 1]))
    rows = stats["row_normalised"]
    assert abs(sum(rows["on time"].values()) - 1.0) < 1e-9
    assert abs(sum(rows["late"].values()) - 1.0) < 1e-9


def test_calibration_brier_is_a_number():
    stats = metrics.calibration_stats(np.array([0, 1, 1, 0]), np.array([0.1, 0.8, 0.9, 0.2]))
    assert stats["brier_score"] >= 0
    assert len(stats["bins"]) > 0


def test_conformal_coverage_within_bounds():
    q = metrics.conformal_quantile(np.array([0, 1, 1, 0]), np.array([0.2, 0.8, 0.9, 0.1]), level=0.9)
    cov = metrics.conformal_coverage(np.array([0, 1, 1, 0]), np.array([0.2, 0.8, 0.9, 0.1]), q, level=0.9)
    assert cov["n"] == 4
    assert 0 <= cov["coverage"] <= 1


def test_interval_coverage_fraction():
    cov = metrics.interval_coverage(
        np.array([1.0, 2.0, 3.0]), np.array([0.5, 1.5, 2.5]), np.array([1.5, 2.5, 3.5]), nominal=0.95)
    assert cov["covered"] == 3
    assert cov["coverage"] == 1.0
    assert cov["mean_width"] > 0


def test_cost_weighted_metrics_penalises_miss_and_false_positive():
    out = metrics.cost_weighted_metrics(
        np.array([0, 1]), np.array([0.9, 0.2]),
        threshold=0.5, cost_false_negative=1500.0, cost_false_positive=60.0)
    assert out["false_negative"] == 1
    assert out["false_positive"] == 1
    assert out["expected_cost_rule"] > 0
