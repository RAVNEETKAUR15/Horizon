"""Load raw Open-Meteo JSON files into DuckDB as long-format covariates."""

import json

import duckdb
import pandas as pd

REGIONS = ["CISO", "ERCO", "PJM", "MISO", "ISNE", "NYIS", "BPAT", "FPL"]

frames = []

for region in REGIONS:
    with open(f"data/raw/{region}_weather.json") as f:
        body = json.load(f)

    # hourly is a dict of columns: {"time": [...], "temperature_2m": [...], ...}
    df = pd.DataFrame(body["hourly"])

    df["ts_utc"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop(columns=["time"])
    df["entity_id"] = region

    # wide -> long: one row per (region, hour, feature)
    long = df.melt(
        id_vars=["entity_id", "ts_utc"],
        var_name="feature",
        value_name="value",
    )

    frames.append(long)
    print(f"{region}: {len(long):,} rows")

all_weather = pd.concat(frames, ignore_index=True)
all_weather = all_weather.dropna(subset=["value"])

print(f"\nTotal covariate rows: {len(all_weather):,}")

con = duckdb.connect("data/horizon.duckdb")

con.execute("DROP TABLE IF EXISTS covariates_raw")
con.execute("""
    CREATE TABLE covariates_raw (
        entity_id  VARCHAR     NOT NULL,
        ts_utc     TIMESTAMPTZ NOT NULL,
        feature    VARCHAR     NOT NULL,
        value      DOUBLE,
        PRIMARY KEY (entity_id, ts_utc, feature)
    )
""")
con.execute("INSERT INTO covariates_raw SELECT entity_id, ts_utc, feature, value FROM all_weather")

print(con.execute("""
    SELECT feature, COUNT(*) AS n, ROUND(MIN(value),1) AS min_v,
           ROUND(AVG(value),1) AS avg_v, ROUND(MAX(value),1) AS max_v
    FROM covariates_raw
    GROUP BY feature ORDER BY feature
""").df())

con.close()