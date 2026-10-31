"""Draw the diagrams used in the week 1 blueprint.

Everything is generated from code so the figures in the report can be rebuilt
from a clean checkout — a screenshot of a whiteboard is not reproducible.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
from PIL import Image, ImageChops

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

FIG_DIR = Path(__file__).resolve().parents[1] / "docs" / "figures"

INK = "#1f2933"
MUTED = "#5c6b7a"
PALETTE = {
    "discover": "#f2c14e",
    "acquire": "#4d9de0",
    "land": "#7b8fa1",
    "profile": "#8e7dbe",
    "clean": "#2a9d8f",
    "validate": "#e76f51",
    "publish": "#4c956c",
    "paper": "#fbfaf7",
}
FONT = "DejaVu Sans"


def _save(fig, out: Path) -> None:
    """Save, then trim the uniform border so the figure sits flush in Word."""
    fig.savefig(out, dpi=200, facecolor=PALETTE["paper"])
    image = Image.open(out).convert("RGB")
    background = Image.new("RGB", image.size, PALETTE["paper"])
    bbox = ImageChops.difference(image, background).getbbox()
    if bbox:
        pad = 40
        box = (
            max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(image.width, bbox[2] + pad), min(image.height, bbox[3] + pad),
        )
        image.crop(box).save(out, optimize=True)
    plt.close(fig)


def _setup(width: float, height: float):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(PALETTE["paper"])
    ax.set_facecolor(PALETTE["paper"])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10 * height / width)
    ax.axis("off")
    return fig, ax


def _box(ax, x, y, w, h, title, lines, colour, title_size=11, body_size=7.6):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.1, edgecolor=colour, facecolor=colour + "22", zorder=2,
    )
    ax.add_patch(patch)
    ax.add_patch(
        FancyBboxPatch(
            (x, y), 0.09, h,
            boxstyle="square,pad=0", linewidth=0, facecolor=colour, zorder=3,
        )
    )
    ax.text(x + 0.2, y + h - 0.2, title, ha="left", va="top",
            fontsize=title_size, fontweight="bold", color=INK, family=FONT, zorder=4)
    if lines:
        ax.text(x + 0.22, y + h - 0.45, "\n".join(lines), ha="left", va="top",
                fontsize=body_size, color=MUTED, family=FONT, linespacing=1.45, zorder=4)


def _arrow(ax, x1, y1, x2, y2, colour=MUTED):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
            linewidth=1.2, color=colour, shrinkA=0, shrinkB=0, zorder=1,
        )
    )


def _caption(ax, text, y, x=0.0):
    ax.text(x, y, text, ha="left", va="top", fontsize=7.4, color=MUTED,
            style="italic", family=FONT)


def figure_workflow() -> Path:
    """End-to-end: discovery to published table."""
    fig, ax = _setup(7.4, 9.6)
    stages = [
        ("1. Source discovery and licensing", [
            "Candidate register: BTS FAF, Comtrade, World Bank LPI,",
            "Eurostat, OpenStreetMap, operator APIs",
            "Gate: licence permits redistribution? personal data present?",
        ], PALETTE["discover"]),
        ("2. Acquisition", [
            "Scheduled pull (requests + retry/backoff) or bulk file download",
            "Raw response stored unmodified; nothing parsed at this step",
            "Record: URL, timestamp, checksum, licence snapshot",
        ], PALETTE["acquire"]),
        ("3. Landing zone", [
            "Immutable, partitioned by source and extraction date",
            "Read-only; every downstream file traces back to a checksum",
            "Re-runs replay from here rather than re-hitting the source",
        ], PALETTE["land"]),
        ("4. Profiling", [
            "Row/column counts, null share, cardinality, min/max",
            "Type inference proposals, schema drift vs previous extract",
            "Output: profiling note committed alongside the data",
        ], PALETTE["profile"]),
        ("5. Cleaning", [
            "Alias mapping, date parsing, unit and currency conversion",
            "Deduplication by shipment key, flagged imputation",
            "Every transform writes to the step log",
        ], PALETTE["clean"]),
        ("6. Validation", [
            "Declarative checks from config/schema.yml",
            "Critical failure blocks publish; warning is recorded",
            "Result: machine-readable check table, not a screenshot",
        ], PALETTE["validate"]),
        ("7. Curated output and documentation", [
            "Typed table + data dictionary + decision log",
            "Quality report regenerated on every run",
            "Publish only when the checks agree with the story",
        ], PALETTE["publish"]),
    ]

    top = 12.35
    h = 1.42
    gap = 0.26
    for i, (title, lines, colour) in enumerate(stages):
        y = top - (i + 1) * h - i * gap
        _box(ax, 0.15, y, 9.6, h, title, lines, colour)
        if i < len(stages) - 1:
            _arrow(ax, 5.0, y - 0.02, 5.0, y - gap - 0.01)

    _caption(ax, "Solid arrow = artefact handed forward. A stage may only read what the previous stage published.", 12.8)
    fig.tight_layout(pad=0.4)
    out = FIG_DIR / "fig1_workflow.png"
    _save(fig, out)
    return out


def figure_pipeline() -> Path:
    """The cleaning stage in detail, with the library doing the work."""
    fig, ax = _setup(11.2, 8.5)  # ylim = 7.6 at this aspect ratio
    steps = [
        ("Trim and type", ["str.strip()", "astype('string')", "drop empty keys"], PALETTE["land"]),
        ("Alias mapping", ["country/mode/category", "dict lookups", "unmapped -> null + log"], PALETTE["profile"]),
        ("Parse dates", ["explicit format list", "errors='coerce'", "ordering rules"], PALETTE["profile"]),
        ("Measures", ["lb -> kg exact", "money parser", "FX snapshot"], PALETTE["acquire"]),
        ("Deduplicate", ["exact dupes dropped", "latest state per key", "grain asserted"], PALETTE["discover"]),
        ("Impute", ["grouped median", "rate-based cost", "boolean flags"], PALETTE["clean"]),
        ("Bound", ["winsorise p1/p99", "domain caps", "transit features"], PALETTE["clean"]),
        ("Emit", ["schema dtypes", "column order", "curated csv + hash"], PALETTE["publish"]),
    ]
    w, h = 2.16, 1.32
    xs = [0.2 + i * 2.42 for i in range(4)]
    ys = [5.45, 3.25]
    for i, (title, lines, colour) in enumerate(steps):
        col, row = i % 4, i // 4
        _box(ax, xs[col], ys[row], w, h, title, lines, colour, title_size=9.6, body_size=7.0)
        if col < 3:
            _arrow(ax, xs[col] + w + 0.02, ys[row] + h / 2, xs[col + 1] - 0.03, ys[row] + h / 2)

    # snake connector: end of row 1 wraps down and back to the start of row 2
    x_tail = xs[3] + w / 2
    x_head = xs[0] + w / 2
    ax.plot([x_tail, x_tail], [ys[0], 4.95], color=MUTED, linewidth=1.2)
    ax.plot([x_tail, x_head], [4.95, 4.95], color=MUTED, linewidth=1.2)
    _arrow(ax, x_head, 4.96, x_head, ys[1] + h + 0.03)

    ax.text(0.2, 7.5, "Cleaning pipeline, stage by stage", fontsize=13, fontweight="bold",
            color=INK, family=FONT)
    _caption(ax, "Each stage returns a frame plus a log entry. Nothing is mutated in place between run 1 and run 2.", 7.32)
    ax.text(0.2, 2.0, "Guardrails", fontsize=9.6, fontweight="bold", color=INK, family=FONT)
    ax.text(
        0.2, 1.6,
        "row counts asserted at every hop  \u00b7  imputed rows flagged, never silent  \u00b7  "
        "rejected values kept in the raw layer  \u00b7  pinned dependencies and pinned FX snapshot",
        fontsize=7.6, color=MUTED, family=FONT,
    )
    fig.tight_layout(pad=0.4)
    out = FIG_DIR / "fig2_pipeline.png"
    _save(fig, out)
    return out


def figure_missingness() -> Path:
    """Decision tree for the missing-data strategy."""
    fig, ax = _setup(7.6, 8.4)  # ylim = 11.05
    ax.text(0.15, 10.75, "Missing-value decision path", fontsize=13, fontweight="bold", color=INK, family=FONT)
    _caption(ax, "Applied per column, per run. The classification question comes before the method question.", 10.4)

    _box(ax, 0.15, 9.05, 9.5, 1.05, "Value is null in the landed extract",
         ["Count the share, check whether the null is a code (999, -1, 'n/a') wearing a costume"], PALETTE["land"], title_size=9.6)

    _box(ax, 1.2, 7.1, 7.6, 1.35, "Is the column required?",
         ["key, date, currency or unit: reject the row, record why, move on",
          "measure such as weight or cost: classify the mechanism below"],
         PALETTE["profile"], title_size=9.4)
    _arrow(ax, 4.9, 9.03, 4.9, 8.5)

    # junction bar: one arrow down, then out to each mechanism
    ax.plot([4.9, 4.9], [7.08, 6.6], color=MUTED, linewidth=1.2)
    ax.plot([1.65, 8.15], [6.6, 6.6], color=MUTED, linewidth=1.2)

    branches = [
        ("MCAR", ["missingness independent of other", "variables"], "drop rows if <1%, else median by", PALETTE["clean"]),
        ("MAR", ["missingness explained by observed", "features (mode, lane, weight)"], "grouped median or model-based fill", PALETTE["acquire"]),
        ("MNAR", ["the absence is the signal", "(unbilled, not weighed, cancelled)"], "impute + indicator column, or keep", PALETTE["validate"]),
    ]
    xs = [0.15, 3.4, 6.65]
    for i, (label, clue, action, colour) in enumerate(branches):
        x = xs[i]
        _box(ax, x, 4.75, 3.0, 1.6, label, clue + ["", action], colour, title_size=10.2, body_size=7.2)
        _arrow(ax, x + 1.5, 6.6, x + 1.5, 6.4)

    _box(ax, 0.15, 2.0, 9.5, 1.55, "Always, regardless of branch",
         ["1. write a boolean indicator column so downstream models can use the fact of imputation",
          "2. log the method, the grouped statistic and the row count in the run report",
          "3. re-run validation after imputation \u2014 imputation must not push values outside domain bounds"],
         PALETTE["publish"], title_size=9.6)

    _box(ax, 0.15, 0.45, 9.5, 1.05, "Never",
         ["silently fill with zero  \u00b7  forward-fill across shipments  \u00b7  impute a key column  \u00b7  impute before deduplication"],
         PALETTE["validate"], title_size=9.6)
    fig.tight_layout(pad=0.4)
    out = FIG_DIR / "fig3_missingness.png"
    _save(fig, out)
    return out


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (figure_workflow, figure_pipeline, figure_missingness):
        print("wrote", fn().name)


if __name__ == "__main__":
    main()
