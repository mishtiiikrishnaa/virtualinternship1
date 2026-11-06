# Week 4 reproducibility

## Environment

Pinned in `weeks/week4/requirements.txt`: pandas 3.0.1, numpy 2.5.4, matplotlib
3.10.8, seaborn 0.13.2, scikit-learn 1.8.0, scipy 1.18.1, python-docx 1.2.0,
pyyaml 6.0.3, pytest 9.2.0.

## Commands

From the repository root:

```bash
make week4
```

From `weeks/week4`:

```bash
python -m src.run_pipeline      # cleaning audit, models, results.json, figures
python -m src.build_report      # Word report from results.json
python -m src.audit_report_numbers  # numeric-token audit; fails on drift
python -m pytest -q              # week 4 test suite
```

## Determinism

- fixed seeds: numpy random_state 42, scikit-learn random_state 42;
- time-ordered splits, no shuffling, test window touched once;
- dates parsed with explicit formats;
- results written to `weeks/week4/results/results.json`.

## Number audit

`python -m src.audit_report_numbers` extracts every numeric token from
`weeks/week4/reports/Week4_Decision_Support_Report.docx` and matches it against
`weeks/week4/results/results.json` within rounding tolerance, or against an
explicit allowlist (years, section numbers, task-spec numbers). Any unmatched
token fails the build.

## Reproducibility check

The full week 4 pipeline was run twice from a clean state; `results.json` was
byte-identical between runs.
