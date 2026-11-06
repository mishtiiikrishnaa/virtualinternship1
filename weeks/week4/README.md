# week 4 — comprehensive reporting and decision support

**status:** done. report, pdf and figures rebuilt from the committed scripts.

## what the task asked for

compile a self-contained decision-support document that integrates the
preprocessing, exploratory analysis and predictive modelling from weeks 1 to 3
into actionable recommendations for logistics management, with an executive
summary, methodology, analysis, strategic recommendations, visual aids, risk
assessment and implementation strategy.

## what is here

the week 4 package re-runs the week 1 cleaning implementation over the week 1
raw extract, reads the week 2 exploratory results, trains the week 3 models on
the week 1 cleaned extract, and writes `results/results.json`.

the decision support layer adds: a full confusion matrix addendum, calibration,
threshold sweep, split-conformal intervals with empirical coverage, cost-weighted
decisions, capacity backtest, triage backtest, scenarios, risks and roadmap.

## pipeline

```bash
cd weeks/week4
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.run_pipeline   # cleaning audit, models, results.json, figures
python -m src.build_report   # Word report from results.json
python -m src.audit_report_numbers  # fails on any unmatched number
python -m pytest -q          # week 4 test suite
```

from the repository root, `make week4` runs the chain.

## outputs

| path | contents |
|---|---|
| `reports/Week4_Decision_Support_Report.docx` | decision-support report |
| `reports/Week4_Decision_Support_Report.pdf` | pdf proof from libreoffice |
| `reports/submission_description.txt` | portal description text |
| `results/results.json` | every number quoted in the report |
| `reports/figures/` | eleven figures at 300 dpi |
| `docs/audit.md`, `docs/rubric.md`, `docs/decisions.md`, `docs/reproducibility.md` | audit, rubric, decisions, reproducibility |

## headline results

| measure | value |
|---|---|
| forecast test MAE, ridge | 2.80 shipments per day |
| naive baseline test MAE | 3.54 shipments per day |
| forecast interval half width | about 6.8 shipments per day |
| forecast interval coverage | 92.9 percent |
| late recall at threshold 0.05 | 0.467 |
| late precision at threshold 0.05 | 0.117 |
| ROC-AUC | 0.900 |
| PR-AUC | 0.102 |

## known limits

- the development extract is seeded sample data, not live carrier telemetry;
- one annual cycle of demand history;
- the late class is rare and the test window holds few positives;
- cost assumptions are tagged and stress-tested, not measured.

mishti krishna — github.com/mishtiiikrishnaa
