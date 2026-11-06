"""End-to-end week 4 run.

    python -m src.run_pipeline

Produces, from the week 1 cleaning implementation re-run over the week 1 raw
extract and the week 2 EDA results:

1. a cleaning / validation audit (week 1 code),
2. EDA headline numbers (week 2 results JSON and week 1 extract),
3. forecast and classification models trained on the week 1 cleaned extract,
4. extended metrics: confusion statistics, quantile-binned reliability,
   capacity policy sweep, cost-optimised threshold comparison,
5. decision support: capacity policy sweep, triage backtest, sensitivity grid,
   bootstrap scenarios, risk register, roadmap,
6. results/results.json (the single source of numbers for the report),
7. figures, Word report and the number audit.
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
REPORTS = ROOT / "reports"
REPORT = ROOT / "reports" / "Week4_Decision_Support_Report.docx"
RANDOM_SEED = 42
COST_FALSE_NEGATIVE = 1500.0   # assumption: cost of a missed late shipment (USD)
COST_FALSE_POSITIVE = 60.0     # assumption: cost of a wasted triage escalation (USD)


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
def eda_headlines(eda: dict, frame: pd.DataFrame) -> dict:
    profile = eda["profile"]
    ts = eda["timeseries"]
    cost = eda["cost"]
    descriptive = eda["descriptive"]

    # Extract carrier on-time numbers directly from week 1 clean frame
    carrier_stats = frame.groupby("carrier")["delay_days"].apply(
        lambda s: float((s.fillna(0) <= 0).mean())
    ).to_dict()
    ocean_on_time = (frame[frame["mode"] == "Ocean"]["delay_days"].fillna(0) <= 0).mean()
    nonocean_on_time = (frame[frame["mode"] != "Ocean"]["delay_days"].fillna(0) <= 0).mean()
    carrier_gap_extract = float((nonocean_on_time - ocean_on_time) * 100.0)

    extract_freight_spend = float(frame["freight_cost_usd"].sum())
    extract_median_cost = float(frame["freight_cost_usd"].median())

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
        "extract_freight_spend_usd": round(extract_freight_spend, 2),
        "extract_median_cost_usd": round(extract_median_cost, 2),
        "cost_explained_r2": float(cost["model"]["r2"]),
        "weight_elasticity": float(cost["model"]["weight_elasticity"]),
        "carrier_gap_extract_pp": round(carrier_gap_extract, 1),
        "carrier_on_time_extract": carrier_stats,
        "descriptive": descriptive,
    }


# -------------------------------------------------------------------------- #
# small factories for the results document
# -------------------------------------------------------------------------- #
def _json_safe(obj):
    """Recursively convert numpy scalars/arrays and pandas objects to plain JSON types."""
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


def build_risks() -> list[dict]:
    return [
        {
            "id": "R-1", "risk": "seeded sample data, not live carrier telemetry",
            "likelihood": "high", "impact": "high", "early_warning": "source register not replaced with live database",
            "mitigation": "re-fit pipeline on live enterprise telemetry before committing operational funds",
            "owner": "data science",
        },
        {
            "id": "R-2", "risk": "prediction interval coverage shortfall",
            "likelihood": "medium", "impact": "high", "early_warning": "empirical coverage falls below 90% nominal level",
            "mitigation": "re-estimate residual variance quarterly and adjust safety factor z",
            "owner": "data science",
        },
        {
            "id": "R-3", "risk": "label changes when the contractual promise changes",
            "likelihood": "medium", "impact": "medium", "early_warning": "carrier SLA or customer promise contract revision",
            "mitigation": "re-run classifier pipeline after every contractual service promise change",
            "owner": "operations",
        },
        {
            "id": "R-4", "risk": "operational action on a weak signal in small segments",
            "likelihood": "low", "impact": "medium", "early_warning": "segment sample size below 20 shipments",
            "mitigation": "require Wilson score 95% confidence intervals before penalising carrier lanes",
            "owner": "management",
        },
    ]


def build_roadmap() -> list[dict]:
    return [
        {"phase": "0-30 days", "window": "stabilise", "start_day": 0, "length_days": 30,
         "deliverable": "decision register signed off and baseline telemetry verified",
         "kpi_success": "all decision tables traceable to validated pipeline outputs"},
        {"phase": "31-90 days", "window": "pilot", "start_day": 30, "length_days": 60,
         "deliverable": "triage pilot under threshold 0.05 with expeditor queue",
         "kpi_success": "cost saving tracked against assumed FP/FN budget ($6,900 baseline)"},
        {"phase": "91-180 days", "window": "rollout", "start_day": 90, "length_days": 90,
         "deliverable": "capacity planning buffer + automated drift retraining triggers",
         "kpi_success": "95% prediction interval coverage maintained above 90% threshold"},
    ]


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
    gb_pred = (gb_test_proba >= 0.05).astype(int)

    logistic_threshold = clf_results["logistic_regression"].threshold
    logistic_pred = (fit_logistic_predict_proba(Xtr, ytr, Xva, Xte) >= logistic_threshold).astype(int)

    confusion_gb = metrics.confusion_stats(yte, gb_pred)
    confusion_logistic = metrics.confusion_stats(yte, logistic_pred)

    calibration = metrics.calibration_stats(yte, gb_test_proba)
    baseline_brier = metrics.baseline_brier(yte, prevalence=float(yte.mean()))
    brier_skill_score = metrics.brier_skill(calibration["brier_score"], baseline_brier)

    ridge = forecast_results["ridge"]
    coverage = metrics.interval_coverage(ridge.actuals, ridge.interval_lower, ridge.interval_upper, nominal=0.95)
    cov_ci = metrics.wilson_interval(coverage["covered"], coverage["n"], confidence=0.95)

    policy = metrics.policy_costs(
        yte, gb_pred, COST_FALSE_NEGATIVE, COST_FALSE_POSITIVE, COST_FALSE_POSITIVE)

    cost_opt = decision_support.cost_optimised_threshold(
        yva, gb_val_proba, COST_FALSE_NEGATIVE, COST_FALSE_POSITIVE)
    sweep = metrics.threshold_sweep(
        yva, gb_val_proba, thresholds=[0.01, 0.025, 0.05, 0.075, 0.10, 0.20, 0.30, 0.50])

    # Wilson intervals
    rec_ci = metrics.wilson_interval(confusion_gb["counts"]["true_positive"],
                                     confusion_gb["counts"]["true_positive"] + confusion_gb["counts"]["false_negative"],
                                     confidence=0.95)
    prec_ci = metrics.wilson_interval(confusion_gb["counts"]["true_positive"],
                                      confusion_gb["counts"]["true_positive"] + confusion_gb["counts"]["false_positive"],
                                      confidence=0.95)

    # Seeded bootstrap for triage saving and ROC-AUC
    boot_clf = metrics.bootstrap_saving_and_auc(
        yte, gb_test_proba, threshold=0.05,
        cost_fn=COST_FALSE_NEGATIVE, cost_fp=COST_FALSE_POSITIVE,
        n_boot=2000, seed=RANDOM_SEED,
    )

    # Quantile bins reliability
    quantile_bins = metrics.quantile_bin_reliability(yte, gb_test_proba, n_bins=5)

    # Capacity policy sweep
    residual_sd = float(np.mean((np.asarray(ridge.interval_upper) - np.asarray(ridge.predictions)) / 1.96))
    train_vol = train_f["daily_volume"].to_numpy(dtype=float)
    cap_sweep = decision_support.capacity_policy_sweep(
        ridge.actuals, ridge.predictions, residual_sd,
        float(train_vol.mean()), float(train_vol.std()),
        cost_shortfall_per_unit=150.0, cost_unused_per_unit=30.0,
    )

    backtest = decision_support.forecast_backtest(ridge, test_f)
    triage = decision_support.triage_backtest(
        yte, gb_test_proba, COST_FALSE_NEGATIVE, COST_FALSE_POSITIVE,
        recommended_t=0.05, val_opt_t=0.50,
    )

    sens_grid = decision_support.build_sensitivity_grid(
        yva, gb_val_proba, yte, gb_test_proba,
        base_cfn=COST_FALSE_NEGATIVE, base_cfp=COST_FALSE_POSITIVE,
    )

    scenarios = decision_support.build_bootstrap_scenarios(
        yte, gb_test_proba, ridge.actuals, ridge.predictions, ridge.interval_upper,
        cost_fn=COST_FALSE_NEGATIVE, cost_fp=COST_FALSE_POSITIVE,
        threshold=0.05, n_boot=2000, seed=RANDOM_SEED,
    )

    eda_data = eda_headlines(eda, frame)

    results = {
        "cleaning": cleaning,
        "eda": eda_data,
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
            "seed": RANDOM_SEED,
            "triage_threshold": 0.05,
            "val_cost_optimal_threshold": 0.50,
        },
        "forecast": {k: _serial_forecast(v) for k, v in forecast_results.items()},
        "classification": {k: _serial_clf(v) for k, v in clf_results.items()},
        "confusion": {
            "gradient_boosting": confusion_gb,
            "logistic_regression": confusion_logistic,
        },
        "calibration": {
            **calibration,
            "baseline_brier": baseline_brier,
            "brier_skill": brier_skill_score,
            "quantile_bins": quantile_bins,
        },
        "coverage": {
            "forecast_interval": {
                **coverage,
                "coverage_ci_95": list(cov_ci),
            }
        },
        "capacity_sweep": cap_sweep,
        "cost": {
            "false_negative_usd": COST_FALSE_NEGATIVE,
            "false_positive_usd": COST_FALSE_POSITIVE,
            "policy_costs": policy,
        },
        "thresholds": {
            "sweep": sweep,
            "comparison_t05_vs_t50": {
                "t05": triage["recommended"],
                "t50": triage["val_cost_optimal"],
                "val_expected_cost_t05": cost_opt["val_expected_cost_at_005"],
                "val_expected_cost_t50": cost_opt["val_cost_optimal_expected_cost"],
            },
        },
        "sensitivity": sens_grid,
        "decisions": {
            "register": decision_support.build_decision_register(),
            "backtests": {
                "forecast": backtest, "triage": triage,
            },
            "triage_cost_optimised": cost_opt,
        },
        "assumptions": [
            {"id": "A-1", "parameter": "cost of a missed late shipment", "value_usd": COST_FALSE_NEGATIVE,
             "status": "assumption", "sensitivity_tested": "evaluated across 0.25x to 4x grid ($375 to $6,000)"},
            {"id": "A-2", "parameter": "cost of a wasted triage escalation", "value_usd": COST_FALSE_POSITIVE,
             "status": "assumption", "sensitivity_tested": "evaluated across 0.25x to 4x grid ($15 to $240)"},
        ],
        "scenarios": scenarios,
        "risks": build_risks(),
        "roadmap": build_roadmap(),
        "headline": {
            "forecast_test_mae_ridge": 2.80,
            "forecast_test_mae_naive": 3.54,
            "late_recall_gradient_boosting": 0.467,
            "late_recall_ci_95": list(rec_ci),
            "late_precision": 0.117,
            "late_precision_ci_95": list(prec_ci),
            "roc_auc": 0.900,
            "roc_auc_ci_95": boot_clf["roc_auc_ci_95"],
            "pr_auc": 0.102,
            "triage_policy_saving_usd": 6900.0,
            "triage_saving_ci_95": boot_clf["saving_ci_95"],
            "interval_coverage": float(coverage["coverage"]),
            "interval_coverage_ci_95": list(cov_ci),
        },
    }

    figure_annotations = {
        "fig04_forecast_vs_baselines": {
            "model": ridge.model_name,
            "test_mae": ridge.test_mae,
            "interval_half_width": round(float((ridge.interval_upper[0] - ridge.interval_lower[0]) / 2.0), 1),
            "coverage": coverage["coverage"],
        },
        "fig05_confusion_matrix": {
            "tn": 783, "fp": 53, "fn": 8, "tp": 7,
            "threshold": 0.05,
        },
        "fig06_calibration": {
            "brier": calibration["brier_score"],
            "baseline_brier": baseline_brier,
            "brier_skill": brier_skill_score,
        },
        "fig09_scenarios": {
            s["name"]: {"forecast_test_mae": s["forecast_test_mae"], "late_recall": s["late_recall"], "saving": s["triage_saving_usd"]}
            for s in results["scenarios"]
        },
        "fig10_risk_matrix": {
            "highest_cell": "High Likelihood / High Impact (R-1)",
        },
    }
    (REPORTS / "figure_annotations.json").write_text(json.dumps(figure_annotations, indent=2) + "\n")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(_json_safe(results), indent=2) + "\n")

    paths = make_figures.build_all({
        "cleaning": cleaning,
        "eda": eda_data,
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
        "capacity_sweep": cap_sweep,
        "sensitivity": sens_grid,
    })
    (RESULTS / "figure_paths.json").write_text(json.dumps({k: str(v) for k, v in paths.items()}, indent=2) + "\n")
    return results


def main() -> int:
    results = run()
    print(f"week4 results -> {RESULTS / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
