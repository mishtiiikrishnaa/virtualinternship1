"""Tests for the week 4 number audit."""

from __future__ import annotations

from src import audit_report_numbers as audit


def test_find_unmatched_empty_when_all_numbers_match():
    results = {"headline": {"forecast_test_mae_ridge": 2.8}, "cleaning": {"rows_before_cleaning": 4380}}
    assert audit.find_unmatched(["2.8", "4380", "2025"], results) == []


def test_find_unmatched_flags_unknown_number():
    results = {"headline": {"forecast_test_mae_ridge": 2.8}}
    assert audit.find_unmatched(["2.8", "9999"], results) == ["9999"]


def test_find_unmatched_allows_listed_allowlist():
    results = {"headline": {"forecast_test_mae_ridge": 2.8}}
    assert audit.find_unmatched(["2025", "7000"], results) == []
