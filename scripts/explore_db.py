import duckdb
import os

os.makedirs("data", exist_ok=True)
con = duckdb.connect("data/horizon.duckdb") # opens the existing database or creates a new one if it doesn't exist

print("\nHow good are the operator's own forecasts? Let's compare the operator's forecast?")
print(con.execute("""
    WITH paired AS (
    SELECT d.entity_id, 
    d.ts_utc, 
    d.value AS actual,
    f.value AS forecast
    FROM observations_raw d
    JOIN observations_raw f
    ON d.entity_id = f.entity_id
    AND d.entity_id = f.entity_id
    AND d.ts_utc = f.ts_utc
    WHERE d.serirs_type = 'D'
    AND f.series_type = 'DF
    )
    SELECT entity_id, 
           COUNT(*)                                        AS n_hours,   
           ROUND(AVG(ABS(actual - forecast)), 1)           AS mae_mw, 
           ROUND(AVG(ABS(actual - forecast)/actual)*100, 2) AS mape_pct
           FROM paired
           WHERE actual > 0
           GROUP BY entity_id
           ORDER BY mape_pct
    """)).df()