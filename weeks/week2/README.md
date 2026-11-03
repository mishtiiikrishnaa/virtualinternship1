# Week 2 — Exploratory Data Analysis and Visualization in Logistics

**Status:** complete. Report, PDF, notebook and figures rebuilt from the
committed scripts on 2 November 2026.

## What the task asked for

Explore a logistics dataset in Python, uncover trends, outliers and patterns,
apply statistical analysis and visualization, and document the process, the
interpretations and the recommendations in a Word report. Every chart must be
an embedded image produced by matplotlib, seaborn or plotly, and every chart
must be explained rather than merely labelled.

## What is here

Two datasets, because the task pulls in two directions. A simulated extract
carries known planted effects, so the analysis can be scored against ground
truth. A real public extract proves the same code survives contact with a
dataset nobody designed for it.

| dataset | source | size | role |
|---|---|---|---|
| Simulated shipments | `src/generate_data.py`, seed 42 | 50,600 raw rows → 49,935 clean, 24 months (2024-01 to 2025-12) | primary; ten planted effects, dirty labels, missing values, duplicates |
| BTS Border Crossing | U.S. Bureau of Transportation Statistics, dataset `keg4-3bc2`, public domain, accessed 2026-11-02 | 38,567 truck crossings, 115 ports, 1996-01 to 2026-09 | external validation of the seasonal and disruption findings |

Provenance, licence, retrieval timestamp and checksums for the real extract are
in `data/external/bts_border_trucks.meta.json`. The download is committed as a
234 KB gzip so the pipeline runs offline.

## Pipeline

```bash
cd weeks/week2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.fetch_real_data    # BTS download; skips if the gzip is present and matches
python -m src.generate_data      # seeded simulation + planted effects + injected dirt
python -m src.clean              # parse, convert, deduplicate, flag
python -m src.analyze            # writes every number the report quotes
python -m src.make_figures       # 15 figures at 200 dpi, plus a plotly HTML export
python -m src.build_report       # .docx, prose assembled from results/*.json
sh src/render_pdf.sh             # PDF proof, compressed under the 2 MB cap
python -m src.build_notebook     # executes notebooks/week2_eda.ipynb in place
python -m src.audit              # 21 checks; non-zero exit on failure
```

From the repository root, `make week2` runs the same chain.

The PDF proof is rendered from the docx, not built by python:

```bash
sh src/render_pdf.sh
```

That converts with LibreOffice, then re-encodes the images as JPEG at 200
dots per inch with Ghostscript. The docx keeps 256-colour PNGs, so the Word
file stays crisp at 0.92 MB; the PDF lands at 1.88 MB. Both are under the
portal's 2 MB upload cap, and the audit fails the build if either grows past
it.

`src/audit.py` is the submission gate, not decoration. It counts prose words,
checks figure count, alt text and interpretation length, verifies that all
fifteen task requirements appear in the coverage matrix, scans for placeholder
text and British spellings, and re-reads the JSON to confirm that quoted numbers
match their source. A passing run prints `PASS` on all twenty-one checks.

Plotly's static export needs a Chrome build for kaleido:

```bash
plotly_get_chrome -y
```

## Outputs

| path | contents |
|---|---|
| `reports/Week2_EDA_and_Visualization.docx` | 31-page report, 15 figures, 12 tables |
| `reports/Week2_EDA_and_Visualization.pdf` | rendered proof used for the visual QA pass |
| `notebooks/week2_eda.ipynb` | executed notebook, 14 code cells, outputs stored |
| `figures/` | 15 PNGs at 200 dpi, plus `fig14_monthly_by_mode.html` |
| `results/` | 14 JSON files; the only source of numbers in the report |
| `data/simulated/` | raw and ground-truth extracts |
| `data/processed/shipments_clean.csv` | cleaned analysis table, 35 columns (generated, not committed) |
| `docs/portal_description.md` | the 250–350 word submission text for the internship portal |

### Figures

| # | file | shows |
|---|---|---|
| 1 | `fig01_eda_workflow.png` | analysis workflow, question to evidence |
| 2 | `fig02_transit_histogram.png` | transit time histogram with KDE, log axis, p90 marker |
| 3 | `fig03_mode_violin.png` | transit distribution by mode |
| 4 | `fig04_monthly_volume.png` | monthly volume with 3-month centered mean |
| 5 | `fig05_stl_decomposition.png` | STL trend, seasonal and residual components |
| 6 | `fig14_plotly_monthly_by_mode.png` + `.html` | interactive stacked monthly volume by mode |
| 7 | `fig13_mode_month_small_multiples.png` | seasonality by mode, small multiples |
| 8 | `fig06_correlation_heatmap.png` | Spearman correlation of numeric fields |
| 9 | `fig07_carrier_ontime.png` | on-time rate by carrier with 95% confidence intervals |
| 10 | `fig08_cost_loglog.png` | cost against weight, log-log, fitted line and flagged rows |
| 11 | `fig12_cost_per_kg_ecdf.png` | empirical CDF of cost per kilogram by mode |
| 12 | `fig09_outlier_methods.png` | univariate rules against residual-modified z |
| 13 | `fig11_lane_pareto.png` | lane concentration, cumulative share |
| 14 | `fig10_delay_heatmap.png` | mean delay by weekday and month |
| 15 | `fig15_bts_real_data.png` | BTS seasonality and the 2020 collapse |

### Results

| file | drives |
|---|---|
| `profile.json` | shape, dtypes, missingness |
| `cleaning.json` | every cleaning count in Table 4 |
| `dirt_injected.json` | defects introduced, for the cleaning log |
| `planted_effects.json` | Table 2, what the simulation hid |
| `descriptive.json` | Table 5 and the distribution section |
| `distributions.json` | mode medians, quantiles, on-time by mode |
| `timeseries.json` | volume index, STL strength, disruption month, BTS benchmark |
| `tests.json` | chi-square and effect size for carrier and mode differences |
| `correlations.json` | heatmap values and the strongest pairs |
| `cost.json` | elasticities, R², spend shares, model comparison |
| `outliers.json` | method comparison, recall and precision |
| `lanes.json` | Pareto shares, HHI, lane counts |
| `validation.json` | planted against recovered, Table 11 |

## Reading order for a reviewer

1. `reports/Week2_EDA_and_Visualization.pdf`, pages 1–2: summary of findings and
   the requirements coverage matrix. The conclusions are on page 1 on purpose;
   nobody should have to read 31 pages to learn that two carriers are failing.
2. `results/validation.json`: ten planted effects, ten recovered.
3. `src/analyze.py`: the definition of every statistic quoted in the report.
4. `src/audit.py`: what "done" was held to.

## Known limits

- The simulated extract is synthetic. It is realistic in shape and defect
  structure, but its elasticities are the ones that were planted, so recovering
  them validates the method and says nothing about real freight markets.
- The BTS extract counts truck crossings at land ports, not shipments. It can
  corroborate a seasonal shape; it cannot corroborate shipment-level transit
  performance, and the report does not ask it to.
- On-time performance is undefined for the 1,088 rows with no delivery date.
  Those rows are excluded from rate calculations and counted, not imputed.
- Freight cost is missing for 2,619 rows, and the missingness is not random:
  cheaper consolidations are less likely to carry a recorded charge. Cost models
  are fitted on observed rows only, and the report states the direction of the
  bias rather than pretending it away.
