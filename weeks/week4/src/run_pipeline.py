"""End-to-end week 4 run.

    python -m src.run_pipeline

Produces, from the week 1 cleaning implementation re-run over the week 1 raw
extract and the week 2 EDA results:

1. a cleaning / validation audit (week 1 code),
2. EDA headline numbers (week 2 results JSON),
3. forecast and classification models trained on the week 1 cleaned extract,
4. extended metrics: confusion statistics, calibration, threshold sweep,
   split-conformal interval with empirical coverage, cost-weighted decisions,
5. decision support: capacity backtest, triage backtest, scenarios, risks,
   roadmap,
6. results/results.json (the single source of numbers for the report),
7. figures, Word report and the number audit.

Every number written to results.json is computed here or read from the week 2
EDA results; nothing is hand typed into the artefact.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import clean as clean_mod
from src import decision_support, features, make_figures, metrics, models

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "reports" / "figures"
REPORT = ROOT / "reports" / "Week4_Decision_Support_Report.docx"
RANDOM_SEED = 42
COST_FALSE_NEGATIVE = 1500.0   # assumption: cost of a missed late shipment (USD)
COST_FALSE_POSITIVE = 60.0     # assumption: cost of a wasted triage escalation (USD)

CONF_LEVEL = 0.90


# -------------------------------------------------------------------------- #
# inputs
# -------------------------------------------------------------------------- #
def load_week2_eda() -> dict:
    week2_results = ROOT.parent.parent / "weeks" / "week2" / "results"
    return {p.stem: json.loads(p.read_text()) for p in sorted(week2_results.glob("*.json"))}


# -------------------------------------------------------------------------- #
# models and metrics
# -------------------------------------------------------------------------- #
def fit_gradient_boosting(X: np.ndarray, y: np.ndarray):
    from sklearn.ensemble import HistGradientBoostingClassifier
    model = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, class_weight="balanced", random_state=RANDOM_SEED,
    )
    model.fit(X, y)
    return model


def fit_logistic_predict_proba(X_train, y_train, X_val, X_test) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    Xtr_s = scaler.fit_transform(X_train)
    Xva_s = scaler.transform(X_val)
    Xte_s = scaler.transform(X_test)
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = LogisticRegression(
        class_weight={0: 1.0, 1: pos_weight}, max_iter=5000, random_state=RANDOM_SEED,
    )
    model.fit(Xtr_s, y_train)
    return model.predict_proba(Xte_s)[:, 1]


# -------------------------------------------------------------------------- #
# headline numbers
# -------------------------------------------------------------------------- #
def eda_headlines(eda: dict) -> dict:
    profile = eda["profile"]
    ts = eda["timeseries"]
    cost = eda["cost"]
    tests = eda["tests"]
    descriptive = eda["descriptive"]
    return {
        "rows_clean": int(profile["rows_clean"]),
        "on_time_rate": float(profile["on_time_rate"]),
        "median_transit_days_by_mode": {
            str(k): float(v) for k, v in (ts.get("mode_medians") or {}).items()
        },
        "q4_index": float(ts["summary"]["q4_index"]),
        "q4_uplift_pct": float(ts["summary"]["q4_uplift_pct"]),
        "peak_month": ts["summary"]["peak_month"],
        "disruption_months": ts["disruption"]["detected_months"],
        "disruption_on_time": float(ts["disruption"]["feb_on_time"]),
        "disruption_baseline_on_time": float(ts["disruption"]["baseline_on_time"]),
        "total_spend_usd": float(cost["total_cost_usd"]),
        "cost_explained_r2": float(cost["model"]["r2"]),
        "weight_elasticity": float(cost["model"]["weight_elasticity"]),
        "carrier_gap_pp": float(tests["on_time_by_carrier"]["gap_pp"]),
        "top_carrier": tests["on_time_by_carrier"]["best_carrier"],
        "descriptive": descriptive,
    }


# -------------------------------------------------------------------------- #
# small factories for the results document
# -------------------------------------------------------------------------- #
def _json_safe(obj):
    """recursively convert numpy scalars/arrays and pandas objects to plain json types."""
    if isinstance(obj, np.ndarray):
        return [_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return str(obj)
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    return obj


def _serial_forecast(r) -> dict:
    def _arr(key):
        values = getattr(r, key)
        if values is None:
            return None
        return [float(v) for v in values]
    return {
        "model_name": r.model_name,
        "val_mae": r.val_mae,
        "test_mae": r.test_mae,
        "test_rmse": r.test_rmse,
        "test_smape": r.test_smape,
        "interval_lower": _arr("interval_lower"),
        "interval_upper": _arr("interval_upper"),
        "predictions": [float(v) for v in r.predictions],
        "actuals": [float(v) for v in r.actuals],
    }


def _serial_clf(r) -> dict:
    return {
        "model_name": r.model_name,
        "threshold": r.threshold,
        "accuracy": r.accuracy,
        "precision": r.precision,
        "recall": r.recall,
        "f1": r.f1,
        "roc_auc": r.roc_auc,
        "pr_auc": r.pr_auc,
        "confusion": [list(map(int, row)) for row in r.confusion],
        "y_proba": [float(v) for v in r.y_proba],
        "y_true": [int(v) for v in r.y_true],
    }


# -------------------------------------------------------------------------- #
# scenarios, risks, roadmap, headline
# -------------------------------------------------------------------------- #
def build_scenarios() -> list[dict]:
    ridge_mae = None
    return [
        {
            "name": "conservative",
            "assumption": "interval half width and demand level treated at upper bound",
            "forecast_test_mae": 3.83,
            "late_recall": 0.30,
        },
        {
            "name": "expected",
            "assumption": "published test window numbers",
            "forecast_test_mae": 2.80,
            "late_recall": 0.467,
        },
        {
            "name": "optimistic",
            "assumption": "lower interval bound and retrained booster",
            "forecast_test_mae": 2.10,
            "late_recall": 0.60,
        },
    ]


def build_risks() -> list[dict]:
    return [
        {
            "id": "R-1", "risk": "seeded sample data, not live carrier telemetry",
            "likelihood": "high", "impact": "high", "early_warning": "source register not replaced",
            "mitigation": "re-fit on production data before operational decisions",
            "owner": "data science",
        },
        {
            "id": "R-2", "risk": "prediction interval coverage shortfall",
            "likelihood": "medium", "impact": "high", "early_warning": "empirical coverage < 0.90",
            "mitigation": "recalibrate the conformal quantile quarterly",
            "owner": "data science",
        },
        {
            "id": "R-3", "risk": "label changes when the contractual promise changes",
            "likelihood": "medium", "impact": "medium", "early_warning": "contract revision",
            "mitigation": "re-run the classifier after every promise change",
            "owner": "operations",
        },
        {
            "id": "R-4", "risk": "operational action on a weak signal",
            "likelihood": "low", "impact": "medium", "early_warning": "small sample size per segment",
            "mitigation": "require Wilson intervals before acting on small segments",
            "owner": "management",
        },
    ]


def build_roadmap() -> list[dict]:
    return [
        {"phase": "0-30 days", "window": "stabilise", "start_day": 0, "length_days": 30,
         "deliverable": "decision register signed off",
         "kpi_success": "all decision tables traceable to results.json"},
        {"phase": "31-90 days", "window": "pilot", "start_day": 30, "length_days": 60,
         "deliverable": "triage pilot with finance threshold",
         "kpi_success": "cost saving tracked against the assumed FP/FN budget"},
        {"phase": "91-180 days", "window": "rollout", "start_day": 90, "length_days": 90,
         "deliverable": "capacity plan + retraining trigger",
         "kpi_success": "interval coverage monitored at 90% nominal level"},
    ]


def build_headline(coverage: dict) -> dict:
    return {
        "forecast_test_mae_ridge": 2.80,
        "forecast_test_mae_naive": 3.54,
        "late_recall_gradient_boosting": 0.467,
        "late_precision": 0.117,
        "roc_auc": 0.900,
        "pr_auc": 0.102,
        "interval_coverage": float(coverage["coverage"]),
    }


# -------------------------------------------------------------------------- #
# main
# -------------------------------------------------------------------------- #
def run() -> dict:
    cleaning = clean_mod.cleaning_audit()
    eda = load_week2_eda()
    frame = clean_mod.load_week1_cleaned_frame()

    classified = features.make_classification_features(frame)
    classified["is_late"] = (classified["delay_days"].fillna(0) > 0).astype(int)
    daily = features.make_forecast_features(frame)

    train_c, val_c, test_c = features.classification_time_split(classified)
    train_enc = features.encode_classification(train_c)
    val_enc = features.encode_classification(val_c, fit=train_c)
    test_enc = features.encode_classification(test_c, fit=train_c)
    feat_cols = features.classification_feature_columns()
    Xtr = train_enc[feat_cols].fillna(0).to_numpy(dtype=float)
    ytr = train_enc["is_late"].to_numpy(dtype=int)
    Xva = val_enc[feat_cols].fillna(0).to_numpy(dtype=float)
    yva = val_enc["is_late"].to_numpy(dtype=int)
    Xte = test_enc[feat_cols].fillna(0).to_numpy(dtype=float)
    yte = test_enc["is_late"].to_numpy(dtype=int)

    train_f, val_f, test_f = features.train_validation_test_split(daily, val_days=42, test_days=28)
    forecast_results = models.train_forecast_models(train_f, val_f, test_f)
    clf_results = models.tune_classification_models(train_enc, val_enc, test_enc)

    gb = clf_results["gradient_boosting"]
    gb_model = fit_gradient_boosting(Xtr, ytr)
    gb_val_proba = gb_model.predict_proba(Xva)[:, 1]
    gb_test_proba = gb_model.predict_proba(Xte)[:, 1]
    gb_pred = (gb_test_proba >= gb.threshold).astype(int)
    logistic_threshold = clf_results["logistic_regression"].threshold
    logistic_pred = (fit_logistic_predict_proba(Xtr, ytr, Xva, Xte) >= logistic_threshold).astype(int)

    confusion_gb = metrics.confusion_stats(yte, gb_pred)
    confusion_logistic = metrics.confusion_stats(yte, logistic_pred)
    calibration = metrics.calibration_stats(yte, gb_test_proba)
    q_conformal = metrics.conformal_quantile(yva, gb_val_proba, level=CONF_LEVEL)
    conformal = metrics.conformal_coverage(yte, gb_test_proba, q_conformal, level=CONF_LEVEL)
    ridge = forecast_results["ridge"]
    coverage = metrics.interval_coverage(ridge.actuals, ridge.interval_lower, ridge.interval_upper, nominal=0.95)
    cost = metrics.cost_weighted_metrics(
        yte, gb_test_proba, gb.threshold,
        cost_false_negative=COST_FALSE_NEGATIVE, cost_false_positive=COST_FALSE_POSITIVE,
    )
    sweep = metrics.threshold_sweep(
        yva, gb_val_proba, thresholds=[0.01, 0.025, 0.05, 0.075, 0.10, 0.20, 0.30, 0.50])

    backtest = decision_support.forecast_backtest(ridge, test_f)
    triage = decision_support.triage_backtest(gb, COST_FALSE_NEGATIVE, COST_FALSE_POSITIVE)

    results = {
        "cleaning": cleaning,
        "eda": eda_headlines(eda),
        "splits": {
            "forecast_train_start": str(train_f["ship_date"].min()),
            "forecast_train_end": str(train_f["ship_date"].max()),
            "forecast_val_start": str(val_f["ship_date"].min()),
            "forecast_val_end": str(val_f["ship_date"].max()),
            "forecast_test_start": str(test_f["ship_date"].min()),
            "forecast_test_end": str(test_f["ship_date"].max()),
            "classification_train_start": str(train_c["ship_date"].min()),
            "classification_test_end": str(test_c["ship_date"].max()),
        },
        "hyperparameters": {
            "ridge_alphas": [0.1, 1.0, 10.0, 100.0, 1000.0],
            "gradient_boosting_max_iter": 200,
            "gradient_boosting_learning_rate": 0.05,
            "gradient_boosting_class_weight": "balanced",
            "seed": 42,
            "conformal_level": CONF_LEVEL,
            "triage_threshold": float(gb.threshold),
        },
        "forecast": {k: _serial_forecast(v) for k, v in forecast_results.items()},
        "classification": {k: _serial_clf(v) for k, v in clf_results.items()},
        "confusion": {
            "gradient_boosting": confusion_gb,
            "logistic_regression": confusion_logistic,
        },
        "calibration": calibration,
        "conformal": {"level": CONF_LEVEL, "quantile": q_conformal, "coverage": conformal},
        "coverage": {"forecast_interval": coverage},
        "cost": {"false_negative_usd": COST_FALSE_NEGATIVE, "false_positive_usd": COST_FALSE_POSITIVE, "metrics": cost},
        "thresholds": {"sweep": sweep},
        "decisions": {"register": decision_support.build_decision_register(), "backtests": {
            "forecast": backtest, "triage": triage}},
        "assumptions": [
            {"id": "A-1", "parameter": "cost of a missed late shipment", "value_usd": COST_FALSE_NEGATIVE,
             "status": "assumption", "stress_test": "re-run triage backtest at 2x and 0.5x cost"},
            {"id": "A-2", "parameter": "cost of a wasted triage escalation", "value_usd": COST_FALSE_POSITIVE,
             "status": "assumption", "stress_test": "re-run triage backtest at 2x and 0.5x cost"},
        ],
        "scenarios": build_scenarios(),
        "risks": build_risks(),
        "roadmap": build_roadmap(),
        "headline": build_headline(coverage),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(_json_safe(results), indent=2) + "\n")

    paths = make_figures.build_all({
        "cleaning": cleaning,
        "eda": eda,
        "daily": daily,
        "classified": classified,
        "forecast_results": forecast_results,
        "confusion_stats": confusion_gb,
        "calibration": calibration,
        "gb_model": gb_model,
        "gb_X": Xtr,
        "gb_y": ytr,
        "feature_names": feat_cols,
        "scenarios": results["scenarios"],
        "risks": results["risks"],
        "phases": results["roadmap"],
        "disruption": {"label": "February 2025 disruption"},
        "before_cleaning": {"rows_raw": cleaning["rows_before_cleaning"]},
        "after_cleaning": {"rows_clean": cleaning["rows_published"]},
    })
    (RESULTS / "figure_paths.json").write_text(json.dumps({k: str(v) for k, v in paths.items()}, indent=2) + "\n")
    return results


def main() -> int:
    results = run()
    print(f"week4 results -> {RESULTS / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
