# Report description (for the submission form)

The field asks for at least 200 words. Paste the block below; it is 318 words.

---

This report presents a strategy for collecting and preprocessing publicly
available logistics data with Python, supported by a working reference
implementation rather than a description alone. It begins by mapping the five
families of public logistics data — modelled freight flow estimates, customs and
trade records, movement telemetry, operational transactions, and reference data
such as UN/LOCODE and road networks — and explains why each family fails in a
different way. A source register assesses fourteen candidate datasets against
five gates: grain and key, licence, release stability, documentation, and
whether the data contains realistic defects. The US Bureau of Transportation
Statistics Freight Analysis Framework is selected as the reference dataset for
subsequent weeks, while several popular Kaggle uploads are rejected for
ambiguous provenance and undocumented grain.

The report then specifies a six-stage collection architecture: discovery and
licensing, acquisition with retries and provenance capture, an immutable
landing zone, profiling, cleaning, and validation gated publication. Three
original diagrams describe the end-to-end workflow, the eight cleaning stages,
and a decision path for missing values. Technical detail is given at the level
of functions rather than libraries: explicit date-format lists instead of
inference, the exact international pound for unit conversion, a currency parser
that resolves symbols and decimal-comma conventions, deduplication by latest
state rather than most complete row, and grouped median imputation with
mandatory boolean flags. Missing data is treated as a classification problem
(MCAR, MAR, MNAR) before it is an imputation problem, and a comparison table
records which methods were used, which were deferred, and why.

The accompanying repository runs the plan. A seeded synthetic extract of 4,380
rows is cleaned to 4,200 typed rows through thirteen validation checks and
nineteen unit tests, with every transform logged and a data-quality report
regenerated on each run. All figures and report numbers are produced by code,
so the claims in the document can be reproduced from a clean checkout with two
commands.
