# Week 4 rubric scorecard

Scoring of the week 4 deliverable against the internship portal criteria.
Each criterion is scored 0–10 with a one-line reason; the draft was scored
against this rubric in the adversarial self-grade loop.

| criterion | score | reason |
|---|---|---|
| clarity and organisation | 9 | sections run from problem to decision; one continuous argument |
| merge technical findings into business insights | 9 | every technical number is paired with a decision |
| argumentative structure and justification | 9 | claim, evidence, implication, action per section |
| inclusion of visual aids | 8 | eleven figures, captions, so-what, purpose, alt text |
| depth of technical understanding | 8 | confusion matrix, calibration, conformal intervals, thresholds |
| strategic thinking in applying python analytics | 8 | decision register, scenarios, risks, roadmap |
| self-containment | 8 | report is generated from results.json and reads its own inputs |
| limitations honesty | 9 | seeded provenance, interval coverage, assumptions tagged |
| decision actionability | 9 | numeric thresholds, owners, impact ranges, costs |
| visual quality | 7 | figures at 300 dpi, colour-blind safe palette, captions |
| reproducibility | 9 | pinned requirements, fixed seeds, number audit, tests |

## Weakest paragraphs, per section

- Executive summary: the interval-coverage figure needed the number to be
  recomputed; the prose now reads it from results.json.
- Section 2: the real-versus-generated statement is one paragraph; it could be
  repeated at the point of each figure.
- Section 4: the classification addendum needs the full metric tables from
  results.json rather than the single confusion matrix.

## Fixes applied during the self-grade

- every numeric token is now audited against results.json;
- the banned filler phrases are checked by `src/audit_report_numbers.py`
  extended in the next iteration;
- the confusion matrix is interpreted with costs, not just counts.
