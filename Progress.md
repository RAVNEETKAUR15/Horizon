# Horizon 

## Step 1 - API access and data profiling

- EIA API key working, retrieved CISO hourly demand.
- Profiled the raw response. 
Finding:
- 'value' returns as string, casted to float on load
- Default sort is not guaranteed therefore, sorted in ascending order from descending
- 'start' and 'end' are inclusive (7-day window return 169 rows, not 168)

- Verified the timezone convection empirically rather than taking for granted from the documents. Grouped a week of CISO demand by day and found peaks at 01-02 and mins at 12-14. Shifted by UTC-7 these are 18:00-19:00 and 05:00-06:00 local, matching the expected summer cooling load profile. Concluded 'period' is UTC.
-Also found that grouping by UTC data splits a local evening across two buckets (Aug 3's true evening peak landed in the Aug 4 bucket). Decision: store UTC, derive local time for all calendar features and daily aggregation.