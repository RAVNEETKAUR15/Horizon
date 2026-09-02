"""Plot demand against temperature to see the physical response curve."""

import duckdb
import matplotlib.pyplot as plt

con = duckdb.connect("data/horizon.duckdb", read_only=True)

import duckdb

con = duckdb.connect("data/horizon.duckdb", read_only=True)

for lo, hi in [(0.1, 5), (0.2, 3), (0.3, 2.5), (0.5, 2)]:
    n = con.execute(f"""
        WITH medians AS (
            SELECT entity_id, MEDIAN(value) AS med
            FROM observations_raw WHERE series_type='D' GROUP BY entity_id
        )
        SELECT COUNT(*) FROM observations_raw o
        JOIN medians m ON o.entity_id = m.entity_id
        WHERE o.series_type='D'
          AND (o.value <= 0 OR o.value NOT BETWEEN m.med*{lo} AND m.med*{hi})
    """).fetchone()[0]
    print(f"band [{lo}, {hi}]: removes {n} rows")

con.close()

df = con.execute("""
    WITH medians AS (
        SELECT entity_id, MEDIAN(value) AS med
        FROM observations_raw
        WHERE series_type = 'D'
        GROUP BY entity_id
    ),
    valid AS (
        SELECT o.entity_id, o.ts_utc, o.value
        FROM observations_raw o
        JOIN medians m ON o.entity_id = m.entity_id
        WHERE o.series_type = 'D'
          AND o.value > 0
          AND o.value BETWEEN m.med * 0.2 AND m.med * 3
    )
    SELECT v.entity_id,
           v.ts_utc,
           v.value AS demand_mw,
           c.value AS temp_c
    FROM valid v
    JOIN covariates_raw c
      ON  v.entity_id = c.entity_id
      AND v.ts_utc    = c.ts_utc
    WHERE c.feature = 'temperature_2m'
""").df()
import duckdb

con = duckdb.connect("data/horizon.duckdb", read_only=True)

print(con.execute("""
    WITH medians AS (
        SELECT entity_id, MEDIAN(value) AS med
        FROM observations_raw WHERE series_type='D' GROUP BY entity_id
    )
    SELECT o.entity_id, o.ts_utc, o.value, ROUND(m.med) AS median_mw,
           ROUND(o.value / m.med, 3) AS ratio
    FROM observations_raw o
    JOIN medians m ON o.entity_id = m.entity_id
    WHERE o.series_type='D'
      AND o.value BETWEEN m.med*0.1 AND m.med*5
      AND o.value NOT BETWEEN m.med*0.2 AND m.med*3
    ORDER BY ratio
""").df())

con.close()
con.close()

print(f"Joined rows: {len(df):,}")

fig, axes = plt.subplots(2, 4, figsize=(18, 8), sharex=True)

for ax, region in zip(axes.flat, sorted(df["entity_id"].unique())):
    sub = df[df["entity_id"] == region]
    ax.scatter(sub["temp_c"], sub["demand_mw"], s=1, alpha=0.05)
    ax.set_title(region)
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Demand (MW)")

plt.tight_layout()
plt.savefig("data/temp_vs_demand.png", dpi=120)
print("Saved data/temp_vs_demand.png")