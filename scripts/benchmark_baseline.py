"""Compute the operators' published day-ahead forecast error — the project benchmark."""

import duckdb

con = duckdb.connect("data/horizon.duckdb", read_only=True)

print("Operators' own day-ahead forecast accuracy (plausible rows only):")
print(con.execute("""
    WITH medians AS (
        SELECT entity_id, MEDIAN(value) AS med
        FROM observations_raw
        WHERE series_type = 'D'
        GROUP BY entity_id
    ),
    valid AS (
        SELECT o.entity_id, o.ts_utc, o.series_type, o.value
        FROM observations_raw o
        JOIN medians m ON o.entity_id = m.entity_id
        WHERE o.value > 0
          AND o.value BETWEEN m.med * 0.2 AND m.med * 3
    ),
    paired AS (
        SELECT d.entity_id,
               d.ts_utc,
               d.value AS actual,
               f.value AS forecast
        FROM valid d
        JOIN valid f
          ON  d.entity_id = f.entity_id
          AND d.ts_utc    = f.ts_utc
        WHERE d.series_type = 'D'
          AND f.series_type = 'DF'
          AND ABS(d.value - f.value) / d.value < 0.5
    )
    SELECT entity_id,
           COUNT(*)                                             AS n_hours,
           ROUND(AVG(ABS(actual - forecast)), 1)                AS mae_mw,
           ROUND(AVG(ABS(actual - forecast) / actual) * 100, 2) AS mape_pct,
           ROUND(MEDIAN(ABS(actual - forecast) / actual) * 100, 2) AS median_ape_pct
    FROM paired
    GROUP BY entity_id
    ORDER BY mape_pct
""").df())

print("\nCISO error distribution:")
print(con.execute("""
    WITH medians AS (
        SELECT entity_id, MEDIAN(value) AS med
        FROM observations_raw WHERE series_type='D' GROUP BY entity_id
    ),
    valid AS (
        SELECT o.* FROM observations_raw o
        JOIN medians m ON o.entity_id = m.entity_id
        WHERE o.value > 0 AND o.value BETWEEN m.med*0.2 AND m.med*3
    ),
    paired AS (
        SELECT d.entity_id, d.value AS actual, f.value AS forecast
        FROM valid d JOIN valid f
          ON d.entity_id=f.entity_id AND d.ts_utc=f.ts_utc
        WHERE d.series_type='D' AND f.series_type='DF'
    )
    SELECT entity_id,
           ROUND(QUANTILE_CONT(ABS(actual-forecast)/actual, 0.50)*100,2) AS p50,
           ROUND(QUANTILE_CONT(ABS(actual-forecast)/actual, 0.90)*100,2) AS p90,
           ROUND(QUANTILE_CONT(ABS(actual-forecast)/actual, 0.99)*100,2) AS p99
    FROM paired
    GROUP BY entity_id ORDER BY p50
""").df())

con.close()