"""Investigate why PJM, FPL and CISO baseline metrics look implausible."""

import duckdb

con = duckdb.connect("data/horizon.duckdb", read_only=True)

print("Value distribution per region (actual demand only):")
print(con.execute("""
    SELECT entity_id,
           MIN(value)                     AS min_val,
           QUANTILE_CONT(value, 0.001)    AS p001,
           MEDIAN(value)                  AS median_val,
           QUANTILE_CONT(value, 0.999)    AS p999,
           MAX(value)                     AS max_val
    FROM observations_raw
    WHERE series_type = 'D'
    GROUP BY entity_id
    ORDER BY entity_id
""").df())



print("\nImplausible rows per region:")
print(con.execute("""
    WITH stats AS (
        SELECT entity_id, MEDIAN(value) AS med
        FROM observations_raw
        WHERE series_type = 'D'
        GROUP BY entity_id
    )
    SELECT o.entity_id,
           COUNT(*) FILTER (WHERE o.value <= 0)             AS non_positive,
           COUNT(*) FILTER (WHERE o.value > 0
                              AND o.value < s.med * 0.2)    AS too_low,
           COUNT(*) FILTER (WHERE o.value > s.med * 3)      AS too_high,
           COUNT(*)                                          AS total
    FROM observations_raw o
    JOIN stats s ON o.entity_id = s.entity_id
    WHERE o.series_type = 'D'
    GROUP BY o.entity_id
    ORDER BY o.entity_id
""").df())

print("\nThe worst offenders:")
print(con.execute("""
    SELECT entity_id, ts_utc, value
    FROM observations_raw
    WHERE series_type = 'D'
      AND (value <= 0 OR value > 500000)
    ORDER BY entity_id, ts_utc
""").df())

con.close()

