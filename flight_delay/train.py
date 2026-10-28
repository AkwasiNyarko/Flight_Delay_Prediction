"""Train, evaluate and export everything.

    python -m flight_delay.train            # full run: models, figures, dashboard data
    python -m flight_delay.train --no-figures
"""
import argparse
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import confusion_matrix

from . import charts, export
from .config import (CATEGORICAL, FIGURES_DIR, MODEL_FEATURES, MODEL_NUMERIC,
                     MODELS_DIR, NUMERIC, RANDOM_STATE)
from .data import read_tables, build_flight_table
from .features import engineer_features, time_split
from .models import build_models, evaluate, tune_threshold


def run(make_figures=True, verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    log("Loading data ...")
    tables = read_tables()
    df = engineer_features(build_flight_table(tables))
    train, val, test = time_split(df)
    log(f"  {len(df):,} departed flights | delay rate {df['delayed'].mean():.1%}")
    log(f"  train {len(train):,} | val {len(val):,} | test {len(test):,}")

    y_train, y_val, y_test = train["delayed"], val["delayed"], test["delayed"]
    pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    results = [evaluate("Baseline (always on time)", y_test, np.zeros(len(y_test)))]
    probs, fitted = {}, {}
    for name, model in build_models(pos_weight, MODEL_NUMERIC).items():
        log(f"Training {name} ...")
        model.fit(train[MODEL_FEATURES], y_train)
        t = tune_threshold(y_val, model.predict_proba(val[MODEL_FEATURES])[:, 1])
        p = model.predict_proba(test[MODEL_FEATURES])[:, 1]
        probs[name], fitted[name] = p, (model, t)
        results.append(evaluate(name, y_test, p, t))

    log("Training XGBoost without real-time airport features (ablation) ...")
    base_feats = NUMERIC + CATEGORICAL
    abl = build_models(pos_weight, NUMERIC)["XGBoost"]
    abl.fit(train[base_feats], y_train)
    t_abl = tune_threshold(y_val, abl.predict_proba(val[base_feats])[:, 1])
    results.append(evaluate("XGBoost, schedule + weather only", y_test,
                            abl.predict_proba(test[base_feats])[:, 1], t_abl))

    res = pd.DataFrame(results)
    log("\n=== TEST-SET RESULTS (days 22-31 of every month) ===")
    log(res.set_index("model").round(3).to_string())

    xgb, threshold = fitted["XGBoost"]
    log("Computing permutation importance ...")
    sample = test[MODEL_FEATURES].sample(20000, random_state=RANDOM_STATE)
    r = permutation_importance(xgb, sample, y_test.loc[sample.index], scoring="roc_auc",
                               n_repeats=5, random_state=RANDOM_STATE, n_jobs=-1)
    imp = pd.Series(r.importances_mean, index=MODEL_FEATURES).sort_values(ascending=False)
    cm = confusion_matrix(y_test, (probs["XGBoost"] >= threshold).astype(int))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": xgb, "threshold": threshold, "features": MODEL_FEATURES},
                MODELS_DIR / "xgb_delay_model.joblib")
    if make_figures:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        charts.eda(df, FIGURES_DIR)
        charts.roc(y_test, probs, FIGURES_DIR)
        charts.importance(imp, FIGURES_DIR)
        charts.confusion(y_test, probs["XGBoost"], threshold, FIGURES_DIR)
        res.round(4).to_csv(FIGURES_DIR.parent / "model_results.csv", index=False)

    log("Exporting dashboard data ...")
    export.write_all(tables=tables, df=df, test=test, xgb=xgb, threshold=threshold,
                     results=res, test_probs=probs, importance=imp, cm=cm)
    log("\nTop drivers of delay (drop in AUC):")
    log(imp.head(8).round(4).to_string())
    log("\nDone. Open docs/index.html via a local server, or the GitHub Pages link.")
    return {"results": res, "threshold": threshold, "importance": imp, "cm": cm}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()
    run(make_figures=not args.no_figures)


if __name__ == "__main__":
    main()
