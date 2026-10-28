"""Feature engineering and the time-based split. Uses only pre-departure information."""
import numpy as np
import pandas as pd

from .config import (RECENT_LAGS, TEST_DAYS, TOP_N_DEST, TRAIN_DAYS,
                     US_HOLIDAYS_2013, VAL_DAYS)

KEYS = ["origin", "year", "month", "day", "sched_dep_hour"]


def days_to_nearest(dates: pd.Series, holidays=US_HOLIDAYS_2013) -> np.ndarray:
    d = dates.values[:, None] - holidays.values[None, :]
    return np.abs(d.astype("timedelta64[D]").astype(int)).min(axis=1)


def recent_airport_delays(df: pd.DataFrame) -> pd.DataFrame:
    """Average delay and delay rate of flights scheduled 2-3 hours earlier at the same airport.

    Shifting the hourly table forward by each lag lines past hours up with later flights.
    """
    hourly = (df.groupby(KEYS)
                .agg(sum_delay=("dep_delay", "sum"), n=("dep_delay", "size"),
                     n_late=("delayed", "sum"))
                .reset_index())
    shifted = []
    for lag in RECENT_LAGS:
        h = hourly.copy()
        h["sched_dep_hour"] += lag
        shifted.append(h)
    recent = pd.concat(shifted).groupby(KEYS)[["sum_delay", "n", "n_late"]].sum().reset_index()
    recent["origin_recent_delay"] = recent["sum_delay"] / recent["n"]
    recent["origin_recent_delay_rate"] = recent["n_late"] / recent["n"]
    return recent[KEYS + ["origin_recent_delay", "origin_recent_delay_rate"]]


def top_destinations(df: pd.DataFrame, n=TOP_N_DEST) -> list:
    return list(df["dest"].value_counts().nlargest(n).index)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sched_dep_hour"] = df["sched_dep_time"] // 100
    date = pd.to_datetime(df[["year", "month", "day"]])
    df["day_of_week"] = date.dt.dayofweek            # 0 = Monday
    df["plane_age"] = 2013 - df["plane_year"]

    # Congestion: scheduled departures in the same hour
    df["origin_hourly_volume"] = df.groupby(["origin", "time_hour"])["flight"].transform("count")
    df["carrier_hour_volume"] = df.groupby(["carrier", "origin", "time_hour"])["flight"].transform("count")
    df["days_to_holiday"] = days_to_nearest(date)

    df = df.merge(recent_airport_delays(df), on=KEYS, how="left")

    top = top_destinations(df)
    df["dest_grouped"] = np.where(df["dest"].isin(top), df["dest"], "OTHER")
    return df


def time_split(df: pd.DataFrame):
    """Train on early days of every month, validate on the middle, test on the last days."""
    def between(lo_hi):
        return df[(df["day"] >= lo_hi[0]) & (df["day"] <= lo_hi[1])]
    return between(TRAIN_DAYS), between(VAL_DAYS), between(TEST_DAYS)
