# Week 4 decisions log

Each entry records a judgement that a reviewer might otherwise have to
reverse-engineer. Ambiguities resolved during week 4 are logged here with a
one-line justification.

| id | decision | justification |
|---|---|---|
| W4-D-01 | the week 4 report re-runs the week 1 cleaning implementation over the week 1 raw extract | week 1 is the authoritative cleaning code; a copy would drift |
| W4-D-02 | the development extract is treated as generated data for all modelling findings | the generator is seeded and the provenance is stated; the report must not overclaim |
| W4-D-03 | the decision to use the cost of a missed late shipment at 1500 USD and a wasted escalation at 60 USD is tagged as an assumption and stress-tested | no operational cost data exists in the extract |
| W4-D-04 | the week 4 report builder is generated from results.json and audited by numeric token | rules out hand-typed numbers and fails the build on drift |
| W4-D-05 | British spelling is used in the week 4 report, per the week 4 style rule, while the week 2 and 3 audits used their own word lists | the operative week 4 rules take precedence and are enforced by the week 4 audit |

# Week 4 decisions pending

- whether to add a weather covariate before the next retraining run.
