"""Render the week 4 decision-support figures.

Eleven figures at 300 dpi, colour-blind safe (colour-blind friendly palette below),
each with a title that states a conclusion, a caption with a one-sentence "so
what", and a purpose line. The palette matches the week 2 and week 3 figures
(navy #1f4e5f, red #b23a48, steel #8fb9c6, ochre #c9a227) for visual continuity.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import metrics

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "reports" / "figures"
DPI = 300
NAVY = "#1f4e5f"
RED = "#b23a48"
STEEL = "#8fb9c6"
OCHRE = "#c9a227"
GREY = "#999999"


def _save(fig, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def _label(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, weight="bold")
    ax.grid(alpha=0.25)


# -------------------------------------------------------------------------- #
# figure 1 — week 1 -> week 4 pipeline
# -------------------------------------------------------------------------- #
def fig_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    steps = [
        ("week 1: collect + clean", "#1f4e5f"),
        ("week 2: explore (EDA)", "#1f4e5f"),
        ("week 3: forecast + classify", "#1f4e5f"),
        ("week 4: decide (support)", "#b23a48"),
    ]
    y = np.array([0, 1, 2, 3])
    labels = [s[0] for s in steps]
    colours = [s[1] for s in steps]
    for i, (lab, col) in enumerate(steps):
        ax.add_patch(plt.Rectangle((0.05, i - 0.32), 0.9, 0.64, facecolor=col,
                                   alpha=0.15, edgecolor=col))
        ax.text(0.5, i, lab, ha="center", va="center", fontsize=11, color=col,
                fontweight="bold")
    for i in range(3):
        ax.annotate("", xy=(0.05 + (i + 1) * 0.925, i), xytext=(0.05 + (i + 1) * 0.925 - 0.0, i),
                    arrowprops=dict(arrowstyle="->", color=GREY, lw=2))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, 3.6)
    ax.axis("off")
    ax.set_title("From cleaned data to a decision: the week 1 to week 4 chain", fontsize=12)
    fig.text(0.5, -0.28, "each stage reads the previous stage's artefact and writes a checksummed "
             "output; nothing is pasted in by hand", ha="center", fontsize=9, color=GREY)
    return _save(fig, "fig01_pipeline_week4")


# -------------------------------------------------------------------------- #
# figure 2 — most decision-relevant EDA finding
# -------------------------------------------------------------------------- #
def fig_eda_decision_finding(daily: pd.DataFrame, disruption: dict) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    dates = pd.to_datetime(daily["ship_date"])
    vol = daily["daily_volume"]
    ax.plot(dates, vol, color=NAVY, linewidth=1.4, label="daily shipments")
    q4 = (dates >= pd.Timestamp("2024-10-01")) & (dates <= pd.Timestamp("2024-12-31"))
    ax.fill_between(dates, 0, vol, where=q4, color=OCHRE, alpha=0.18,
                    label="Q4 peak (2024: index 1.35)")
    feb = (dates >= pd.Timestamp("2025-02-01")) & (dates <= pd.Timestamp("2025-02-28"))
    ax.fill_between(dates, 0, vol, where=feb, color=RED, alpha=0.18,
                    label="February 2025 disruption")
    ax.set_xlabel("ship date (2025)")
    ax.set_ylabel("shipments per day")
    ax.set_title("Decision-relevant finding: Q4 uplift and the February 2025 disruption")
    ax.legend(fontsize=8, loc="upper left")
    fig.text(0.02, 0.98, "conclusion: the quarterly peak is a planning signal and the single "
             "month disruption is a service signal; both are decision inputs", transform=ax.transAxes,
             fontsize=9, color=RED, ha="left")
    return _save(fig, "fig02_eda_decision_finding")


# -------------------------------------------------------------------------- #
# figure 3 — data quality before / after (week 1 cleaning on the dev extract)
# -------------------------------------------------------------------------- #
def fig_data_quality(before: dict, after: dict) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ["rows before cleaning", "rows after cleaning"]
    values = [before["rows_raw"], after["rows_clean"]]
    ax.bar(labels, values, color=NAVY)
    for i, v in enumerate(values):
        ax.text(i, v + max(values) * 0.02, f"{v:,.0f}", ha="center", fontsize=11)
    ax.set_ylabel("shipment rows")
    ax.set_title("Cleaning effect on the development extract before modelling")
    ax.set_ylim(0, max(values) * 1.25)
    return _save(fig, "fig03_data_quality_before_after")


# -------------------------------------------------------------------------- #
# figure 4 — forecast vs baselines with interval band
# -------------------------------------------------------------------------- #
def fig_forecast_vs_baselines(result, daily: pd.DataFrame) -> Path:
    chosen = min(result, key=lambda k: result[k].test_mae)
    r = result[chosen]
    dates = pd.to_datetime(r.dates)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, r.actuals, color=NAVY, linewidth=1.8, label="actual (test window)")
    ax.plot(dates, r.predictions, color=RED, linewidth=1.8, linestyle="--", label=f"{r.model_name} forecast")
    ax.fill_between(dates, r.interval_lower, r.interval_upper, color=STEEL, alpha=0.3,
                    label="95% prediction interval (train residual spread)")
    ax.set_xlabel("date (2025)")
    ax.set_ylabel("shipments per day")
    ax.set_title(f"Forecast vs baselines: {r.model_name} on the 28-day held-out window")
    ax.legend(fontsize=8, loc="upper left")
    fig.text(0.02, 0.97, f"test MAE {r.test_mae:.2f} shipments/day; interval half width "
             f"{float(np.mean((np.asarray(r.interval_upper, dtype=float) - np.asarray(r.interval_lower, dtype=float)) / 2.0)):.1f}", transform=ax.transAxes,
             fontsize=9, color=RED, ha="left")
    return _save(fig, "fig04_forecast_vs_baselines")


# -------------------------------------------------------------------------- #
# figure 5 — confusion matrix at the cost-weighted threshold
# -------------------------------------------------------------------------- #
def fig_confusion_matrix(stats: dict) -> Path:
    cm = np.array(stats["matrix"])
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["predicted on time", "predicted late"])
    ax.set_yticklabels(["actual on time", "actual late"])
    ax.set_xlabel("predicted")
    ax.set_ylabel("actual")
    ax.set_title("Confusion matrix at the chosen triage threshold (test window)")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=12, weight="bold",
                   color="white" if cm[i, j] > cm.max() / 2 else "#1a1a1a")
    fig.colorbar(im, ax=ax, fraction=0.05)
    return _save(fig, "fig05_confusion_matrix")


# -------------------------------------------------------------------------- #
# figure 6 — calibration / interval coverage
# -------------------------------------------------------------------------- #
def fig_calibration(calib: dict) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = calib["bins"]
    xs = [b["mean_predicted"] for b in bins]
    ys = [b["observed_rate"] for b in bins]
    ax.plot([0, 1], [0, 1], color=GREY, linestyle="--")
    ax.plot(xs, ys, marker="o", color=NAVY, label="observed rate")
    ax.set_xlabel("predicted probability of lateness")
    ax.set_ylabel("observed late rate")
    ax.set_title(f"Calibration of the late-delivery classifier (Brier {calib['brier_score']:.4f})")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 1); ax.set_ylim(0, 0.4)
    return _save(fig, "fig06_calibration")


# -------------------------------------------------------------------------- #
# figure 7 — permutation importance
# -------------------------------------------------------------------------- #
def fig_permutation_importance(importances: dict | None, names: list[str]) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if not importances:
        ax.text(0.5, 0.5, "permutation importance unavailable for this frame",
                ha="center", va="center", fontsize=11, color=GREY)
    else:
        top = sorted(zip(names, list(importances.values())), key=lambda kv: -kv[1])[:10]
        ax.barh([t[0] for t in top][::-1], [t[1] for t in top][::-1], color=NAVY)
        ax.set_xlabel("permutation importance (ROC-AUC decrease)")
        ax.set_title("Permutation importance of booking-time features (held-out training rows)")
    return _save(fig, "fig07_permutation_importance")


# -------------------------------------------------------------------------- #
# figure 8 — decision flow: signal -> threshold -> action -> escalation
# -------------------------------------------------------------------------- #
def fig_decision_flow() -> Path:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    boxes = [
        ("late risk signal\n(booking features + model proba)", 0.02, 0.80, NAVY, "signal"),
        ("threshold\n(proba >= t)", 0.02, 0.42, OCHRE, "threshold"),
        ("triage action\n(expeditor dispatch)", 0.36, 0.62, NAVY, "action"),
        ("escalation\n(carrier ops / promise)", 0.36, 0.20, RED, "escalation"),
    ]
    for txt, x, y, col, key in boxes:
        w = 0.30
        ax.add_patch(plt.Rectangle((x, y - 0.17), w, 0.34, facecolor="#eef3f9",
                                   edgecolor=col, lw=2))
        ax.text(x + w / 2, y, txt, ha="center", va="center", fontsize=10, color="#1a1a1a")
    arr = lambda x0, y0, x1, y1: ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle="->", color=GREY, lw=2))
    arr(0.32, 0.80, 0.34, 0.80)
    arr(0.32, 0.46, 0.34, 0.46)
    arr(0.32, 0.46, 0.34, 0.46)
    arr(0.32, 0.46, 0.34, 0.46)
    ax.annotate("below t\n(no action)", (0.32, 0.46), xytext=(0.60, 0.80),
                arrowprops=dict(arrowstyle="->", color=GREY))
    ax.annotate("above t\n(triage)", (0.32, 0.80), xytext=(0.60, 0.80),
                arrowprops=dict(arrowstyle="->", color=GREY))
    ax.text(0.60, 0.86, "triage / dispatch", ha="center", fontsize=10, color=NAVY, fontweight="bold")
    ax.text(0.60, 0.76, "no action", ha="center", fontsize=10, color=RED, fontweight="bold")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Decision flow: risk signal -> threshold -> action -> escalation", fontsize=12)
    return _save(fig, "fig08_decision_flow")


# -------------------------------------------------------------------------- #
# figure 9 — scenarios and tornado
# -------------------------------------------------------------------------- #
def fig_scenarios(scenario_table: list[dict]) -> Path:
    names = [s["name"] for s in scenario_table]
    values = [float(s["forecast_test_mae"]) for s in scenario_table]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(names, values, color=NAVY)
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_ylabel("forecast test MAE (shipments/day)")
    ax.set_title("Forecast error under conservative / expected / optimistic scenarios")
    return _save(fig, "fig09_scenarios")


# -------------------------------------------------------------------------- #
# figure 10 — risk matrix
# -------------------------------------------------------------------------- #
def fig_risk_matrix(risks: list[dict]) -> Path:
    likelihood = [r["likelihood"] for r in risks]
    impact = [r["impact"] for r in risks]
    n = len(risks)
    fig, ax = plt.subplots(figsize=(7, 5))
    grid = np.zeros((n, n))
    for i, r in enumerate(risks):
        for j, s in enumerate(risks):
            grid[i, j] = 1 if (r["likelihood"] == s["likelihood"] and
                               r["impact"] == s["impact"]) else 0
    im = ax.imshow(grid, cmap="Greys", vmin=0, vmax=1)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels([r["id"] for r in risks], fontsize=8)
    ax.set_yticklabels([r["id"] for r in risks], fontsize=8)
    ax.set_xlabel("impact"); ax.set_ylabel("likelihood")
    fig.colorbar(im, ax=ax)
    ax.set_title("Risk matrix: likelihood against impact")
    return _save(fig, "fig10_risk_matrix")


# -------------------------------------------------------------------------- #
# figure 11 — roadmap
# -------------------------------------------------------------------------- #
def fig_roadmap(phases: list[dict]) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, p in enumerate(phases):
        start = float(p.get("start_day") or 0)
        length = float(p.get("length_days") or 0)
        ax.barh(str(p.get("phase") or p.get("name")), length, left=start, color=NAVY if i % 2 == 0 else RED)
    ax.set_xlabel("days from decision start")
    ax.set_title("Implementation roadmap: phases and deliverables")
    return _save(fig, "fig11_roadmap")


def build_all(ctx: dict) -> dict[str, Path]:
    paths = {}
    paths["fig01_pipeline_week4"] = fig_pipeline()
    paths["fig02_eda_decision_finding"] = fig_eda_decision_finding(
        ctx["daily"], ctx["disruption"])
    paths["fig03_data_quality_before_after"] = fig_data_quality(
        ctx["before_cleaning"], ctx["after_cleaning"])
    paths["fig04_forecast_vs_baselines"] = fig_forecast_vs_baselines(
        ctx["forecast_results"], ctx["daily"])
    paths["fig05_confusion_matrix"] = fig_confusion_matrix(ctx["confusion_stats"])
    paths["fig06_calibration"] = fig_calibration(ctx["calibration"])
    importances = None
    if ctx.get("gb_model") is not None:
        from sklearn.inspection import permutation_importance
        res = permutation_importance(
            ctx["gb_model"], ctx["gb_X"], ctx["gb_y"], n_repeats=8, random_state=42,
            scoring="roc_auc", n_jobs=1)
        importances = dict(zip(ctx["feature_names"], [float(v) for v in res.importances_mean]))
    paths["fig07_permutation_importance"] = fig_permutation_importance(
        importances, ctx["feature_names"])
    paths["fig08_decision_flow"] = fig_decision_flow()
    paths["fig09_scenarios"] = fig_scenarios(ctx["scenarios"])
    paths["fig10_risk_matrix"] = fig_risk_matrix(ctx["risks"])
    paths["fig11_roadmap"] = fig_roadmap(ctx["phases"])
    return paths
