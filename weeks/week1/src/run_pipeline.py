"""End-to-end run: land -> clean -> validate -> publish -> report.

    python -m src.run_pipeline

Exits non-zero if a critical check fails, so that CI on the repository fails
with it rather than publishing a quietly broken table.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import clean as clean_mod
from src import ingest, validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data" / "raw" / "shipments_raw.csv"
DEFAULT_OUT = ROOT / "data" / "processed"
DEFAULT_REPORT = ROOT / "reports" / "data_quality_report.md"


def _md_table(frame: pd.DataFrame) -> str:
    headers = [str(c) for c in frame.columns]
    rows = [[str(v) for v in row] for row in frame.itertuples(index=False)]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    line = lambda vals: "| " + " | ".join(v.ljust(w) for v, w in zip(vals, widths, strict=True)) + " |"
    border = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([line(headers), border, *(line(r) for r in rows)])


def build_report(
    raw_path: Path,
    manifest: dict,
    cleaned: pd.DataFrame,
    log: clean_mod.CleaningLog,
    checks: list[validate.Check],
    summary: dict[str, int],
    data_hash: str,
) -> str:
    step_table = _md_table(log.to_frame().assign(step=lambda d: d["step"]))
    check_table = _md_table(pd.DataFrame([c.as_dict() for c in checks]))
    profile = pd.DataFrame(
        {
            "column": cleaned.columns,
            "dtype": [str(cleaned[c].dtype) for c in cleaned.columns],
            "nulls": [int(cleaned[c].isna().sum()) for c in cleaned.columns],
            "distinct": [int(cleaned[c].nunique(dropna=True)) for c in cleaned.columns],
        }
    )
    profile_table = _md_table(profile)
    generated = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""# Data quality report — shipment table

Generated {generated} by `src/run_pipeline.py`. This file is an artefact, not a
document: it is regenerated on every run and its numbers are the numbers the
cleaned table actually contains.

## Run provenance

| property | value |
|---|---|
| source file | `{manifest['file']}` |
| source sha256 | `{manifest['sha256'][:16]}…` |
| source size | {manifest['bytes']:,} bytes |
| rows before cleaning | {manifest['rows_before']:,} |
| rows published | {len(cleaned):,} |
| output sha256 | `{data_hash[:16]}…` |
| checks | {summary['total']} total, {summary['failed']} failed, {summary['critical_failures']} critical |

## Cleaning steps

{step_table}

## Validation

{check_table}

## Column profile

{profile_table}

## Headline figures

- median weight: {cleaned['weight_kg'].median():,.1f} kg
- median freight cost: ${cleaned['freight_cost_usd'].median():,.2f}
- median transit: {cleaned['transit_days'].median()} days
- share of rows with late delivery (> 0 delay days): {(cleaned['delay_days'].fillna(0) > 0).mean():.1%}
- weights imputed: {cleaned['weight_imputed'].mean():.2%}
- costs imputed: {cleaned['cost_imputed'].mean():.2%}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the week 1 cleaning pipeline.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    manifest = ingest.fingerprint(args.raw)
    raw = ingest.read_raw(args.raw)
    manifest["rows_before"] = int(len(raw))

    cleaned, log = clean_mod.clean(raw)
    checks = validate.run_checks(cleaned)
    summary = validate.summarise(checks)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "shipments_clean.csv"
    cleaned.to_csv(out_path, index=False)
    data_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    ingest.write_manifest(out_path, {**manifest, "output_sha256": data_hash}, args.out_dir)

    report = build_report(args.raw, manifest, cleaned, log, checks, summary, data_hash)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")

    print(f"published {len(cleaned):,} rows -> {out_path.relative_to(ROOT)}")
    print(f"report -> {args.report.relative_to(ROOT)}")
    for check in checks:
        if not check.passed:
            print(f"  {check.severity.upper():8} {check.name}: {check.detail}")

    return 1 if summary["critical_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
