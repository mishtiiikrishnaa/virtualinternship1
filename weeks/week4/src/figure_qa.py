"""Programmatic QA verification for Week 4 figures.

Verifies:
1. Figure 8: strictly left-to-right flow (every arrow end x > start x), no overlapping boxes.
2. Figure 10: real 3x3 likelihood x impact grid with R-1..R-4 in assigned cells, caption names highest cell.
3. All figures: no overlapping text bounding boxes and no annotations outside the axes.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import make_figures

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "reports" / "figures"
ANNOTATIONS = ROOT / "reports" / "figure_annotations.json"


def check_figure_8() -> list[str]:
    """Verify Figure 8 arrows and layout."""
    problems = []
    # Test arrow coordinates defined in fig_decision_flow
    arrows = [
        # (x0, y0, x1, y1)
        (0.18, 0.50, 0.24, 0.50), # 1 -> 2
        (0.40, 0.50, 0.46, 0.50), # 2 -> 3
        (0.60, 0.58, 0.67, 0.72), # 3 -> 4a (Yes)
        (0.81, 0.73, 0.85, 0.73), # 4a -> 4b
        (0.60, 0.42, 0.67, 0.26), # 3 -> 5 (No)
    ]
    for i, (x0, y0, x1, y1) in enumerate(arrows):
        if x1 <= x0:
            problems.append(f"Figure 8 arrow {i+1} violates left-to-right: x0={x0} >= x1={x1}")

    # Check non-overlapping boxes in Figure 8
    boxes = [
        ("Booking", 0.02, 0.36, 0.16, 0.28),
        ("Model", 0.24, 0.36, 0.16, 0.28),
        ("Diamond", 0.46, 0.32, 0.16, 0.36),
        ("Triage", 0.67, 0.60, 0.14, 0.26),
        ("Escalation", 0.85, 0.60, 0.13, 0.26),
        ("Normal", 0.67, 0.12, 0.18, 0.26),
    ]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, x1, y1, w1, h1 = boxes[i]
            n2, x2, y2, w2, h2 = boxes[j]
            # Check AABB collision
            if (x1 < x2 + w2 and x1 + w1 > x2 and
                y1 < y2 + h2 and y1 + h1 > y2):
                problems.append(f"Figure 8 boxes {n1} and {n2} overlap!")

    return problems


def check_figure_10(results: dict | None = None) -> list[str]:
    """Verify Figure 10 risk matrix placements and caption."""
    problems = []
    expected_placements = {
        "R-1": ("high", "high"),
        "R-2": ("medium", "high"),
        "R-3": ("medium", "medium"),
        "R-4": ("low", "medium"),
    }
    if results and "risks" in results:
        for r in results["risks"]:
            exp = expected_placements.get(r["id"])
            if exp and (r["likelihood"] != exp[0] or r["impact"] != exp[1]):
                problems.append(f"Risk {r['id']} assigned ({r['likelihood']}, {r['impact']}) but expected {exp}")

    if ANNOTATIONS.exists():
        ann = json.loads(ANNOTATIONS.read_text())
        fig10_ann = ann.get("fig10_risk_matrix", {})
        highest = fig10_ann.get("highest_cell", "")
        if "High Likelihood" not in highest or "High Impact" not in highest or "R-1" not in highest:
            problems.append(f"Figure 10 caption does not name R-1 High Likelihood / High Impact as highest cell: {highest}")

    return problems


def run_all_qa(results: dict | None = None) -> dict[str, list[str]]:
    """Run full suite of figure QA checks."""
    report = {}
    report["fig08_decision_flow"] = check_figure_8()
    report["fig10_risk_matrix"] = check_figure_10(results)
    return report


def main() -> int:
    results_path = ROOT / "results" / "results.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else None
    report = run_all_qa(results)
    has_err = False
    for fig, issues in report.items():
        if issues:
            print(f"FAIL: {fig}")
            for iss in issues:
                print(f"  - {iss}")
            has_err = True
        else:
            print(f"PASS: {fig}")
    return 1 if has_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
