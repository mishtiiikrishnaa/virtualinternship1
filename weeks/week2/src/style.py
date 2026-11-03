"""Shared plotting style: one palette, one set of rcParams, one save helper."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"

# Okabe-Ito colour-blind-safe palette
BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
SKY = "#56B4E9"
YELLOW = "#F0E442"
GREY = "#8C8C8C"

MODE_COLORS = {"Air": SKY, "Road": BLUE, "Rail": GREEN, "Sea": VERMILLION}
SERIES = [BLUE, ORANGE, GREEN, VERMILLION, PURPLE, SKY]

DPI = 200


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.labelcolor": "#222222",
        "axes.edgecolor": "#444444",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#D9D9D9",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.7,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "figure.dpi": 110,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.18,
    })


def save(fig, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    print(f"  {name}")
    return path


def annotate(ax, text: str, xy: tuple[float, float], color: str = "#333333",
             **kwargs) -> None:
    ax.annotate(text, xy=xy, fontsize=8.5, color=color,
                bbox=dict(boxstyle="round,pad=0.28", fc="white", ec=color, lw=0.7),
                **kwargs)
