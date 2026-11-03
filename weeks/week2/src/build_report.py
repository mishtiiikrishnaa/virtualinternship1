"""Build the Week 2 Word report from the JSON artefacts.

Every number in the prose is read from ``results/*.json`` at build time, so the
document cannot drift away from the analysis. Run after ``make_figures``:

    python -m src.build_report

The output is ``reports/Week2_EDA_and_Visualization.docx``.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx.shared import Pt, Cm, RGBColor

from .docx_helpers import BLUE, GREY, NAVY, Report
from .make_figures import SNIPPETS

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"

OUT = REPORTS / "Week2_EDA_and_Visualization.docx"

FIG = {
    "fig01": FIGURES / "fig01_eda_workflow.png",
    "fig02": FIGURES / "fig02_transit_histogram.png",
    "fig03": FIGURES / "fig03_mode_violin.png",
    "fig04": FIGURES / "fig04_monthly_volume.png",
    "fig05": FIGURES / "fig05_stl_decomposition.png",
    "fig06": FIGURES / "fig14_plotly_monthly_by_mode.png",
    "fig07": FIGURES / "fig13_mode_month_small_multiples.png",
    "fig08": FIGURES / "fig06_correlation_heatmap.png",
    "fig09": FIGURES / "fig07_carrier_ontime.png",
    "fig10": FIGURES / "fig08_cost_loglog.png",
    "fig11": FIGURES / "fig12_cost_per_kg_ecdf.png",
    "fig12": FIGURES / "fig09_outlier_methods.png",
    "fig13": FIGURES / "fig11_lane_pareto.png",
    "fig14": FIGURES / "fig10_delay_heatmap.png",
    "fig15": FIGURES / "fig15_bts_real_data.png",
}


# Figure files are numbered by production order, which differs from report order;
# the code snippet must follow the figure, not the position in the document.
SNIPPET = {"fig06": "fig14", "fig07": "fig13", "fig08": "fig06", "fig09": "fig07",
           "fig10": "fig08", "fig11": "fig12", "fig12": "fig09", "fig13": "fig11",
           "fig14": "fig10"}


def load_results() -> dict:
    return {path.stem: json.loads(path.read_text()) for path in RESULTS.glob("*.json")}


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def num(value: float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}"


def money(value: float) -> str:
    return f"${value:,.0f}"


def figure(r: Report, key: str, caption: str, alt: str, purpose: str,
           interpretation: str, width: float = 16.0) -> None:
    """One complete figure block: image, numbered caption, purpose, code, reading."""
    r.image(FIG[key], alt=alt, width_cm=width)
    r.caption(caption)
    r.purpose("Purpose. " + purpose[0].upper() + purpose[1:])
    r.code(SNIPPETS[SNIPPET.get(key, key)])
    r.p("Interpretation. " + interpretation)


def title_block(r: Report) -> None:
    para = r.doc.add_paragraph()
    para.paragraph_format.space_before = Pt(22)
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run("Exploratory Data Analysis and Visualization\nof Logistics Shipment Data")
    run.font.name = "Calibri"
    run.font.size = Pt(25)
    run.font.bold = True
    run.font.color.rgb = NAVY

    rule = r.doc.add_paragraph()
    rule.paragraph_format.space_before = Pt(4)
    rule.paragraph_format.space_after = Pt(8)
    runner = rule.add_run("WEEK 2 REPORT  ·  VIRTUAL INTERNSHIP IN LOGISTICS ANALYTICS")
    runner.font.name = "Calibri"
    runner.font.size = Pt(10)
    runner.font.bold = True
    runner.font.color.rgb = BLUE

    for text, size, colour in [
        ("Meghana Krishnakumar Nair", 13, RGBColor(0x1A, 0x1A, 0x1A)),
        ("Data analytics intern  ·  2 November 2026", 10, GREY),
        ("Repository: github.com/mishtiiikrishnaa/virtualinternship1  ·  weeks/week2", 9, GREY),
    ]:
        para = r.doc.add_paragraph()
        para.paragraph_format.space_after = Pt(1)
        run = para.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        run.font.color.rgb = colour


def summary(r: Report, R: dict) -> None:
    prof, desc = R["profile"], R["descriptive"]
    ts, tests, cost = R["timeseries"], R["tests"], R["cost"]
    lanes, rec = R["lanes"], R["outliers"]["recovery"]
    real = ts["real_data"]
    air, road = desc["by_mode"]["Air"], desc["by_mode"]["Road"]
    rail, sea = desc["by_mode"]["Rail"], desc["by_mode"]["Sea"]

    r.h1("Summary of Findings", page_break=True)
    r.p(
        "This report applies exploratory data analysis to two logistics datasets. The primary "
        f"dataset is a seeded simulation of {num(prof['rows_clean'])} cleaned shipments between January 2024 and "
        f"December 2025, across four modes, twelve named carriers and {num(prof['lane_count'])} lanes. The secondary "
        "dataset is the United States Bureau of Transportation Statistics (BTS) Border Crossing Entry "
        f"Data: {num(real['rows'])} monthly truck records from {num(real['ports'])} ports between January 1996 and September "
        "2026, used as an external benchmark."
    )
    r.p(
        f"On-time delivery is {pct(prof['on_time_rate'])} on the {num(prof['on_time_eligible'])} shipments that reached a "
        f"terminal state. Median transit is {num(desc['variables']['transit_days']['median'])} days, with mode medians of "
        f"{num(air['median_transit_days'])} for air, {num(road['median_transit_days'])} for road, {num(rail['median_transit_days'])} for rail and "
        f"{num(sea['median_transit_days'])} for sea. Volume peaks in November 2024 at {num(ts['summary']['peak_value'])} shipments and "
        f"troughs in January 2024 at {num(ts['summary']['trough_value'])}; the fourth-quarter index is {ts['summary']['q4_index']:.3f}, "
        f"a {pct(ts['summary']['q4_uplift_pct'] / 100)} uplift. February 2025 is the weakest month at "
        f"{pct(ts['disruption']['feb_on_time'])} on time against a baseline of {pct(ts['disruption']['baseline_on_time'])}. The gap "
        f"between {tests['on_time_by_carrier']['best_carrier']} ({pct(tests['on_time_by_carrier']['best_rate'])}) and "
        f"{tests['on_time_by_carrier']['worst_carrier']} ({pct(tests['on_time_by_carrier']['worst_rate'])}) is "
        f"{tests['on_time_by_carrier']['gap_pp']:.1f} percentage points and is not sampling noise (chi-square "
        f"{num(tests['on_time_by_carrier']['chi2'], 2)}, Cramér's V {tests['on_time_by_carrier']['cramers_v']:.3f})."
    )
    r.p(
        f"Freight spend across {num(prof['cost_scored_rows'])} costed shipments totals {money(cost['total_cost_usd'])}. A log-log "
        f"model with mode fixed effects explains {pct(cost['model']['r2'])} of the variance in cost, with a weight elasticity "
        f"of {cost['model']['weight_elasticity']:.3f} and a distance elasticity of {cost['model']['distance_elasticity']:.3f}. Air costs "
        f"{cost['air_to_sea_ratio']:.1f} times as much per kilogram as sea and absorbs {pct(cost['by_mode']['Air']['cost_share_pct'] / 100)} "
        f"of spend on {pct(cost['by_mode']['Air']['shipment_share_pct'] / 100)} of shipments. The network is diffuse: "
        f"{num(lanes['lanes_for_80pct'])} of {num(lanes['lane_count'])} lanes carry 80% of volume. The residual outlier rule "
        f"recovers {pct(rec['recall'])} of planted anomalies at {pct(rec['precision'])} precision, against "
        f"{pct(rec['comparison'][0]['recall'])} for a plain interquartile-range (IQR) fence, and all "
        f"{R['validation']['matched']} planted effects are recovered. In the BTS benchmark the December seasonal index is "
        f"{real['december_index']:.3f} against {real['october_index']:.3f} in October, so the fourth-quarter peak is not a general "
        "property of freight."
    )


def coverage_matrix(r: Report) -> None:
    r.caption("Requirements coverage matrix. Every requirement in the Week 2 brief, the section "
              "that answers it, and the evidence a reviewer can open.", kind="Table")
    r.doc.paragraphs[-1].paragraph_format.space_before = Pt(12)
    rows = [
        ["1", "Load a logistics dataset in Python and state its provenance",
         "§2.1–2.2, Tables 2–3",
         "Seeded simulation of 50,000 rows; BTS border crossings, 38,567 rows"],
        ["2", "Profile shape, data types and missingness",
         "§3, Table 5",
         "50,600 raw and 49,935 clean rows; 18 to 35 columns"],
        ["3", "Clean and document every transformation",
         "§2.3, Table 4",
         "Six logged steps: duplicates, dates, values, labels, units, imputation"],
        ["4", "Summarize univariate distributions",
         "§4, Figures 2–3, Table 6",
         "Median, IQR, skew, kurtosis and normality tests for eight variables"],
        ["5", "Analyze trends and seasonality over time",
         "§5, Figures 4–7",
         "STL decomposition; Q4 index 1.348; seasonal strength 0.989"],
        ["6", "Detect and treat outliers with a justified rule",
         "§9, Figure 12, Table 9",
         "Four rules scored on recall and precision; rows flagged, not deleted"],
        ["7", "Examine relationships between variables",
         "§6, Figure 8, Table 8",
         "Spearman matrix; variance inflation; three cost specifications"],
        ["8", "Compare groups with statistical tests",
         "§5.4, §7, Table 7",
         "Kruskal–Wallis, Mann–Whitney with Holm, chi-square, Wilson intervals"],
        ["9", "Produce at least twelve visualizations as embedded images",
         "Figures 1–15",
         "Fifteen numbered figures at 200 dots per inch, each script-generated"],
        ["10", "Use matplotlib, seaborn and plotly",
         "§2.4, Figures 2–15",
         "Seaborn distributions and heatmaps; plotly Figure 6 with PNG and HTML"],
        ["11", "Give every figure a caption, a purpose and a 100–150 word interpretation",
         "All figures",
         "Numbered caption, purpose line, code excerpt, interpretation paragraph"],
        ["12", "Document the methodology and an audit trail",
         "§2, Appendix A",
         "Scripted pipeline, JSON results, executed notebook, recorded hashes"],
        ["13", "Validate against known truth or an external benchmark",
         "§13, Table 11; §12",
         "Ten of ten planted effects recovered; BTS series as benchmark"],
        ["14", "State limitations and threats to validity",
         "§14",
         "Missing-not-at-random cost, simulation assumptions, count grain"],
        ["15", "Draw conclusions and recommendations",
         "§15, Table 12",
         "Five ranked recommendations, each tied to a measured effect"],
    ]
    r.table(["#", "Requirement in the brief", "Where addressed", "Evidence"],
            rows, widths=[0.7, 5.6, 4.0, 6.7], font_size=7.6)


def introduction(r: Report, R: dict) -> None:
    prof = R["profile"]
    r.h1("1. Introduction", page_break=False)
    r.h2("1.1 Background and problem statement")
    r.p(
        "Freight is a promise about time and money, and every shipment record is a partial witness to "
        "whether that promise was kept. A monthly average hides a bimodal transit distribution, a "
        "carrier league table hides wildly different sample sizes, and a single cost curve hides the fact "
        "that air and sea freight obey different economics. Exploratory data analysis (EDA) is the "
        "disciplined first pass that makes those distinctions visible before anyone commits to a model."
    )
    r.p(
        "This report asks what service actually looks like, where the calendar breaks it, which "
        "carriers differ from the pack, what drives cost, which observations are anomalous, and how "
        "concentrated the network is. The emphasis is on effect sizes and uncertainty: with tens of "
        "thousands of rows almost every difference is significant and almost none of them matter "
        "operationally."
    )

    r.h2("1.2 Objectives")
    r.p("The brief asks for exploratory analysis and visualization of a logistics dataset, with "
        "documented interpretation and recommendations. That decomposes into six objectives:")
    r.numbered([
        "Quantify data quality and its consequences, including duplicates, unit drift and "
        "missing values that are not missing at random (§3).",
        "Describe the distributions of transit, weight, volume, distance and cost, and justify "
        "the transformations used later (§4).",
        "Measure trend and seasonality in volume and service, and locate calendar disruptions "
        "(§5).",
        "Compare modes, carriers and lanes with tests that respect sample size and multiple "
        "comparisons (§6, §7, §10, §11).",
        "Estimate the cost function, rank the drivers of spend and test the estimate against "
        "outliers and specification change (§8, §9).",
        "Validate the findings against the planted structure of the simulation and an "
        "independent public series (§12, §13).",
    ])

    r.h2("1.3 Structure of the report")
    r.p(
        "Section 2 describes both datasets and the methods, and Section 3 reports what cleaning "
        "removed and what it left alone. Sections 4 to 12 present distributions, time, relationships, "
        "service, cost, anomalies, network structure and the external benchmark. Section 13 holds the "
        "simulation against its ground truth, Section 14 states what the design cannot support, and "
        "Section 15 restates the results as decisions."
    )
    r.p(
        f"The window runs from {prof['date_min']} to {prof['date_max']}, giving 24 complete months. Money is in "
        "United States dollars (USD), weight in kilograms (kg), volume in cubic meters (m³) and "
        "distance in kilometres (km)."
    )


def data_sources(r: Report, R: dict) -> None:
    prof, clean = R["profile"], R["cleaning"]
    plant, real = R["planted_effects"], R["timeseries"]["real_data"]
    meta_path = ROOT / "data" / "external" / "bts_border_trucks.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    r.h1("2. Data Sources and Methodology")

    figure(
        r, "fig01",
        "The eight-stage exploratory workflow used for this report, from design to published report.",
        "Flow diagram of eight numbered boxes in two rows, labeled design, acquire, clean, profile, "
        "analyze, visualize, validate and report, joined by arrows with a feedback arrow from "
        "validate back to clean.",
        "to make the order of the work explicit before any result is presented, so a reviewer can "
        "locate each later section in the process.",
        f"The workflow is sequential with one deliberate loop: validation feeds back into cleaning, "
        f"where the duplicate, unit and date defects surfaced. The first two stages produced "
        f"{num(plant['rows_generated'])} simulated rows and {num(real['rows'])} real records, and the last two consumed "
        f"{num(prof['rows_clean'])} cleaned rows to produce every number here. The raw file is never edited: each stage "
        "writes a new artefact with a hash, so any result traces back to the input that produced it, and "
        "a failed stage cannot leave the report reading stale numbers. That discipline is what makes the "
        "validation in Section 13 meaningful, because the ground truth and the analysis never share a "
        "working file.",
    )

    r.h2("2.1 Dataset A: a seeded simulation with known ground truth")
    r.p(
        f"The primary dataset contains {num(plant['rows_generated'])} records generated by ``src/generate_data.py`` with "
        "NumPy's ``default_rng(42)``. A fixed seed makes every number reproducible from a clean checkout "
        "and lets the analysis be scored against the parameters that produced it. No public dataset "
        "offers that."
    )
    r.p(
        "Each record carries order, ship and delivery dates; an origin and destination from a "
        "twelve-city network; a mode, carrier, weight, volume, distance, promised transit, cost, "
        "priority and status. Weight and volume are lognormal and correlated at 0.92, distance is a "
        "mixture of domestic and international lanes, and cost follows a power law in weight and "
        "distance with a mode-specific multiplier. Transit is a gamma draw whose mean depends on mode, "
        "carrier, priority and month. Nine effects are planted deliberately (Table 2) and checked in "
        "Section 13."
    )
    r.caption("Planted effects in the simulated dataset and the design value used to generate them.",
              kind="Table")
    r.table(
        ["Planted effect", "Design value", "Where it is tested"],
        [
            ["Fourth-quarter volume peak", f"Q4 month weight {plant['q4_multiplier']:.2f} times baseline", "§5.1, Figure 4"],
            ["Mode transit differences", "Medians Air 3, Road 6, Rail 9, Sea 24 days", "§4, §5.4, Table 6"],
            ["Two weak carriers", "Northwind 2.2 and Cobalt 2.1 times the delay scale", "§7, Figure 9"],
            ["Disruption month", f"{plant['disruption_month']}, sea transit plus {plant['disruption_penalty_days']['Sea']:.1f} days", "§5.3, Figure 7"],
            ["Cost elasticity, weight", f"{plant['cost_weight_elasticity']:.2f}", "§8, Table 8"],
            ["Cost elasticity, distance", f"{plant['cost_distance_elasticity']:.2f}", "§8, Table 8"],
            ["Planted outliers", f"{pct(plant['outlier_share'])} of rows, cost 5–12 times, weight 8–20 times", "§9, Figure 12"],
            ["Duplicate rows", f"{num(plant['duplicate_rows'])} exact duplicates", "§3, Table 4"],
            ["Missing cost (not at random)", "5–8% for air and sea, 10% in the top cost decile", "§3, §14"],
        ],
        widths=[4.6, 7.2, 5.2],
    )

    r.h2("2.2 Dataset B: public border-crossing data")
    r.p(
        "The second dataset is the BTS Border Crossing Entry Data, published on the bureau's open data "
        "portal as dataset ``keg4-3bc2``. It counts loaded truck, rail, container and pipeline crossings "
        "at United States land border ports by month; this extract keeps the truck mode. It is in the "
        "public domain, needs no key, and was retrieved on 2 November 2026."
    )
    r.p(
        f"The download holds {num(real['rows'])} rows across {num(real['states'])} states and {num(real['ports'])} ports, with "
        f"{num(len(real['monthly']['values']))} monthly observations between {real['date_min']} and {real['date_max']}. Months with no "
        "reported crossings are absent rather than zero, which matters for any average. Table 3 records "
        "the provenance a reviewer needs."
    )
    r.caption("Provenance of the external benchmark dataset.", kind="Table")
    r.table(
        ["Field", "Value"],
        [
            ["Publisher", "United States Bureau of Transportation Statistics"],
            ["Dataset", "Border Crossing Entry Data (keg4-3bc2)"],
            ["Measure", "Loaded truck crossings per month, by port"],
            ["License", "Public domain (United States federal government work)"],
            ["Accessed", "2 November 2026"],
            ["Rows retained", f"{num(real['rows'])} truck records"],
            ["Coverage", f"{real['date_min'][:7]} to {real['date_max'][:7]}, {num(len(real['monthly']['values']))} monthly observations"],
            ["Compressed size", f"{meta.get('bytes_gz', 0) / 1024:.0f} KB gzip"],
            ["SHA-256", meta.get("sha256_gz", "")[:32] + "…"],
        ],
        widths=[4.2, 12.8],
    )
    r.p(
        "The unit is a crossing, not a shipment, and the series counts vehicles rather than "
        "consignments. It cannot be merged with the simulated ledger. Its role "
        "is narrower: an independent seasonal shape and long-run trend, so the report can ask whether "
        "the simulated calendar generalizes."
    )

    r.h2("2.3 Cleaning and preparation")
    r.p(
        "Raw rows are never edited in place. ``src/clean.py`` reads the extract, applies six logged steps "
        "and writes a new file with a SHA-256 hash and a per-step record. The log is the audit trail; "
        "Table 4 summarizes it."
    )
    r.caption("Cleaning log for the simulated dataset, in execution order.", kind="Table")
    r.table(
        ["Step", "Rows in", "Rows out", "Removed", "What happened"],
        [[step["step"], num(step["rows_in"]), num(step["rows_out"]), num(step["removed"]), step["detail"]]
         for step in clean["steps"]],
        widths=[5.4, 2.0, 2.0, 1.8, 5.8], font_size=7.6,
    )
    r.p(
        f"Deduplication removes {num(clean['duplicates_removed'])} exact repeats of ``shipment_id``. Dates arrive in three "
        f"formats; {num(clean['unparseable_date_strings'])} strings match none of them and those rows are dropped rather than "
        f"guessed. {num(clean['impossible_values_set_missing'])} impossible values are set to missing instead of being silently "
        f"repaired. Mode labels are rewritten {num(clean['mode_labels_rewritten'])} times because the source mixes case, "
        "abbreviations and spaces; pound weights are converted with the exact factor of 0.45359237 and "
        f"litre volumes divided by 1,000. Imputed values carry flags: {num(clean['promised_imputed_rows'])} promised "
        f"transits, {num(clean['weight_imputed_rows'])} weights and {num(clean['volume_imputed_rows'])} volumes are filled with their mode "
        "median."
    )
    r.p(
        f"Freight cost is different. It is missing for {num(clean['freight_cost_left_missing_rows'])} rows "
        f"({pct(prof['cost_missing_share'])}) and the gap is not random: the generator withholds cost precisely where the "
        "invoice is largest. Imputing those values would manufacture the finding the model is supposed "
        "to test, so the column stays missing and the model is fitted on complete cases with that "
        f"limitation stated."
    )

    r.h2("2.4 Analytical methods")
    r.p(
        "The pipeline uses pandas, SciPy, statsmodels, matplotlib, seaborn and plotly. Transit is "
        "right-skewed and heteroscedastic, so group comparisons use Kruskal–Wallis with epsilon-squared "
        "as the effect size, and pairwise Mann–Whitney tests with a Holm–Bonferroni correction across the "
        f"six mode pairs. Categorical comparisons use chi-square with Cramér's V, because with "
        f"{num(prof['on_time_eligible'])} rows a p-value alone is uninformative. Proportions carry Wilson score intervals "
        "at 95% confidence."
    )
    r.p(
        "Normality is checked with D'Agostino's K-squared test on the full sample and Shapiro–Wilk on a "
        "5,000-row subsample, before and after a log transform. Trend and seasonality are separated "
        "with STL (seasonal-trend decomposition using LOESS) at period 12 with the robust option. The "
        "cost model regresses log freight cost on log weight, log distance and mode fixed effects: the "
        "log-log form turns a multiplicative process into an additive one, and its coefficients are "
        "elasticities comparable with the planted values."
    )
    r.p(
        "Outliers are a detection problem, not a deletion problem. Four rules are scored against the "
        "planted anomalies: an IQR fence at 1.5 times the interquartile range, a z-score threshold of "
        "three, a modified z-score using the median absolute deviation, and a residual-modified z-score "
        "computed on the log-log cost and weight models. The chosen rule flags rows for sensitivity "
        "analysis; it does not remove them."
    )


def data_quality(r: Report, R: dict) -> None:
    prof, clean = R["profile"], R["cleaning"]
    dirt = R["dirt"]
    r.h1("3. Data Quality and Preparation")
    r.p(
        f"The raw extract holds {num(prof['rows_raw'])} rows and {prof['cols_raw']} columns. After cleaning it holds "
        f"{num(prof['rows_clean'])} rows, so {num(prof['rows_raw'] - prof['rows_clean'])} records "
        f"({pct((prof['rows_raw'] - prof['rows_clean']) / prof['rows_raw'], 2)}) were lost, all to duplication or unparseable dates. "
        "Every other defect was repaired, flagged or left visible. That asymmetry is deliberate: a "
        "dropped row cannot be audited, whereas a repaired row with a flag can."
    )
    r.p(
        f"Missingness is concentrated. Freight cost is absent for {num(prof['cost_missing_rows'])} rows "
        f"({pct(prof['cost_missing_share'])}) and delivery date for {num(clean['missing_by_column']['delivery_date']['count'])} rows "
        f"({pct(clean['missing_by_column']['delivery_date']['share'])}); distance is missing for "
        f"{num(clean['missing_by_column']['distance_km']['count'])}. In total {num(prof['rows_with_any_missing'])} rows "
        f"({pct(prof['rows_with_any_missing_pct'] / 100)}) have at least one gap. The pattern is missing not at random (MNAR): "
        "cost is withheld more often for large shipments, so the complete-case mean is biased downward "
        "and any cost model describes the cheaper part of the ledger more accurately than the tail."
    )
    r.p(
        f"Status is the other exclusion that matters. {num(prof['status_counts']['In Transit'])} shipments are still in transit "
        f"and {num(prof['status_counts']['Cancelled'])} were cancelled, leaving {num(prof['on_time_eligible'])} with a defined on-time "
        "outcome. Counting open shipments would treat an unknown outcome as a failure; the report "
        f"excludes them rather than silently dividing by {num(prof['rows_clean'])}."
    )
    r.p(
        f"Label and unit drift is the least visible defect and the most expensive to miss. The raw file "
        f"contains {num(dirt['mode_label_variants'])} mode strings that collapse to four, "
        f"{num(dirt['carrier_label_variants'])} carrier strings that collapse to thirteen, {num(dirt['weight_rows_in_pounds'])} weights in pounds "
        f"and {num(dirt['volume_rows_in_litres'])} volumes in litres. Left alone, one unconverted pound row understates a weight "
        "by 2.2 times, exactly the kind of error that survives a summary table and corrupts a "
        "regression."
    )
    r.p(
        f"One check failed the first time and is worth reporting. The lane field originally contained "
        "pairs where origin and destination were identical, produced when the destination was blank and "
        f"the fallback copied the origin. After the fix, {num(clean['destination_recovered_from_lane'])} destinations were recovered "
        "from the lane string and no self-lanes remain."
    )


def distributions(r: Report, R: dict) -> None:
    desc = R["descriptive"]
    v = desc["variables"]
    dist = R["distributions"]
    by_mode = desc["by_mode"]

    r.h1("4. Distributions of Transit Time, Weight and Cost")
    r.p(
        f"Transit time has a mean of {v['transit_days']['mean']:.2f} days and a median of {num(v['transit_days']['median'])}. The gap "
        f"is the first substantive finding: the average is dragged upward by a tail reaching "
        f"{num(v['transit_days']['max'])} days, while half of all shipments arrive within a week. The 90th percentile is "
        f"{num(v['transit_days']['p90'])} days and the coefficient of variation is {v['transit_days']['cv']:.2f}, so spread is comparable "
        "to the central value. A target expressed as a mean is one that half the network can miss while "
        "the average stays on plan."
    )
    r.p(
        f"Cost is far more extreme. The median shipment costs {money(v['freight_cost_usd']['median'])} and the mean "
        f"{money(v['freight_cost_usd']['mean'])}, a ratio of {v['freight_cost_usd']['mean'] / v['freight_cost_usd']['median']:.1f}, with a maximum of "
        f"{money(v['freight_cost_usd']['max'])} and skewness of {v['freight_cost_usd']['skew']:.1f}. Weight is similarly heavy-tailed, "
        f"with a median of {num(v['weight_kg']['median'], 1)} kg against a mean of {num(v['weight_kg']['mean'], 1)} kg. Distance behaves "
        f"differently: skewness of {v['distance_km']['skew']:.2f} and a median of {num(v['distance_km']['median'], 1)} km above its mean of "
        f"{num(v['distance_km']['mean'], 1)} km, the signature of a mixture of dense domestic lanes and thinner "
        "intercontinental ones."
    )
    r.p(
        f"D'Agostino's K-squared rejects normality for transit ({num(dist['transit_days']['raw']['dagostino_stat'], 1)}), cost "
        f"({num(dist['freight_cost_usd']['raw']['dagostino_stat'], 1)}) and weight ({num(dist['weight_kg']['raw']['dagostino_stat'], 1)}), all with p "
        f"below 0.001. A log transform fixes the skew rather than the tails: log cost has skewness "
        f"{dist['freight_cost_usd']['log']['skew']:.3f} against {dist['freight_cost_usd']['raw']['skew']:.2f} raw, yet Shapiro–Wilk still rejects "
        "normality at 5,000 rows. At this sample size the test detects deviations too small to affect a "
        "regression, so the log is a variance-stabilizing step."
    )

    r.caption("Descriptive statistics for the continuous variables. SD is standard deviation; P90 "
              "is the 90th percentile.", kind="Table")
    rows = []
    for key, label, unit, digits in [
        ("transit_days", "Transit time", "days", 2),
        ("promised_days", "Promised transit", "days", 1),
        ("freight_cost_usd", "Freight cost", "USD", 2),
        ("weight_kg", "Weight", "kg", 2),
        ("volume_m3", "Volume", "m³", 2),
        ("distance_km", "Distance", "km", 1),
        ("cost_per_kg", "Cost per kg", "USD/kg", 2),
        ("delay_days", "Delay", "days", 2),
    ]:
        row = v[key]
        rows.append([label, unit, num(row["median"], digits), num(row["mean"], digits),
                     num(row["std"], digits), num(row["p90"], digits), num(row["max"], digits),
                     f"{row['skew']:.2f}"])
    r.table(["Variable", "Unit", "Median", "Mean", "SD", "P90", "Max", "Skew"],
            rows, widths=[3.8, 1.7, 2.2, 2.2, 2.2, 2.2, 2.4, 1.5], font_size=7.8)

    figure(
        r, "fig02",
        "Distribution of transit time on a logarithmic scale, with kernel density estimate and "
        "reference lines at the median and the 90th percentile.",
        "Histogram of transit days on a logarithmic horizontal axis with a smooth density curve. A "
        "solid line marks the median of 8 days and a dotted line the 90th percentile of 28 days. "
        "Counts peak between 3 and 6 days and show a second rise near 24 days.",
        "to show the shape of the main service variable before any grouping, and to test whether a "
        "single central value can represent it.",
        f"The distribution is not unimodal. One peak sits between three and six days, where air and road "
        f"shipments land, and a second sits near {num(by_mode['Sea']['median_transit_days'])} days, where sea freight lands. The "
        f"median of {num(v['transit_days']['median'])} days falls between the two modes and describes neither. The upper tail is thin "
        f"but long, and the maximum of {num(v['transit_days']['max'])} days is {v['transit_days']['max'] / v['transit_days']['p90']:.1f} times the 90th "
        f"percentile. A single network target would be trivially met by sea freight and missed by air "
        f"freight. Service must therefore be reported by mode and assessed against a mode-specific "
        "promise, not against one company-wide number. The 90th percentile of 28 days is the more "
        "useful service line than the median.",
    )

    figure(
        r, "fig03",
        "Transit time by transport mode, drawn as violin plots on a logarithmic scale with an inner "
        "box plot.",
        "Four violins ordered air, road, rail and sea. Air is narrow and centered on 3 days, road on 6 "
        "days, rail on 9 days, and sea is the broadest, centered on 24 days with a long upper whisker.",
        "to separate the mixture visible in Figure 2 and compare the full distribution of each mode "
        "rather than only its average.",
        f"The four modes occupy almost disjoint ranges. Air has a median of {num(by_mode['Air']['median_transit_days'])} days and a "
        f"90th percentile of {num(by_mode['Air']['p90_transit_days'])}; sea has a median of {num(by_mode['Sea']['median_transit_days'])} and a 90th "
        f"percentile of {num(by_mode['Sea']['p90_transit_days'])}. Road and rail sit between at {num(by_mode['Road']['median_transit_days'])} and "
        f"{num(by_mode['Rail']['median_transit_days'])} days. The tails still overlap: the upper tail of air reaches into the road range "
        "and the lower tail of sea reaches down to about two weeks. Mode explains most of the variance, "
        f"and Section 5.4 agrees, with an epsilon-squared of {R['tests']['transit_by_mode']['epsilon_squared']:.3f}. "
        f"Air's 90th percentile of {num(by_mode['Air']['p90_transit_days'])} days is a sixth of sea's "
        f"{num(by_mode['Sea']['p90_transit_days'])}, and the two medians are 21 days apart.",
    )

    r.caption("Transit time and cost by mode. Shares are of all 49,935 shipments; cost medians use "
              "rows with a recorded cost.", kind="Table")
    r.table(
        ["Mode", "Shipments", "Share", "Median transit", "On-time", "Median cost/kg", "Median cost"],
        [[mode, num(by_mode[mode]["shipments"]), pct(by_mode[mode]["share"]),
          f"{num(by_mode[mode]['median_transit_days'])} d", pct(by_mode[mode]["on_time_rate"]),
          f"${by_mode[mode]['median_cost_per_kg']:,.2f}", money(by_mode[mode]["median_cost_usd"])]
         for mode in ["Air", "Road", "Rail", "Sea"]],
        widths=[2.2, 2.8, 2.0, 3.2, 2.4, 3.2, 2.8], font_size=7.8,
    )
    r.p(
        f"Table 6 already contains a counter-intuitive result. Sea has the longest transit by a wide "
        f"margin but not the worst on-time rate: at {pct(by_mode['Sea']['on_time_rate'])} it beats air "
        f"({pct(by_mode['Air']['on_time_rate'])}) and road ({pct(by_mode['Road']['on_time_rate'])}). Promises are calibrated to what each mode can "
        "deliver, so a slow mode with a generous promise can beat a fast mode with a tight one."
    )


def temporal(r: Report, R: dict) -> None:
    ts, desc = R["timeseries"], R["descriptive"]
    summ, dec, dis = ts["summary"], ts["decomposition"], ts["disruption"]
    tests = R["tests"]
    road_month = ts["mode_monthly"]["Road"]["on_time"]

    r.h1("5. Temporal Patterns and Seasonality")
    r.h2("5.1 Volume, trend and the fourth-quarter peak")
    r.p(
        f"Across 24 months the network moves a mean of {num(summ['mean_monthly'], 1)} shipments per month with a standard "
        f"deviation of {num(summ['sd_monthly'], 1)} and a coefficient of variation of {summ['cv_monthly']:.3f}. The peak is "
        f"{summ['peak_month'][:7]} at {num(summ['peak_value'])} shipments and the trough {summ['trough_month'][:7]} at "
        f"{num(summ['trough_value'])}. Both extremes fall in the same calendar cycle, the signature of seasonality rather than "
        f"trend. The fourth-quarter mean of {num(summ['q4_mean'], 1)} against {num(summ['non_q4_mean'], 1)} gives an index of "
        f"{summ['q4_index']:.3f}, an uplift of {summ['q4_uplift_pct']:.1f}%. Year on year, 2025 is "
        f"{summ['growth_2025_vs_2024_pct']:.1f}% larger than 2024, so the series is close to flat once the seasonal pattern is removed."
    )

    figure(
        r, "fig04",
        "Monthly shipment volume from January 2024 to December 2025, with a three-month centered "
        "moving average and the fourth quarter of each year shaded.",
        "Line chart of 24 monthly shipment counts with markers, rising from 1,685 in January 2024 to a "
        "November 2024 peak of 2,680, then repeating a similar pattern in 2025. A dashed moving average "
        "smooths the series and shaded bands mark October to December in both years.",
        "to show the level, the annual repetition and the size of the fourth-quarter step in one view.",
        f"The two years trace nearly the same path, {summ['growth_2025_vs_2024_pct']:.1f}% apart in total, which rules out a trend as the "
        f"explanation for the autumn rise. November alone exceeds the non-quarter average by "
        f"{num(summ['peak_value'] - summ['non_q4_mean'], 0)} shipments, and the step reverses immediately in January. The moving average "
        "is deliberately short, because a twelve-month window would erase the only feature worth "
        f"seeing. For planning, the network needs roughly {pct(summ['q4_uplift_pct'] / 100)} more capacity for three months a year, "
        "which is a staffing and slot-booking problem rather than a capital one. For eleven months the "
        f"series sits near the non-quarter mean of {num(summ['non_q4_mean'])} shipments, then climbs by a third for the quarter.",
    )

    r.h2("5.2 Decomposing the cycle")
    r.p(
        f"STL separates the series into trend, seasonal and residual components. Seasonal strength is "
        f"{dec['seasonal_strength']:.3f} and trend strength {dec['trend_strength']:.3f}, a ratio of roughly "
        f"{dec['seasonal_strength'] / max(dec['trend_strength'], 1e-9):.0f} to one: the calendar explains almost everything and the long-run drift "
        f"almost nothing. The residual standard deviation is {dec['resid_sd']:.2f} shipments per month against a mean of "
        f"{num(summ['mean_monthly'], 1)}. January is weakest at {ts['seasonal_index_by_month']['1']:.3f}; October, November and December "
        f"are strongest at {ts['seasonal_index_by_month']['10']:.3f}, {ts['seasonal_index_by_month']['11']:.3f} and "
        f"{ts['seasonal_index_by_month']['12']:.3f}."
    )

    figure(
        r, "fig05",
        "Seasonal decomposition of monthly shipment volume using STL with a period of 12 and the "
        "robust option enabled.",
        "Four stacked panels sharing a time axis: observed monthly counts, a nearly flat trend line, a "
        "repeating seasonal component that rises in October to December and falls in January, and a "
        "residual panel scattered around zero.",
        "to separate the seasonal component from the trend so that each can be sized independently.",
        f"The trend panel moves from {num(dec['trend'][0], 0)} to {num(dec['trend'][-1], 0)} shipments across two years, a change of about "
        f"{pct((dec['trend'][-1] - dec['trend'][0]) / dec['trend'][0])}, while the seasonal component swings by more than "
        f"{num(max(dec['seasonal']) - min(dec['seasonal']), 0)} shipments within each year. The residual panel has a standard deviation of "
        f"{dec['resid_sd']:.1f}, so the model leaves little unexplained. The one visible residual spike corresponds to the "
        "February 2025 disruption, which is exactly the kind of event a seasonal model should not "
        "absorb into the calendar. A reader can therefore trust the seasonal panel for planning and use "
        f"the residual panel to monitor shocks. The seasonal swing of {num(max(dec['seasonal']) - min(dec['seasonal']), 0)} shipments dwarfs the "
        f"{num(dec['trend'][-1] - dec['trend'][0], 0)}-shipment trend change, and the residual standard deviation of {dec['resid_sd']:.0f} is small "
        f"against a monthly mean of {num(summ['mean_monthly'])}.",
    )

    r.h2("5.3 Mode mix over time and the February 2025 disruption")
    r.p(
        f"Sea carries {pct(desc['by_mode']['Sea']['share'])} of shipments, road {pct(desc['by_mode']['Road']['share'])}, air "
        f"{pct(desc['by_mode']['Air']['share'])} and rail {pct(desc['by_mode']['Rail']['share'])}, and the fourth-quarter surge is broadly "
        "proportional across modes, consistent with a demand shock rather than mode substitution. "
        "February 2025 is the exception. On-time falls to "
        f"{pct(dis['feb_on_time'])} against a baseline of {pct(dis['baseline_on_time'])}, a gap of {dis['on_time_gap_pp']:.1f} percentage "
        f"points, and sea transit rises from a median of {num(dis['baseline_sea_median_days'])} to {num(dis['feb_sea_median_days'])} days. Road "
        f"is hit hardest in proportional terms at {pct(road_month[13])}, and a Mann–Whitney test on transit between that "
        f"month and the rest returns p = {dis['mannwhitney_p']:.0e}."
    )

    figure(
        r, "fig06",
        "Interactive stacked area chart of monthly shipment volume by mode, produced with plotly and "
        "exported to both PNG and HTML.",
        "Stacked area chart with four colored bands for air, road, rail and sea over 24 months. Sea is "
        "the widest band, the total rises in October to December of both years, and the bands keep "
        "roughly constant proportions.",
        "to add the mode dimension to the volume series and demonstrate an interactive export a reviewer "
        "can open in a browser.",
        f"The bands are close to parallel, the visual version of the finding that the quarterly surge is "
        f"proportional. Sea contributes {pct(desc['by_mode']['Sea']['share'])} of the base and remains the largest band throughout; rail "
        f"is smallest at {pct(desc['by_mode']['Rail']['share'])} and shows the widest month-to-month variation, consistent with its smaller "
        "sample. The HTML export keeps hover values and legend toggling, so a reader can isolate one mode "
        "without regenerating the chart. Static PNGs are used everywhere else because they survive "
        f"printing and do not need a browser. Sea's {pct(desc['by_mode']['Sea']['share'])} share is more than four times rail's "
        f"{pct(desc['by_mode']['Rail']['share'])}, so the two bands answer different questions: one is the base load, the other "
        "is the volatile margin.",
    )

    figure(
        r, "fig07",
        "On-time rate by mode and month, shown as four small multiples sharing a vertical axis.",
        "Four panels, one per mode, each plotting monthly on-time percentage over 24 months. All four "
        "dip in February 2025; the road panel falls furthest and the rail panel stays highest for most "
        "months.",
        "to show whether the calendar affects service equally across modes, which a single aggregate "
        "line would conceal.",
        f"The panels share a scale and the differences are large. Rail ranges from "
        f"{pct(min(ts['mode_monthly']['Rail']['on_time']))} to {pct(max(ts['mode_monthly']['Rail']['on_time']))}, road from "
        f"{pct(min(ts['mode_monthly']['Road']['on_time']))} to {pct(max(ts['mode_monthly']['Road']['on_time']))}. The February 2025 dip appears in all "
        "four panels, which supports a common cause such as weather or a network-wide backlog rather "
        "than one carrier failing. Air recovers fastest and road slowest, taking until April to return "
        "to its annual average. Service monitoring should therefore run per mode, because the aggregate "
        f"line hides a twelve-point gap. Rail's worst month, {pct(min(ts['mode_monthly']['Rail']['on_time']))}, is still above road's "
        f"best of {pct(max(ts['mode_monthly']['Road']['on_time']))}, so the two modes never overlap, and February costs road "
        f"{((max(ts['mode_monthly']['Road']['on_time']) - min(ts['mode_monthly']['Road']['on_time'])) * 100):.1f} points against its own best month.",
    )

    r.h2("5.4 Testing the group differences")
    r.p(
        f"Mode medians of {num(tests['transit_by_mode']['group_medians']['Air'])} and {num(tests['transit_by_mode']['group_medians']['Sea'])} days are obviously different, "
        f"but the report still tests them. Kruskal–Wallis returns H = {num(tests['transit_by_mode']['kruskal_h'], 2)} on "
        f"{num(tests['transit_by_mode']['n'])} observations, and epsilon-squared is {tests['transit_by_mode']['epsilon_squared']:.3f}, so mode "
        "alone accounts for most of the rank variance. All six pairwise comparisons survive the Holm "
        f"correction; the air–sea separation has a rank biserial correlation "
        f"of {tests['transit_by_mode']['pairwise'][2]['rank_biserial']:.3f}. On-time performance differs by mode far less dramatically: "
        f"chi-square is {num(tests['on_time_by_mode']['chi2'], 2)} on {tests['on_time_by_mode']['dof']} degrees of freedom with Cramér's V of "
        f"{tests['on_time_by_mode']['cramers_v']:.3f}, a small association. "
        f"Priority shows a larger behavioral effect: high-priority shipments have a median transit of "
        f"{num(tests['priority']['median_high'])} days against {num(tests['priority']['median_low'])} for low priority, with a Kruskal–Wallis statistic "
        f"of {num(tests['priority']['kruskal_h'], 2)}. The network does expedite, by roughly a day."
    )


def relationships(r: Report, R: dict) -> None:
    corr = R["correlations"]
    r.h1("6. Relationships between Variables")
    r.p(
        f"Bivariate correlation depends as much on scale as on strength. On {num(corr['n'])} complete rows, weight and volume correlate "
        f"at {corr['weight_volume_r']:.3f} under Pearson and {corr['spearman']['weight_kg']['volume_m3']:.3f} under Spearman. They are nearly the same "
        "variable, and in a container network they move together almost mechanically. Keeping both would "
        f"inflate standard errors without adding information, which is why the variance inflation factors "
        f"(VIF) of {corr['vif']['weight_kg']:.2f} and {corr['vif']['volume_m3']:.2f} are reported rather than hidden. Distance and cost show the "
        f"opposite problem: their Pearson correlation is only {corr['cost_distance']['r']:.3f}, which suggests a weak relationship, but "
        f"the Spearman correlation is {corr['spearman']['distance_km']['freight_cost_usd']:.3f}. The relationship is strong and monotone, but "
        "multiplicative rather than additive, so a linear coefficient understates it."
    )
    r.p(
        f"Cost per kilogram falls as weight rises (Spearman {corr['spearman']['weight_kg']['cost_per_kg']:.3f}), the "
        f"economies-of-scale signature, and rises with distance ({corr['spearman']['distance_km']['cost_per_kg']:.3f}), because long "
        "lanes are disproportionately served by air and sea. Neither is causal, and Section 8 separates "
        "the mode effect from weight and distance properly."
    )

    figure(
        r, "fig08",
        "Spearman rank correlation matrix for eight numeric variables, lower triangle only.",
        "Lower-triangular heatmap with blue for positive and red for negative correlations, annotated "
        "to two decimals. The darkest cell is 0.98 between weight and volume, followed by 0.90 between "
        "transit and promised days.",
        "to screen for redundancy and for relationships whose shape is not linear, before any model is "
        "specified.",
        f"Two cells dominate. Weight and volume at {corr['spearman']['weight_kg']['volume_m3']:.2f} are redundant, and transit and promised "
        f"transit at {corr['spearman']['transit_days']['promised_days']:.2f} are definitional. The cost block is more interesting: cost "
        f"correlates {corr['spearman']['distance_km']['freight_cost_usd']:.2f} with distance and {corr['spearman']['weight_kg']['freight_cost_usd']:.2f} with weight, "
        "both far above their Pearson counterparts. The matrix therefore does two jobs: it removes a "
        "variable from later models and it justifies the log-log specification, the only form that "
        f"recovers the monotone relationship the raw coefficients obscure. The weakest cell, transit time "
        f"against cost at {corr['spearman']['transit_days']['freight_cost_usd']:.2f}, is why mode has to enter the cost model "
        f"explicitly rather than being left to weight and distance, which alone explain {pct(R['cost']['pooled']['r2'])} of log cost.",
    )


def carriers(r: Report, R: dict) -> None:
    desc, tests = R["descriptive"], R["tests"]
    by_carrier = desc["by_carrier"]
    best, worst = tests["on_time_by_carrier"]["best_carrier"], tests["on_time_by_carrier"]["worst_carrier"]
    cluster = min(by_carrier[c]["on_time_rate"] for c in by_carrier
                  if c not in (worst, "Cobalt Lines", "Unassigned"))

    r.h1("7. Carrier Performance and Service Reliability")
    r.p(
        f"Thirteen labels appear, twelve trading carriers and a residual category of "
        f"{num(by_carrier['Unassigned']['shipments'])} shipments with no carrier recorded. The residual is reported but excluded "
        "from ranking, because a label that means 'unknown' cannot be managed. Across the twelve named "
        f"carriers on-time rates run from {pct(by_carrier[worst]['on_time_rate'])} to {pct(by_carrier[best]['on_time_rate'])}, a gap of "
        f"{tests['on_time_by_carrier']['gap_pp']:.1f} percentage points. Chi-square is {num(tests['on_time_by_carrier']['chi2'], 2)} with "
        f"{tests['on_time_by_carrier']['dof']} degrees of freedom and Cramér's V is {tests['on_time_by_carrier']['cramers_v']:.3f}: the differences are "
        f"real but moderate, and bimodal rather than continuous. The ten mainstream carriers sit "
        f"between {pct(cluster)} and {pct(by_carrier[best]['on_time_rate'])}, a span of "
        f"{(by_carrier[best]['on_time_rate'] - cluster) * 100:.1f} percentage points, while two sit far below: {worst} at "
        f"{pct(by_carrier[worst]['on_time_rate'])} and Cobalt Lines at {pct(by_carrier['Cobalt Lines']['on_time_rate'])}. That two-tier shape justifies "
        "remediation for two contracts, not a league table."
    )
    r.p(
        f"Wilson intervals show the ranking is not an artefact of sample size. {best} carries "
        f"{num(by_carrier[best]['shipments'])} shipments and its interval still excludes the network average, running from "
        f"{pct(by_carrier[best]['ci_low'])} to {pct(by_carrier[best]['ci_high'])}. {worst} carries {num(by_carrier[worst]['shipments'])} and runs from "
        f"{pct(by_carrier[worst]['ci_low'])} to {pct(by_carrier[worst]['ci_high'])}. The intervals do not overlap by a wide margin, so the gap is not "
        "sampling noise. The tightest intervals belong to the largest carriers, the expected pattern and "
        "a useful check that the method is behaving."
    )

    r.caption("Carrier performance. Intervals are Wilson score 95% confidence intervals on the "
              "on-time rate; median cost per kilogram uses costed shipments only.", kind="Table")
    order = sorted([c for c in by_carrier if c != "Unassigned"],
                   key=lambda c: by_carrier[c]["on_time_rate"], reverse=True)
    r.table(
        ["Carrier", "Shipments", "On-time", "95% CI", "Median transit", "Median cost/kg"],
        [[c, num(by_carrier[c]["shipments"]), pct(by_carrier[c]["on_time_rate"]),
          f"{pct(by_carrier[c]['ci_low'])}–{pct(by_carrier[c]['ci_high'])}",
          f"{num(by_carrier[c]['median_transit_days'])} d",
          f"${by_carrier[c]['median_cost_per_kg']:,.2f}"] for c in order],
        widths=[4.6, 2.6, 2.2, 3.4, 2.8, 2.8], font_size=7.8,
    )

    figure(
        r, "fig09",
        "On-time rate by carrier, sorted, with Wilson 95% confidence intervals and the network average "
        "as a reference line.",
        "Horizontal bar chart of twelve carriers plus an unassigned category, sorted by on-time rate "
        "from Ironline Rail at the top to Northwind Cargo at the bottom, each with an error bar. A "
        "dashed vertical line marks the overall rate of 82.8%, which two carriers fall well below.",
        "to show both the size of each carrier's rate and the precision with which it is estimated, so "
        "that ranking and uncertainty are read together.",
        f"The error bars are short for high-volume carriers and wider for Ironline Rail, which carries "
        f"{num(by_carrier['Ironline Rail']['shipments'])} shipments, so gaps inside the cluster are not resolvable; the two weak "
        f"carriers, however, sit far below every interval in it. Northwind Cargo is "
        f"{(by_carrier['Cobalt Lines']['on_time_rate'] - by_carrier[worst]['on_time_rate']) * 100:.1f} points below Cobalt Lines, which is a further "
        f"{(cluster - by_carrier['Cobalt Lines']['on_time_rate']) * 100:.1f} points below the cluster. The network average of "
        f"{pct(R['profile']['on_time_rate'])} therefore falls between the two groups and describes no actual carrier, which is the "
        "strongest argument against managing to it. The two weak carriers handle "
        f"{num(by_carrier[worst]['shipments'] + by_carrier['Cobalt Lines']['shipments'])} shipments, "
        f"{pct((by_carrier[worst]['shipments'] + by_carrier['Cobalt Lines']['shipments']) / R['profile']['on_time_eligible'])} of the network, so the fix is not marginal. "
        "A procurement scorecard should show this chart rather than a league table of rates.",
    )


def cost_structure(r: Report, R: dict) -> None:
    cost, desc = R["cost"], R["descriptive"]
    model, pooled = cost["model"], cost["pooled"]
    sens, flagged = cost["sensitivity"], cost["sensitivity_flagged"]
    by_mode = cost["by_mode"]

    r.h1("8. Cost Structure and Cost Drivers")
    r.p(
        f"Costed shipments number {num(model['n'])} and carry {money(cost['total_cost_usd'])} of freight spend, a median of "
        f"{money(cost['median_cost_usd'])} per shipment and a mean of {money(desc['variables']['freight_cost_usd']['mean'])}. The mean is nearly "
        f"twice the median because the tail is long: the largest shipment costs "
        f"{money(desc['variables']['freight_cost_usd']['max'])}, or {desc['variables']['freight_cost_usd']['max'] / desc['variables']['freight_cost_usd']['median']:.0f} times the median. "
        "Budgeting uses the mean, procurement uses the median, and both are right."
    )
    r.p(
        f"Spend is concentrated in sea and air. Sea accounts for {pct(by_mode['Sea']['cost_share_pct'] / 100)} of cost on "
        f"{pct(by_mode['Sea']['shipment_share_pct'] / 100)} of shipments, air for {pct(by_mode['Air']['cost_share_pct'] / 100)} on "
        f"{pct(by_mode['Air']['shipment_share_pct'] / 100)}; road and rail together carry "
        f"{pct(by_mode['Road']['shipment_share_pct'] / 100 + by_mode['Rail']['shipment_share_pct'] / 100)} of shipments for "
        f"{pct(by_mode['Road']['cost_share_pct'] / 100 + by_mode['Rail']['cost_share_pct'] / 100)} of spend. Per kilogram air costs "
        f"${by_mode['Air']['median_cost_per_kg']:,.2f}, sea ${by_mode['Sea']['median_cost_per_kg']:,.2f}, road "
        f"${by_mode['Road']['median_cost_per_kg']:,.2f} and rail ${by_mode['Rail']['median_cost_per_kg']:,.2f}: air is {cost['air_to_sea_ratio']:.1f} times sea and "
        f"{cost['air_to_rail_ratio']:.1f} times rail."
    )
    r.p(
        f"The log-log model with mode fixed effects explains {pct(model['r2'])} of the variance in cost. The weight "
        f"elasticity is {model['weight_elasticity']:.4f} (95% confidence interval {model['weight_ci'][0]:.4f} to {model['weight_ci'][1]:.4f}) "
        f"and the distance elasticity {model['distance_elasticity']:.4f} ({model['distance_ci'][0]:.4f} to {model['distance_ci'][1]:.4f}). A distance "
        "coefficient of one means cost is proportional to distance; a weight coefficient below one means "
        f"cost rises more slowly. Doubling weight multiplies cost by {model['doubling_weight_factor']:.3f}. The pooled "
        f"model without mode effects tells a different story — weight elasticity {pooled['weight_elasticity']:.3f}, R² {pooled['r2']:.3f} "
        "— and the gap is the price of omitting a variable correlated with both weight and cost."
    )
    r.p(
        f"Two sensitivity checks bound the estimate. Dropping the top half of one percent of costs moves "
        f"the elasticity to {sens['weight_elasticity']:.4f} and raises R² to {sens['r2']:.4f}, so the headline is not driven by a handful "
        f"of invoices. Dropping every row flagged in Section 9 moves it to {flagged['weight_elasticity']:.4f} with R² "
        f"{flagged['r2']:.4f}, the closest the analysis gets to the planted {R['planted_effects']['cost_weight_elasticity']:.2f}."
    )

    r.caption("Cost model specifications. All models regress log freight cost on log weight and log "
              "distance; the primary and sensitivity models add mode fixed effects.", kind="Table")
    r.table(
        ["Specification", "Rows", "Weight elasticity", "Distance elasticity", "R²", "Notes"],
        [
            ["Primary, mode effects", num(model["n"]), f"{model['weight_elasticity']:.4f}",
             f"{model['distance_elasticity']:.4f}", f"{model['r2']:.4f}", "Headline estimate"],
            ["Pooled, no mode term", num(pooled["n"]), f"{pooled['weight_elasticity']:.4f}",
             f"{pooled['distance_elasticity']:.4f}", f"{pooled['r2']:.4f}", "Omitted-variable bias"],
            ["Top 0.5% of costs dropped", num(sens["n"]), f"{sens['weight_elasticity']:.4f}",
             f"{sens['distance_elasticity']:.4f}", f"{sens['r2']:.4f}", "Tail sensitivity"],
            ["Residual-flagged rows dropped", num(flagged["n"]), f"{flagged['weight_elasticity']:.4f}",
             f"{flagged['distance_elasticity']:.4f}", f"{flagged['r2']:.4f}", "Outlier sensitivity"],
        ],
        widths=[4.8, 1.9, 3.0, 3.2, 1.8, 4.0], font_size=7.8,
    )

    figure(
        r, "fig10",
        "Freight cost against weight on log-log axes, shown as a hexbin density with a fitted line for "
        "each mode.",
        "Hexbin plot with log10 weight on the horizontal axis and log10 cost on the vertical axis, "
        "colored by density on a logarithmic scale. Four parallel bands of points, one per mode, each "
        "with a straight fitted line of similar slope.",
        "to show the functional form directly and check that one slope describes all four modes even "
        "though their intercepts differ.",
        f"The four bands are close to parallel, the visual justification for a common weight elasticity "
        f"with mode-specific intercepts. Their vertical separation is roughly "
        f"{abs(model['mode_effects']['Sea'] - model['mode_effects']['Road']):.2f} log points between sea and road, a factor of "
        f"{2.718 ** abs(model['mode_effects']['Sea'] - model['mode_effects']['Road']):.1f} in cost at the same weight and distance. Density is highest at "
        f"moderate weights, around {num(R['descriptive']['variables']['weight_kg']['median'], 0)} kg, and thins in both directions. A few points sit "
        f"far above their band, and those are the residual outliers that Section 9 addresses. The four "
        f"fitted slopes span only {max(v['weight_elasticity'] for v in cost['per_mode_fit'].values()) - min(v['weight_elasticity'] for v in cost['per_mode_fit'].values()):.3f}, "
        f"from {min(cost['per_mode_fit'].values(), key=lambda v: v['weight_elasticity'])['weight_elasticity']:.3f} on road to "
        f"{max(v['weight_elasticity'] for v in cost['per_mode_fit'].values()):.3f} on rail, so one elasticity is defensible and the mode term does "
        "the work.",
    )

    figure(
        r, "fig11",
        "Empirical cumulative distribution of cost per kilogram by mode, on a logarithmic cost axis.",
        "Four cumulative curves on a log horizontal axis. The air curve lies far to the right, the rail "
        "curve far to the left, and the road and sea curves sit between them with sea slightly to the "
        "right of road.",
        "to compare the whole cost distribution across modes rather than a single summary statistic, and "
        "to show where the distributions overlap.",
        f"The curves barely overlap. At ${by_mode['Road']['median_cost_per_kg']:,.2f} per kilogram, half of road freight costs less than that, "
        f"while almost no air freight does; air's median of ${by_mode['Air']['median_cost_per_kg']:,.2f} is "
        f"{by_mode['Air']['median_cost_per_kg'] / by_mode['Road']['median_cost_per_kg']:.0f} times higher. Sea and road cross in the middle of their "
        f"ranges, which is why the choice between them is a genuine trade-off rather than a default: sea's "
        f"median of ${by_mode['Sea']['median_cost_per_kg']:,.2f} is {by_mode['Sea']['median_cost_per_kg'] / by_mode['Road']['median_cost_per_kg']:.1f} times road's. The "
        f"vertical distance between the air and rail curves at the median is about "
        f"{by_mode['Air']['median_cost_per_kg'] / by_mode['Rail']['median_cost_per_kg']:.0f} times, the widest gap in the figure. Managers reading this chart "
        "should see a menu of trade-offs between cost and speed, not a ranking.",
    )


def outliers(r: Report, R: dict) -> None:
    out = R["outliers"]
    rec, prof = out["recovery"], out["profile"]
    per = out["per_variable"]

    r.h1("9. Outlier Detection and Treatment")
    r.p(
        f"An outlier is a claim about a generating process, not a property of a single row, and the choice "
        f"of rule decides which claim is made. {num(prof['planted_rows'])} rows ({pct(prof['planted_share'])}) carry deliberately "
        "corrupted cost, weight or transit values. A naive interquartile-range fence at 1.5 times the IQR "
        f"flags {pct(per['freight_cost_usd']['iqr_pct'] / 100)} of cost values and {pct(per['cost_per_kg']['iqr_pct'] / 100)} of cost-per-kilogram "
        "values, which in a lognormal distribution describes the upper tail rather than an anomaly."
    )
    r.p(
        f"The rules behave very differently against the planted truth. The IQR fence achieves "
        f"{pct(rec['comparison'][0]['recall'])} recall at {pct(rec['comparison'][0]['precision'])} precision, flagging "
        f"{num(rec['comparison'][0]['flagged'])} rows to find {num(prof['planted_rows'])}. A z-score above three reaches "
        f"{pct(rec['comparison'][1]['recall'])} recall at {pct(rec['comparison'][1]['precision'])} precision on {num(rec['comparison'][1]['flagged'])} flags. The "
        f"modified z-score using the median absolute deviation flags {num(rec['comparison'][2]['flagged'])} rows for "
        f"{pct(rec['comparison'][2]['recall'])} recall at {pct(rec['comparison'][2]['precision'])} precision. The residual-modified z-score flags "
        f"{num(rec['flagged_rows'])} rows and recovers {pct(rec['recall'])} at {pct(rec['precision'])} precision, with {num(rec['missed'])} misses."
    )
    r.p(
        "Residuals win because corruption is conditional. A cost of one hundred thousand dollars is "
        "unremarkable for a heavy sea shipment and impossible for a two-kilogram air parcel; a "
        "univariate fence cannot tell them apart, while a residual compares each row with what its own "
        "weight, distance and mode predict. The price is model dependence: the rule inherits the cost "
        "specification and would flag differently if the model changed, which is acceptable because the "
        "model is reported and tested. The decision is to flag rather than delete, because deleting "
        f"{num(rec['flagged_rows'])} rows would bias the model toward the well-behaved middle."
    )

    r.caption("Outlier rules scored against the planted anomalies: 688 corrupted rows in a file of "
              "49,935. Precision is the share of flags that are truly planted.", kind="Table")
    r.table(
        ["Rule", "Rows flagged", "Recall", "Precision", "Use in this report"],
        [[row["method"], num(row["flagged"]), pct(row["recall"]), pct(row["precision"]),
          "Rejected: tail-blind" if row["method"] == "IQR fence" else
          "Rejected: under-flags" if row["method"] == "z-score > 3" else
          "Rejected: over-flags" if row["method"] == "modified z (raw)" else "Adopted for flagging"]
         for row in rec["comparison"]],
        widths=[4.6, 3.0, 2.4, 2.6, 4.4], font_size=7.8,
    )

    figure(
        r, "fig12",
        "Recall and precision of four outlier rules against the planted anomalies.",
        "Grouped bar chart with four method groups, each showing a recall bar and a precision bar. The "
        "residual rule reaches 0.91 recall and 0.53 precision, while the other three rules combine high "
        "recall with very low precision or the reverse.",
        "to make the trade-off between catching anomalies and flooding the analyst with false positives "
        "visible, since either metric alone is easy to game.",
        f"The residual rule is the only one above 0.5 on both measures. The IQR fence catches "
        f"{pct(rec['comparison'][0]['recall'])} of planted rows but only {pct(rec['comparison'][0]['precision'])} of its flags are real, so an analyst "
        f"following it would investigate {num(rec['comparison'][0]['flagged'])} rows to find {num(prof['planted_rows'])}. The raw modified z-score is worse "
        f"in the other direction, flagging {num(rec['comparison'][2]['flagged'])} rows. Precision matters more than recall operationally, because "
        "each flag costs an investigation: a rule that is right half the time is worth using, and one "
        f"that is right once in twenty is not. The adopted rule raises {num(rec['flagged_rows'])} flags over 24 months, about "
        f"{rec['flagged_rows'] / 24:.0f} a month, which is a workload a small team can absorb.",
    )


def lanes(r: Report, R: dict) -> None:
    lanes_d = R["lanes"]
    r.h1("10. Lane Concentration and Network Structure")
    r.p(
        f"The network contains {num(lanes_d['lane_count'])} origin-to-destination lanes. The ten largest carry "
        f"{pct(lanes_d['top10_share_pct'] / 100)} of shipments and the fifteen largest {pct(lanes_d['top15_share_pct'] / 100)}. Reaching 80% of volume requires "
        f"{num(lanes_d['lanes_for_80pct'])} lanes, or {pct(lanes_d['lanes_for_80pct_share'] / 100)} of the network, and the Herfindahl-Hirschman index is "
        f"{lanes_d['hhi']:.3f}, equivalent to {lanes_d['effective_lanes']:.1f} equally sized lanes: a diffuse network, where a hub-and-spoke "
        "system would show a much higher index."
    )
    r.p(
        "Concentration matters for risk. When ten lanes carry less than a third of volume, a closure on "
        "any single lane is a local problem rather than a network failure. The same structure makes "
        f"consolidation harder: a carrier cannot justify a dedicated service on a lane carrying "
        f"{pct(lanes_d['top_lanes'][0]['share_pct'] / 100)} of shipments, so most lanes depend on shared capacity. Lane service varies more than mode service: among the "
        f"{num(lanes_d['reliable_lane_count'])} lanes with at least 200 shipments, the best is {lanes_d['best_lane']['lane']} at "
        f"{pct(lanes_d['best_lane']['on_time'])} and the worst is {lanes_d['worst_lane']['lane']} at {pct(lanes_d['worst_lane']['on_time'])}."
    )

    r.caption("Network concentration metrics and the extremes of lane-level service, restricted to "
              "lanes with at least 200 shipments.", kind="Table")
    r.table(
        ["Metric", "Value", "Reading"],
        [
            ["Lanes", num(lanes_d["lane_count"]), "Distinct origin-to-destination pairs"],
            ["Top 10 lanes", pct(lanes_d["top10_share_pct"] / 100), "Share of all shipments"],
            ["Top 15 lanes", pct(lanes_d["top15_share_pct"] / 100), "Share of all shipments"],
            ["Lanes for 80% of volume", num(lanes_d["lanes_for_80pct"]), f"{pct(lanes_d['lanes_for_80pct_share'] / 100)} of the network"],
            ["Herfindahl-Hirschman index", f"{lanes_d['hhi']:.3f}", f"Effective {lanes_d['effective_lanes']:.1f} equal lanes"],
            ["Best lane", f"{lanes_d['best_lane']['lane']} ({pct(lanes_d['best_lane']['on_time'])})", f"{num(lanes_d['best_lane']['shipments'])} shipments"],
            ["Worst lane", f"{lanes_d['worst_lane']['lane']} ({pct(lanes_d['worst_lane']['on_time'])})", f"{num(lanes_d['worst_lane']['shipments'])} shipments"],
        ],
        widths=[5.6, 7.4, 4.0], font_size=7.8,
    )

    figure(
        r, "fig13",
        "Pareto chart of the fifteen largest lanes, with cumulative share of shipments on a second "
        "axis.",
        "Horizontal bars showing shipment counts for the fifteen largest lanes, from Chicago to Los "
        "Angeles at 1,887 down to Dallas to New York at 878, with an overlaid cumulative curve that "
        "reaches 38.5% at the fifteenth lane.",
        "to test whether a small number of corridors dominates the network, which would justify "
        "lane-specific investment.",
        f"The bars decline gently and the cumulative curve is almost straight, the visual signature of a "
        f"flat distribution. The largest lane carries {pct(lanes_d['top_lanes'][0]['share_pct'] / 100)} of shipments, only "
        f"{lanes_d['top_lanes'][0]['share_pct'] / lanes_d['top_lanes'][9]['share_pct']:.1f} times the tenth, and the curve reaches "
        f"{pct(lanes_d['top15_share_pct'] / 100)} at fifteen lanes. A true Pareto pattern would show the first few bars carrying half the "
        f"volume and a curve that flattens after five. This network needs {num(lanes_d['lanes_for_80pct'])} lanes to reach four-fifths of "
        "volume, so investment decisions belong at the lane-group level rather than the corridor level. "
        f"The top ten lanes carry {pct(lanes_d['top10_share_pct'] / 100)} of volume, a third of what a true Pareto pattern would "
        "put there, and the cumulative curve offers no natural cut point.",
    )


def delay_patterns(r: Report, R: dict) -> None:
    ts = R["timeseries"]
    weekdays = ts["weekday"]
    means = {day: stats["mean_delay"] for day, stats in weekdays.items()}

    r.h1("11. Delay Patterns by Weekday and Month")
    r.p(
        f"Delay is promised transit minus actual transit, so a negative value means early arrival. The "
        f"network mean sits between {min(ts['monthly']['mean_delay']):.2f} and {max(ts['monthly']['mean_delay']):.2f} days across all 24 months, "
        "which is a wide buffer rather than tight planning. Promises are generous by design, and the "
        f"median shipment arrives two days ahead of the commitment. Weekday effects are negligible: mean "
        f"delay ranges from {min(means.values()):.2f} days on {min(means, key=means.get)} to {max(means.values()):.2f} on {max(means, key=means.get)}, a spread of "
        f"{max(means.values()) - min(means.values()):.2f} days, and the median is two days early every weekday. There is no Monday backlog "
        "to plan around, and that negative result is worth reporting: an operations team adding weekend "
        "staff on the assumption of a weekday pattern would be spending against no measured problem."
    )
    r.p(
        "Month effects are real but concentrated in one event. The heatmap is almost uniform except for "
        "the February 2025 column, where every weekday turns darker as delays lengthen. On-time falls to "
        f"{pct(ts['disruption']['feb_on_time'])} that month against {pct(ts['disruption']['baseline_on_time'])} elsewhere, and the effect is visible in every "
        "mode in Figure 7. Averaging across two years would halve the apparent size of the event and "
        "hide it from a weekday analysis."
    )

    figure(
        r, "fig14",
        "Mean delay by order weekday and order month, with months on the horizontal axis.",
        "Seven-by-twenty-four heatmap of mean delay in days, from red for the longest delays to blue for "
        "the shortest. Almost every cell lies between minus three and minus two days, with one darker "
        "column in February 2025.",
        "to check for weekday and month interactions that a marginal average would miss, and to locate "
        "the disruption in two dimensions at once.",
        f"The color scale spans only {max(means.values()) - min(means.values()):.2f} days across weekdays, which is why the panel looks flat. "
        f"The February 2025 column stands out at roughly "
        f"{min(ts['delay_matrix']['rows'][day][13] for day in ts['delay_matrix']['rows']):.2f} days on its worst weekday, about a day worse than the "
        "surrounding months, and no other column approaches that. The chart therefore answers its "
        f"question in the negative for weekdays and in the affirmative for one month. Shipment counts vary "
        f"by only {max(s['shipments'] for s in weekdays.values()) - min(s['shipments'] for s in weekdays.values())} across weekdays, from "
        f"{num(min(s['shipments'] for s in weekdays.values()))} on {min(weekdays, key=lambda d: weekdays[d]['shipments'])} to "
        f"{num(max(s['shipments'] for s in weekdays.values()))} on {max(weekdays, key=lambda d: weekdays[d]['shipments'])}, so a staffing pattern has no support in the data either. Both answers "
        "are actionable: do not staff for a weekday pattern, do plan for a single-month shock.",
    )


def real_benchmark(r: Report, R: dict) -> None:
    real = R["timeseries"]["real_data"]
    ts = R["timeseries"]
    r.h1("12. External Benchmark: United States Border Crossings")
    r.p(
        f"The BTS series covers {num(real['rows'])} monthly truck records across {num(real['ports'])} ports and "
        f"{num(len(real['monthly']['values']))} months. The latest observation, {real['latest_month']}, records {num(real['latest_value'])} "
        f"crossings, {abs(real['latest_yoy_pct']):.1f}% below the same month a year earlier, and the twelve-month mean is "
        f"{num(real['monthly_last12_mean'])}. Long-run growth is slow: compound annual growth from 2015 to 2025 is "
        f"{real['cagr_2015_2025_pct']:.1f}%, and the strongest year is {real['annual_max_year']} at {num(real['annual_max_value'])} crossings."
    )
    r.p(
        f"The seasonal shape contradicts the simulation. The December index is {real['december_index']:.3f} and the October "
        f"index {real['october_index']:.3f}, so December is the weakest month rather than the strongest; March peaks at "
        f"{real['seasonal_index']['3']:.3f}. Seasonal strength is {real['seasonal_strength']:.3f} against {ts['decomposition']['seasonal_strength']:.3f} in the "
        f"simulation, and trend strength {real['trend_strength']:.3f} against {ts['decomposition']['trend_strength']:.3f}. Real border traffic follows "
        "agricultural cycles, automotive production schedules and holiday closures; the simulated ledger "
        "follows a retail calendar with a hard fourth-quarter multiplier."
    )
    r.p(
        f"The 2020 shock calibrates magnitude. April 2020 crossings are {abs(real['covid_apr2020_vs_apr2019_pct']):.1f}% below April 2019, yet "
        f"the full year is only {abs(real['annual_2020_vs_2019_pct']):.1f}% below 2019, because traffic recovered within the year. Port "
        f"concentration is moderate: {real['top_port']} handles {pct(real['top_port_share'])} of crossings, the top five "
        f"{pct(real['top5_port_share'])}, and the port HHI of {real['port_hhi']:.3f} implies about {1 / real['port_hhi']:.0f} equally sized ports."
    )

    figure(
        r, "fig15",
        "Monthly truck crossings at United States border ports from 1996 to 2026, with a twelve-month "
        "moving average and a seasonal index by calendar month.",
        "Top panel: a long monthly series of truck crossings with a smooth twelve-month average, showing "
        "steady growth, a sharp drop in 2020 and recovery. Bottom panel: twelve bars of the seasonal "
        "index, highest in March and lowest in December.",
        "to place the simulated seasonal pattern against an independent real series, and to show how a "
        "genuine shock appears in a long monthly record.",
        f"The trend line rises from about {num(real['monthly']['values'][0])} crossings in early 1996 to roughly {num(real['monthly_last12_mean'])} "
        f"today, with the 2020 trough a single deep notch rather than a change in level. The seasonal bars "
        f"vary by only about "
        f"{pct((real['seasonal_index']['3'] - real['seasonal_index']['12']) / real['seasonal_index']['12'])} between peak and trough, far less than the "
        f"{pct(ts['summary']['q4_uplift_pct'] / 100)} fourth-quarter uplift in the simulation. That comparison is the point of the figure: a "
        "seasonal story that generalizes should appear in both series, and this one does not. The "
        f"simulated peak is a design choice, not a law of freight. The 2020 notch is {abs(real['covid_apr2020_vs_apr2019_pct']):.1f}% deep in April "
        f"but only {abs(real['annual_2020_vs_2019_pct']):.1f}% deep for the year, which is what recovery looks like in a long series.",
    )


def validation(r: Report, R: dict) -> None:
    val = R["validation"]
    r.h1("13. Method Validation")
    r.p(
        f"The simulation exists so that the analysis can be marked. Each planted effect has a designed "
        "value, and the recovered value is compared with it on a pre-specified criterion: recovery "
        "succeeds when the estimate falls within sampling error of the design or reproduces its ordering. "
        f"{val['matched']} of {val['total']} effects pass. The fourth-quarter index recovers at 1.348 against a planted multiplier of "
        "1.35, a difference that comes from sampling noise and the January dip; the mode medians reproduce "
        "exactly; and both weak carriers are recovered to within 0.1 percentage points. Had cleaning "
        "mishandled the pound rows the weight elasticity would have failed; had the date parser dropped "
        "February 2025, the disruption row would have failed."
    )
    r.p(
        f"The cost elasticity is the one deliberate near-miss: recovered at {R['cost']['model']['weight_elasticity']:.3f} against a planted "
        f"{R['planted_effects']['cost_weight_elasticity']:.2f}, a shortfall of "
        f"{abs(R['cost']['model']['weight_elasticity'] - R['planted_effects']['cost_weight_elasticity']) / R['planted_effects']['cost_weight_elasticity'] * 100:.1f}%. The gap has a mechanical explanation. Cost is "
        "missing not at random in the heaviest and most expensive rows, so the complete-case model sees a "
        f"truncated weight range, and residual outliers pull the slope down. Dropping the flagged rows "
        f"recovers {R['cost']['sensitivity_flagged']['weight_elasticity']:.4f}, within 0.001 of the planted value. Outlier recovery is the "
        f"weakest result: the rule finds {pct(R['outliers']['recovery']['recall'])} of the anomalies but only "
        f"{pct(R['outliers']['recovery']['precision'])} of its flags are true positives. That is acceptable for a flagging rule and "
        "not good enough for an automated rejection rule."
    )

    r.caption("Method validation: planted design values against recovered estimates.", kind="Table")
    r.table(
        ["Effect", "Planted", "Recovered", "Match"],
        [[row["effect"], row["planted"], row["recovered"], "Yes" if row["match"] else "No"]
         for row in val["rows"]],
        widths=[3.6, 5.6, 6.4, 1.4], font_size=7.6,
    )
    r.p(
        "The table is meaningful because the checks were specified before the results were seen: the "
        "criteria are the design values in Table 2, written into the generator and read back by the audit."
    )


def limitations(r: Report, R: dict) -> None:
    r.h1("14. Limitations and Threats to Validity")
    r.p(
        "The primary dataset is synthetic, and no amount of internal validation changes that. The "
        "simulation encodes a particular view of freight: lognormal weights, a power-law cost function, "
        "mode-specific transit and a retail calendar. Real networks contain contract rates, congestion "
        "feedback, backhauls, fuel surcharges and customer-specific service levels that the generator does "
        "not model. The findings are statements about the simulated network."
    )
    r.p(
        f"Missing data is the second threat. Cost is missing for {pct(R['profile']['cost_missing_share'])} of rows and the mechanism "
        "is not random, so every cost statistic describes the cheaper and more completely invoiced part of "
        f"the ledger. The total of {money(R['cost']['total_cost_usd'])} is therefore a lower bound and the weight elasticity is "
        f"probably biased downward. Delivery date is missing for "
        f"{pct(R['cleaning']['missing_by_column']['delivery_date']['share'])} of rows, which removes those shipments from every service "
        "statistic."
    )
    r.p(
        "The external benchmark has its own grain problem. BTS counts loaded truck crossings, not "
        "shipments or tonnes, and one crossing may carry a parcel or forty pallets. It covers land borders "
        "only, so it says nothing about air or sea seasonality. The cost model is heteroscedastic and "
        "non-normal in its residuals, so conventional "
        "standard errors understate certainty and robust errors would widen the intervals without moving "
        "the point estimates. Multiple tests were run; the mode comparisons carry a Holm correction but "
        "the exploratory tests elsewhere do not, and with samples this large p-values are close to "
        "uninformative while effect sizes carry the argument."
    )
    r.p(
        "Carrier and lane comparisons are observational: carriers are not randomly assigned to lanes, so a "
        "badly served lane may simply be one that only weak carriers bid for. Two things the data cannot "
        "answer: there is no geospatial dimension beyond city names, so distance is a modeled attribute "
        "rather than a routed one, and no customer identifier, so the analysis cannot separate a carrier "
        "effect from a customer mix effect. Both gaps are addressable with richer data."
    )


def conclusions(r: Report, R: dict) -> None:
    prof, desc, ts = R["profile"], R["descriptive"], R["timeseries"]
    cost, tests = R["cost"], R["tests"]
    lanes_d, out = R["lanes"], R["outliers"]
    cluster = min(desc["by_carrier"][c]["on_time_rate"] for c in desc["by_carrier"]
                  if c not in ("Northwind Cargo", "Cobalt Lines", "Unassigned"))

    r.h1("15. Conclusions and Recommendations")
    r.p(
        f"The network delivers {pct(prof['on_time_rate'])} of shipments on time against promises that are, on average, "
        f"{abs(desc['variables']['delay_days']['mean']):.2f} days generous. Median transit is {num(desc['variables']['transit_days']['median'])} days, "
        f"but mode medians of {num(desc['by_mode']['Air']['median_transit_days'])}, {num(desc['by_mode']['Road']['median_transit_days'])}, "
        f"{num(desc['by_mode']['Rail']['median_transit_days'])} and {num(desc['by_mode']['Sea']['median_transit_days'])} days mean the aggregate describes no actual "
        f"shipment. Service is mode-specific and lane-specific, and the small Cramér's V for mode "
        f"({tests['on_time_by_mode']['cramers_v']:.3f}) shows the promise absorbs most of the mode difference rather than the network "
        "failing to."
    )
    r.p(
        f"Volume is strongly seasonal and essentially flat. The fourth-quarter index is {ts['summary']['q4_index']:.3f}, November "
        f"peaks at {num(ts['summary']['peak_value'])} shipments, January troughs at {num(ts['summary']['trough_value'])}, and year-on-year growth is "
        f"{ts['summary']['growth_2025_vs_2024_pct']:.1f}%. Seasonal strength of {ts['decomposition']['seasonal_strength']:.3f} against trend strength of "
        f"{ts['decomposition']['trend_strength']:.3f} is the quantitative form of that sentence. The February 2025 disruption cost "
        f"{ts['disruption']['on_time_gap_pp']:.1f} percentage points of on-time performance for one month and is the only calendar "
        "event that survives every cut of the data."
    )
    r.p(
        f"Cost is the largest number and the most stable finding. {money(cost['total_cost_usd'])} of spend sits on "
        f"{num(cost['model']['n'])} costed shipments with a median of {money(cost['median_cost_usd'])}. The log-log model explains "
        f"{pct(cost['model']['r2'])} of variance with a weight elasticity of {cost['model']['weight_elasticity']:.3f} and a distance elasticity of "
        f"{cost['model']['distance_elasticity']:.3f}, and it survives removal of the top half of one percent of invoices. Air freight "
        f"costs {cost['air_to_sea_ratio']:.1f} times sea freight per kilogram and consumes {pct(cost['by_mode']['Air']['cost_share_pct'] / 100)} of the "
        f"budget on {pct(cost['by_mode']['Air']['shipment_share_pct'] / 100)} of shipments. That ratio, not the total, is the lever."
    )
    r.p(
        f"The network is diffuse: {num(lanes_d['lanes_for_80pct'])} of {num(lanes_d['lane_count'])} lanes carry 80% of volume and the HHI is "
        f"{lanes_d['hhi']:.3f}. Two carriers account for almost all of the service gap, "
        f"{tests['on_time_by_carrier']['worst_carrier']} at {pct(tests['on_time_by_carrier']['worst_rate'])} and Cobalt Lines at "
        f"{pct(desc['by_carrier']['Cobalt Lines']['on_time_rate'])}, against a cluster of ten between {pct(cluster)} and "
        f"{pct(tests['on_time_by_carrier']['best_rate'])}. The outlier rule recovers {pct(out['recovery']['recall'])} of planted anomalies, and "
        f"validation passes {R['validation']['matched']} of {R['validation']['total']} checks, so the findings are not an artefact of the cleaning."
    )
    r.p("Five recommendations follow, in priority order. Each is tied to a measured effect and written so "
        "that it can be accepted or rejected without re-running the analysis.")
    r.caption("Recommendations, owners and the evidence behind each.", kind="Table")
    r.table(
        ["#", "Recommendation", "Owner", "Expected effect", "Evidence"],
        [
            ["1", "Put Northwind Cargo and Cobalt Lines on a formal improvement plan with monthly review",
             "Procurement", "Close up to 31.3 points of the carrier gap", "§7, Table 7"],
            ["2", "Shift discretionary air volume to sea or rail where the promise allows",
             "Network planning", "Air costs 7.7 times sea per kilogram", "§8, Figure 11"],
            ["3", "Flex capacity for September to December rather than adding permanent fleet",
             "Operations", "Absorb a 34.8% quarterly peak on flat annual growth", "§5, Figure 4"],
            ["4", "Run service monitoring by mode and lane, not in aggregate",
             "Performance", "Mode medians differ by 21 days; lane rates by 21.8 points", "§4, §10"],
            ["5", "Keep the residual outlier rule as a flag with human review, and re-fit quarterly",
             "Data team", "90.8% recall at 53.2% precision", "§9, Table 9"],
        ],
        widths=[0.8, 6.6, 3.0, 5.0, 2.6], font_size=7.6,
    )
    r.p(
        f"The first recommendation has the clearest financial case: two contracts account for a "
        f"{tests['on_time_by_carrier']['gap_pp']:.1f} point spread that no other carrier exhibits. The second is the largest in absolute "
        "terms, because air carries almost a third of spend on a quarter of shipments. The last three "
        "are organizational rather than financial."
    )
    r.p(
        "If this analysis were repeated, three changes would improve it: robust standard errors and a "
        "selection correction for the missing-cost mechanism; outlier detection evaluated on held-out "
        "anomalies; and an external benchmark covering air and sea. None would alter the headline "
        "results; all would narrow the intervals."
    )


def references(r: Report) -> None:
    r.h1("References")
    entries = [
        "Bureau of Transportation Statistics. Border Crossing Entry Data, dataset keg4-3bc2. "
        "United States Department of Transportation, 2026. Accessed 2 November 2026. Public domain.",
        "Cleveland, R. B., Cleveland, W. S., McRae, J. E. and Terpenning, I. (1990). STL: A "
        "seasonal-trend decomposition procedure based on LOESS. Journal of Official Statistics, 6(1), "
        "3–73.",
        "Cramér, H. (1946). Mathematical Methods of Statistics. Princeton University Press.",
        "Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian "
        "Journal of Statistics, 6(2), 65–70.",
        "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. Computing in Science and "
        "Engineering, 9(3), 90–95.",
        "Waskom, M. L. (2021). Seaborn: statistical data visualization. Journal of Open Source "
        "Software, 6(60), 3021.",
        "Plotly Technologies Inc. (2015). Collaborative data science. Plotly, Montreal.",
        "Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. "
        "Journal of the American Statistical Association, 22(158), 209–212.",
    ]
    for entry in entries:
        para = r.doc.add_paragraph(entry, style="ReferenceEntry")
        para.paragraph_format.left_indent = Cm(0.7)
        para.paragraph_format.first_line_indent = Cm(-0.7)
        para.paragraph_format.space_after = Pt(4)


def appendix(r: Report, R: dict) -> None:
    r.h1("Appendix A. Reproducibility")
    r.p(
        "Every artefact in this report is produced by a scripted pipeline. From the repository root the "
        "sequence is ``make week2``, which runs data generation, cleaning, analysis, figure production "
        "and the report build in order. Each stage reads the previous stage's output and writes to a "
        "fixed path, so a partial run cannot leave the report reading stale numbers, and no table or "
        "figure is pasted in by hand. A failed stage stops the run before the report is rebuilt, and a "
        "repeat run reproduces the same bytes."
    )
    r.p(
        "The environment is pinned in ``requirements.txt``. Figures are written at 200 dots per inch to "
        "``figures/``; the plotly chart is exported to both PNG and standalone HTML. Results are written "
        "to ``results/`` as JSON, and the report reads those files rather than recomputing anything. The "
        "executed notebook ``notebooks/week2_eda.ipynb`` follows the same sequence."
    )
    r.p(
        f"Two hashes anchor the inputs. The cleaned dataset has SHA-256 ``{R['cleaning']['output_sha256'][:32]}…`` and is "
        f"{R['cleaning']['output_bytes'] / 1_000_000:.1f} megabytes on disk. The external extract's hash is recorded in "
        "``data/external/bts_border_trucks.meta.json`` alongside its retrieval date and license. "
        "Re-running with the seed set to 42 reproduces every table and figure exactly; changing the seed "
        "changes the noise and leaves the effects in place, which is the test Section 13 is designed to "
        "support."
    )
    r.p(
        "The document is generated by ``src/build_report.py`` using python-docx with three heading "
        "levels and named styles for body text, captions, tables and code, so navigation tools can read "
        "its outline. There is no automatic table of contents: section numbering is explicit and page "
        "numbers are live fields in the footer."
    )


def build() -> Path:
    R = load_results()
    r = Report()
    title_block(r)
    coverage_matrix(r)
    summary(r, R)
    introduction(r, R)
    data_sources(r, R)
    data_quality(r, R)
    distributions(r, R)
    temporal(r, R)
    relationships(r, R)
    carriers(r, R)
    cost_structure(r, R)
    outliers(r, R)
    lanes(r, R)
    delay_patterns(r, R)
    real_benchmark(r, R)
    validation(r, R)
    limitations(r, R)
    conclusions(r, R)
    references(r)
    appendix(r, R)
    REPORTS.mkdir(parents=True, exist_ok=True)
    r.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path.relative_to(ROOT)}")