"""Number audit for the week 4 report.

Reads the built DOCX, extracts every numeric token, and checks it against
results/results.json (rounding tolerance) or an explicit allowlist (years,
section and figure numbers, task-spec numbers). Exits non-zero on any
unmatched number, so the Makefile and CI can gate on it.

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


def extract_tokens(doc: Document) -> list[str]:
    tokens: list[str] = []
    for para in doc.paragraphs:
        tokens.extend(TOKEN_RE.findall(para.text))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                tokens.extend(TOKEN_RE.findall(cell.text))
    return tokens


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


def main() -> int:
    doc = Document(DOCX)
    results = json.loads(RESULTS.read_text())
    tokens = extract_tokens(doc)
    unmatched = find_unmatched(tokens, results)
    for key in sorted(unmatched, key=lambda k: float(k) if re.fullmatch(r"\d+", k) else 0):
        print(f"UNMATCHED  {key}")
    print(f"tokens checked: {len(set(t.strip().replace(',', '') for t in tokens))}; unmatched: {len(unmatched)}")
    if unmatched:
        print("OVERALL: FAIL")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
