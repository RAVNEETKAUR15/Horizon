"""Build the model-ready feature table from raw demand and weather"""

import duckdb

con = duckdb.connect("data/horizon.duckdb")

con.execute("DROP TABLE IF EXISTS features")

con.execute("""
CREATE TABLE features AS

WITH tz AS ( 
    SELECT * FROM (VALUES
        ('CISO', 'America/Los_Angeles'),
        ('BPAT', 'America/Los_Angeles'),
        ('ERCO', 'America/Chicago'),
        ('MISO', 'America/Chicago'),
        ('PJM', 'America/New_York'),
        ('ISNE', 'America/New_York'),
        ('NYIS', 'America/New_York'),
        ('FPL', 'America/New_York')
    ) AS t(entity_id, tzname)
),

medians AS (
    SELECT entity_id, MEDIAN(value) AS med
        FROM observations_raw
        WHERE series_type = 'D'
        GROUP BY entity_id
),

demand AS (
    SELECT o.entity_id, o.ts_utc, o.value AS demand_mw
    FROM observations_raw o
    JOIN medians m ON o.entity_id = m.entity_id
    WHERE o.series_type = 'D'
        AND o.value > 0
        AND o.value BETWEEN m.med * 0.2 AND m.med * 3
),

weather AS (
    SELECT entity_id, ts_utc, 
        MAX(CASE WHEN feature = 'temperature_2m'     THEN value END) AS temp_c,
        MAX(CASE WHEN feature = 'dewpoint_2m'        THEN value END) AS dewpoint_c, 
        MAX(CASE WHEN feature = 'relative_humidity_2m' THEN value END) AS humidity_pct,
        MAX(CASE WHEN feature = 'windspeed_10m' THEN value END) AS wind_kmh,
        MAX(CASE WHEN feature = 'cloudcover' THEN value END) AS cloud_pct,
        MAX(CASE WHEN feature = 'shortwave_raditation' THEN value END) AS radiation_wm2
    FROM covariates_raw
    GROUP BY entity_id, ts_utc
)
SELECT 
   d.entity_id, 
   d.ts_utc, 
   d.demand_mw,

   -- weather, raw
   w.temp_c,
   w.dewpoint_c,
   w.humidity_pct, 
   w.wind_kmh,
   w.cloud_pct,
   w.radiation_wm2,

   -- degree days: split the U into two monotonic pieces 
   GREATEST(0, 18 - w.temp_c) AS hdd, 
   GREATEST(0, w.temp_c - 18) AS cdd, 

   -- nonlinear temperature terms 
   w.temp_c * w.temp_c AS temp_sq,

   -- calendar, in LOCAL time

   EXTRACT(hour FROM d.ts_utc AT TIME ZONE t.tzname) AS hour_local, 
   EXTRACT(dow FROM d.ts_utc AT TIME ZONE t.tzname) AS dayofweek, 
   EXTRACT(month FROM d.ts_utc AT TIME ZONE t.tzname) AS month_local,
   EXTRACT(doy FROM d.ts_utc AT TIME ZONE t.tzname) AS dayofyear, 
   EXTRACT(year FROM d.ts_utc AT TIME ZONE t.tzname) AS year, 

   CASE WHEN EXTRACT(dow FROM d.ts_utc AT TIME ZONE t. tzname) IN (0, 6)
        THEN 1 ELSE 0 END AS is_weekend,

FROM demand d
JOIN weather w ON d.entity_id = w.entity_id AND d.ts_utc = w.ts_utc
JOIN tz t ON d.entity_id = t.entity_id

""")

n = con.execute("SELECT COUNT(*) FROM features").fetchone()[0]
print(f"Feature rows: {n:,}\n")

print(con.execute("SELECT * FROM features LIMIT 5").df())

print("\nSantiy checks:")
print(con.execute("""
     SELECT entity_id, 
            ROUND(AVG(hdd), 1) AS avg_hdd, 
            ROUND(AVG(cdd), 1) AS avg_cdd, 
            MIN(hour_local) AS min_hr, 
            MAX(hour_local) AS max_hr

        FROM features
        GROUP BY entity_id
        ORDER BY avg_cdd DESC
""").df())

con.close()
import duckdb
con = duckdb.connect("data/horizon.duckdb", read_only=True)
print(con.execute("""
    SELECT ts_utc,
           ts_utc AT TIME ZONE 'UTC'                AS as_utc,
           ts_utc AT TIME ZONE 'America/Los_Angeles' AS as_la,
           hour_local
    FROM features WHERE entity_id='CISO' LIMIT 5
""").df())
con.close()