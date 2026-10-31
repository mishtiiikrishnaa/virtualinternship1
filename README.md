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
| 2 | Real dataset ingestion, profiling and contract changes | not started | [`weeks/week2`](weeks/week2) |
| 3 | Geospatial and temporal enrichment | not started | [`weeks/week3`](weeks/week3) |
| 4 | Quality automation, scheduled runs and reporting | not started | [`weeks/week4`](weeks/week4) |

Week 2 onward build on the same schema contract and entry point introduced in
week 1, so the structure is deliberately shallow: one folder per week, no
shared package to break, and a root `Makefile` that delegates.

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

Or from the repository root: `make week1`.

## Why one repository

The internship asks for a single project URL, and splitting four weeks across
four repositories would make the progression invisible — the interesting part
of this work is that the week 2 dataset arrives with week 1's contract already
in place, and the diff shows what the contract had to learn. One repository
with one folder per week keeps that diff readable.
