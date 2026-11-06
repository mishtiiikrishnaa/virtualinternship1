# virtualinternship1

One repository for the four-week virtual internship: public logistics data,
python preprocessing, and the written reports that go with each week.

Each week lives in its own directory with its own report, code, data contract
and generated artefacts. Nothing from a later week overwrites an earlier one,
so a reviewer can read week 1 without wading through week 4, and the commit
history for each week stays legible.

## The four weeks

| week | focus | status | folder |
|---|---|---|---|
| 1 | Strategic data collection and preprocessing blueprint | submitted | [`weeks/week1`](weeks/week1) |
| 2 | Exploratory data analysis and visualization | submitted | [`weeks/week2`](weeks/week2) |
| 3 | Predictive modelling and forecasting | submitted (in this commit) | [`weeks/week3`](weeks/week3) |
| 4 | Decision support and business impact | submitted | [`weeks/week4`](weeks/week4) |

Week 2 onward build on the same schema contract and entry point introduced in
week 1, so the structure is deliberately shallow: one folder per week, no
shared package to break, and a root `Makefile` that delegates.

## Progress

- [x] week 1
- [x] week 2
- [x] week 3
- [x] week 4

## Layout

```
virtualinternship1/
├── Makefile                 # delegates: make week1 / week2 / ...
├── README.md                # this file
└── weeks/
    ├── week1/               # strategy, pipeline, diagrams, submitted .docx
    │   ├── config/          # schema contract
    │   ├── data/            # raw (seeded, committed) and processed (generated)
    │   ├── docs/            # report source, source register, dictionary, decisions
    │   ├── reports/         # generated quality report, submitted docx + pdf
    │   ├── src/             # ingest, clean, validate, run, figures, docx build
    │   └── tests/
    ├── week2/
    ├── week3/
    └── week4/
        ├── config/          # model and decision constants
        ├── data/            # raw (seeded, committed) and processed (generated)
        ├── docs/            # audit, rubric, decisions, reproducibility, week readme
        ├── reports/         # decision-support report, figures, submission description
        ├── results/         # single source of numbers (results.json, figure paths)
        ├── src/             # clean, features, models, metrics, decision support, figures, report, audit
        └── tests/           # week 4 test suite
```

## Running week 1

```bash
cd weeks/week1
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.run_pipeline    # clean, validate, publish, regenerate the report
python -m pytest -q           # 19 tests
python -m src.build_report    # rebuild the .docx (needs pandoc + libreoffice)
```

Or from the repository root: `make week1` or `make week2`. Week 2 needs a
Chrome build once for plotly's static export (`plotly_get_chrome -y`); its PDF
is rendered with LibreOffice and compressed with Ghostscript.

## Running week 3

```bash
cd weeks/week3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.run_pipeline    # build features, models, figures, results, report
python -m pytest -q           # 13 tests
python -m src.build_report     # rebuild the .docx (no pandoc; LibreOffice only for the optional PDF proof)
```

Or from the repository root: `make week3`.

## Running week 4

```bash
cd weeks/week4
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.run_pipeline     # clean audit, models, metrics, decisions, results, figures
python -m pytest -q            # 15 tests
python -m src.build_report     # rebuild the .docx from results/results.json
python -m src.audit_report_numbers   # fail the build on any unmatched number

Or from the repository root: `make week4`.
```

The week 4 pipeline is re-run from a clean environment on every build, and
the number audit compares every numeric token in the document against
`weeks/week4/results/results.json`, failing the build when a number cannot be
matched. The full reproducibility record lives in
[`weeks/week4/docs/reproducibility.md`](weeks/week4/docs/reproducibility.md).

## Headline results

Week 4 closed the loop between cleaning, forecasting, triage and decisions.
On the week 1 development extract, the ridge forecast reached a test mean
absolute error of 2.8 shipments per day against a naive lag-1 forecast of 3.5,
an interval half width of about 6.8 shipments per day, and an empirical
coverage of 92.9 percent. The late-delivery classifier at the cost-weighted
threshold of 0.05 reached a recall of 46.7 percent at a precision of 11.7
percent, with an expected cost of 1,500 dollars per missed late shipment and 60
dollars per wasted escalation. Its Brier score is 0.025 against a base-rate
Brier of 0.017 with a negative Brier skill, so the probabilities are ranking
scores rather than calibrated probabilities.

## How the numbers are guaranteed to match the code

Every number in the week 4 report is read from
[`weeks/week4/results/results.json`](weeks/week4/results/results.json) by
`weeks/week4/src/build_report.py`, and `weeks/week4/src/audit_report_numbers.py`
extracts every numeric token from the built document and checks it against that
file or an explicit allowlist. The build fails on any unmatched number, and the
pipeline writes results from computed values only.

## Built with

Python 3, pandas, numpy, scikit-learn, scipy, matplotlib, seaborn, python-docx,
pytest, and LibreOffice for the PDF render.

## Why one repository

The internship asks for a single project URL, and splitting four weeks across
four repositories would make the progression invisible — the interesting part
of this work is that the week 2 dataset arrives with week 1's contract already
in place, and the diff shows what the contract had to learn. One repository
with one folder per week keeps that diff readable.
