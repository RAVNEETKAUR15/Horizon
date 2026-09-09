![CI](https://github.com/RAVNEETKAUR15/Horizon/actions/workflows/ci.yml/badge.svg)


# Horizon - Operational Electricity Demand Forecasting💡
**What makes electricity demand so hard to predict? Sometimes it's the sun☀️.**

This project predicts how much electricity a region will use **tomorrow, hour by hour,** and the single hardest region to predict turned out to be covered in solar panels. It measures itself against the one benchmark that actually matters: the grid operators' own published forecasts. 

# In California, it beats them.
**Status:** Live and growing. The data pipeline, benchmarking, features, backtesting, and models are complete. Uncertainty quantification and deployment are next.

The result, up front

| Region | Mean | Ridge | LightGBM | Operator Baseline |
|---|---:|---:|---:|---:|
| CISO | 11.46% | 4.79% | **3.54%** | 5.04% |
| ERCO | 13.92% | 5.72% | **4.14%** | 2.43% |
| MISO | 11.13% | 3.98% | **3.27%** | 2.82% |
| FPL | 20.28% | 5.83% | **4.59%** | 3.67% |


<sub>Error = MAPE(mean average % error). Lower is better. Averaged over 8 time-ordered backtests.</sub>


