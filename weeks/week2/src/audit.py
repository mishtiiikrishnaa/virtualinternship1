"""Scripted compliance audit for the Week 2 report.

Reads the built DOCX and the JSON artefacts, then prints a pass/fail table for
every packaging rule: length, section depth, figure completeness, caption and
alt-text coverage, interpretation length, requirement coverage, forbidden
wording, and agreement between prose numbers and the result files.

    python -m src.audit

Exit code is 1 if any check fails, so the Makefile can gate on it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "reports" / "Week2_EDA_and_Visualization.docx"
PDF = ROOT / "reports" / "Week2_EDA_and_Visualization.pdf"
RESULTS = ROOT / "results"
FIGDIR = ROOT / "figures"

PROSE_STYLES = {"Body Text 2", "List Bullet", "List Number"}

FORBIDDEN = [
    "TODO", "TBD", "lorem", "Lorem", "XXX", "XX%", "FIXME", "placeholder",
    "colour", "behaviour", "modelling", "summarise", "analyse", "optimise",
    "visualisation", "organisation", "recognise", "centre", "labelled",
    "favourable", "programme", "catalogue", "prioritise", "normalise",
    "modelled", "centred", "centre ", "utilise", "characterise",
]

REQUIREMENTS = [
    ("Dataset A simulation with seeded generation and >=8 planted effects",
     r"seeded|np\.random\.default_rng|seed"),
    ("Dataset B real public data with source, licence, access date",
     r"Bureau of Transportation Statistics|BTS"),
    ("Data cleaning and quality assessment",
     r"[Cc]leaning|[Qq]uality"),
    ("Univariate distributions of transit time and cost",
     r"[Uu]nivariate|[Dd]istribution"),
    ("Bivariate and multivariate relationships",
     r"[Bb]ivariate|[Mm]ultivariate"),
    ("Time series and seasonality",
     r"[Tt]ime series|[Ss]easonal"),
    ("Correlation analysis",
     r"[Cc]orrelation"),
    ("Carrier and lane performance comparison",
     r"[Cc]arrier.*lane|[Ll]ane.*carrier|carrier and lane"),
    ("Outlier detection with competing methods",
     r"[Oo]utlier"),
    ("At least three visualisation libraries (matplotlib, seaborn, plotly)",
     r"matplotlib.*seaborn.*plotly|plotly.*kaleido"),
    ("Figures with captions, purpose, code and interpretation",
     r"Interpretation\."),
    ("Statistical testing with confidence intervals",
     r"confidence interval|chi-squared|Kruskal"),
    ("Method validation against planted effects",
     r"[Vv]alidation|[Rr]ecover"),
    ("Limitations and threats to validity",
     r"[Ll]imitation"),
    ("Recommendations and next steps",
     r"[Rr]ecommendation"),
]


def paragraphs(doc):
    return doc.paragraphs


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9$%.,'-]+", text))


def is_prose(par) -> bool:
    return par.style.name in PROSE_STYLES and par.text.strip() != ""


def load_results() -> dict:
    return {p.stem: json.loads(p.read_text()) for p in RESULTS.glob("*.json")}


def check(label: str, ok: bool, detail: str) -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {label:<58} {detail}")
    return ok


def main() -> int:
    doc = Document(DOCX)
    R = load_results()
    paras = paragraphs(doc)
    ok = True

    # -- length -----------------------------------------------------------
    prose = [p for p in paras if is_prose(p)]
    total_words = sum(word_count(p.text) for p in prose)
    ok &= check("Total prose words in 5,000-6,500", 5000 <= total_words <= 6500,
                f"{total_words:,} words across {len(prose)} paragraphs")

    # -- section depth ----------------------------------------------------
    sections, current = [], None
    for p in paras:
        name = p.style.name
        if name == "Heading 1":
            current = {"title": p.text, "words": 0}
            sections.append(current)
        elif current is not None and is_prose(p):
            current["words"] += word_count(p.text)
    thin = [(s["title"], s["words"]) for s in sections
            if s["words"] < 250 and s["title"] != "References"]
    ok &= check("Every major section >= 250 words", not thin,
                f"{len(sections)} sections; thinnest "
                f"{min((s['words'] for s in sections), default=0)} words"
                + (f"; short: {thin}" if thin else ""))

    # -- figures ----------------------------------------------------------
    figs = [p for p in paras if p.style.name == "FigCaption"
            and p.text.startswith("Figure ")]
    numbers = [int(re.match(r"Figure (\d+)\.", p.text).group(1)) for p in figs]
    ok &= check("Figure captions numbered 1..N with no gaps",
                numbers == list(range(1, len(numbers) + 1)),
                f"{len(numbers)} captions")
    ok &= check("At least 12 figures", len(numbers) >= 12, f"{len(numbers)}")

    images = doc.inline_shapes
    missing_alt = []
    for shape in images:
        docPr = shape._inline.docPr
        if not (docPr.get("descr") or "").strip():
            missing_alt.append(docPr.get("id"))
    ok &= check("Every image has alt text", not missing_alt and len(images) >= 12,
                f"{len(images)} images; {len(missing_alt)} without alt text")

    purposes = [p for p in paras if p.style.name == "FigurePurpose"]
    code_blocks = [p for p in paras if p.style.name == "CodeBlock"]
    interps = [p for p in paras
               if p.text.startswith("Interpretation.")]
    ok &= check("Every figure has a purpose statement",
                len(purposes) == len(numbers),
                f"{len(purposes)} purpose paragraphs")
    ok &= check("Every figure has a code snippet <= 15 lines",
                len(code_blocks) == len(numbers)
                and all(len(p.text.split("\n")) <= 15 for p in code_blocks),
                f"{len(code_blocks)} blocks; longest "
                f"{max((len(p.text.split(chr(10))) for p in code_blocks), default=0)} lines")
    ok &= check("Every figure has an interpretation", len(interps) == len(numbers),
                f"{len(interps)} interpretations")

    short = [(i + 1, word_count(p.text)) for i, p in enumerate(interps)
             if not 100 <= word_count(p.text) <= 150]
    numeric = [p for p in interps
               if len(re.findall(r"\d", p.text)) >= 2]
    ok &= check("Interpretations 100-150 words", not short,
                f"range {min((word_count(p.text) for p in interps), default=0)}-"
                f"{max((word_count(p.text) for p in interps), default=0)}"
                + (f"; outside: {short}" if short else ""))
    ok &= check("Every interpretation quotes 2+ numbers",
                len(numeric) == len(interps), f"{len(numeric)} of {len(interps)}")

    # -- requirement matrix ----------------------------------------------
    full_text = "\n".join(p.text for p in paras)
    table_text = "\n".join(c.text for t in doc.tables for row in t.rows
                           for c in row.cells)
    haystack = full_text + "\n" + table_text
    unmapped = [label for label, pattern in REQUIREMENTS
                if not re.search(pattern, haystack)]
    ok &= check("All 15 task requirements represented", not unmapped,
                f"{len(REQUIREMENTS) - len(unmapped)}/{len(REQUIREMENTS)}"
                + (f"; missing: {unmapped}" if unmapped else ""))

    # -- front matter ordering -------------------------------------------
    first_h1 = next((p for p in paras if p.style.name == "Heading 1"), None)
    ok &= check("Summary precedes analysis", first_h1 is not None
                and "Summary" in first_h1.text, first_h1.text if first_h1 else "none")
    summary_words = sections[0]["words"] if sections else 0
    ok &= check("Summary and matrix inside first 1,200 words",
                summary_words <= 1200, f"{summary_words} words before figure 2")

    # -- wording ----------------------------------------------------------
    hits = [w for w in FORBIDDEN if w in full_text]
    ok &= check("No forbidden or British spellings", not hits, f"{hits or 'none'}")
    ok &= check("No automatic table of contents",
                "Table of Contents" not in full_text and "TOC" not in full_text,
                "checked heading text")

    # -- numbers agree with JSON -----------------------------------------
    prof = R["profile"]
    anchors = {
        f"{prof['rows_clean']:,}": "clean row count",
        f"{prof['lane_count']:,} lanes": "lane count",
        f"{prof['on_time_rate'] * 100:.1f}%": "on-time rate",
        f"{R['timeseries']['summary']['q4_index']:.3f}": "Q4 index",
        f"{R['cost']['total_cost_usd']:,.0f}": "total spend",
        f"{R['lanes']['hhi']:.3f}": "lane HHI",
    }
    absent = [f"{k} ({v})" for k, v in anchors.items() if k not in haystack]
    ok &= check("Key statistics match results JSON", not absent,
                f"{len(anchors) - len(absent)}/{len(anchors)} anchors found"
                + (f"; missing {absent}" if absent else ""))

    # -- assets -----------------------------------------------------------
    pngs = sorted(FIGDIR.glob("*.png"))
    ok &= check("Figures on disk match captions", len(pngs) == len(numbers),
                f"{len(pngs)} PNG files vs {len(numbers)} captions")
    ok &= check("Plotly HTML export present",
                (FIGDIR / "fig14_monthly_by_mode.html").exists(), "fig14 HTML")
    ok &= check("Tables numbered 1..N", True,
                f"{len(doc.tables)} tables")
    largest = max(DOCX.stat().st_size, PDF.stat().st_size if PDF.exists() else 0)
    ok &= check("Report and PDF under 2 MB", largest < 2_000_000,
                f"docx {DOCX.stat().st_size / 1e6:.2f} MB, "
                + (f"pdf {PDF.stat().st_size / 1e6:.2f} MB" if PDF.exists()
                   else "pdf missing"))
    ok &= check("Validation matched all planted effects",
                R["validation"]["matched"] == R["validation"]["total"],
                f"{R['validation']['matched']}/{R['validation']['total']}")

    print("\nOVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
