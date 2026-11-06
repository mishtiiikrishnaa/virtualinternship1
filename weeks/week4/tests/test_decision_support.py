"""Tests for the week 4 decision support layer."""

from __future__ import annotations

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
