"""Add lag and rolling features, respecting the 39-hour horizon constraint.
Forecast is made at 09:00 local on day D for all 24 hours of day D+1. 
The last target hour is 38 hours after forecast time, so lag must be at least 39 hours to stay inside known data.
"""

import duckdb

con = duckdb.connect("data/horizon.duckdb")

con.execute("""DROP TABLE IF EXISTS features_lagged""")

con.execute("""
CREATE TABLE features_lagged AS
SELECT
     *,
     
     -- lags: all>= 39h, so safe at forecast time
     LAG(demand_mw, 48) OVER w AS lag_48h,
     LAG(demand_mw, 168) OVER w AS lag_168h,
     LAG(demand_mw, 336) OVER w AS lag_336h,
     
     -- same hour, averaged over the last 4 weeks (168h steps back)
     ( LAG(demand_mw, 168) OVER w
     + LAG(demand_mw, 336) OVER w
     + LAG(demand_mw, 504) OVER w
     + LAG(demand_mw, 672) OVER w) / 4.0 AS same_hour_4wk_avg,
     
     -- recent level: 24h mean ending 48h before the target 
     AVG(demand_mw) OVER (
         PARTITION BY entity_id ORDER by ts_utc
         ROWS BETWEEN 71 PRECEDING AND 48 PRECEDING
         ) AS rolling_24h_mean

    FROM features
    WINDOW w AS (PARTITION BY entity_id ORDER BY ts_utc)
    """)

n = con.execute("SELECT COUNT(*) FROM features_lagged").fetchone()[0]
print(f"Rows: {n:,}\n")

print("Null counts (expected: early rows have no history):")
print(con.execute("""
    SELECT entity_id, 
           COUNT(*) AS total, 
           COUNT(*) FILTER (WHERE lag_48h IS NULL) AS null_48,
           COUNT(*) FILTER (WHERE lag_168h IS NULL) AS null_168,
           COUNT(*) FILTER (WHERE lag_336h IS NULL) AS  null_336
        FROM features_lagged
        GROUP BY entity_id ORDER BY entity_id
""").df())

print("\nHow predictive is each lag? (correlation with demand)")
print(con.execute("""
     SELECT entity_id, 
            ROUND(CORR(demand_mw, lag_48h), 3) AS c_48h,
            ROUND(CORR(demand_mw, lag_168h), 3) AS c_168h,
            ROUND(CORR(demand_mw, lag_336h), 3) AS c_336h,
            ROUND(CORR(demand_mw, hdd), 3) AS c_hdd, 
            ROUND(CORR(demand_mw, cdd), 3) AS c_cdd
    FROM features_lagged
    GROUP BY entity_id ORDER BY entity_id
""").df())

con.close()

