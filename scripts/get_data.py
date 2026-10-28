"""Rebuild data/ from the nycflights23 package (all 2023 departures from JFK, LGA and EWR).

Source: Ismay, C., Couch, S. P., & Wickham, H. nycflights23 (CC0), built from U.S. Bureau of
Transportation Statistics on-time data, NOAA hourly weather (ASOS) and the FAA aircraft registry.
https://github.com/moderndive/nycflights23

    pip install pyreadr
    python scripts/get_data.py
"""
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pyreadr

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPO = "https://github.com/moderndive/nycflights23"
TABLES = ["flights", "weather", "planes", "airlines", "airports"]


def read_rda(path: Path) -> pd.DataFrame:
    df = next(iter(pyreadr.read_r(str(path)).values()))
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # pyreadr returns New York wall-clock times (the `hour` columns agree); store them as such
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def main():
    DATA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "--depth", "1", REPO, tmp], check=True)
        for t in TABLES:
            df = read_rda(Path(tmp) / "data" / f"{t}.rda")
            if t == "flights":
                with zipfile.ZipFile(DATA / "flights.csv.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
                    z.writestr("flights.csv", df.to_csv(index=False))
            else:
                df.to_csv(DATA / f"{t}.csv", index=False)
            print(f"{t:9s} {len(df):>8,} rows")


if __name__ == "__main__":
    sys.exit(main())
