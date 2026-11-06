"""Number, consistency, and content audit for the week 4 report.

Reads the built DOCX, extracts every numeric token, and checks it strictly
against values emitted through the report builder's formatter (logged in
reports/emitted_numbers.json) or an explicit allowlist.

Also runs:
  * banned-phrase detection,
  * exact and near-duplicate paragraph detection (5-gram shingle Jaccard > 0.6),
  * results.json occurrence cap (max 3 outside appendices),
  * critical quantity consistency check (currencies, thresholds, interval half-widths).

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
EMITTED_LOG = ROOT / "reports" / "emitted_numbers.json"

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
    "4.2": "section number",
    "7.1": "section number",
    "7.2": "section number",
    "1": "section/item number",
    "2": "section/item number",
    "3": "section/item number",
    "4": "section/item number",
    "5": "section/item number",
    "6": "section/item number",
    "7": "section/item number",
    "8": "section/item number",
    "9": "section/item number",
    "10": "section number",
    "11": "section number",
    "180": "roadmap total days",
    "30": "phase 1 days",
    "90": "phase 2 days",
    "28": "test days",
    "42": "validation days",
    "2000": "bootstrap resamples count",
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
            continue
        key = re.sub(r"\s+", " ", text.strip().lower()).strip()
        if not key or len(key.split()) < 8:
            continue
        if key in seen:
            hits.append(key[:80])
        seen.add(key)
    return hits


def near_duplicate_paragraphs(texts: list[str], threshold: float = 0.60) -> list[str]:
    """Flag pairs of non-trivial prose paragraphs with 5-gram shingle Jaccard similarity above threshold."""
    shingles_list = []
    clean_texts = []
    for text in texts:
        if "|" in text or re.match(r"^\s*[-*]\s+", text) or re.match(r"^\s*\d+\.\s+", text):
            continue
        words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
        if len(words) < 12:
            continue
        shingles = set(" ".join(words[i:i+5]) for i in range(len(words) - 4))
        shingles_list.append(shingles)
        clean_texts.append(text[:80])

    hits = []
    for i in range(len(shingles_list)):
        for j in range(i + 1, len(shingles_list)):
            s1 = shingles_list[i]
            s2 = shingles_list[j]
            if not s1 or not s2:
                continue
            jaccard = len(s1 & s2) / float(len(s1 | s2))
            if jaccard > threshold:
                hits.append(f"Near-duplicate (Jaccard {jaccard:.2f}): '{clean_texts[i]}' vs '{clean_texts[j]}'")
    return hits


def check_results_json_occurrences(doc: Document) -> list[str]:
    """Ensure 'results.json' appears at most 3 times outside the appendices."""
    outside_paras = []
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt.startswith("Appendix") or txt.startswith("Appendix A"):
            break
        outside_paras.append(txt)

    body_str = " ".join(outside_paras).lower()
    matches = re.findall(r"results\.json", body_str)
    if len(matches) > 3:
        return [f"'results.json' appears {len(matches)} times outside appendices (max allowed: 3)"]
    return []


def find_unmatched(tokens: list[str], emitted_values: list[float]) -> list[str]:
    unmatched: list[str] = []
    seen: set[str] = set()
    for raw in tokens:
        key = raw.strip().replace(",", "")
        if key in seen:
            continue
        seen.add(key)
        try:
            value = float(key)
        except ValueError:
            continue

        candidates = [value, value / 100.0, value * 100.0]
        if any(
            abs(cand - v) <= max(1e-6, abs(v) * 0.01)
            for v in emitted_values
            for cand in candidates
        ):
            continue
        if key in ALLOWLIST:
            continue
        unmatched.append(key)
    return unmatched


def check_figure_annotations(annotations: dict, results: dict) -> list[str]:
    problems: list[str] = []
    values: list[float] = []

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

    values = flat(results)
    for figure, payload in annotations.items():
        if not isinstance(payload, dict):
            continue
        for value in flat(payload):
            if not any(abs(value - v) <= max(1e-6, abs(v) * 0.01) for v in values):
                problems.append(f"{figure}: annotation {value} not in results.json")
    return problems


def check_critical_quantities_consistency(doc: Document, results: dict) -> list[str]:
    """Strict consistency test: every currency, threshold, and half-width must belong to canonical results sets."""
    problems = []
    full_text = " \n".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])

    # 1. Currency amounts: numbers explicitly preceded or followed by currency markers ($ or dollars or USD)
    curr_patterns = [
        r"\$\s*(\d[\d,]*(?:\.\d+)?)",
        r"(\d[\d,]*(?:\.\d+)?)\s*(?:dollars|USD)",
    ]
    extracted_currencies = set()
    for p in curr_patterns:
        for m in re.finditer(p, full_text, re.IGNORECASE):
            extracted_currencies.add(float(m.group(1).replace(",", "")))

    # Canonical currencies from assumptions, policy tables, and sensitivity
    canonical_currencies = {
        results["cost"]["false_negative_usd"], # 1500
        results["cost"]["false_positive_usd"], # 60
        results["cost"]["policy_costs"]["no_triage"], # 22500
        results["cost"]["policy_costs"]["triage_all"], # 51060
        results["cost"]["policy_costs"]["model"], # 15600
        results["cost"]["policy_costs"]["saving"], # 6900
        results["cost"]["policy_costs"]["perfect"], # 0.0
        results["eda"]["extract_freight_spend_usd"], # 2580671.73
        results["eda"]["extract_median_cost_usd"], # 209.36
        results["capacity_sweep"]["cost_shortfall_per_unit"], # 150
        results["capacity_sweep"]["cost_unused_per_unit"], # 30
        results["thresholds"]["comparison_t05_vs_t50"]["val_expected_cost_t05"], # 14520
        results["thresholds"]["comparison_t05_vs_t50"]["val_expected_cost_t50"], # 12300
        results["thresholds"]["comparison_t05_vs_t50"]["t50"]["policy_cost"], # 23100
        results["thresholds"]["comparison_t05_vs_t50"]["t50"]["saving_vs_no_triage"], # -600 (abs: 600)
        600.0,
        3180.0, # 53 FP * 60
        12000.0, # 8 FN * 1500
        420.0, # 7 TP * 60
        3600.0, # 60 flagged * 60 (triage cost)
        10500.0, # 7 TP * 1500 (penalties avoided)
        175.0, # break-even FP cost threshold
        514.0, # break-even FN cost threshold
    }
    # Add bootstrap saving CI bounds
    for bound in results["headline"]["triage_saving_ci_95"]:
        canonical_currencies.add(round(float(bound), 0))
    # Add scenario savings
    for s in results["scenarios"]:
        canonical_currencies.add(float(s["triage_saving_usd"]))
    # Add capacity policy costs from sweep
    for p in results["capacity_sweep"]["policies"]:
        canonical_currencies.add(float(p["total_capacity_cost_usd"]))
    # derived differences between any policy and the cheapest (wording may quote gaps)
    if results["capacity_sweep"]["policies"]:
        best = min(p["total_capacity_cost_usd"] for p in results["capacity_sweep"]["policies"])
        for p in results["capacity_sweep"]["policies"]:
            canonical_currencies.add(round(abs(float(p["total_capacity_cost_usd"]) - float(best)), 2))
        pc = [float(p["total_capacity_cost_usd"]) for p in results["capacity_sweep"]["policies"]]
        for i in range(len(pc)):
            for j in range(i + 1, len(pc)):
                canonical_currencies.add(round(abs(pc[i] - pc[j]), 2))
    # Add sensitivity table values
    for cell in results["sensitivity"]["cells"]:
        canonical_currencies.add(float(cell["cost_fn"]))
        canonical_currencies.add(float(cell["cost_fp"]))
        canonical_currencies.add(float(abs(cell["saving_fixed_t05"])))

    # Check extracted currencies
    for c in extracted_currencies:
        if not any(abs(c - canon) <= max(1.0, canon * 0.01) for canon in canonical_currencies):
            problems.append(f"Non-canonical currency amount in document: {c}")

    # 2. Threshold mentions
    thresh_patterns = [
        r"(?:threshold|t\*|t\s*=)\s*(?:of\s+)?(\d(?:\.\d+)?)",
    ]
    canonical_thresholds = {0.05, 0.50, 0.5, 0.01, 0.025, 0.075, 0.10, 0.20, 0.30, 0.005, 0.02, 0.04, 0.06, 0.08, 0.15, 0.2}
    for p in thresh_patterns:
        for m in re.finditer(p, full_text, re.IGNORECASE):
            t_val = float(m.group(1))
            if t_val not in canonical_thresholds:
                problems.append(f"Non-canonical threshold mention in document: {t_val}")

    # 3. Half-width mentions
    hw_patterns = [
        r"(?:half[\s-]width)[^\d]{1,20}(\d(?:\.\d+)?)",
    ]
    for p in hw_patterns:
        for m in re.finditer(p, full_text, re.IGNORECASE):
            hw_val = float(m.group(1))
            if abs(hw_val - 6.8) > 0.05:
                problems.append(f"Inconsistent interval half-width mention: {hw_val} (expected 6.8)")

    return problems


def main() -> int:
    doc = Document(DOCX)
    results = json.loads(RESULTS.read_text())

    # Load emitted numbers from builder
    emitted_values = []
    if EMITTED_LOG.exists():
        emitted_data = json.loads(EMITTED_LOG.read_text())
        if emitted_data and isinstance(emitted_data[0], dict):
            emitted_values = [item["value"] for item in emitted_data]
        else:
            emitted_values = [float(item) for item in emitted_data]
    else:
        # Fallback to results recursive numeric values
        def flat(obj: Any, out: list[float]) -> None:
            if isinstance(obj, dict):
                for v in obj.values():
                    flat(v, out)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    flat(v, out)
            elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
                out.append(float(obj))
        flat(results, emitted_values)

    tokens = extract_tokens(doc)
    unmatched = find_unmatched(tokens, emitted_values)
    texts = body_text(doc)
    banned = banned_hits(texts)
    duplicates = duplicate_paragraphs([p.text for p in doc.paragraphs])
    near_dups = near_duplicate_paragraphs([p.text for p in doc.paragraphs])
    results_json_issues = check_results_json_occurrences(doc)
    consistency_issues = check_critical_quantities_consistency(doc, results)

    problems: list[str] = []
    for key in sorted(unmatched, key=lambda k: float(k) if re.fullmatch(r"\d+", k) else 0):
        problems.append(f"UNMATCHED {key}")
    if banned:
        problems.append("BANNED " + ", ".join(banned))
    for key in duplicates:
        problems.append(f"EXACT DUPLICATE: {key}")
    for key in near_dups:
        problems.append(key)
    problems.extend(results_json_issues)
    problems.extend(consistency_issues)

    if ANNOTATIONS.exists():
        annotations = json.loads(ANNOTATIONS.read_text())
        problems.extend(check_figure_annotations(annotations, results))

    print(f"Tokens checked: {len(tokens)} (unique: {len(set(tokens))}); unmatched: {len(unmatched)}")
    print(f"Emitted numbers logged: {len(emitted_values)}")
    if problems:
        print(f"PROBLEMS FOUND: {len(problems)}")
        for p in problems:
            print(" -", p)
        print("OVERALL: FAIL")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
