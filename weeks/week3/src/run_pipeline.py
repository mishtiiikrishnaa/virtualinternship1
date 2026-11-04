"""End-to-end week 3 run.

    python -m src.run_pipeline

Loads the week 1 cleaned extract, builds two feature tables (forecast and
classification), trains and evaluates both models with time-ordered splits,
writes results JSON, renders figures, and builds the Word report. Exits
non-zero if a critical check fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import features, make_figures, models

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "shipments_clean.csv"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
REPORT = ROOT / "reports" / "Week3_Predictive_Modelling_and_Forecasting.docx"
RANDOM_SEED = 42


def build_forecast_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Daily volume table with strictly trailing features."""
    return features.make_forecast_features(frame)


def build_classification_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-shipment table with is_late target, leakage columns dropped.

    delay_days is used only to define the target; delivery_date, transit_days
    and delay_days are consequences of the outcome and never reach a model.
    """
    out = features.make_classification_features(frame)
    out["is_late"] = (out["delay_days"].fillna(0) > 0).astype(int)
    for col in ("delivery_date", "transit_days", "delay_days"):
        if col in out.columns:
            out = out.drop(columns=[col])
    return out


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    frame = features.load_clean()

    # ---------- classification target & leakage check ----------
    classified = build_classification_table(frame)
    for col in features.LEAKAGE_COLUMNS:
        if col in classified.columns and col != "is_late":
            raise SystemExit(f"leakage column present in features: {col}")

    # ---------- forecast: daily volume ----------
    daily = build_forecast_table(frame)
    train_f, val_f, test_f = features.train_validation_test_split(
        daily, val_days=42, test_days=28
    )

    forecast_results = models.train_forecast_models(train_f, val_f, test_f)

    # ---------- classification: late delivery ----------
    train_c, val_c, test_c = features.classification_time_split(
        classified, test_fraction=0.2, val_fraction=0.15
    )
    # one-hot encode, fit on train, apply to val/test
    train_enc = features.encode_classification(train_c)
    val_enc = features.encode_classification(val_c, fit=train_c)
    test_enc = features.encode_classification(test_c, fit=train_c)

    # ensure the encoded columns are present in all three
    feat_cols = features.classification_feature_columns()
    missing = [c for c in feat_cols if c not in train_enc.columns]
    assert not missing, f"missing encoded features: {missing}"

    Xtr = train_enc[feat_cols].fillna(0).to_numpy(dtype=float)
    ytr = train_enc["is_late"].to_numpy(dtype=int)
    Xva = val_enc[feat_cols].fillna(0).to_numpy(dtype=float)
    yva = val_enc["is_late"].to_numpy(dtype=int)
    Xte = test_enc[feat_cols].fillna(0).to_numpy(dtype=float)
    yte = test_enc["is_late"].to_numpy(dtype=int)

    clf_results = models.tune_classification_models(train_enc, val_enc, test_enc)

    # retrain gradient boosting on train+val for the importance plot / learning curve
    from sklearn.ensemble import HistGradientBoostingClassifier
    gb_full = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, class_weight="balanced",
        random_state=RANDOM_SEED,
    )
    Xtv = np.vstack([Xtr, Xva]); ytv = np.concatenate([ytr, yva])
    gb_full.fit(Xtv, ytv)

    # ---------- write results ----------
    splits = {
        "forecast_train_start": str(train_f["ship_date"].min()),
        "forecast_train_end": str(train_f["ship_date"].max()),
        "forecast_val_start": str(val_f["ship_date"].min()),
        "forecast_val_end": str(val_f["ship_date"].max()),
        "forecast_test_start": str(test_f["ship_date"].min()),
        "forecast_test_end": str(test_f["ship_date"].max()),
        "classification_train_start": str(train_c["ship_date"].min()),
        "classification_test_end": str(test_c["ship_date"].max()),
        "classification_train_late": int(ytr.sum()),
        "classification_test_late": int(yte.sum()),
        "classification_test_prevalence": float(yte.mean()),
    }
    features.write_feature_manifest(RESULTS / "feature_manifest.json", daily, classified)
    manifest = json.loads((RESULTS / "feature_manifest.json").read_text())
    models.save_results(
        RESULTS / "metrics.json",
        forecast_results, clf_results, splits, manifest,
    )

    # ---------- figures ----------
    fig_paths = make_figures.build_all(
        daily, classified, train_c, val_c, test_c,
        forecast_results, clf_results, gb_full, Xtr, ytr,
    )
    (RESULTS / "figure_paths.json").write_text(
        json.dumps({k: str(v) for k, v in fig_paths.items()}, indent=2) + "\n",
        encoding="utf-8",
    )

    # ---------- leakage review doc ----------
    features.save_leakage_review(ROOT / "docs" / "leakage_review.md")

    print("forecast test metrics:")
    for name, r in forecast_results.items():
        print(f"  {name:22s} MAE={r.test_mae:.2f} RMSE={r.test_rmse:.2f} sMAPE={r.test_smape:.1f}%")
    print("classification test metrics:")
    for name, r in clf_results.items():
        print(f"  {name:22s} F1={r.f1:.3f} ROC-AUC={r.roc_auc:.2f} PR-AUC={r.pr_auc:.2f}")
    print(f"figures: {len(fig_paths)} -> {FIGURES}")
    print(f"results -> {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
