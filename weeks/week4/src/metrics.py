"""Extended evaluation metrics for the week 4 decision-support addendum.

Builds on the week 3 confusion matrices: full class-level statistics,
row-normalised matrices, calibration, threshold sweeps and a split-conformal
prediction interval with an empirical coverage check.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy import stats
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


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval with continuity correction / asymptotic formulation for a binomial proportion."""
    if n <= 0:
        return 0.0, 0.0
    p = float(k) / float(n)
    z = float(stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    denom = 1.0 + (z**2) / n
    centre = (p + (z**2) / (2.0 * n)) / denom
    margin = (z * np.sqrt(p * (1.0 - p) / n + (z**2) / (4.0 * (n**2)))) / denom
    return max(0.0, float(centre - margin)), min(1.0, float(centre + margin))


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

    The escalation cost applies to every flagged shipment (true positives and
    false positives), and missed late shipments incur the full false negative cost.
    """
    pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(np.asarray(y_true), pred).ravel()
    flagged = int(tp) + int(fp)
    missed = int(fn)
    rule_cost = cost_false_positive * flagged + cost_false_negative * missed
    no_triage_cost = cost_false_negative * int(np.asarray(y_true).sum())
    triage_all_cost = cost_false_positive * int(len(y_true))
    return {
        "threshold": float(threshold),
        "predicted_positive": flagged,
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
        "expected_cost_saving": float(no_triage_cost - rule_cost),
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


def baseline_brier(y_true: np.ndarray, prevalence: float | None = None) -> float:
    """Brier score of the constant predictor sitting at the base rate.

    A constant predictor that always predicts the observed prevalence scores
    Brier = mean((y - p)^2) = p * (1 - p); this is the honest no-skill baseline
    for a probabilistic classifier on a skewed base rate.
    """
    y_true = np.asarray(y_true, dtype=int)
    p = float(y_true.mean()) if prevalence is None else float(prevalence)
    return float(np.mean((y_true - p) ** 2))


def brier_skill(model_brier: float, base_brier: float) -> float:
    """Brier skill score: negative means the model is worse than the base rate."""
    if base_brier <= 0:
        return float("nan")
    return float(1.0 - model_brier / base_brier)


def policy_costs(
    y_true: np.ndarray, pred: np.ndarray, cost_false_negative: float,
    cost_false_positive: float, cost_per_action: float,
) -> dict:
    """One policy-cost table computed from the confusion matrix and the costs.

    Policies compared on the same shipment set:
      no_triage        every positive is missed -> cost_false_negative * n_pos
      triage_all       every shipment is escalated -> cost_per_action * n
      model            escalation on flagged (tp + fp) plus missed (fn)
      perfect          no missed promise at all -> 0
    The escalation cost is charged to every flagged shipment, including true
    positives, because an escalation that prevents a miss is itself an action.
    """
    y_true = np.asarray(y_true, dtype=int)
    pred = np.asarray(pred, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    flagged = int(tp) + int(fp)
    missed = int(fn)
    return {
        "no_triage": float(cost_false_negative * int(np.asarray(y_true).sum())),
        "triage_all": float(cost_per_action * int(len(y_true))),
        "model": float(cost_per_action * flagged + cost_false_negative * missed),
        "perfect": 0.0,
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "n_shipments": int(len(y_true)),
        "n_flagged": flagged,
        "n_missed": missed,
        "saving": float(cost_false_negative * int(np.asarray(y_true).sum()) - (cost_per_action * flagged + cost_false_negative * missed)),
        "cost_of_missed_late_shipments": float(cost_false_negative),
        "cost_of_wasted_triage": float(cost_per_action),
    }


def bootstrap_saving_and_auc(
    y_true: np.ndarray, proba: np.ndarray, threshold: float,
    cost_fn: float, cost_fp: float, n_boot: int = 2000, seed: int = 42,
) -> dict:
    """Seeded non-parametric bootstrap (2,000 resamples) for triage saving and ROC-AUC."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    n = len(y_true)
    savings = []
    aucs = []

    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        y_b = y_true[idx]
        p_b = proba[idx]
        pred_b = (p_b >= threshold).astype(int)
        flagged = int(pred_b.sum())
        fn = int(((pred_b == 0) & (y_b == 1)).sum())
        no_triage = cost_fn * int(y_b.sum())
        policy = cost_fp * flagged + cost_fn * fn
        savings.append(no_triage - policy)
        if len(np.unique(y_b)) > 1:
            aucs.append(roc_auc_score(y_b, p_b))

    s_low, s_mid, s_high = np.percentile(savings, [2.5, 50.0, 97.5])
    s_p10, s_p50, s_p90 = np.percentile(savings, [10.0, 50.0, 90.0])
    auc_low, auc_mid, auc_high = np.percentile(aucs, [2.5, 50.0, 97.5])

    return {
        "n_boot": n_boot,
        "seed": seed,
        "saving_mean": float(np.mean(savings)),
        "saving_ci_95": [float(s_low), float(s_high)],
        "saving_percentiles": {"p10": float(s_p10), "p50": float(s_p50), "p90": float(s_p90)},
        "roc_auc_mean": float(np.mean(aucs)),
        "roc_auc_ci_95": [float(auc_low), float(auc_high)],
    }


def quantile_bin_reliability(y_true: np.ndarray, proba: np.ndarray, n_bins: int = 5) -> list[dict]:
    """Quantile-binned reliability evaluation with sample counts and Wilson intervals."""
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    import pandas as pd
    df = pd.DataFrame({"y": y_true, "p": proba})
    df["qbin"] = pd.qcut(df["p"], q=n_bins, duplicates="drop")
    rows = []
    for qb, grp in df.groupby("qbin", observed=False):
        n = int(len(grp))
        k = int(grp["y"].sum())
        obs = float(k / n) if n > 0 else 0.0
        ci_lo, ci_hi = wilson_interval(k, n, confidence=0.95)
        rows.append({
            "bin": str(qb),
            "n": n,
            "late_events": k,
            "mean_score": float(grp["p"].mean()),
            "observed_rate": obs,
            "ci_95": [ci_lo, ci_hi],
        })
    return rows

