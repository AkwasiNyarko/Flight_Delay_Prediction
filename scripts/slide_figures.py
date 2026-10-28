"""Presentation charts drawn from the exported dashboard data (docs/data/*.json).

    python scripts/slide_figures.py   -> reports/slides/*.png
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "reports" / "slides"
NAVY, BLUE, AMBER, GREY, MUTED, GRID = "#0F1B2D", "#2F6FED", "#F5A524", "#AEB6C2", "#566173", "#E6EAF0"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 17, "axes.edgecolor": GREY, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 21, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left",
    "axes.titlepad": 14, "figure.dpi": 100, "savefig.dpi": 200,
})


def load(name):
    return json.loads((DATA / name).read_text())


def tally(explore, dim):
    out = {}
    for _, _, v, n, late in explore["dims"][dim]["rows"]:
        a = out.setdefault(v, [0, 0]); a[0] += n; a[1] += late
    keys = sorted(out)
    return keys, np.array([out[k][1] / out[k][0] for k in keys])


def pct_axis(ax, top):
    ax.set_ylim(0, top)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)


def hour_month(explore, overall):
    fig, (a, b) = plt.subplots(1, 2, figsize=(16, 5.6), gridspec_kw={"width_ratios": [1.45, 1]})
    hours, hr = tally(explore, "hour")
    colors = [AMBER if r >= 0.30 else BLUE for r in hr]
    a.bar(hours, hr, color=colors, width=0.78)
    a.axhline(overall, color=NAVY, ls="--", lw=1.4)
    a.text(hours[0] - 0.4, overall + 0.012, f"average {overall:.0%}", color=NAVY, fontsize=15)
    a.set_xticks([h for h in hours if h % 3 == 0], [f"{h:02d}:00" for h in hours if h % 3 == 0])
    a.set_title("By scheduled departure hour")
    pct_axis(a, 0.5)
    months, mr = tally(explore, "month")
    b.bar([MONTHS[m - 1] for m in months], mr, color=[AMBER if r >= 0.28 else BLUE for r in mr], width=0.72)
    b.axhline(overall, color=NAVY, ls="--", lw=1.4)
    b.set_title("By month"); pct_axis(b, 0.5)
    b.tick_params(axis="x", labelsize=14)
    fig.tight_layout(); fig.savefig(OUT / "hour_month.png"); plt.close(fig)


def airlines(explore, lookup, overall, min_flights=5000):
    by = {}
    for _, c, _, n, late in explore["dims"]["month"]["rows"]:
        a = by.setdefault(explore["carriers"][c], [0, 0]); a[0] += n; a[1] += late
    rows = sorted([(k, v[1] / v[0], v[0]) for k, v in by.items() if v[0] >= min_flights], key=lambda r: r[1])
    names = [lookup["carriers"][k].replace(" Inc.", "").replace(" Co.", "").replace(" Air Lines", "") for k, _, _ in rows]
    fig, ax = plt.subplots(figsize=(9, 6.6))
    bars = ax.barh(names, [r[1] for r in rows], color=[AMBER if r[1] >= 0.30 else BLUE for r in rows], height=0.68)
    for bar, r in zip(bars, rows):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2, f"{r[1]:.0%}", va="center", color=NAVY, fontsize=15)
    ax.axvline(overall, color=NAVY, ls="--", lw=1.4)
    ax.set_xlim(0, 0.4); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_title(f"By airline ({min_flights:,}+ departures)")
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT / "airlines.png"); plt.close(fig)


def roc(summary):
    auc = {r["model"]: r["roc_auc"] for r in summary["results"]}
    fig, ax = plt.subplots(figsize=(8, 7))
    styles = {"XGBoost": (BLUE, 3.2), "Random Forest": (AMBER, 2.4), "Logistic Regression": (GREY, 2.4)}
    for name, (c, lw) in styles.items():
        ax.plot(summary["roc"]["fpr"], summary["roc"]["curves"][name], color=c, lw=lw, label=f"{name}  AUC {auc[name]:.3f}")
    ax.plot([0, 1], [0, 1], "--", color=NAVY, lw=1.2, label="Random guessing  AUC 0.500")
    ax.set_xlabel("False-alarm rate (on-time flights flagged)"); ax.set_ylabel("Share of delays caught")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.0); ax.grid(color=GRID); ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False, fontsize=15)
    ax.set_title("ROC curves on 129,802 unseen flights" if summary["dataset"]["test"] == 129802 else "ROC curves on unseen flights")
    fig.tight_layout(); fig.savefig(OUT / "roc.png"); plt.close(fig)


def importance(summary, top=8):
    imp = summary["importance"][:top][::-1]
    fig, ax = plt.subplots(figsize=(9, 6.6))
    vals = [d["value"] for d in imp]
    bars = ax.barh([d["label"] for d in imp], vals, color=[BLUE if v >= 0.015 else GREY for v in vals], height=0.66)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + 0.0006, bar.get_y() + bar.get_height() / 2, f"{v:.3f}", va="center", color=NAVY, fontsize=15)
    ax.set_xlim(0, max(vals) * 1.22)
    ax.set_xlabel("Drop in ROC-AUC when the input is shuffled")
    ax.set_title("What the model relies on")
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(OUT / "importance.png"); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s, e, l = load("summary.json"), load("explore.json"), load("lookup.json")
    overall = s["dataset"]["delay_rate"]
    hour_month(e, overall); airlines(e, l, overall); roc(s); importance(s)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
