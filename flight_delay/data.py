"""Load the raw tables and join flights with weather and aircraft data."""
import pandas as pd

from .config import DATA_DIR, DELAY_THRESHOLD_MIN


def read_tables(data_dir=DATA_DIR):
    return {
        "flights": pd.read_csv(data_dir / "flights.csv.zip"),
        "weather": pd.read_csv(data_dir / "weather.csv"),
        "planes": pd.read_csv(data_dir / "planes.csv"),
        "airlines": pd.read_csv(data_dir / "airlines.csv"),
        "airports": pd.read_csv(data_dir / "airports.csv"),
    }


def build_flight_table(tables) -> pd.DataFrame:
    """One row per departed flight, with origin weather and aircraft details."""
    df = tables["flights"].copy()
    # Cancelled flights have no departure delay - a different problem, out of scope
    df = df.dropna(subset=["dep_delay"])
    df["time_hour"] = pd.to_datetime(df["time_hour"])
    df["delayed"] = (df["dep_delay"] >= DELAY_THRESHOLD_MIN).astype(int)

    w = tables["weather"].copy()
    w["time_hour"] = pd.to_datetime(w["time_hour"])
    w = (w.drop(columns=["year", "month", "day", "hour"])
          .drop_duplicates(subset=["origin", "time_hour"]))
    df = df.merge(w, on=["origin", "time_hour"], how="left")

    p = tables["planes"][["tailnum", "year", "seats"]].rename(columns={"year": "plane_year"})
    return df.merge(p, on="tailnum", how="left")


def load_data(data_dir=DATA_DIR) -> pd.DataFrame:
    return build_flight_table(read_tables(data_dir))
