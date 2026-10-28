import pandas as pd

from flight_delay.config import (DELAY_THRESHOLD_MIN, LEAKY_COLUMNS, MODEL_FEATURES,
                                 RECENT_LAGS)
from flight_delay.features import KEYS, time_split


def test_label_uses_15_minute_threshold(raw):
    assert ((raw["dep_delay"] >= DELAY_THRESHOLD_MIN) == raw["delayed"].astype(bool)).all()
    assert raw["dep_delay"].notna().all(), "cancelled flights must be dropped"


def test_no_post_departure_columns_are_model_inputs():
    assert not set(LEAKY_COLUMNS) & set(MODEL_FEATURES)


def test_split_days_do_not_overlap_and_cover_everything(featured):
    train, val, test = time_split(featured)
    assert train["day"].max() < val["day"].min()
    assert val["day"].max() < test["day"].min()
    assert len(train) + len(val) + len(test) == len(featured)
    # every month appears in training, so no season is unseen
    assert set(train["month"]) == set(range(1, 13))


def test_recent_delay_uses_only_earlier_hours(featured):
    """Recompute the feature for one airport-hour by hand from flights 2-3 hours earlier."""
    row = featured.dropna(subset=["origin_recent_delay"]).sample(1, random_state=0).iloc[0]
    same_day = featured[(featured["origin"] == row["origin"]) & (featured["year"] == row["year"])
                        & (featured["month"] == row["month"]) & (featured["day"] == row["day"])]
    earlier = same_day[same_day["sched_dep_hour"].isin([row["sched_dep_hour"] - l for l in RECENT_LAGS])]
    assert len(earlier) > 0
    assert abs(earlier["dep_delay"].mean() - row["origin_recent_delay"]) < 1e-9
    assert abs(earlier["delayed"].mean() - row["origin_recent_delay_rate"]) < 1e-9


def test_feature_rows_unique_per_flight(raw, featured):
    assert len(raw) == len(featured), "joins must not duplicate flights"
    assert featured[KEYS].notna().all().all()
