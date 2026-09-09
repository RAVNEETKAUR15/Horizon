"""Run the model ladder through the backtester, per region."""

import duckdb
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge

from horizon.evaluation.backtest import rolling_origin_backtest

FEATURES = [
    "hdd", "cdd", "temp_c", "temp_sq",
    "humidity_pct", "wind_kmh", "cloud_pct", "radiation_wm2",
    "hour_local", "dayofweek", "month_local", "is_weekend",
    "lag_48h", "lag_168h", "lag_336h", "same_hour_4wk_avg", "rolling_24h_mean",
]

class MeanModel:
    def fit(self, X, y): self.mean_ = y.mean()
    def predict(self, X): return np.full(len(X), self.mean_)


def make_models():
    return {
        "mean":     MeanModel(),
        "ridge":    Ridge(alpha=1.0),
        "lightgbm": LGBMRegressor(
            n_estimators=400, learning_rate=0.05, num_leaves=63,
            min_child_samples=50, verbose=-1,
        ),
    }


con = duckdb.connect("data/horizon.duckdb", read_only=True)

for region in ["CISO", "ERCO", "MISO", "FPL"]:
    df = con.execute(
        "SELECT * FROM features_lagged WHERE entity_id = ?", [region]
    ).df()

    print(f"\n=== {region} ===")
    for name, model in make_models().items():
        results = rolling_origin_backtest(df, model, FEATURES, n_folds=8)
        mean_mape = np.mean([r.metrics["mape"] for r in results])
        print(f"  {name:10s}  MAPE {mean_mape:.2f}%")

con.close()