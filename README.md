<a id="readme-top"></a>
<div align="center">
    
<!-- PROJECT SHIELDS -->
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Last Commit][commit-shield]][commit-url]

</div>
<!-- PROJECT HEADER -->
<br />
<div align="center">
  <h3 align="center">Virtual Logistics Data Analysis Internship</h3>

  <p align="center">
    A four-week, end-to-end analytics project on shipment data: preprocessing, exploratory analysis,
    predictive modelling, and a cost-grounded decision support report.
    <br />
    <a href="#deliverables"><strong>Explore the deliverables »</strong></a>
    <br />
    <br />
    <a href="weeks/week4/reports/Week4_Decision_Support_Report.pdf">Read the Week 4 report</a>
    &middot;
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/issues/new">Report Bug</a>
    &middot;
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/issues/new">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#deliverables">Deliverables</a></li>
        <li><a href="#headline-results-week-4">Headline Results (Week 4)</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#repository-layout">Repository Layout</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

This repository holds all four weeks of a virtual logistics data analysis internship. The work follows one
thread from raw data to a business decision:

1. clean and validate shipment data against an explicit schema contract,
2. explore it for demand and service-quality signals,
3. build next-day demand forecasts and a late-delivery risk model, and
4. turn those models into costed operational decisions, with the uncertainty stated.

Each week lives in its own directory with its own code, requirements, generated results and report. Nothing
from a later week overwrites an earlier one, so a reviewer can read Week 1 without wading through Week 4, and
the commit history for each week stays legible.

The final deliverable is the [Week 4 Comprehensive Decision Support Report](weeks/week4/reports/Week4_Decision_Support_Report.pdf),
which integrates the earlier weeks into a decision register, a risk assessment, a sensitivity analysis and an
implementation roadmap. Every number in it is checked by an automated audit against the values the pipeline
emitted.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Deliverables

| Week | Focus | Report | Code | Figures |
|------|-------|--------|------|---------|
| 1 | Strategic data collection and preprocessing blueprint | [PDF](weeks/week1/reports/Week1_Strategic_Data_Collection_and_Preprocessing_Blueprint.pdf) · [DOCX](weeks/week1/reports/Week1_Strategic_Data_Collection_and_Preprocessing_Blueprint.docx) | [`weeks/week1`](weeks/week1) | 3 |
| 2 | Exploratory data analysis and visualization, with a real transborder freight benchmark | [PDF](weeks/week2/reports/Week2_EDA_and_Visualization.pdf) · [DOCX](weeks/week2/reports/Week2_EDA_and_Visualization.docx) | [`weeks/week2`](weeks/week2) | 15 |
| 3 | Predictive modelling and forecasting, with a leakage review | [PDF](weeks/week3/reports/Week3_Predictive_Modelling_and_Forecasting.pdf) · [DOCX](weeks/week3/reports/Week3_Predictive_Modelling_and_Forecasting.docx) | [`weeks/week3`](weeks/week3) | 10 |
| 4 | Comprehensive reporting and decision support | [PDF](weeks/week4/reports/Week4_Decision_Support_Report.pdf) · [DOCX](weeks/week4/reports/Week4_Decision_Support_Report.docx) | [`weeks/week4`](weeks/week4) | 13 |

Week 4 also keeps its working notes in [`weeks/week4/docs`](weeks/week4/docs): `audit.md`, `decisions.md`,
`leakage_review.md`, `reproducibility.md` and `rubric.md`. Week 3 has its own
[`leakage_review.md`](weeks/week3/docs/leakage_review.md).

### Headline Results (Week 4)

All figures below are on the **simulated development extract** (4,200 shipments, calendar year 2025) and match
the submitted report.

| Question | Result |
|----------|--------|
| Next-day demand forecast (28-day test window) | Scaled ridge MAE **2.80** shipments/day, against 3.54 for lag-1 naive and 4.32 for seasonal-naive (lag-7) |
| Forecast uncertainty | 95% prediction interval half-width 6.8; coverage 92.9% (26 of 28 days; Wilson 95% CI 77.4% to 98.0%) |
| Capacity policy | Forecast + 1 residual standard deviation: total cost **$5,339**, 4 of 28 under-capacity days. The 95% bound ($6,638) is kept as a service-level alternative |
| Late-delivery triage (threshold 0.05) | Recall 46.7% (Wilson 24.8% to 69.9%), precision 11.7%, ROC-AUC 0.900 on 15 late events |
| Net triage saving | **$6,900**, 95% bootstrap CI $0 to $14,641 |
| Break-even | Triage beats no-triage when the missed-late to wasted-triage cost ratio exceeds 8.57:1 |

Unit costs ($1,500 per missed late shipment, $60 per escalation, $150 per capacity shortfall unit, $30 per
unused reservation unit) are modelling assumptions, not observed data.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

[![Python][python-shield]][python-url]
[![pandas][pandas-shield]][pandas-url]
[![NumPy][numpy-shield]][numpy-url]
[![scikit-learn][sklearn-shield]][sklearn-url]
[![Matplotlib][mpl-shield]][mpl-url]
[![Plotly][plotly-shield]][plotly-url]
[![Jupyter][jupyter-shield]][jupyter-url]
[![pytest][pytest-shield]][pytest-url]

Reports are generated by each week's `build_report.py` as `.docx` and rendered to `.pdf`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running, follow these steps. Each week is self-contained with its own
`requirements.txt`, so you can run any one of them on its own.

### Prerequisites

- Python 3.13
- `pandoc` and LibreOffice, only if you want to rebuild the `.docx` / `.pdf` reports
- `make` (optional; every step also works as a plain `python` command)

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/mishtiiikrishnaa/virtualinternship1.git
   cd virtualinternship1
   ```
2. Create a virtual environment inside the week you want to run (Week 4 shown)
   ```sh
   cd weeks/week4
   python -m venv .venv && source .venv/bin/activate
   ```
3. Install that week's dependencies
   ```sh
   pip install -r requirements.txt
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->
## Usage

Run these from inside the week's directory.

**Week 4: decision support** (22 tests)

```sh
python -m src.run_pipeline          # fit models, compute policies, emit results.json and emitted_numbers.json
python -m src.build_report          # rebuild the report from the emitted values
python -m src.audit_report_numbers  # check every number in the report against the emitted values
python -m src.figure_qa             # figure checks
python -m pytest -q
```

The audit extracts every numeric token from the built report and verifies it against the pipeline's emitted
numbers, so a figure in the text cannot drift away from what the code produced.

**Week 3: predictive modelling** (13 tests) and **Week 1: preprocessing** (19 tests)

```sh
python -m src.run_pipeline
python -m pytest -q
python -m src.build_report          # needs pandoc + LibreOffice
```

**Week 2: exploratory analysis.** See [`weeks/week2/README.md`](weeks/week2/README.md)
for the run order. The analysis is also available as a notebook:
[`weeks/week2/notebooks/week2_eda.ipynb`](weeks/week2/notebooks/week2_eda.ipynb).

The Week 4 report's **decision register** turns the models into four operational rules:

| ID | Rule |
|----|------|
| D-1 | Commit next-day dispatch capacity at forecast + 1 residual standard deviation |
| D-2 | Escalate shipments with late-delivery risk score at or above 0.05 |
| D-3 | Apply mode-specific delivery promises where Ocean lateness persists in live data |
| D-4 | Retrain when rolling 28-day forecast coverage falls below 90% or feature drift PSI exceeds 0.20 |

_For the full argument, tables, figures and appendices, see the [Week 4 report](weeks/week4/reports/Week4_Decision_Support_Report.pdf)._

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- REPOSITORY LAYOUT -->
## Repository Layout

```
virtualinternship1/
├── .github/workflows/ci.yml
├── Makefile
├── README.md
└── weeks/
    ├── week1/               # preprocessing blueprint
    │   ├── config/          #   schema contract (schema.yml)
    │   ├── data/            #   raw and processed shipments, manifest
    │   ├── docs/            #   blueprint, data dictionary, decision log, sources, figures
    │   ├── reports/         #   data quality report, report .docx and .pdf
    │   ├── src/             #   ingest, clean, validate, run_pipeline, make_figures, build_report
    │   └── tests/
    ├── week2/               # exploratory analysis
    │   ├── data/            #   external (BTS), simulated, processed
    │   ├── figures/         #   15 figures, incl. an interactive Plotly chart
    │   ├── notebooks/       #   week2_eda.ipynb
    │   ├── reports/         #   report .docx and .pdf
    │   ├── results/         #   JSON results (profile, tests, outliers, time series, ...)
    │   └── src/             #   generate_data, fetch_real_data, clean, analyze, audit, make_figures, ...
    ├── week3/               # forecasting and late-delivery models
    │   ├── docs/            #   leakage review
    │   ├── figures/         #   10 figures
    │   ├── reports/         #   report .docx and .pdf
    │   ├── results/         #   metrics.json, feature_manifest.json
    │   ├── src/             #   features, models, run_pipeline, make_figures, build_report
    │   └── tests/
    └── week4/               # decision support report
        ├── docs/            #   audit, decisions, leakage review, reproducibility, rubric
        ├── reports/         #   report .docx and .pdf, 13 figures, emitted_numbers.json
        ├── results/         #   results.json
        ├── src/             #   features, models, decision_support, metrics, run_pipeline,
        │                    #   build_report, audit_report_numbers, figure_qa, ...
        └── tests/
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] Week 1: preprocessing blueprint and schema contract
- [x] Week 2: exploratory analysis and visualization
- [x] Week 3: predictive modelling and forecasting
- [x] Week 4: decision support report with automated number audit

See the [open issues](https://github.com/mishtiiikrishnaa/virtualinternship1/issues) for a full list of
proposed features and known issues.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

This is individual internship coursework, so pull requests are not expected. Suggestions and bug reports are
welcome: please open an issue with the `bug` or `enhancement` tag.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Best-README-Template](https://github.com/othneildrew/Best-README-Template) for this README's structure
* [Bureau of Transportation Statistics](https://www.bts.gov/) for the North American transborder freight data used in Week 2
* [Img Shields](https://shields.io) for the badges

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[stars-shield]: https://img.shields.io/github/stars/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[stars-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/stargazers
[issues-shield]: https://img.shields.io/github/issues/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[issues-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/issues
[commit-shield]: https://img.shields.io/github/last-commit/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[commit-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/commits/main
[python-shield]: https://img.shields.io/badge/python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[pandas-shield]: https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white
[pandas-url]: https://pandas.pydata.org/
[numpy-shield]: https://img.shields.io/badge/numpy-013243?style=for-the-badge&logo=numpy&logoColor=white
[numpy-url]: https://numpy.org/
[sklearn-shield]: https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white
[sklearn-url]: https://scikit-learn.org/
[mpl-shield]: https://img.shields.io/badge/matplotlib-11557C?style=for-the-badge
[mpl-url]: https://matplotlib.org/
[plotly-shield]: https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white
[plotly-url]: https://plotly.com/python/
[jupyter-shield]: https://img.shields.io/badge/jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white
[jupyter-url]: https://jupyter.org/
[pytest-shield]: https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white
[pytest-url]: https://pytest.org/
