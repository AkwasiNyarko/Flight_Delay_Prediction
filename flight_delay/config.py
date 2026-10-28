"""Shared constants: paths, feature lists, split rules."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
FIGURES_DIR = ROOT / "reports" / "figures"
SITE_DATA_DIR = ROOT / "docs" / "data"

RANDOM_STATE = 42
DELAY_THRESHOLD_MIN = 15          # U.S. DOT definition of a delayed departure

# Time-based split inside every month (day of month)
TRAIN_DAYS = (1, 17)
VAL_DAYS = (18, 21)
TEST_DAYS = (22, 31)

# Features known before departure
NUMERIC = ["sched_dep_hour", "day_of_week", "month", "distance", "plane_age",
           "seats", "temp", "dewp", "humid", "wind_speed", "wind_gust",
           "precip", "pressure", "visib", "origin_hourly_volume",
           "carrier_hour_volume", "days_to_holiday"]
# Airport state ~1 hour before departure: delays of flights scheduled 2-3 h earlier
REALTIME = ["origin_recent_delay", "origin_recent_delay_rate"]
CATEGORICAL = ["carrier", "origin", "dest_grouped"]
MODEL_NUMERIC = NUMERIC + REALTIME
MODEL_FEATURES = MODEL_NUMERIC + CATEGORICAL

TOP_N_DEST = 30
RECENT_LAGS = (2, 3)

US_HOLIDAYS_2013 = pd.to_datetime([
    "2013-01-01", "2013-01-21", "2013-02-18", "2013-05-27", "2013-07-04",
    "2013-09-02", "2013-10-14", "2013-11-11", "2013-11-28", "2013-12-25"])

# Columns that are only known AFTER departure - must never be model inputs
LEAKY_COLUMNS = ["dep_time", "dep_delay", "arr_time", "arr_delay", "air_time", "delayed"]
