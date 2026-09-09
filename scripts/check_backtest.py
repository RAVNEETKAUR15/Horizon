"""Smoke-test the backtester with a trivial mean model."""

import duckdb
import numpy as np

from horizon.evaluation.backtest import rolling_origin_backtest, summarize


class MeanModel:
    """Predicts the training mean for every row. Deliberately dumb baseline."""
    def fit(self, X, y):
        self.mean_ = y.mean()
    def predict(self, X):
        return np.full(len(X), self.mean_)


con = duckdb.connect("data/horizon.duckdb", read_only=True)
df = con.execute("""
    SELECT * FROM features_lagged WHERE entity_id = 'CISO'
""").df()
con.close()

feature_cols = ["hdd", "cdd", "hour_local", "lag_48h", "lag_168h"]

results = rolling_origin_backtest(
    df, MeanModel(), feature_cols, n_folds=8, test_days=30, gap_hours=39,
)

print(summarize(results))
print(f"\nMean MAPE across folds: {np.mean([r.metrics['mape'] for r in results]):.2f}%")