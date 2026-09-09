"""Find out why the backtest returns empty folds."""

import duckdb
import pandas as pd

FEATURES = [
    "hdd", "cdd", "temp_c", "temp_sq",
    "humidity_pct", "wind_kmh", "cloud_pct", "radiation_wm2",
    "hour_local", "dayofweek", "month_local", "is_weekend",
    "lag_48h", "lag_168h", "lag_336h", "same_hour_4wk_avg", "rolling_24h_mean",
]

con = duckdb.connect("data/horizon.duckdb", read_only=True)
df = con.execute("SELECT * FROM features_lagged WHERE entity_id = 'CISO'").df()
con.close()

print("1. Row count:", len(df))
print("\n2. Do all features exist as columns?")
for f in FEATURES:
    print(f"   {f:20s} {'OK' if f in df.columns else 'MISSING'}")

print("\n3. NaN count per feature (out of", len(df), "rows):")
print(df[[c for c in FEATURES if c in df.columns] + ["demand_mw"]].isna().sum())

print("\n4. Rows surviving dropna on all features + target:")
cols = [c for c in FEATURES if c in df.columns] + ["demand_mw"]
print("   ", len(df.dropna(subset=cols)))

print("\n5. Time range:")
print("   ", df["ts_utc"].min(), "→", df["ts_utc"].max())
print("   span in days:", (df["ts_utc"].max() - df["ts_utc"].min()).days)


import duckdb
con = duckdb.connect("data/horizon.duckdb", read_only=True)
print(con.execute("""
    SELECT feature, COUNT(*) AS n
    FROM covariates_raw
    GROUP BY feature ORDER BY feature
""").df())
con.close()