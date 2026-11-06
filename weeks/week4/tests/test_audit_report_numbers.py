"""Tests for the week 4 number and content audit."""

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


def test_banned_hits_flags_task_phrase():
    assert audit.banned_hits(["we leverage insights to grow"]) != []
    assert audit.banned_hits(["the robust plan is ready"]) != []
    assert audit.banned_hits(["a calm ordinary sentence"]) == []


def test_duplicate_paragraphs_flags_repeat():
    assert audit.duplicate_paragraphs(["the same sentence twice here", "the same sentence twice here"]) != []
    assert audit.duplicate_paragraphs(["unique first paragraph", "unique second paragraph"]) == []


def test_check_figure_annotations_passes_for_results_backed_values():
    results = {"forecast": {"ridge": {"test_mae": 2.8}}}
    annotations = {"fig04_forecast_vs_baselines": {"test_mae": 2.8}}
    assert audit.check_figure_annotations(annotations, results) == []


def test_check_figure_annotations_flags_value_absent_from_results():
    results = {"forecast": {"ridge": {"test_mae": 2.8}}}
    annotations = {"fig04_forecast_vs_baselines": {"test_mae": 99.0}}
    problems = audit.check_figure_annotations(annotations, results)
    assert problems != []
