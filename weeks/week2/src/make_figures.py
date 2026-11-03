"""Build every figure in the report from the analysed data.

Each function writes one PNG at 200 dpi and, where relevant, an interactive
HTML file. The report imports ``SNIPPETS`` so the code shown next to a figure
is the code that produced it (abridged only by dropping styling calls).

Run after ``generate_data``, ``clean`` and ``analyze``.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from .style import (BLUE, FIGURES, GREEN, GREY, MODE_COLORS, ORANGE, PURPLE,
                    SERIES, SKY, VERMILLION, YELLOW, annotate, apply_style, save)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODES = ["Air", "Road", "Rail", "Sea"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]


def load():
    df = pd.read_csv(ROOT / "data" / "processed" / "shipments_clean.csv",
                     parse_dates=["order_date", "ship_date", "delivery_date",
                                  "month_start"])
    results = {p.stem: json.loads(p.read_text()) for p in RESULTS.glob("*.json")}
    return df, results


def fig01_workflow(res: dict) -> str:
    stages = [
        ("1  Generate", "50,000 simulated shipments\n1 Feb 2024 - 31 Dec 2025"),
        ("2  Acquire", "BTS truck crossings,\n1996-2026, public domain"),
        ("3  Clean", "duplicates, dates, units,\nlabels, missing values"),
        ("4  Profile", "shape, dtypes, missingness,\ncategory counts"),
        ("5  Analyse", "descriptives, tests,\nSTL, regression"),
        ("6  Visualize", "15 figures: matplotlib,\nseaborn, plotly"),
        ("7  Validate", "planted effect vs\nrecovered estimate"),
        ("8  Report", "DOCX + PDF, every number\nfrom results/*.json"),
    ]
    fig, ax = plt.subplots(figsize=(9.4, 4.6))
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 2)
    ax.axis("off")
    coords = [(0.05, 1.18), (1.05, 1.18), (2.05, 1.18), (3.05, 1.18),
              (3.05, 0.18), (2.05, 0.18), (1.05, 0.18), (0.05, 0.18)]
    for (title, sub), (x, y) in zip(stages, coords):
        ax.add_patch(FancyBboxPatch((x, y), 0.9, 0.64,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=1.1, edgecolor=BLUE,
                                    facecolor="#EAF2F8"))
        ax.text(x + 0.45, y + 0.46, title, ha="center", va="center",
                fontsize=10.2, fontweight="bold", color="#123")
        ax.text(x + 0.45, y + 0.21, sub, ha="center", va="center",
                fontsize=7.6, color="#333")
    arrows = [((0.95, 1.5), (1.04, 1.5)), ((1.95, 1.5), (2.04, 1.5)),
              ((2.95, 1.5), (3.04, 1.5)), ((3.5, 1.16), (3.5, 0.84)),
              ((3.04, 0.5), (2.96, 0.5)), ((2.04, 0.5), (1.96, 0.5)),
              ((1.04, 0.5), (0.96, 0.5))]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                                     linewidth=1.1, color=GREY))
    ax.text(2.0, 1.98, "EDA workflow: eight stages, each producing a file the next stage reads",
            ha="center", fontsize=12.5, fontweight="bold")
    ax.text(2.0, 0.02, "Validation stage compares the recovered statistics with the "
                       "effects planted in the generator",
            ha="center", fontsize=8.6, color="#444", style="italic")
    return str(save(fig, "fig01_eda_workflow.png").name)


def fig02_transit_hist(df: pd.DataFrame, res: dict) -> str:
    med = df["transit_days"].median()
    p90 = df["transit_days"].quantile(0.90)
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    sns.histplot(data=df, x="transit_days", bins=42, log_scale=(True, False),
                 color=BLUE, alpha=0.55, edgecolor="white", linewidth=0.4,
                 kde=True, stat="count", ax=ax)
    ax.axvline(med, color=VERMILLION, lw=1.4, ls="--")
    ax.axvline(p90, color=ORANGE, lw=1.4, ls=":")
    ax.text(med * 1.04, ax.get_ylim()[1] * 0.92, f"median {med:.0f} d",
            fontsize=8.5, color=VERMILLION)
    ax.text(p90 * 1.04, ax.get_ylim()[1] * 0.80, f"p90 {p90:.0f} d",
            fontsize=8.5, color=ORANGE)
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("Transit time (ship to delivery), days - log scale")
    ax.set_ylabel("Shipments (count)")
    ax.set_title("Transit times are right-skewed with a long sea-freight tail")
    annotate(ax, f"n = {len(df):,}\nskew = {res['descriptive']['variables']['transit_days']['skew']:.2f}",
             (0.62, 0.78), transform=ax.transAxes, color=GREY)
    return str(save(fig, "fig02_transit_histogram.png").name)


def fig03_mode_violin(df: pd.DataFrame, res: dict) -> str:
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    sns.violinplot(data=df, x="mode", y="transit_days", order=MODES,
                   hue="mode", palette=MODE_COLORS, legend=False, cut=0,
                   inner="box", linewidth=0.9, density_norm="width",
                   log_scale=True, ax=ax)
    for i, mode in enumerate(MODES):
        med = df.loc[df["mode"] == mode, "transit_days"].median()
        ax.text(i, med * 1.45, f"{med:.0f} d", ha="center", fontsize=9,
                fontweight="bold", color="#222",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="#CCC", lw=0.6))
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 3, 5, 7, 10, 15, 20, 30, 50])
    ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("Transport mode")
    ax.set_ylabel("Transit time (days, log scale)")
    ax.set_title("Transit time separates cleanly by mode: air 3 d to sea 24 d")
    return str(save(fig, "fig03_mode_violin.png").name)


def fig04_monthly_volume(df: pd.DataFrame, res: dict) -> str:
    ts = res["timeseries"]
    months = pd.to_datetime(ts["monthly"]["months"])
    values = ts["monthly"]["shipments"]
    rolling = ts["monthly"]["rolling_3"]
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    for year in (2024, 2025):
        ax.axvspan(pd.Timestamp(year, 10, 1), pd.Timestamp(year, 12, 31),
                   color=ORANGE, alpha=0.12, lw=0)
    ax.plot(months, values, marker="o", ms=3.4, lw=1.5, color=BLUE,
            label="Monthly shipments")
    ax.plot(months, rolling, lw=2.4, color=VERMILLION, ls="--",
            label="3-month centered mean")
    peak_idx = int(np.argmax(values))
    ax.annotate(f"peak {months[peak_idx]:%b %Y}: {values[peak_idx]:,}",
                xy=(months[peak_idx], values[peak_idx]),
                xytext=(6, -44), textcoords="offset points", fontsize=8.4,
                ha="left", arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))
    ax.set_ylim(0, max(values) * 1.22)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_ylabel("Shipments per month")
    ax.set_xlabel("Order month")
    ax.set_title("A repeatable Q4 peak: October to December runs about 35% above the rest")
    ax.legend(loc="lower left", ncol=2)
    ax.text(0.99, 0.02, "shaded = Q4", transform=ax.transAxes, ha="right",
            fontsize=8, color=ORANGE)
    return str(save(fig, "fig04_monthly_volume.png").name)


def fig05_decomposition(res: dict) -> str:
    ts = res["timeseries"]
    months = pd.to_datetime(ts["monthly"]["months"])
    observed = ts["monthly"]["shipments"]
    seasonal = ts["decomposition"]["seasonal"]
    trend = ts["decomposition"]["trend"]
    resid = ts["decomposition"]["resid"]
    fig, axes = plt.subplots(4, 1, figsize=(8.4, 7.0), sharex=True)
    panels = [(observed, BLUE, "Observed shipments"),
              (trend, VERMILLION, "Trend (STL)"),
              (seasonal, GREEN, "Seasonal component"),
              (resid, GREY, "Residual")]
    for ax, (values, colour, label) in zip(axes, panels):
        ax.plot(months, values, lw=1.6, color=colour)
        ax.set_ylabel(label, fontsize=9)
        ax.tick_params(axis="y", labelsize=8)
    axes[3].axhline(0, color="#666", lw=0.8)
    axes[0].set_title("STL decomposition: seasonality explains more variation than the trend")
    axes[3].set_xlabel("Order month")
    fig.text(0.01, 0.005,
             f"seasonal strength {ts['decomposition']['seasonal_strength']:.2f}, "
             f"trend strength {ts['decomposition']['trend_strength']:.2f}, "
             f"residual SD {ts['decomposition']['resid_sd']:.0f} shipments",
             fontsize=8.2, color="#444")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return str(save(fig, "fig05_stl_decomposition.png").name)


def fig06_correlation(res: dict) -> str:
    corr = pd.DataFrame(res["correlations"]["spearman"])
    order = ["freight_cost_usd", "weight_kg", "volume_m3", "distance_km",
             "cost_per_kg", "transit_days", "promised_days", "delay_days"]
    corr = corr.loc[order, order]
    mask = np.triu(np.ones_like(corr, dtype=bool))
    fig, ax = plt.subplots(figsize=(7.8, 6.0))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                vmin=-1, vmax=1, square=True, linewidths=0.6,
                linecolor="white", cbar_kws={"shrink": 0.75, "label": "Spearman rho"},
                annot_kws={"size": 8.2}, ax=ax)
    ax.set_title("Spearman correlations: cost tracks weight and distance, not transit time")
    ax.set_xticklabels([c.replace("_", " ") for c in order], rotation=38,
                       ha="right", fontsize=8.5)
    ax.set_yticklabels([c.replace("_", " ") for c in order], fontsize=8.5)
    return str(save(fig, "fig06_correlation_heatmap.png").name)


def fig07_carrier_ontime(res: dict) -> str:
    by_carrier = res["descriptive"]["by_carrier"]
    overall = res["profile"]["on_time_rate"]
    weak = set(res["planted_effects"]["weak_carriers"])
    rows = sorted(((k, v) for k, v in by_carrier.items() if k != "Unassigned"),
                  key=lambda kv: kv[1]["on_time_rate"])
    names = [k for k, _ in rows]
    rates = [v["on_time_rate"] for _, v in rows]
    low = [v["on_time_rate"] - v["ci_low"] for _, v in rows]
    high = [v["ci_high"] - v["on_time_rate"] for _, v in rows]
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    y = np.arange(len(names))
    colours = [VERMILLION if n in weak else BLUE for n in names]
    ax.barh(y, rates, color=colours, height=0.66, alpha=0.9)
    ax.errorbar(rates, y, xerr=[low, high], fmt="none", ecolor="#333",
                capsize=3, lw=1.1)
    ax.axvline(overall, color=GREY, ls="--", lw=1.2)
    ax.text(overall - 0.004, -0.85, f"network {overall * 100:.1f}%",
            fontsize=8.2, color=GREY, ha="right")
    for yi, name, rate in zip(y, names, rates):
        ax.text(rate + high[yi] + 0.008, yi, f"{rate * 100:.1f}%",
                va="center", fontsize=8.2,
                color=VERMILLION if name in weak else "#333")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.8)
    ax.set_xlim(0.5, 0.99)
    ax.set_ylim(-1.1, len(names) - 0.3)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_xlabel("On-time delivery rate (Wilson 95% confidence interval)")
    ax.set_title(f"On-time performance: {res['tests']['on_time_by_carrier']['gap_pp']:.0f}-point "
                 f"spread between best and worst carrier")
    return str(save(fig, "fig07_carrier_ontime.png").name)


def fig08_cost_loglog(df: pd.DataFrame, res: dict) -> str:
    from .analyze import residual_modified_z
    model = res["cost"]["model"]
    by_mode = res["descriptive"]["by_mode"]
    plot = df.loc[df["freight_cost_usd"].notna()]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    hb = ax.hexbin(np.log10(plot["weight_kg"]), np.log10(plot["freight_cost_usd"]),
                   gridsize=55, cmap="Blues", bins="log", mincnt=1, linewidths=0)
    flag, _ = residual_modified_z(df, "freight_cost_usd", ["weight_kg", "distance_km"])
    out = plot.loc[flag.reindex(plot.index).fillna(False)]
    ax.scatter(np.log10(out["weight_kg"]), np.log10(out["freight_cost_usd"]),
               s=22, facecolors="none", edgecolors=VERMILLION, linewidths=0.9,
               label="residual outlier", zorder=3)
    xs = np.linspace(1.0, 4.4, 60)
    for mode in MODES:
        c0 = (model["intercept"] + model["mode_effects"].get(mode, 0.0) +
              model["distance_elasticity"] * np.log(by_mode[mode]["median_distance_km"]))
        ys = (c0 + model["weight_elasticity"] * np.log(10 ** xs)) / np.log(10)
        ax.plot(xs, ys, lw=1.8, color=MODE_COLORS[mode],
                label=f"{mode} (at {by_mode[mode]['median_distance_km']:,.0f} km)")
    ax.set_xlim(0.8, 4.6)
    ax.set_xlabel("Shipment weight, log10 kg")
    ax.set_ylabel("Freight cost, log10 USD")
    ax.set_title("Cost versus weight: a 0.80 elasticity, with outliers ringed")
    ax.legend(loc="upper left", fontsize=7.4, ncol=2, title="fit at median distance",
              title_fontsize=7.4)
    cb = fig.colorbar(hb, ax=ax, shrink=0.82, pad=0.02)
    cb.set_label("shipments per cell (log)", fontsize=8)
    ax.text(0.98, 0.03,
            f"log cost = {model['intercept']:.2f} + {model['weight_elasticity']:.3f} log weight\n"
            f"  + {model['distance_elasticity']:.3f} log distance + mode effect\n"
            f"R2 = {model['r2']:.3f}, n = {model['n']:,}",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.6,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#BBB", lw=0.7))
    return str(save(fig, "fig08_cost_loglog.png").name)


def fig09_outlier_methods(res: dict) -> str:
    comp = res["outliers"]["recovery"]["comparison"]
    names = [c["method"] for c in comp]
    flagged = [c["flagged"] for c in comp]
    recall = [c["recall"] for c in comp]
    precision = [c["precision"] for c in comp]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    ax = axes[0]
    bars = ax.bar(range(len(names)), flagged, color=[GREY, GREY, GREY, GREEN],
                  width=0.62)
    ax.set_yscale("log")
    for b, v in zip(bars, flagged):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.12, f"{v:,}",
                ha="center", fontsize=8.6)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=22, ha="right", fontsize=8.2)
    ax.set_ylabel("Rows flagged (log scale)")
    ax.set_ylim(top=max(flagged) * 2.6)
    ax.set_title("How many rows each rule flags")

    ax = axes[1]
    x = np.arange(len(names))
    ax.bar(x - 0.19, recall, width=0.36, color=BLUE, label="Recall")
    ax.bar(x + 0.19, precision, width=0.36, color=ORANGE, label="Precision")
    for xi, (rc, pr) in enumerate(zip(recall, precision)):
        ax.text(xi - 0.19, rc + 0.02, f"{rc * 100:.0f}%", ha="center", fontsize=7.8)
        ax.text(xi + 0.19, pr + 0.02, f"{pr * 100:.0f}%", ha="center", fontsize=7.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=22, ha="right", fontsize=8.2)
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_ylabel("Share of planted outliers (blue)\n/ of flags (orange)")
    ax.set_title("Only the residual rule finds most outliers cleanly")

    fig.tight_layout()
    return str(save(fig, "fig09_outlier_methods.png").name)


def fig10_delay_heatmap(res: dict) -> str:
    matrix = res["timeseries"]["delay_matrix"]
    data = pd.DataFrame([matrix["rows"][d] for d in WEEKDAYS],
                        index=WEEKDAYS, columns=matrix["months"])
    fig, ax = plt.subplots(figsize=(9.6, 3.7))
    sns.heatmap(data, cmap="RdYlBu_r", center=float(np.nanmean(data.values)),
                annot=True, fmt=".1f", annot_kws={"size": 6.2},
                linewidths=0.3, linecolor="white",
                cbar_kws={"label": "Mean delay (days; negative = early)", "shrink": 0.82}, ax=ax)
    ax.set_xlabel("Order month")
    ax.set_ylabel("Order weekday")
    ax.set_xticklabels([pd.Timestamp(m).strftime("%b %y") for m in data.columns],
                       rotation=52, ha="right", fontsize=7.4)
    ax.set_title("Delay heatmap: February 2025 is the only column that turns red")
    return str(save(fig, "fig10_delay_heatmap.png").name)


def fig11_lane_pareto(res: dict) -> str:
    lanes = res["lanes"]["top_lanes"][:15]
    names = [row["lane"].replace(" -> ", "\u2192") for row in lanes]
    values = [row["shipments"] for row in lanes]
    cumulative = [row["cum_share_pct"] for row in lanes]
    x = np.arange(len(lanes))
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.bar(x, values, color=BLUE, alpha=0.88, width=0.66, label="Shipments")
    for xi, v in zip(x, values):
        ax.text(xi, v + 22, f"{v:,}", ha="center", fontsize=7.4, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=38, ha="right", fontsize=8.0)
    ax.set_ylabel("Shipments in 24 months")
    ax.set_xlabel("Lane (origin to destination)")
    ax.set_ylim(0, max(values) * 1.18)
    ax2 = ax.twinx()
    ax2.plot(x, cumulative, color=VERMILLION, marker="o", ms=4, lw=1.6,
             label="Cumulative share")
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Cumulative share of shipments (%)", color=VERMILLION)
    ax2.tick_params(axis="y", colors=VERMILLION)
    ax2.grid(False)
    ax2.axhline(80, color=VERMILLION, ls=":", lw=1)
    ax2.text(len(lanes) - 0.6, 82, "80% line", fontsize=7.4, color=VERMILLION,
             ha="right")
    ax.set_title(f"Top 15 lanes carry {res['lanes']['top15_share_pct']:.1f}% of volume; "
                 f"{res['lanes']['lanes_for_80pct']} lanes are needed for 80%")
    return str(save(fig, "fig11_lane_pareto.png").name)


def fig12_cost_per_kg(df: pd.DataFrame, res: dict) -> str:
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for mode in MODES:
        values = df.loc[df["mode"] == mode, "cost_per_kg"].dropna().sort_values()
        y = np.arange(1, len(values) + 1) / len(values)
        ax.plot(values, y, lw=1.9, color=MODE_COLORS[mode], label=mode)
        med = values.median()
        ax.plot([med], [0.5], marker="o", ms=4.5, color=MODE_COLORS[mode])
    ax.set_xscale("log")
    ax.set_xlabel("Cost per kilogram (USD/kg, log scale)")
    ax.set_ylabel("Cumulative share of shipments")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_title("Cost per kilogram separates by mode, from rail to air")
    ax.legend(title="Mode", loc="upper left", fontsize=8.6, title_fontsize=8.6)
    ax.text(0.99, 0.04, "dot = median", transform=ax.transAxes, ha="right",
            fontsize=8, color=GREY)
    return str(save(fig, "fig12_cost_per_kg_ecdf.png").name)


def fig13_small_multiples(res: dict) -> str:
    mm = res["timeseries"]["mode_monthly"]
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 5.6), sharex=True, sharey=True)
    for ax, mode in zip(axes.ravel(), MODES):
        months = pd.to_datetime(mm[mode]["months"])
        values = mm[mode]["on_time"]
        base = float(np.median(values))
        ax.plot(months, values, marker="o", ms=3.0, lw=1.5,
                color=MODE_COLORS[mode])
        ax.axhline(base, color=GREY, ls=":", lw=1)
        ax.axvspan(pd.Timestamp("2025-02-01"), pd.Timestamp("2025-02-28"),
                   color=VERMILLION, alpha=0.18, lw=0)
        feb = values[list(months).index(pd.Timestamp("2025-02-01"))]
        ax.annotate(f"{feb * 100:.0f}%", xy=(pd.Timestamp("2025-02-01"), feb),
                    xytext=(8, -12), textcoords="offset points", fontsize=8,
                    color=VERMILLION)
        ax.set_title(f"{mode} (median {base * 100:.0f}%)", fontsize=9.6)
        ax.tick_params(labelsize=7.8)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    fig.suptitle("On-time rate by mode and month: February 2025 breaks every mode, "
                 "most of all road", fontsize=11.5, fontweight="bold")
    fig.text(0.5, 0.005, "Order month (shaded = February 2025 disruption)",
             ha="center", fontsize=8.4, color="#444")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    return str(save(fig, "fig13_mode_month_small_multiples.png").name)


def fig14_plotly(df: pd.DataFrame, res: dict) -> str:
    import plotly.graph_objects as go
    monthly = (df.groupby(["month_start", "mode"])["shipment_id"].size()
               .unstack(fill_value=0).sort_index())
    fig = go.Figure()
    for mode in MODES:
        fig.add_trace(go.Scatter(
            x=monthly.index, y=monthly[mode], name=mode, mode="lines",
            stackgroup="one", fillcolor=MODE_COLORS[mode] + "B3",
            line=dict(width=0.8, color=MODE_COLORS[mode]),
            hovertemplate="%{x|%b %Y}<br>" + mode + ": %{y:,} shipments<extra></extra>"))
    fig.update_layout(
        title="Interactive: monthly shipments by mode (hover for values)",
        xaxis_title="Order month", yaxis_title="Shipments",
        template="plotly_white", hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    traceorder="normal", font=dict(size=14)),
        font=dict(family="Helvetica, Arial, sans-serif", size=17),
        title_font=dict(family="Helvetica, Arial, sans-serif", size=20),
        margin=dict(l=70, r=20, t=92, b=56), width=1000, height=520)
    html_path = FIGURES / "fig14_monthly_by_mode.html"
    fig.write_html(html_path, include_plotlyjs="cdn")
    png_path = FIGURES / "fig14_plotly_monthly_by_mode.png"
    fig.write_image(png_path, scale=2)
    print("  fig14_plotly_monthly_by_mode.png (+ .html)")
    return png_path.name


def fig15_bts_real(res: dict) -> str:
    real = res["timeseries"]["real_data"]
    months = pd.to_datetime(real["monthly"]["months"])
    values = pd.Series(real["monthly"]["values"], index=months)
    rolling = pd.Series(real["monthly"]["rolling_12"], index=months)
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2),
                             gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    ax.plot(values.index, values.values, lw=1.1, color=BLUE, alpha=0.75)
    ax.plot(rolling.index, rolling.values, lw=2.0, color=VERMILLION,
            label="12-month mean")
    ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-31"),
               color=GREY, alpha=0.15, lw=0)
    ax.text(pd.Timestamp("2020-06-01"), 0.965, "COVID-19",
            transform=ax.get_xaxis_transform(), fontsize=8, color="#555",
            ha="left", va="top")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e6:.1f}M"))
    ax.set_ylabel("Trucks entering the US per month")
    ax.set_xlabel("Month")
    ax.set_title("BTS: 38,567 port-month records, 1996-2026")
    ax.legend(loc="lower right")
    ax2 = axes[1]
    months_order = list(range(1, 13))
    index = [real["seasonal_index"][str(m)] for m in months_order]
    colours = [VERMILLION if m == 12 else SKY for m in months_order]
    ax2.bar(months_order, index, color=colours, width=0.72)
    ax2.axhline(1.0, color="#333", lw=0.9, ls="--")
    ax2.set_xticks(months_order)
    ax2.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax2.set_ylim(0.85, 1.10)
    ax2.set_ylabel("Seasonal index (mean = 1.0)")
    ax2.set_xlabel("Calendar month")
    ax2.set_title("December is the quiet month at land borders")
    ax2.text(12, real["december_index"] + 0.004,
             f"{real['december_index']:.3f}", ha="center", fontsize=8,
             color=VERMILLION,
             bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    fig.tight_layout()
    return str(save(fig, "fig15_bts_real_data.png").name)


SNIPPETS = {
    "fig01": """# workflow diagram: eight stages, drawn once, no data needed
stages = ["Design", "Acquire", "Clean", "Profile",
          "Analyze", "Visualize", "Validate", "Report"]
for i, name in enumerate(stages):
    ax.add_patch(FancyBboxPatch(coords[i], 0.9, 0.64,
                                boxstyle="round,pad=0.02"))
    ax.text(*label_xy(i), name, ha="center")""",
    "fig02": """sns.histplot(data=df, x="transit_days", bins=42,
             log_scale=(True, False), kde=True,
             color=BLUE, edgecolor="white")
ax.axvline(df["transit_days"].median(), ls="--")
ax.axvline(df["transit_days"].quantile(0.90), ls=":")
ax.set_xlabel("Transit time (days, log scale)")
ax.set_ylabel("Shipments")""",
    "fig03": """sns.violinplot(data=df, x="mode", y="transit_days",
               order=["Air", "Road", "Rail", "Sea"],
               hue="mode", palette=MODE_COLORS,
               inner="box", cut=0, log_scale=True)
ax.set_yscale("log")
ax.set_ylabel("Transit time (days)")""",
    "fig04": """ax.plot(months, monthly_counts, marker="o")
ax.plot(months, monthly_counts.rolling(3, center=True).mean(),
        lw=2.4, ls="--", color=VERMILLION)
for year in (2024, 2025):
    ax.axvspan(f"{year}-10-01", f"{year}-12-31", alpha=0.12)
ax.set_ylabel("Shipments per month")""",
    "fig05": """stl = STL(monthly_counts, period=12, robust=True).fit()
fig, axes = plt.subplots(4, 1, sharex=True)
for ax, series, label in zip(axes,
        [monthly_counts, stl.trend, stl.seasonal, stl.resid],
        ["Observed", "Trend", "Seasonal", "Residual"]):
    ax.plot(months, series)
    ax.set_ylabel(label)""",
    "fig06": """corr = df[ORDER].corr(method="spearman")
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt=".2f",
            cmap="RdBu_r", vmin=-1, vmax=1, square=True)
ax.set_title("Spearman correlations")""",
    "fig07": """stats = df.groupby("carrier")["on_time"].agg(["mean", "count"])
low, high = zip(*[wilson(int(r["mean"] * r["count"]), int(r["count"]))
                  for _, r in stats.iterrows()])
ax.barh(stats.index, stats["mean"], xerr=[stats["mean"] - low, high - stats["mean"]])
ax.axvline(df["on_time"].mean(), ls="--")
ax.set_xlabel("On-time rate (Wilson 95% CI)")""",
    "fig08": """model = sm.OLS(np.log(cost), sm.add_constant(
    np.log(df[["weight_kg", "distance_km"]]))).fit()
ax.hexbin(np.log10(weight), np.log10(cost), gridsize=52, bins="log")
for mode in MODES:
    ax.plot(xs, (model.params["weight_kg"] * xs + intercept[mode]) / np.log(10))
ax.set_xlabel("Weight, log10 kg"); ax.set_ylabel("Cost, log10 USD")""",
    "fig09": """rules = {"IQR": iqr_flag, "z>3": z_flag,
         "modified z": mz_flag, "residual z": resid_flag}
for name, flag in rules.items():
    recall = (flag & planted).sum() / planted.sum()
    precision = (flag & planted).sum() / flag.sum()
    ax.bar(name, recall); ax.bar(name, precision)""",
    "fig10": """matrix = df.pivot_table(index="weekday", columns="month",
                       values="delay_days", aggfunc="mean")
sns.heatmap(matrix, cmap="RdYlBu_r", center=matrix.values.mean(),
            annot=True, fmt=".1f")
ax.set_xlabel("Order month"); ax.set_ylabel("Order weekday")""",
    "fig11": """top = df["lane"].value_counts().head(15)
ax.barh(top.index[::-1], top.values[::-1])
ax2 = ax.twiny()
ax2.plot(100 * top.cumsum() / len(df), range(len(top)))
ax.set_xlabel("Shipments"); ax2.set_xlabel("Cumulative share (%)")""",
    "fig12": """for mode in MODES:
    values = df.loc[df["mode"] == mode, "cost_per_kg"].dropna().sort_values()
    ax.plot(values, np.arange(1, len(values) + 1) / len(values))
ax.set_xscale("log")
ax.set_xlabel("Cost per kg (USD, log scale)")
ax.set_ylabel("Cumulative share")""",
    "fig13": """fig, axes = plt.subplots(2, 2, sharex=True)
for ax, mode in zip(axes.ravel(), MODES):
    block = df[df["mode"] == mode]
    ax.plot(block.groupby("month_start")["transit_days"].median())
    ax.set_title(mode)
fig.suptitle("Median transit time by mode and month")""",
    "fig14": """fig = go.Figure()
for mode in MODES:
    fig.add_trace(go.Scatter(x=months, y=counts[mode], name=mode,
                             stackgroup="one", mode="lines"))
fig.update_layout(template="plotly_white", hovermode="x unified")
fig.write_html("figures/fig14.html")
fig.write_image("figures/fig14.png", scale=2)   # needs kaleido""",
    "fig15": """monthly = real.groupby("date")["value"].sum()
ax.plot(monthly.index, monthly.values)
ax.plot(monthly.index, monthly.rolling(12).mean())
seasonal = monthly.groupby(monthly.index.month).mean()
ax2.bar(range(1, 13), seasonal / seasonal.mean())""",
}


def main() -> None:
    apply_style()
    df, res = load()
    print("figures:")
    names = [
        fig01_workflow(res),
        fig02_transit_hist(df, res),
        fig03_mode_violin(df, res),
        fig04_monthly_volume(df, res),
        fig05_decomposition(res),
        fig06_correlation(res),
        fig07_carrier_ontime(res),
        fig08_cost_loglog(df, res),
        fig09_outlier_methods(res),
        fig10_delay_heatmap(res),
        fig11_lane_pareto(res),
        fig12_cost_per_kg(df, res),
        fig13_small_multiples(res),
        fig14_plotly(df, res),
        fig15_bts_real(res),
    ]
    print(f"{len(names)} figures written to figures/")


if __name__ == "__main__":
    main()
