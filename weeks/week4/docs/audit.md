# Week 4 forensic audit — what the code says, what the earlier reports said

Scope: weeks 1 to 3 artefacts reviewed before any week 4 analysis was written.
Source of record: the committed code and results JSON, plus the submitted
documents.

## Week 1 — collection and preprocessing

Task: define a source, a schema contract and a cleaning process for logistics
shipment data.

Built: `weeks/week1/src/*` with a 13-check validation contract, a cleaning log,
a data-quality report and a blueprint report.

Dataset: seeded sample extract of 4,380 raw rows reduced to 4,200 published rows.

Findings: missingness, unit drift, duplicates, outliers.

Inconsistencies found: none material in the code; the report prose quoted the
cleaning log and the JSON agreed.

## Week 2 — exploratory analysis and visualisation

Task: EDA on two datasets (seeded simulation and BTS border crossings).

Built: `weeks/week2/src/analyze.py`, `make_figures.py`, `build_report.py`,
`audit.py`; results in `weeks/week2/results/*.json`.

Dataset: 49,935 cleaned simulated rows over 24 months; 38,567 BTS crossings.

Findings: Q4 uplift index 1.348, disruption month February 2025,
carrier gap, cost elasticity.

Inconsistencies found: the submitted report and the code agree on the headline
numbers; the cleaning table labelled steps 5 and 6 as one row, which is a
presentation gap rather than a number error.

## Week 3 — predictive modelling and forecasting

Task: forecast daily volume and classify late delivery.

Built: `weeks/week3/src/{features,models,make_figures,build_report}.py`;
results in `weeks/week3/results/metrics.json`.

Dataset: week 1 cleaned extract, 4,200 shipments, 2025.

Findings: ridge test MAE 2.80 vs naive 3.54; late recall 0.467 at precision
0.117 at threshold 0.05; ROC-AUC 0.900; PR-AUC 0.102.

Inconsistencies found: the built Word document carries week 2 core properties
(title, subject, keywords) because `docx_helpers.save` overwrote the values set
by the builder. This is a packaging defect, not a number defect, and week 4
fixed it in its own copy of the helper.

Also found: the executive summary and the forecast section disagreed about the
interval half width (7.5 versus the value recomputed at build time); the report
was regenerated, so the defect is latent rather than persistent.

## Week 4 — what changed

The week 4 pipeline re-runs the week 1 cleaning implementation over the week 1
raw extract, reads the week 2 EDA results, trains the week 3 models on the week
1 cleaned extract, and writes `weeks/week4/results/results.json`. Every number
in the week 4 report is read from that file by `src/build_report.py`, and
`src/audit_report_numbers.py` fails the build on any numeric token that cannot
be matched to it or to the allowlist.
