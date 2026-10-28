"""Model pipelines, evaluation and threshold tuning."""
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from .config import CATEGORICAL, RANDOM_STATE


def build_preprocessor(scale: bool, numeric: list) -> ColumnTransformer:
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scale", StandardScaler()))
    # Dense output so the browser port sees exactly the matrix XGBoost saw
    return ColumnTransformer([
        ("num", Pipeline(num_steps), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ], sparse_threshold=0)


def build_models(pos_weight: float, numeric: list) -> dict:
    return {
        "Logistic Regression": Pipeline([
            ("prep", build_preprocessor(True, numeric)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))]),
        "Random Forest": Pipeline([
            ("prep", build_preprocessor(False, numeric)),
            ("clf", RandomForestClassifier(n_estimators=200, max_depth=16, min_samples_leaf=20,
                                           class_weight="balanced", n_jobs=-1,
                                           random_state=RANDOM_STATE))]),
        "XGBoost": Pipeline([
            ("prep", build_preprocessor(False, numeric)),
            ("clf", XGBClassifier(n_estimators=400, max_depth=7, learning_rate=0.05,
                                  subsample=0.8, colsample_bytree=0.8,
                                  scale_pos_weight=pos_weight, eval_metric="auc",
                                  n_jobs=-1, random_state=RANDOM_STATE))]),
    }


def tune_threshold(y, prob) -> float:
    """Decision threshold that maximises F1 on validation data."""
    grid = np.arange(0.20, 0.81, 0.01)
    return float(round(grid[np.argmax([f1_score(y, prob >= t) for t in grid])], 2))


def evaluate(name, y_true, prob, threshold=0.5) -> dict:
    pred = (prob >= threshold).astype(int)
    return {
        "model": name,
        "threshold": round(float(threshold), 2),
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, prob) if np.std(prob) > 0 else 0.5,
    }
