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

- Built a pagination fetch loop: EIA caps response at 5,000 rows, so the loop advances 'offset' by the page size and stops when a  page returns short.
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

Row counts differ slightly between regions (66,433 - 66,457) over an identical date range, so each region has its own minor reporting quirks.

Decision: train on all available demand hours. Restrict the baseline comparison to hours where both series exist, and report coverage alongside the skill score, so the model and the operators are scored on identical hours. 


## Open Questions

- Are the DST-adjacent missing hours actually the repeated/skipped local hour?
Needs verification against each region's local timezone.

- Why do row counts differ by up to 24 across regions over an identical range?

- ISNE has 1 hour with no matching actual - cause unknown.



## Data base load

- Loaded 1,062,479 rows into DuckDB (data/horizon.duckdb) with a composite primary key on (entity_id, ts_utc, series_type).
- The primary key cuaght a real bug on first load: storing timezone-aware pandas timestamps in a TIMESTAMP column collapsed distinct UTC instants onto the same wall-clock time at the 2020-11-01 DST boundary, creating a duplicate. 
- Verified there were no duplicated in the DataFrame before insert, proving DuckDB created them during type conversion. 
- Declare constraints at the boundary. Without the primary key this would have silently corrupted the data with no error.



## Benchmark - operators' own day-ahead forecast 

## Mean Absolute Percentage Error (MAPE)
BPAT 2.00 ERCO 2.43 ISNE 2.52 NYIS 2.66 MISO 2.82 PJM 3.60 FPL 3.67 CISO 5.04

Computed plausible rows only. Every model is measured against these.


## Step 4 - Weather Forecast

- Fetched hourly weather for 8 regions from Open-Meteo (no API key). Six variables chosen on heat-transfer grounds: temperature, domainant driver. Heating below 18°C and cooling above. Dewpoint and humidity (latent load on airconditioning), wind speed (convective loss from building envelops), cloud cover and shortwave radiation (solar gain and rooftop PV output).


- Open-Meteo returns columnar JSON (dict of aligned lists) rather than row-wise JSON. Different unlike EIA. Different parse, same canonical output - which is the point 
of the adapater pattern.

- Melted wide to long using pandas. 66,456 hours x 6 features x 8 regions = 3,189,888 rows in covariates_raw, keyed on (entity_id, ts_utc, feature).

- Joined demand to temperature: 530, 673 rows.

- Endpoint choice: used the ERA5 reanalysis archives for full 2019-2026 coverage.
This is techincally leakage. At 09:00 you have a weather forecast, not the truth. Open-Meteo's historical-forecast archive avoids this but only reaches back to 2021. 
So, training on reanalysis, then run a controlled comparison on the 2021+ overlap to quantify the accuracy cost of forecast only weather. 

- Location approximation: one representative city per region (largest load centre). PJM spans 13 states, so Philadelphia is a poor proxy. A better version would population-weight several cities.

## Outlier audit - the metrics failed first

The first benchmark run gave physically impossible results: PJM at 65, 350 MW MAE and 3.6% MAPE, which implies ~1.8M MW of demand against a real peak near 152,000. CISO at 8.62% is far above what any professional day-ahead forecast produces.

Treated the implaussible metric as a data bug rather than a result, and checked value distributions. Found 37 bad rows out of 531, 626 (0.007%), in three patterns:

1. PJM - three consecutive hours (2021-10-18/19) at 15.3e9, 2.15e9, 4.31e8. The middle value is 2,147,483, 647, the 32-bit signed integer maximum: an upstream overflow or sentinel. One such row shifts the mean by ~32,000 MW.

2. NYIS - 12 zero readings, mostly consecutive (six straight hours on 2026-02-09). Consistent with a reporting feed dropout.

3. FPL - 3 negatives (min -6,813 MW), all at 00:00 local. Suggests a daily rollover boundary bug.

Why each metric broke differently: MAE is inflated by the huge sentinesl; MAPE is inflated by near-zero denomirators (CISO min 14 MW against a median of 24, 296 produced ~170,000% error on one row). A 'WHERE value > 0' gaurd catched NYIS's exact zero but not CISO's 14.

A case no magnitude threshold can catch: CISO's worst remaining hours showed actuals of 12,000-14,600 MW against normal forecasts of 22,000-26,800 - partial reporting. but 13,000 MW is plausible for CISO in isolation; it is only wrong relative to the forecast for that hour. Added a relational filter (|actual - forecast| / actual < 0.5) for the baseline computation only.

After all filters, CISO retains p50 3.02% / p90 12.15% / p99 29.07%, against p99 of 7.4-12.5% everywhere else. That is a fat tail, not corruption - no threshold removes it. Explanation: CISO reports net demand (load minus behind-the-meter solar), so forecasting it implicitly requires forecasting cloud cover over distributed generation a day ahead.

Methodological constraint: the exclusion list must be fixed before any model is evaluated, and applied identically to the baseline and every model. Filtering on forecast error at evaluation time would flatter the baseline. 

Key Take-away: A physically implausible metric is a data bug until proven otherwise.

## Threshold Justification

Tested plausibility bands by remobal count:

[0.1, 5] -> 29 rows, [0.2, 3] -> 37 [0.3, 2.5] -> 42 [0.5, 2] -> 76

The first three form a plateau and [0.5, 2] jumps to 76 as the band begins cutting into legitimate low-demand hours. Chose [0.2, 3] from within the stable region.

Insepect the rows caught by [0.2, 3] but missed by [0.1, 5]: six FPL and one PJM reading at 4.4-4.8x their region's median (FPL 66,577-72,201 MW against a real peak near 28,000; PJM 417,669 against a real peak near 165,000), plus one FPL reading at 0.149x. All physically impossible. The wider band is therefore impossible.

Several occur in consecutive runs (FPL 2023-11-14 22:00 through 11-15 00:00;
2023-02-07 23:00 through 02-08 00:00), matching the burst pattern seen in PJM's integer-overflow sentinels and NYIS's zero runs. Bad data in this dataset arrives in burst, not as isolated points. Several also fall at or near midnight local, the same boundary where FPL's negative values appeared - suggesting an unreliable daily rollover in FPL's reporting. 


## Predictions:

CISO has the most headroom against the baseline (5.04% vs 2.00-3.67% elsewhere), and the gains should come from irradiance and cloud-cover features rather than calendar features, since its error is driven by solar variability. BPAT at 2.00% will be the hardest to beat. To be checked in future work.

## Temperature-demand curve 
![Temp-Demand curve](data/temp_vs_demand.png)




## Step 5 - Feature Engineering

- Built the 'features' table (530, 651 rows, 18 columns) joining cleaned demand to pivoted weather.

- Pivoted covariates long -> wide with MAX(CASE WHEN feature= ... THEN value END).
This is the cost of long-format storage, paid once in a single place rather than spread across the codebase.

- Degree days: HDD = max(0, 18 - T), CDD = max(0, T - 18). Splits the U-shaped temperature-demand relationship into two monotonic pieces so linear models can fit it. The 18°C balance point is where internal heat gains (people, lighting, appliances) roughly offsets envelope losses which is a real but building-physics parameter, not a convection. It genuinely varies by region and building stock; a refinement would fit it per region.

- All calendar features computed in local time via AT TIME ZONE, since we are more habitual to follow local clocks. DuckDB handles DST automatically.

- Verified: avg CDD ranks FPL 7.2 > ERCO 5.2 > ... > BPAT 1.1, and avg HDD ranks MISO 9.0 > ISNE > 8.6 > ... > FPL 0.2. Matches geography exactly.

- CISO is near-balanced (HDD 2.6, CDD 2.5) and both are small - costal California has littel temperature swing, so temperature explains proportionality less of its variance. Consistent with its flat-topped scatter and its fat error tail.

- hour_local spans 0-23 for all eight regions, confirming the timezone conversion.

## We still need
- Lage features (yesterday's demand, last week's demand) - alongside, the backtester, because lags are where leakage risk lives.
- Fourier terms for smooth daily/weekly/annual cycles.
- Holiday flags.


## Step 6 - Lag features and the horizon constraint

Task definition: at 09:00 local on day D, predict all 24 hours of day D+1.
Each region is forecast independently on it local clock.

The furthest target (23:00 on D+1) is 38 hours after forecast time, so every lag must be >=39 hours to stay inside known data. lag_24h is therefore invalid for this task - for most targets it reaches into the future. Used 48h, 168h, 336h, a 4-week same-hour average, and a 24h rolling mean ending 48h back. 

Caveat: LAG counts rows, not hours, so where rows are missing the offset is approximate. 37 excluded rows in 530,651 makes this neglible; a stricter version would join on an explicit timestamp offset. 

## Predicition check
Predicted lag_168h would beat lag_48h because weekday alignment matters.
WRONG - 48h wins in all 48 regions (e.g. FPL 0.924 vs 0.883). Temporal proximity beats weekday alignment at this horizon.

### Correlations reveal heating fuel mix
HDD correlates negatively with demand in 5 of 8 regions (CISO -0.369, MISO -0.133, ERCO -0.111). Not a bug: correlation fits one straight line to a U-shaped, asymmetric relationship. Where summer cooling peaks exceed winter heating load, cold hours are also low-demand hours. As weak or wrong-signed correlation does not mean a useless feature - tree models split within regimes.

ISNE is the standout: 2nd-highest average HDD (8.6) but c_hdd = 0.058, while c_dd = 0.519. New England heats largely with oil and gas rather than electricity, so cold drives fuel demand, not grid demand. Confirmed on the scatter plot: INSE's summer branch peaks ~25,500 MW against ~20,000 in winter. 

BPAT is the only region with meaningfully positive c_hdd(0.414), consistent with high electric heating penetration in the Pacific Northwest.


## Rolling-origin backtester

Built the evauluation engine from scratch (not a library) because a wrong baktest silently invalidates every downstream number, and the protocol is the thing most likely to be probed.

Design:
- Rolling origin, expanding window: train on all history up to each origin, advancing forward. No shuffling - shuffling let the model see the future.

- 39 hour gap between train_end and test_start. The forecast is made at 09:00 for the next day (furthest target 38h ahead), so the freshest usable data is already 39h old. The gap witholds recent data the model wouldn't have at forecast time, preventing leakage through lag features.

- Model-agnostic: take anything with .fit/.predict, so the same code path scores the naive baseline, linear model, LightGBM, and neural net. 
This is the Forecaster protocol from step 1.

Smoke test with a mean-predictor baseline (always predicts training average): CISO, 8 folds of 30 days each. Confirmed n_train grows (60,462 -> 65,502), n_test = 720 = 30x24, every test window after its training window. Mean MAPE 11.4%, worst in summer folds (fold 7 = 19.76%) where cooling-driven variance is highest and the mean is furthest from the truth. This is the floor real models must beat. CISO's operator baseline is 5.04%.


## Step 7 - First models: the ladder

Ran mean -> ridge -> LightGBM through the backtester on 4 regions.

              mean    ridge   lightgbm   operator baseline
  CISO       11.46%   4.79%   3.54%      5.04%   ← BEAT the operators
  ERCO       13.92%   5.72%   4.14%      2.43%
  MISO       11.13%   3.98%   3.27%      2.82%
  FPL        20.28%   5.83%   4.59%      3.67%

  Headline: LightGBM beats CISO's published day-ahead operator forecast (3.54% vs 5.04%). This confirms the Day-4 predicition made before any modelling: CISO has the most headroom because its error is solar/cooling driven variance, which weather features can capture. The prediction was recorded in advance and held.

  LightGBM beats ridge in every region (~1-1.5 pts), confirming the temperature-demand relationship is non-linear with interactions a straight line can't fit.

  Not yet beating operators at ERCO/MISO/FPL - expected: no tuning, missing features (Fourier seasonality, holidday), and operators have years of refinement.

  Bug found and fixed: three weather features (wind, cloud, radiation) were all-Nan due to feature-name typos in the Day-5 pivot ('winds_peed_10m' vs 'wind_speed_10m', etc). All-Nan columns silently wiped every row via dropna, producing Nan MAPE with no crash. Added a Nan-check to build_features.py and a missing-feature guard to the backtester so this fails by saying it loud.           