''' Load raw EIA JSON files into a DuckDB database'''

import json
import pandas as pd


REGION = ["CISO", "ERCO", "PJM", "MISO", "ISNE", "NYIS", "BPAT", "FPL"]
SERIES = ["D", "DF"]

frames = []

for region in REGION:
    for series in SERIES:
        path = f"data/raw/{region}_{series}.json"
        with open(path) as f:
             rows = json.load(f)
        df = pd.DataFrame(rows)
        df = df[["period", "respondent", "type", "value"]]
        df["ts_utc"] = pd.to_datetime(df["period"], utc=True)
        df["value"] = df["value"].astype(float)
        df = df.rename(columns={"respondent":"entity_id", "type":"series_type"})
        df = df[["entity_id", "ts_utc", "series_type", "value"]]

        frames.append(df)
        print(f"{path}:{len(df)} rows")

all_data = pd.concat(frames, ignore_index=True)
print(f"\nTotal rows: {len(all_data)}")
print(all_data.groupby(["entity_id", "series_type"]).size())


import duckdb
import os

os.makedirs("data", exist_ok=True)
con = duckdb.connect("data/horizon.duckdb") # opens the existing database or creates a new one if it doesn't exist

con.execute("DROP TABLE IF EXISTS observations_raw")

# Create table defines the shape and the types
# VARCHAR is text
# TIMESTAMPTZ is a timezone-aware timestamp
# DOUBLE is a float

con.execute("""
    CREATE TABLE observations_raw (
    entity_id   VARCHAR      NOT NULL, 
    ts_utc      TIMESTAMPTZ   NOT NULL, 
    series_type VARCHAR    NOT NULL, 
    value       DOUBLE,
    PRIMARY KEY (entity_id, ts_utc, series_type))""")
    # Primary key declares the combination must be unique, you cannot have two rows with the same entity_id, ts_utc, and series_type


con.execute("INSERT INTO observations_raw SELECT * FROM all_data")
# Duckdb can read a pandas DataFrame sitting in python sesssion directly by name
# Copy every row from pandas DataFrame into the table.
count = con.execute("SELECT COUNT(*) FROM observations_raw").fetchone()[0]
# fetchone()[0] return the single number of the results.
print(f"\nRows in database: {count:,}")

con.close() # close connection


# Duplicate verification

dupes = all_data[all_data.duplicated(subset=["entity_id", "ts_utc", "series_type"], keep=False)]
print(f"Duplicates in the DataFrame:{len(dupes)}")

print(dupes.sort_values(["entity_id", "ts_utc", "series_type"]).head(20))