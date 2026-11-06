"""Tests for the week 4 data loading layer."""

from __future__ import annotations

import pandas as pd

from src import clean, features


def test_cleaning_audit_reports_expected_row_counts():
    audit = clean.cleaning_audit()
    assert audit["rows_before_cleaning"] > audit["rows_published"]
    assert audit["rows_published"] == 4200


def test_week1_cleaned_frame_loads():
    frame = clean.load_week1_cleaned_frame()
    assert len(frame) == 4200
    assert "shipment_id" in frame.columns


def test_forecast_features_are_trailing():
    frame = clean.load_week1_cleaned_frame()
    daily = features.make_forecast_features(frame)
    assert len(daily) > 0
    assert "lag_1" in daily.columns
    assert "rolling_7_mean" in daily.columns


def test_classification_target_is_late_delay_positive():
    frame = clean.load_week1_cleaned_frame()
    classified = features.make_classification_features(frame)
    classified["is_late"] = (classified["delay_days"].fillna(0) > 0).astype(int)
    assert classified["is_late"].sum() > 0
    assert float(classified["is_late"].mean()) > 0
