"""Write the static JSON files the GitHub Pages dashboard reads (docs/data/)."""
import json
import math

import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve

from .config import (CATEGORICAL, MODEL_FEATURES, MODEL_NUMERIC, RANDOM_STATE,
                     SITE_DATA_DIR, TEST_DAYS, TRAIN_DAYS, VAL_DAYS, YEAR)

PRETTY = {
    "sched_dep_hour": "Departure hour", "day_of_week": "Day of week", "month": "Month",
    "distance": "Distance", "plane_age": "Aircraft age", "seats": "Seats", "temp": "Temperature",
    "dewp": "Dew point", "humid": "Humidity", "wind_speed": "Wind speed", "wind_gust": "Wind gust",
    "precip": "Precipitation", "pressure": "Pressure", "visib": "Visibility",
    "origin_hourly_volume": "Airport departures this hour",
    "carrier_hour_volume": "Airline departures this hour", "days_to_holiday": "Days to holiday",
    "origin_recent_delay": "Recent airport delay (min)",
    "origin_recent_delay_rate": "Recent airport delay rate", "carrier": "Airline",
    "origin": "Origin airport", "dest_grouped": "Destination",
}
VIS_BINS = [-0.1, 1, 3, 5, 9.9, 10]
VIS_LABELS = ["<1 mi", "1–3 mi", "3–5 mi", "5–10 mi", "10 mi (clear)"]


def _f32(x):
    """Shortest decimal that round-trips to the same float32 (keeps the JSON small and exact)."""
    return float(str(np.float32(x)))


def _num(x, nd=None):
    if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x):
        return None
    x = float(x)
    return round(x, nd) if nd is not None else x


def _write(name, obj):
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = SITE_DATA_DIR / name
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"), allow_nan=False)
    return path


# --------------------------------------------------------------------------- model
def base_margin(booster) -> float:
    """XGBoost stores base_score as a probability for binary:logistic; trees add to its logit."""
    cfg = json.loads(booster.save_config())
    raw = cfg["learner"]["learner_model_param"]["base_score"]
    p = float(str(raw).strip("[]"))
    return math.log(p / (1 - p))


def flatten_tree(tree: dict) -> dict:
    """Nested XGBoost JSON dump -> parallel arrays indexed by node id."""
    nodes = {}
    stack = [tree]
    while stack:
        n = stack.pop()
        nodes[n["nodeid"]] = n
        stack.extend(n.get("children", []))
    size = max(nodes) + 1
    f, t, y, no, v = [-1] * size, [0.0] * size, [0] * size, [0] * size, [0.0] * size
    for i, n in nodes.items():
        if "leaf" in n:
            v[i] = _f32(n["leaf"])
        else:
            f[i] = int(n["split"].lstrip("f"))
            t[i] = _f32(n["split_condition"])
            y[i], no[i] = n["yes"], n["no"]
    return {"f": f, "t": t, "y": y, "n": no, "v": v}


def model_spec(pipe, threshold) -> dict:
    prep, clf = pipe.named_steps["prep"], pipe.named_steps["clf"]
    medians = prep.named_transformers_["num"].named_steps["impute"].statistics_
    ohe = prep.named_transformers_["cat"]
    booster = clf.get_booster()
    trees = [flatten_tree(json.loads(t)) for t in booster.get_dump(dump_format="json")]
    return {
        "version": 1,
        "numeric": MODEL_NUMERIC,
        "medians": [float(m) for m in medians],
        "categorical": [{"name": n, "categories": [str(c) for c in cats]}
                        for n, cats in zip(CATEGORICAL, ohe.categories_)],
        "base_margin": base_margin(booster),
        "threshold": threshold,
        "trees": trees,
    }


def feature_records(frame: pd.DataFrame) -> list:
    """Rows as compact arrays in MODEL_FEATURES order (None = missing -> median in JS).

    Numbers are written at full float32 precision, never rounded: XGBoost compares inputs as
    float32, so rounding (e.g. 1/3 -> 0.333333) can push a value across a split threshold.
    """
    out = []
    for row in frame[MODEL_FEATURES].itertuples(index=False):
        rec = []
        for name, val in zip(MODEL_FEATURES, row):
            rec.append(str(val) if name in CATEGORICAL else (None if pd.isna(val) else _f32(val)))
        out.append(rec)
    return out


# --------------------------------------------------------------------------- site data
def summary(df, test, results, test_probs, importance, cm, threshold) -> dict:
    grid = np.linspace(0, 1, 101)
    roc = {}
    for name, p in test_probs.items():
        fpr, tpr, _ = roc_curve(test["delayed"], p)
        roc[name] = [round(float(v), 4) for v in np.interp(grid, fpr, tpr)]
    best = results.set_index("model").loc["XGBoost"]
    return {
        "dataset": {
            "flights": int(len(df)), "delay_rate": round(float(df["delayed"].mean()), 4),
            "airlines": int(df["carrier"].nunique()), "destinations": int(df["dest"].nunique()),
            "airports": sorted(df["origin"].unique().tolist()), "year": YEAR,
            "split": {"train_days": TRAIN_DAYS, "val_days": VAL_DAYS, "test_days": TEST_DAYS},
            "train": int((df["day"] <= TRAIN_DAYS[1]).sum()),
            "val": int(((df["day"] >= VAL_DAYS[0]) & (df["day"] <= VAL_DAYS[1])).sum()),
            "test": int(len(test)), "test_delay_rate": round(float(test["delayed"].mean()), 4),
        },
        "headline": {"auc": round(float(best["roc_auc"]), 3), "recall": round(float(best["recall"]), 3),
                     "f1": round(float(best["f1"]), 3), "accuracy": round(float(best["accuracy"]), 3)},
        "results": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                    for r in results.to_dict("records")],
        "threshold": threshold,
        "confusion": {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1])},
        "roc": {"fpr": [round(float(g), 2) for g in grid], "curves": roc},
        "importance": [{"feature": k, "label": PRETTY.get(k, k), "value": round(float(v), 5)}
                       for k, v in importance.head(12).items()],
    }


def explore(df) -> dict:
    d = df.assign(
        hour=df["sched_dep_hour"], dow=df["day_of_week"],
        vis=pd.cut(df["visib"], VIS_BINS, labels=False),
        precip_flag=np.where(df["precip"].fillna(0) > 0, 1, 0))
    origins = sorted(d["origin"].unique()); carriers = sorted(d["carrier"].unique())
    oi = {o: i for i, o in enumerate(origins)}; ci = {c: i for i, c in enumerate(carriers)}
    dims = {}
    for dim, labels in [("hour", None), ("month", None), ("dow", None),
                        ("vis", VIS_LABELS), ("precip_flag", ["Dry", "Precipitation"])]:
        g = d.dropna(subset=[dim]).groupby(["origin", "carrier", dim])["delayed"].agg(["size", "sum"]).reset_index()
        values = sorted(int(v) for v in g[dim].unique())
        rows = [[oi[r.origin], ci[r.carrier], int(getattr(r, dim)), int(r.size), int(r.sum)]
                for r in g.itertuples(index=False)]
        dims[dim] = {"values": values, "labels": labels, "rows": rows}
    return {"origins": origins, "carriers": carriers, "dims": dims}


def lookup(tables, df, spec) -> dict:
    names = dict(zip(tables["airlines"]["carrier"], tables["airlines"]["name"]))
    ap = dict(zip(tables["airports"]["faa"], tables["airports"]["name"]))
    routes = {}
    g = df.groupby(["origin", "dest"])
    for (o, dst), grp in g:
        routes.setdefault(o, []).append({
            "dest": dst, "distance": int(grp["distance"].median()), "flights": int(len(grp)),
            "carriers": sorted(grp["carrier"].value_counts().index.tolist())})
    for o in routes:
        routes[o].sort(key=lambda r: -r["flights"])

    def q(s, qs=(0.25, 0.5, 0.75, 0.9)):
        s = s.dropna()
        return [round(float(s.quantile(x)), 3) for x in qs] if len(s) else None

    typical = {}
    for (o, h), grp in df.groupby(["origin", "sched_dep_hour"]):
        typical.setdefault(o, {})[int(h)] = {
            "volume": round(float(grp["origin_hourly_volume"].median()), 1),
            "recent_delay": q(grp["origin_recent_delay"]),
            "recent_rate": q(grp["origin_recent_delay_rate"]),
            "delay_rate": round(float(grp["delayed"].mean()), 4)}
    carrier_vol = {f"{c}|{o}|{int(h)}": round(float(v), 1) for (c, o, h), v in
                   df.groupby(["carrier", "origin", "sched_dep_hour"])["carrier_hour_volume"].median().items()}
    weather = {}
    for (o, m), grp in df.groupby(["origin", "month"]):
        weather.setdefault(o, {})[int(m)] = {
            k: _num(grp[k].median(), 1) for k in ["temp", "dewp", "humid", "wind_speed", "pressure", "visib"]}
    plane = {c: {"plane_age": _num(grp["plane_age"].median(), 0), "seats": _num(grp["seats"].median(), 0)}
             for c, grp in df.groupby("carrier")}
    return {
        "carriers": {c: names.get(c, c) for c in sorted(df["carrier"].unique())},
        "airports": {a: ap.get(a, a) for a in sorted(set(df["origin"]) | set(df["dest"]))},
        "routes": routes, "typical": typical, "carrier_volume": carrier_vol,
        "weather": weather, "plane": plane,
        "medians": dict(zip(spec["numeric"], [round(m, 4) for m in spec["medians"]])),
        "top_dests": next(c["categories"] for c in spec["categorical"] if c["name"] == "dest_grouped"),
    }


def replay(test, n=2000) -> dict:
    s = test.sample(n, random_state=RANDOM_STATE).sort_values(["month", "day", "sched_dep_time"])
    meta = [[f"{YEAR}-{r.month:02d}-{r.day:02d}", r.carrier, int(r.flight), r.origin, r.dest,
             int(r.sched_dep_time), int(r.dep_delay)] for r in s.itertuples(index=False)]
    return {"features": MODEL_FEATURES,
            "meta_fields": ["date", "carrier", "flight", "origin", "dest", "sched", "dep_delay"],
            "meta": meta, "rows": feature_records(s)}


def write_all(tables, df, test, xgb, threshold, results, test_probs, importance, cm):
    spec = model_spec(xgb, threshold)
    paths = [
        _write("model.json", spec),
        _write("summary.json", summary(df, test, results, test_probs, importance, cm, threshold)),
        _write("explore.json", explore(df)),
        _write("lookup.json", lookup(tables, df, spec)),
        _write("replay.json", replay(test)),
    ]
    for p in paths:
        print(f"  wrote {p.relative_to(SITE_DATA_DIR.parents[1])} ({p.stat().st_size / 1e6:.2f} MB)")
    return spec
