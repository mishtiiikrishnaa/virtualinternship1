"""Tests for the week 4 decision support layer."""

from __future__ import annotations

import numpy as np

from src import decision_support


def test_decision_register_has_four_decisions():
    register = decision_support.build_decision_register()
    assert len(register) == 4
    for d in register:
        for key in ("decision_id", "question", "decision", "trigger_metric", "action",
                    "owner", "data_required", "review_cadence"):
            assert key in d, key


def test_forecast_backtest_reports_shipment_days():
    class R:
        predictions = [10.0, 12.0]
        interval_lower = [8.0, 9.0]
        interval_upper = [12.0, 15.0]
        actuals = [11.0, 14.0]
        dates = ["2025-12-01", "2025-12-02"]
        test_mae = 2.0

    import pandas as pd
    daily = pd.DataFrame({
        "ship_date": pd.to_datetime(["2025-12-01", "2025-12-02"]),
        "daily_volume": [11.0, 14.0],
    })
    out = decision_support.forecast_backtest(R(), daily)
    assert out["decision_id"] == "D-1"
    assert out["horizon_days"] == 2
    assert out["model_mae"] == 2.0


def test_cost_optimised_threshold_picks_minimising_candidate():
    y = np.array([0, 0, 1, 1, 0, 1])
    proba = np.array([0.9, 0.8, 0.7, 0.2, 0.3, 0.85])
    out = decision_support.cost_optimised_threshold(y, proba, cost_false_negative=1500.0, cost_false_positive=60.0)
    best = min(out["candidates"], key=lambda c: c["expected_cost"])
    assert out["val_cost_optimal_threshold"] == best["threshold"]
    assert out["val_cost_optimal_expected_cost"] == best["expected_cost"]
