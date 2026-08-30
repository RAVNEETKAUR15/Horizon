# Horizon 

## Step 1 - API access and data profiling

- EIA API key working, retrieved CISO hourly demand.
- Profiled the raw response. 
Finding:
- 'value' returns as string, casted to float on load
- Default sort is not guaranteed therefore, sorted in ascending order from descending
- 'start' and 'end' are inclusive (7-day window return 169 rows, not 168)

- Verified the timezone convention empirically rather than taking for granted from the documents. Grouped a week of CISO demand by day and found peaks at 01-02 and mins at 12-14. Shifted by UTC-7 these are 18:00-19:00 and 05:00-06:00 local, matching the expected summer cooling load profile. Concluded 'period' is UTC.
-Also found that grouping by UTC data splits a local evening across two buckets (Aug 3's true evening peak landed in the Aug 4 bucket). Decision: store UTC, derive local time for all calendar features and daily aggregation.



## Step 2 - Interfaces and CI

- Defined two Protocols: 'DataSource' (fetch_observations/ fetch_covariates / fetch_external_baseline) and 'Forecaster' (fit/predict/ predict_quantiles).
Structural typing means new sources and models plug in without touching downstream code, this is what makes the platform domain-agnostic. 
- Chose long format for covarites so feature count can vary between domains.
- Put 'predict_quantiles' in the model contract from the start: uncertainty is a requirement of every model, not an add-on.
- Test cover both conformance and rejection of an incomplete implementation.

- CI on ever push, fresh Ubuntu, clean install, ruff + pytest.


## Step 3 - Data quality audit (8 regions, 2019-2026)

- Built a pagination fetch loop: EIA caps response at 5,000 rows, so the loop advances 'offset' by the page size and stops when a  page short.
Includes a 0.5s delay between requests (EIA suspends keys that exceed their rate tolerance) and a 500-page safety cap against infinite loops.

- Backfilled 8 regions x 2 series x 2019-2026 = 16 files, 1.06M rows, cached to data/raw/ as JSON so development never re-hits the API.

- Missing forecast (actual exists, forecast does not):
PJM 237, FPL 157, CISO 120, MISO 120, NYIS/BPAT/ERCO 48, ISNE 0.
 Worst case 0.36% of rows.

- Missing actual (forecast exists, actual does not):
CISO 2, NYIS 1, ERCO 1, ISNE 1. Only visible after checked the set difference in both directions, the one-way check reported ISNE as clean.

Two distinct failure modes:
1. Isolated single hours on US DST transition dates (FPL: 2019-03-10, 2020-03-08, 2020-11-01; PJM: 2019-03-10). Systematic, consistent with mishandling of the repeated/skipped local hour.

2. Multi-day blocks at region-specific dates unrelated to DST (MISO 2020-05-27, BPAT 2021-09-16, ERCO 2025-12-05, NYIS 2026-05-13).

Row counts differ slightly between regions (66, 433 - 66, 457) over an identical date range, so each region has its own minor reporting quirks.

Decision: train on all available demand hours. Restrict the baseline comparison to hours where both series exist, and report coverage alongside the skill score, so the model and the operators are scored on identical hours. 


## Open Questions

- Are the DST-adjacent missing hours actually the repeated/skipped local hour?
Needs verification against each region's local timezone.

- Why do row counts differ by up to 24 across regions over an identical range?

- ISNE has 1 hour with no matching actual - cause unknown.



## Data base load

- Loaded 1,062,479 rows into DuckDB (data/horizon.duckdb) with a composite primary key on (entity_id, ts_utc, series_type).
- The primary key cuaght a real bug on first load: storing timezone-aware pandas timestamps in a TIMESTAMP column collapsed distinct UTC instants onto the same wall-clock time at the 2020-11-01 DST boundary, creating a duplicate. 
- Verified on duplicates in the data. 
- Declare constraints at the boundary. Without the primary key this would have silently corrupted the data with no error.
