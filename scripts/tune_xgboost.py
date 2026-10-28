"""Pick XGBoost settings on the VALIDATION days only (never the test days).

    python scripts/tune_xgboost.py   -> reports/xgb_tuning.csv
The chosen row is copied into XGB_PARAMS in flight_delay/config.py.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from flight_delay.config import *
from flight_delay.data import load_data
from flight_delay.features import engineer_features, time_split
from flight_delay.models import build_preprocessor
df = engineer_features(load_data()); tr, va, te = time_split(df)
pw = (tr.delayed==0).sum()/(tr.delayed==1).sum()
grid = [dict(n_estimators=400, max_depth=7, learning_rate=0.05, min_child_weight=1),
        dict(n_estimators=600, max_depth=6, learning_rate=0.05, min_child_weight=5),
        dict(n_estimators=800, max_depth=5, learning_rate=0.05, min_child_weight=10),
        dict(n_estimators=600, max_depth=8, learning_rate=0.03, min_child_weight=20),
        dict(n_estimators=1000, max_depth=6, learning_rate=0.03, min_child_weight=10),
        dict(n_estimators=500, max_depth=9, learning_rate=0.03, min_child_weight=50)]
rows = []
for g in grid:
    t=time.time()
    m = Pipeline([("prep", build_preprocessor(False, MODEL_NUMERIC)), ("clf", XGBClassifier(subsample=0.8, colsample_bytree=0.8, scale_pos_weight=pw, n_jobs=-1, random_state=RANDOM_STATE, **g))])
    m.fit(tr[MODEL_FEATURES], tr.delayed)
    auc = roc_auc_score(va.delayed, m.predict_proba(va[MODEL_FEATURES])[:, 1])
    rows.append({**g, "val_auc": round(auc, 4), "seconds": round(time.time() - t)})
    print(rows[-1], flush=True)
pd.DataFrame(rows).sort_values("val_auc", ascending=False).to_csv(ROOT / "reports" / "xgb_tuning.csv", index=False)
