"""Extended evaluation metrics for the week 4 decision-support addendum.

Builds on the week 3 confusion matrices: full class-level statistics,
row-normalised matrices, calibration, threshold sweeps and a split-conformal
prediction interval with an empirical coverage check.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def confusion_stats(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Counts, row-normalised matrix, per-class and macro/weighted statistics."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    cm = np.array([[tn, fp], [fn, tp]])
    # row-normalised: rows are actual outcomes, columns predictions
    with np.errstate(invalid="ignore"):
        row_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    per_class = {
        "positive (late)": {
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        },
        "negative (on time)": {
            "specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else float("nan"),
            "true_negative_rate": float(tn / (tn + fp)) if (tn + fp) > 0 else float("nan"),
        },
    }
    return {
        "counts": {
            "true_positive": int(tp), "false_negative": int(fn),
            "false_positive": int(fp), "true_negative": int(tn),
        },
        "matrix": cm.tolist(),
        "row_normalised": {
            str(actual): {str(pred): float(row_norm[i, j])
                          for j, pred in enumerate(["on time", "late"])}
            for i, actual in enumerate(["on time", "late"])
        },
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "prevalence": float(y_true.mean()),
        "positive": {
            "precision": per_class["positive (late)"]["precision"],
            "recall": per_class["positive (late)"]["recall"],
            "f1": per_class["positive (late)"]["f1"],
        },
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }


def calibration_stats(y_true: np.ndarray, proba: np.ndarray, n_bins: int = 10) -> dict:
    """Reliability: mean predicted probability against observed rate per bin."""
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    edges = list(zip(bins[:-1], bins[1:]))
    rows = []
    for lo, hi in edges:
        mask = (proba >= lo) & (proba < hi)
        if mask.sum() == 0:
            continue
        rows.append({
            "bin": f"{lo:.1f}-{hi:.1f}",
            "n": int(mask.sum()),
            "mean_predicted": float(proba[mask].mean()),
            "observed_rate": float(y_true[mask].mean()),
            "accuracy": float(((proba[mask] >= 0.5).astype(int) == y_true[mask]).mean()),
        })
    predicted = float(proba.mean())
    observed = float(y_true.mean())
    return {
        "n_bins": n_bins,
        "bins": rows,
        "mean_predicted": predicted,
        "observed_rate": observed,
        "brier_score": float(brier_score_loss(y_true, proba)),
        "calibration_slope": float(np.corrcoef(proba, y_true)[0, 1] or float("nan")),
    }


def threshold_sweep(
    y_true: np.ndarray, proba: np.ndarray, thresholds: Sequence[float]
) -> list[dict]:
    """Precision/recall/F1/accuracy at each candidate threshold on one frame."""
    out = []
    for t in thresholds:
        pred = (np.asarray(proba) >= t).astype(int)
        out.append({
            "threshold": float(t),
            "accuracy": float(accuracy_score(y_true, pred)),
            "precision": float(precision_score(y_true, pred, zero_division=0)),
            "recall": float(recall_score(y_true, pred, zero_division=0)),
            "f1": float(f1_score(y_true, pred, zero_division=0)),
        })
    return out


def cost_weighted_metrics(
    y_true: np.ndarray, proba: np.ndarray, threshold: float,
    cost_false_negative: float, cost_false_positive: float,
) -> dict:
    """Expected cost of a decision rule under explicit FP and FN costs.

    cost_false_negative: cost of a missed late shipment (a broken promise).
    cost_false_positive: cost of a wasted triage escalation (an on-time
    shipment pulled into an expeditor's queue).
    """
    pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(np.asarray(y_true), pred).ravel()
    rule_cost = cost_false_positive * fp + cost_false_negative * fn
    # baseline policies expressed in the same units
    no_triage_cost = cost_false_negative * int(np.asarray(y_true).sum())  # every late missed
    triage_all_cost = cost_false_positive * int((pred == 1).sum())        # every shipment escalated
    return {
        "threshold": float(threshold),
        "predicted_positive": int((pred == 1).sum()),
        "true_positive": int(tp),
        "false_negative": int(fn),
        "false_positive": int(fp),
        "true_negative": int(tn),
        "precision": float(precision_score(np.asarray(y_true), pred, zero_division=0)),
        "recall": float(recall_score(np.asarray(y_true), pred, zero_division=0)),
        "f1": float(f1_score(np.asarray(y_true), pred, zero_division=0)),
        "expected_cost_rule": float(rule_cost),
        "expected_cost_no_triage": float(no_triage_cost),
        "expected_cost_triage_all": float(triage_all_cost),
        "cost_of_missed_late": float(cost_false_negative),
        "cost_of_wasted_triage": float(cost_false_positive),
    }


def conformal_quantile(y_true: np.ndarray, proba: np.ndarray, level: float = 0.9) -> float:
    """Split-conformal quantile on a calibration set (in probability space)."""
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    scores = np.abs(y_true - proba)
    return float(np.quantile(scores, 1 - (1 - level), method="higher"))


def conformal_coverage(
    y_true: np.ndarray, proba: np.ndarray, quantile: float, level: float = 0.9,
) -> dict:
    """Empirical coverage of the conformal interval on a held-out set."""
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    within = np.abs(y_true - proba) <= quantile
    return {
        "level": level,
        "quantile": quantile,
        "n": int(len(y_true)),
        "covered": int(within.sum()),
        "coverage": float(within.mean()),
    }


def interval_coverage(
    actuals: np.ndarray, lower: np.ndarray, upper: np.ndarray, nominal: float = 0.95,
) -> dict:
    """Fraction of held-out actuals inside the forecast interval band."""
    actuals = np.asarray(actuals, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    inside = (actuals >= lower) & (actuals <= upper)
    return {
        "nominal": nominal,
        "covered": int(inside.sum()),
        "n": int(len(actuals)),
        "coverage": float(inside.mean()),
        "mean_width": float((upper - lower).mean()),
    }
