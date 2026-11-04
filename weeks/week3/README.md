# week 3 — predictive modelling and forecasting

**status:** done. report, pdf and figures rebuilt from the committed scripts.

## what the task asked for

build and evaluate a predictive model in python that forecasts a logistics
parameter, and write it up as a word document: problem statement, algorithm
choice and rationale, preprocessing and feature engineering, training and
testing, evaluation with metrics and a confusion matrix, forecast trends, and
recommendations for logistics decision-making. the brief also demands honesty
about limitations — my week 2 report lost marks there, so this one is front
loaded with them.

## what is here

i reused the week 1 cleaned extract — 4,200 shipments shipped between 1
january and 29 december 2025 — rather than downloading yet another dataset.
it is seeded sample data, not a live carrier feed, and i say so in the report
and in every figure title. two models fall out of the same table:

| model | target | what it does |
|---|---|---|
| demand forecast | daily shipment volume | predicts the next 28 days of shipments per day |
| late delivery | late (delay > 0) vs on time | flags individual shipments likely to arrive late |

the late class is rare (1.7% of rows, 72 shipments), which makes the
classification genuinely hard and the confusion matrix honest rather than
decorative.

## pipeline

```bash
cd weeks/week3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.run_pipeline   # build features, train both models, evaluate,
                             # write results json, make figures, build the docx
python -m pytest -q          # 8 tests: splits, leakage, metrics, reproducibility
python -m src.build_report   # rebuild reports/Week3_Predictive_Modelling_and_Forecasting.docx
```

from the repository root, `make week3` runs the pipeline plus the test suite.

## outputs

| path | contents |
|---|---|
| `reports/Week3_Predictive_Modelling_and_Forecasting.docx` | ~3,000-word report, 10 figures, 6 tables |
| `reports/Week3_Predictive_Modelling_and_Forecasting.pdf` | pdf proof from libreoffice, used for the layout check |
| `results/metrics_forecast.json` | every forecast number quoted in the report |
| `results/metrics_classification.json` | every classification number quoted in the report |
| `results/splits.json` | train/validation/test date boundaries and class counts |
| `figures/` | 10 PNGs at 200 dpi, each with title, axes and a so-what caption |
| `data/processed/shipments_clean.csv` | week 1 cleaned extract, reused as input (committed) |
| `docs/leakage_review.md` | which columns are consequences of the target and banned from features |

### figures

| # | file | shows |
|---|---|---|
| 1 | `fig01_demand_series.png` | daily shipments with train/validation/test windows |
| 2 | `fig02_weekly_seasonality.png` | mean volume by day of week |
| 3 | `fig03_forecast_intervals.png` | 28-day forecast vs actual with prediction intervals |
| 4 | `fig04_residuals.png` | forecast residuals vs fitted values |
| 5 | `fig05_error_by_dow.png` | forecast MAE by day of week |
| 6 | `fig06_late_by_mode.png` | late rate by transport mode |
| 7 | `fig07_confusion_matrix.png` | confusion matrix at the chosen threshold |
| 8 | `fig08_roc_pr.png` | ROC and precision-recall curves |
| 9 | `fig09_feature_importance.png` | model feature importances |
| 10 | `fig10_learning_curve.png` | training size vs validation F1 |

## headline results

these come from the committed `results/*.json`, produced by an actual run:

| measure | value |
|---|---|
| forecast test MAE, ridge (naive 3.54) | 2.80 shipments/day |
| forecast test RMSE | 3.83 |
| forecast test sMAPE | 23.9% |
| late-delivery recall @ 0.05 threshold | 0.467 (7 of 15 test late) |
| late-delivery precision @ 0.05 threshold | 0.106 |
| ROC-AUC | 0.91 |
| PR-AUC | 0.11 (test prevalence 0.018) |

these come from the committed results/metrics.json, produced by an actual run.

## known limits

- the extract is seeded sample data from week 1, not real carrier telemetry; treat the results as method validation and re-fit on production data before acting.
- one year of daily volume means one annual cycle, so yearly seasonality is assumed, not proved.
- only 72 late shipments exist in total and 15 fall in the test window; a handful of misclassifications swing precision and recall, so rates carry wide uncertainty.
- no weather covariate exists in the extract, and distance is great-circle km between city centroids, not road miles.
- "late" is defined against a data-derived per-mode p90 promise, not a contractual SLA.
- the 28-day forecast is recursive, so errors compound; treat anything past two weeks as directional.

mishti krishna — github.com/mishtiiikrishnaa
