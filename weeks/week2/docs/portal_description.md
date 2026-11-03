# Portal submission text

Week 2 asked for exploratory analysis that finds something and then proves it,
rather than a gallery of charts. I analyzed 49,935 cleaned shipments from a
seeded two-year simulation, then checked the seasonal findings against 38,567
real truck crossings published by the U.S. Bureau of Transportation Statistics.

The analysis moves from distribution to explanation. Transit times are strongly
mode-dependent, with medians of 3 days by air, 6 by road, 9 by rail and 24 by
sea, and the distributions are right-skewed enough that means mislead. Volume
peaks in the fourth quarter at 1.35 times the baseline, a seasonal pattern that
STL decomposition isolates with a strength of 0.99. February 2025 is the named
disruption: on-time performance falls to 71.4% against 83.1% elsewhere, and sea
transit gains two days.

Carrier performance is the finding with the clearest commercial consequence.
On-time rates run from 90.7% at Ironline to 59.4% at Northwind, a 31.3
percentage-point gap that a chi-square test confirms is not sampling noise
(p < 0.001, Cramér's V = 0.29). Two carriers sit far below an otherwise tight
88–91% cluster, which turns a vague concern about service into a short list for
a contract review. Cost behaves as a power law: elasticity with respect to
weight is 0.80 and with respect to distance is 1.00, giving an R² of 0.95 once
mode is included. Omitting mode drops the weight elasticity to 0.47, a clean
demonstration of omitted-variable bias.

Outliers needed care. Simple percentile rules flagged 1.4% of rows but mostly
caught legitimate heavy freight; a residual-modified z-score on log cost raised
recall to 91% at 53% precision. Lane concentration is milder than expected:
117 lanes, with 55 carrying 80% of volume.

Ten planted effects were recovered, ten confirmed. The report is 31 pages with
15 figures, each paired with its code and an interpretation, and the whole
pipeline reruns from a pinned environment.
