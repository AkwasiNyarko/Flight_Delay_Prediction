"""Static report figures (used in the README and slides)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

BLUE, ORANGE, GREY = "#2563eb", "#ea580c", "#6b7280"


def _clean(ax):
    ax.spines[["top", "right"]].set_visible(False)


def eda(df, out):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    by_hour = df.groupby("sched_dep_hour")["delayed"].mean() * 100
    axes[0].bar(by_hour.index, by_hour.values, color=BLUE)
    axes[0].set(title="Delay rate by scheduled hour", xlabel="Hour of day", ylabel="% delayed 15+ min")
    by_month = df.groupby("month")["delayed"].mean() * 100
    axes[1].bar(by_month.index, by_month.values, color=BLUE)
    axes[1].set(title="Delay rate by month", xlabel="Month", ylabel="% delayed", xticks=range(1, 13))
    by_carrier = (df.groupby("carrier")["delayed"].mean() * 100).sort_values()
    axes[2].barh(by_carrier.index, by_carrier.values, color=BLUE)
    axes[2].set(title="Delay rate by airline", xlabel="% delayed")
    for ax in axes:
        _clean(ax)
    plt.tight_layout(); plt.savefig(out / "01_eda_delay_patterns.png", dpi=150); plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    vis = df.assign(v=pd.cut(df["visib"], [-0.1, 1, 3, 5, 9.9, 10])).groupby("v", observed=False)["delayed"].mean() * 100
    axes[0].bar(["<1", "1-3", "3-5", "5-10", "10 (clear)"], vis.values, color=ORANGE)
    axes[0].set(title="Delay rate by visibility (miles)", ylabel="% delayed")
    rain = df.assign(r=np.where(df["precip"] > 0, "Precipitation", "Dry")).groupby("r")["delayed"].mean() * 100
    axes[1].bar(rain.index, rain.values, color=[GREY, ORANGE])
    axes[1].set(title="Delay rate: dry vs precipitation", ylabel="% delayed")
    for ax in axes:
        _clean(ax)
    plt.tight_layout(); plt.savefig(out / "02_eda_weather.png", dpi=150); plt.close()


def roc(y, probs: dict, out):
    plt.figure(figsize=(6, 5))
    for (name, p), c in zip(probs.items(), [GREY, ORANGE, BLUE]):
        fpr, tpr, _ = roc_curve(y, p)
        plt.plot(fpr, tpr, color=c, lw=2, label=f"{name} (AUC={roc_auc_score(y, p):.3f})")
    plt.plot([0, 1], [0, 1], "k--", lw=1, label="Random guess")
    plt.xlabel("False positive rate"); plt.ylabel("True positive rate")
    plt.title("ROC curves - test set (days 22-31, all months)")
    plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(out / "03_roc_curves.png", dpi=150); plt.close()


def importance(imp: pd.Series, out):
    top = imp.sort_values().tail(15)
    plt.figure(figsize=(7, 6))
    plt.barh(top.index, top.values, color=BLUE)
    plt.title("XGBoost - permutation importance (drop in AUC)")
    plt.xlabel("Decrease in ROC-AUC when feature is shuffled")
    _clean(plt.gca()); plt.tight_layout()
    plt.savefig(out / "04_feature_importance.png", dpi=150); plt.close()


def confusion(y, prob, threshold, out):
    cm = confusion_matrix(y, (prob >= threshold).astype(int))
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=13)
    ax.set_xticks([0, 1], ["On time", "Delayed"]); ax.set_yticks([0, 1], ["On time", "Delayed"])
    ax.set(xlabel="Predicted", ylabel="Actual", title=f"XGBoost confusion matrix (threshold={threshold:.2f})")
    plt.tight_layout(); plt.savefig(out / "05_confusion_matrix.png", dpi=150); plt.close()
    return cm
