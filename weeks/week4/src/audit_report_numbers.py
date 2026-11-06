"""Number and content audit for the week 4 report.

Reads the built DOCX, extracts every numeric token, and checks it against
results/results.json (rounding tolerance) or an explicit allowlist (years,
section and figure numbers, task-spec numbers). Exits non-zero on any
unmatched number, so the Makefile and CI can gate on it.

Also runs two content checks:
  * banned-filler phrases and near-duplicate paragraphs are flagged, and
  * every figure annotation number is checked against results.json.

    python -m src.audit_report_numbers
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "reports" / "Week4_Decision_Support_Report.docx"
RESULTS = ROOT / "results" / "results.json"
ANNOTATIONS = ROOT / "reports" / "figure_annotations.json"

TOKEN_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

ALLOWLIST = {
    "200": "task minimum word count",
    "5000": "task target prose length",
    "7000": "task target prose length",
    "1996": "year in the external benchmark",
    "2024": "year of the development window",
    "2025": "year of the development window",
    "2026": "year of the report",
    "1.2": "section number",
    "3.2": "section number",
    "4.1": "section number",
}

BANNED_PHRASES = [
    "data-driven decision making is crucial",
    "in today's fast-paced world",
    "leverage insights",
    "optimise operations",
    "robust",
    "holistic",
    "cutting-edge",
]

ANNOTATION_FILES = [
    "fig04_forecast_vs_baselines",
    "fig05_confusion_matrix",
    "fig06_calibration",
    "fig09_scenarios",
]


def extract_tokens(doc: Document) -> list[str]:
    tokens: list[str] = []
    for para in doc.paragraphs:
        tokens.extend(TOKEN_RE.findall(para.text))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                tokens.extend(TOKEN_RE.findall(cell.text))
    return tokens


def body_text(doc: Document) -> list[str]:
    texts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.append(cell.text)
    return texts


def banned_hits(texts: list[str]) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for text in texts:
        low = text.lower()
        for phrase in BANNED_PHRASES:
            if phrase in low and phrase not in seen:
                hits.append(phrase)
                seen.add(phrase)
    return hits


def duplicate_paragraphs(texts: list[str]) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if "|" in text or re.match(r"^\s*[-*]\s+", text) or re.match(r"^\s*\d+\.\s+", text):
            # tables and lists are structured content, not prose
            continue
        key = re.sub(r"\s+", " ", text.strip().lower()).strip()
        if not key:
            continue
        if key in seen:
            hits.append(key[:80])
        seen.add(key)
    return hits


def numeric_values(obj: Any, out: list[float]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            numeric_values(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            numeric_values(v, out)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        out.append(float(obj))


def find_unmatched(tokens: list[str], results: dict) -> list[str]:
    values: list[float] = []
    numeric_values(results, values)
    unmatched: list[str] = []
    seen: set[str] = set()
    for raw in tokens:
        key = raw.strip().replace(",", "")
        if key in seen:
            continue
        seen.add(key)
        value = float(key)
        candidates = [value, value / 100.0, value * 100.0]
        if any(
            abs(value_ - v) <= max(1e-6, abs(v) * 0.01)
            for v in values
            for value_ in candidates
        ):
            continue
        if key in ALLOWLIST:
            continue
        unmatched.append(key)
    return unmatched


def check_figure_annotations(annotations: dict, results: dict) -> list[str]:
    problems: list[str] = []
    values: list[float] = []
    numeric_values(results, values)

    def flat(obj: Any) -> list[float]:
        out: list[float] = []
        if isinstance(obj, dict):
            for v in obj.values():
                out.extend(flat(v))
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                out.extend(flat(v))
        elif isinstance(obj, bool):
            pass
        elif isinstance(obj, (int, float)):
            out.append(float(obj))
        return out

    for figure, payload in annotations.items():
        if not isinstance(payload, dict):
            continue
        for value in flat(payload):
            if not any(abs(value - v) <= max(1e-6, abs(v) * 0.01) for v in values):
                problems.append(f"{figure}: annotation {value} not in results.json")
    return problems


def main() -> int:
    doc = Document(DOCX)
    results = json.loads(RESULTS.read_text())
    tokens = extract_tokens(doc)
    unmatched = find_unmatched(tokens, results)
    texts = body_text(doc)
    banned = banned_hits(texts)
    duplicates = duplicate_paragraphs([p.text for p in doc.paragraphs])
    problems: list[str] = []
    for key in sorted(unmatched, key=lambda k: float(k) if re.fullmatch(r"\d+", k) else 0):
        problems.append(f"UNMATCHED {key}")
    if banned:
        problems.append("BANNED " + ", ".join(banned))
    for key in duplicates:
        problems.append(f"DUPLICATE {key}")
    if ANNOTATIONS.exists():
        annotations = json.loads(ANNOTATIONS.read_text())
        problems.extend(check_figure_annotations(annotations, results))
    for key in sorted(unmatched, key=lambda k: float(k) if re.fullmatch(r"\d+", k) else 0):
        print(f"UNMATCHED  {key}")
    print(f"tokens checked: {len(set(t.strip().replace(',', '') for t in tokens))}; unmatched: {len(unmatched)}")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(" -", p)
        print("OVERALL: FAIL")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
