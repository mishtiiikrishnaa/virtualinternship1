"""Operational decision support for week 4.

Turns the week 3 forecasts and classifiers into explicit, back-tested
decision rules: capacity planning, triage escalation, service-level
selection and retraining triggers. Every decision carries a numeric trigger,
an expected impact range with arithmetic, and the cost of a wrong call.
"""

from __future__ import annotations

from pathlib import Path
import json
from typing import Sequence

import numpy as np
import pandas as pd

from src import metrics

ROOT = Path(__file__).resolve().parents[1]


# -------------------------------------------------------------------------- #
# D-1: capacity planning from the demand forecast
# -------------------------------------------------------------------------- #
def forecast_backtest(
    result, test_daily: pd.DataFrame, safety_z: float = 1.96,
) -> dict:
    """Compare the forecast-plus-interval capacity policy against a simple
    baseline (rolling 7-day mean) on the held-out period, in shipment-days."""
    pred = np.asarray(result.predictions, dtype=float)
    upper = np.asarray(result.interval_upper, dtype=float)
    lower = np.asarray(result.interval_lower, dtype=float)
    actual = np.asarray(result.actuals, dtype=float)
    dates = pd.to_datetime(pd.Series(result.dates).reset_index(drop=True))
    planned_model = pred + safety_z * (upper - pred)  # upper bound of the band
    planned_baseline = test_daily.sort_values("ship_date")["daily_volume"].rolling(
        7, min_periods=1).mean().to_numpy()
    planned_model_full = pd.Series(planned_model, index=dates).reindex(
        pd.to_datetime(test_daily["ship_date"])).to_numpy()
    baseline = planned_baseline[: len(planned_model_full)]
    interval_half_width = float(np.mean((upper - pred) / 2.0))

    under_model = int((actual > planned_model_full).sum())
    under_baseline = int((actual > baseline).sum())
    # shipment-days of under-capacity on the held-out period
    ud_model = float(np.maximum(actual - planned_model_full, 0.0).sum())
    ud_baseline = float(np.maximum(actual - baseline, 0.0).sum())
    return {
        "decision_id": "D-1",
        "horizon_days": int(len(actual)),
        "safety_z": safety_z,
        "interval_half_width": interval_half_width,
        "baseline_policy": "rolling 7-day mean of realised demand",
        "model_policy": "point forecast + upper prediction interval bound",
        "under_capacity_events_model": under_model,
        "under_capacity_events_baseline": under_baseline,
        "under_capacity_shipment_days_model": round(ud_model, 2),
        "under_capacity_shipment_days_baseline": round(ud_baseline, 2),
        "avoided_shipment_days": round(ud_baseline - ud_model, 2),
        "baseline_mae": float(np.mean(np.abs(actual - baseline))),
        "model_mae": float(result.test_mae),
        "interval_upper_bound_mean": float(planned_model_full.mean()),
        "interval_half_width": interval_half_width,
    }


# -------------------------------------------------------------------------- #
# D-2: triage escalation with cost-weighted threshold
# -------------------------------------------------------------------------- #
def triage_backtest(
    clf_result, cost_false_negative: float, cost_false_positive: float,
) -> dict:
    stats = {
        "threshold": float(clf_result.threshold),
        "precision": float(clf_result.precision),
        "recall": float(clf_result.recall),
        "f1": float(clf_result.f1),
        "confusion": clf_result.confusion,
        "predicted_positive": int((clf_result.y_proba >= clf_result.threshold).sum()),
        "expected_cost_rule": float(
            cost_false_positive * clf_result.confusion[0][1]
            + cost_false_negative * clf_result.confusion[1][0]
        ),
        "expected_cost_no_triage": float(
            cost_false_negative * int(clf_result.y_true.sum())),
        "expected_cost_triage_all": float(
            cost_false_positive * int((clf_result.y_proba >= 0.5).sum())),
    }
    stats["cost_of_missed_late_shipments"] = float(cost_false_negative)
    stats["cost_of_wasted_triage"] = float(cost_false_positive)
    stats["expected_cost_savings_rule_vs_nontriage"] = float(
        stats["expected_cost_no_triage"] - stats["expected_cost_rule"])
    return stats


def cost_optimised_threshold(
    y_true: np.ndarray, proba: np.ndarray, cost_false_negative: float,
    cost_false_positive: float, grid: Sequence[float] | None = None,
) -> dict:
    """Threshold on the validation window that minimises expected triage cost.

    expected cost of a rule = cost_false_positive * flagged + cost_false_negative * missed,
    minimised over a grid of candidate thresholds on the validation probabilities.
    """
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    if grid is None:
        grid = [0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50]
    best_t, best_cost = None, None
    rows = []
    for t in grid:
        pred = (proba >= t).astype(int)
        tn, fp, fn, tp = metrics.confusion_matrix(y_true, pred).ravel()
        flagged = int(tp) + int(fp)
        missed = int(fn)
        cost = float(cost_false_positive * flagged + cost_false_negative * missed)
        rows.append({
            "threshold": float(t),
            "expected_cost": cost,
            "flagged": flagged,
            "missed": missed,
        })
        if best_cost is None or cost < best_cost:
            best_t, best_cost = float(t), cost
    return {
        "threshold": best_t,
        "expected_cost": float(best_cost),
        "candidates": rows,
        "cost_false_negative": float(cost_false_negative),
        "cost_false_positive": float(cost_false_positive),
    }


# -------------------------------------------------------------------------- #
# decision registry
# -------------------------------------------------------------------------- #
def build_decision_register() -> list[dict]:
    return [
        {
            "decision_id": "D-1",
            "question": "how much dispatch buffer / safety stock should operations plan",
            "decision": "plan capacity at the point forecast plus the upper bound of its "
                        "prediction interval, refreshed every planning cycle",
            "trigger_metric": "14-day ahead ridge forecast and its interval",
            "trigger_threshold": "upper bound = forecast + 1.96 x residual sd (sigma)",
            "action": "commit dispatch capacity and dock slots against the interval bound",
            "owner": "operations / capacity planning",
            "expected_impact_range": {
                "low": "avoided under-capacity shipment-days bounded by the interval width",
                "high": "avoided under-capacity shipment-days from the point forecast alone",
            },
            "cost_of_wrong_call": "under-planning shows up as under-capacity shipment-days; "
                                 "over-planning as unused capacity",
            "data_required": "daily shipment volume history and a time-ordered forecast",
            "review_cadence": "per planning cycle (weekly at most)",
        },
        {
            "decision_id": "D-2",
            "question": "which at-risk shipments should an expeditor triage, and at what "
                        "threshold",
            "decision": "escalate shipments whose late model probability exceeds the "
                        "cost-weighted threshold",
            "trigger_metric": "gradient boosting probability and its conformal interval",
            "trigger_threshold": "cost-weighted threshold from the validation set",
            "action": "dispatch expeditor attention; escalate to carrier ops when flagged",
            "owner": "dispatch / customer operations",
            "expected_impact_range": {
                "low": "expected cost saving from triage of the flagged share",
                "high": "expected cost saving if the threshold were lowered to recall-optimal",
            },
            "cost_of_wrong_call": "false negative (missed late) costs the promise; false "
                                 "positive (wasted triage) costs expeditor time",
            "data_required": "booking-time features plus confirmed delivery outcomes",
            "review_cadence": "daily triage list refresh; threshold review quarterly",
        },
        {
            "decision_id": "D-3",
            "question": "where should service effort and capacity be concentrated",
            "decision": "hold mode-specific service-level promises and remediate the weakest "
                        "carrier-lane pairs before rebalancing volume",
            "trigger_metric": "late share by mode and carrier-lane on-time rate",
            "trigger_threshold": "carrier on-time rate below network cluster median",
            "action": "formal improvement plan for weak carriers; shift discretionary air "
                      "volume where the promise allows",
            "owner": "procurement / network planning",
            "expected_impact_range": {
                "low": "partial closure of the carrier gap (31.3pp network spread)",
                "high": "full closure of the two-tier gap",
            },
            "cost_of_wrong_call": "acting on a lane with insufficient sample size as if it were "
                                 "a real gap",
            "data_required": "per-lane sample sizes and on-time outcomes",
            "review_cadence": "per contract quarter",
        },
        {
            "decision_id": "D-4",
            "question": "when should the model be retrained and the decisions re-visited",
            "decision": "retire or retrain when the coverage of the prediction interval or the "
                        "performance metric drifts",
            "trigger_metric": "interval coverage and metric drift (PSI / KS)",
            "trigger_threshold": "coverage falls below the nominal level",
            "action": "retrain on rolling window; re-derive threshold and decisions",
            "owner": "data science / platform",
            "expected_impact_range": {
                "low": "conservative retrain cadence",
                "high": "continuous monitoring and immediate retraining",
            },
            "cost_of_wrong_call": "acting on a drifted model or ignoring drift",
            "data_required": "fresh labelled shipments and forecast outcomes",
            "review_cadence": "monthly monitoring, retraining per trigger",
        },
    ]
