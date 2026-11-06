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


def test_baseline_brier_is_base_rate_score():
    y = np.array([0, 0, 1, 1])
    base = metrics.baseline_brier(y, prevalence=0.5)
    assert abs(base - 0.25) < 1e-9
    y2 = np.array([0, 0, 1])
    base2 = metrics.baseline_brier(y2, prevalence=float(np.array([0, 0, 1]).mean()))
    assert abs(base2 - float(np.mean((y2 - np.array([0, 0, 1]).mean()) ** 2))) < 1e-9


def test_brier_skill_is_negative_when_model_is_worse_than_base_rate():
    skill = metrics.brier_skill(model_brier=0.025, base_brier=0.0173)
    assert skill < 0


def test_policy_costs_recompute_from_confusion_matrix():
    # test window: 851 shipments, 15 late; at the chosen threshold 60 flagged
    # (7 tp + 53 fp), 8 missed -> tn=783, fp=53, fn=8, tp=7
    y_true = np.array([0] * 836 + [1] * 15)
    pred = np.zeros(851, dtype=int)
    pred[0:53] = 1        # false positives: on-time flagged
    pred[836:843] = 1     # true positives: late flagged (7 of the 15 late)
    out = metrics.policy_costs(y_true, pred, cost_false_negative=1500.0,
                               cost_false_positive=60.0, cost_per_action=60.0)
    assert out["no_triage"] == pytest.approx(1500.0 * 15)
    assert out["triage_all"] == pytest.approx(60.0 * 851)
    assert out["model"] == pytest.approx(60.0 * 60 + 1500.0 * 8)
    assert out["perfect"] == 0.0
    assert out["n_flagged"] == 60 and out["n_missed"] == 8
