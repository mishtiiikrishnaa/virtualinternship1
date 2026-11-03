"""Regenerate and execute ``notebooks/week2_eda.ipynb``.

The notebook is a walkthrough of the same functions that produce the report, so
the numbers a reader sees there match the numbers in the document. Building it
from this script keeps the notebook free of stale outputs: every run re-executes
against the committed data.

    python -m src.build_notebook
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "week2_eda.ipynb"

HEADER = """import json
import sys
from pathlib import Path

import pandas as pd
from IPython.display import Image, display

ROOT = Path.cwd().parent
sys.path.insert(0, str(ROOT))

from src.analyze import (build_cost, build_correlations, build_descriptive,
                         build_lanes, build_outliers, build_profile,
                         build_tests)

DATA = ROOT / "data" / "processed" / "shipments_clean.csv"
REAL = ROOT / "data" / "external" / "bts_border_trucks.csv.gz"
FIG = ROOT / "figures"
RESULTS = ROOT / "results"

df = pd.read_csv(DATA, parse_dates=["order_date", "ship_date",
                                    "delivery_date", "month_start"])
real = pd.read_csv(REAL, parse_dates=["date"])
clean = json.loads((RESULTS / "cleaning.json").read_text())
prof = json.loads((RESULTS / "profile.json").read_text())
print(f"cleaned rows: {len(df):,}  columns: {df.shape[1]}")
print(f"window: {df['order_date'].min():%Y-%m-%d} to {df['order_date'].max():%Y-%m-%d}")
print(f"BTS rows: {len(real):,}  ports: {real['port_name'].nunique()}")"""


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source.strip("\n"))


def md(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(source.strip("\n"))


CELLS = [
    md("""# Week 2 - Exploratory Data Analysis and Visualization

This notebook walks through the analysis behind
`reports/Week2_EDA_and_Visualization.docx` using the same functions in `src/`.
Every number below is recomputed from `data/processed/shipments_clean.csv`;
the seed is fixed at 42 in `src/generate_data.py`.

Run `make week2` from the repository root to rebuild the data, figures,
results and report, then execute this notebook against them."""),
    code(HEADER),
    md("""## 1. Profile and data quality

`build_profile` counts rows, flags and eligible denominators. Cost is missing
not at random, so it is never imputed and on-time rates use only shipments with
a terminal status."""),
    code("""
profile = build_profile(df, (clean["rows_raw"], clean["cols_raw"]))
for key in ["rows_clean", "cols_clean", "on_time_eligible", "on_time_rate",
            "cost_scored_rows", "cost_missing_share", "lane_count"]:
    print(f"{key:20s} {profile[key]}")
print("\\nstatus counts:", profile["status_counts"])
"""),
    md("""## 2. Distributions by mode

Transit is right-skewed with a second mass near 24 days, which is sea freight.
The mode comparison uses medians and 90th percentiles because the mean is
dragged by a tail that reaches 75 days."""),
    code("""
desc = build_descriptive(df)
summary = pd.DataFrame({
    m: {"shipments": v["shipments"],
        "share": round(v["share"], 4),
        "median transit (d)": v["median_transit_days"],
        "p90 transit (d)": v["p90_transit_days"],
        "on-time": round(v["on_time_rate"], 4),
        "median cost/kg": round(v["median_cost_per_kg"], 2)}
    for m, v in desc["by_mode"].items()}).T
summary
"""),
    code("""
display(Image(filename=str(FIG / "fig02_transit_histogram.png"), width=760))
display(Image(filename=str(FIG / "fig03_mode_violin.png"), width=760))
"""),
    md("""## 3. Trend and seasonality

The fourth-quarter index compares the mean of October to December with the
other nine months. STL separates the calendar from the trend; the seasonal
strength is the share of variance the seasonal component explains."""),
    code("""
ts = json.loads((RESULTS / "timeseries.json").read_text())
s, dec, dis = ts["summary"], ts["decomposition"], ts["disruption"]
print(f"mean monthly volume      {s['mean_monthly']:,.1f}")
print(f"peak / trough            {s['peak_month'][:7]} {s['peak_value']:,} | "
      f"{s['trough_month'][:7]} {s['trough_value']:,}")
print(f"Q4 index                 {s['q4_index']:.3f}  (+{s['q4_uplift_pct']:.1f}%)")
print(f"seasonal strength        {dec['seasonal_strength']:.3f}")
print(f"trend strength           {dec['trend_strength']:.3f}")
print(f"Feb 2025 on-time         {dis['feb_on_time']:.3f} vs {dis['baseline_on_time']:.3f}")
"""),
    code("""
display(Image(filename=str(FIG / "fig04_monthly_volume.png"), width=760))
display(Image(filename=str(FIG / "fig05_stl_decomposition.png"), width=760))
"""),
    md("""## 4. Relationships and group tests

Pearson understates a multiplicative relationship, so the matrix is Spearman.
Group tests use Kruskal-Wallis with epsilon-squared, and carrier differences use
chi-square with Cramer's V because the sample is large enough to make p-values
uninformative on their own."""),
    code("""
corr = build_correlations(df)
print(corr["top_pairs"][:3])
tests = build_tests(df)
print("\\nmode transit: H =", round(tests["transit_by_mode"]["kruskal_h"], 2),
      "epsilon^2 =", tests["transit_by_mode"]["epsilon_squared"])
otc = tests["on_time_by_carrier"]
print(f"carrier on-time: chi2 {otc['chi2']:.2f}, V {otc['cramers_v']:.3f}, "
      f"{otc['best_carrier']} {otc['best_rate']:.3f} vs "
      f"{otc['worst_carrier']} {otc['worst_rate']:.3f}")
"""),
    code("""
display(Image(filename=str(FIG / "fig06_correlation_heatmap.png"), width=700))
display(Image(filename=str(FIG / "fig07_carrier_ontime.png"), width=760))
"""),
    md("""## 5. Cost structure

The primary model regresses log cost on log weight, log distance and mode fixed
effects. The coefficients are elasticities, directly comparable with the
planted values of 0.82 and 1.00."""),
    code("""
cost = build_cost(df)
m = cost["model"]
print(f"rows                 {m['n']:,}")
print(f"weight elasticity    {m['weight_elasticity']:.4f}  CI {m['weight_ci']}")
print(f"distance elasticity  {m['distance_elasticity']:.4f}  CI {m['distance_ci']}")
print(f"R2                   {m['r2']:.4f}")
print(f"pooled weight elast. {cost['pooled']['weight_elasticity']:.4f}")
print(f"air : sea cost/kg    {cost['air_to_sea_ratio']:.2f}x")
"""),
    code("""
display(Image(filename=str(FIG / "fig08_cost_loglog.png"), width=760))
display(Image(filename=str(FIG / "fig12_cost_per_kg_ecdf.png"), width=760))
"""),
    md("""## 6. Outliers and network concentration

Four rules are scored against the planted anomalies. The residual rule wins
because corruption is conditional on weight, distance and mode; a univariate
fence cannot see that. Lane concentration uses a Herfindahl-Hirschman index."""),
    code("""
out = build_outliers(df)
comp = pd.DataFrame(out["recovery"]["comparison"])[["method", "flagged", "recall", "precision"]]
display(comp.round(4))
print(f"planted rows {out['profile']['planted_rows']:,} "
      f"({out['profile']['planted_share']:.3f} of the file)")
lanes = build_lanes(df)
print(f"lanes {lanes['lane_count']}, top 10 {lanes['top10_share_pct']:.1f}%, "
      f"HHI {lanes['hhi']:.3f}, {lanes['lanes_for_80pct']} lanes for 80%")
"""),
    code("""
display(Image(filename=str(FIG / "fig09_outlier_methods.png"), width=700))
display(Image(filename=str(FIG / "fig11_lane_pareto.png"), width=760))
"""),
    md("""## 7. External benchmark and validation

The BTS series is an independent check on the seasonal story. Validation
compares each planted design value with the recovered estimate; ten of ten
pass, and the cost elasticity is the one deliberate near-miss."""),
    code("""
real_ts = ts["real_data"]
print(f"BTS months           {len(real_ts['monthly']['values'])}")
print(f"December index       {real_ts['december_index']:.3f}")
print(f"October index        {real_ts['october_index']:.3f}")
print(f"2020 vs 2019         {real_ts['annual_2020_vs_2019_pct']:.1f}%")
val = json.loads((RESULTS / "validation.json").read_text())
display(pd.DataFrame(val["rows"])[["effect", "planted", "recovered", "match"]])
"""),
    code("""
display(Image(filename=str(FIG / "fig15_bts_real_data.png"), width=760))
"""),
    md("""## 8. What the notebook shows

- Service is mode-specific: medians run from 3 days by air to 24 by sea, while
  on-time rates are highest for rail and lowest for air and road.
- Volume is strongly seasonal and flat between years; February 2025 is the one
  calendar shock that survives every cut.
- Two carriers sit far below a tight ten-carrier cluster, so the actionable
  comparison is two contracts, not a league table.
- Cost is a power law: a weight elasticity near 0.80 and a distance elasticity
  near 1.00 with mode fixed effects, which is also what the simulation planted.
- The residual outlier rule is fit for flagging, not for automatic deletion."""),
]


def build_notebook() -> Path:
    nb = nbformat.v4.new_notebook(cells=CELLS, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python"},
    })
    client = NotebookClient(nb, timeout=300, kernel_name="python3",
                            resources={"metadata": {"path": str(OUT.parent)}})
    client.execute()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, OUT)
    return OUT


if __name__ == "__main__":
    print(f"wrote {build_notebook().relative_to(ROOT)}")
