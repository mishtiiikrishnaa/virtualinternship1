"""Tests for the week 4 number and content audit."""

from __future__ import annotations

from src import audit_report_numbers as audit

EMITTED = [2.8, 4380.0, 1500.0]


def test_find_unmatched_empty_when_all_numbers_match():
    assert audit.find_unmatched(["2.8", "4380", "2025"], EMITTED) == []


def test_find_unmatched_flags_unknown_number():
    assert audit.find_unmatched(["2.8", "9999"], EMITTED) == ["9999"]


def test_find_unmatched_allows_listed_allowlist():
    assert audit.find_unmatched(["2025", "7000"], EMITTED) == []


def test_banned_hits_flags_task_phrase():
    assert audit.banned_hits(["we leverage insights to grow"]) != []
    assert audit.banned_hits(["the robust plan is ready"]) != []
    assert audit.banned_hits(["a calm ordinary sentence"]) == []


def test_duplicate_paragraphs_flags_repeat():
    longp = "this is a sufficiently long repeated paragraph across two pages in the report body"
    assert audit.duplicate_paragraphs([longp, longp]) != []


def test_check_figure_annotations_flags_value_absent_from_results():
    results = {"forecast": {"ridge": {"test_mae": 2.8}}}
    annotations = {"fig04_forecast_vs_baselines": {"test_mae": 99.0}}
    problems = audit.check_figure_annotations(annotations, results)
    assert problems != []
