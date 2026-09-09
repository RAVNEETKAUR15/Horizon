"""Rolling-origin backtester — the core evaluation engine.

Simulates real forecasting: at each origin, train only on the past, leave a gap
so no feature can use data more recent than would be available at forecast time,
then score on the held-out period. Advance the origin and repeat.

This file is written from scratch on purpose: the backtest protocol is the thing
most likely to be probed in an interview, and a wrong backtest silently
invalidates every downstream number.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FoldResult:
    fold: int
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    n_train: int
    n_test: int
    metrics: dict


def mae(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred)))


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred) / actual) * 100)


def rolling_origin_backtest(
    df: pd.DataFrame,
    model,
    feature_cols: list[str],
    target_col: str = "demand_mw",
    time_col: str = "ts_utc",
    n_folds: int = 8,
    test_days: int = 30,
    gap_hours: int = 39,
    min_train_days: int = 365,
) -> list[FoldResult]:
    """Backtest one model on one entity's data.

    df must be sorted by time, single entity, with no missing feature rows.
    model must have .fit(X, y) and .predict(X).
    """
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Features not in dataframe: {missing}")
    df = df.sort_values(time_col).reset_index(drop=True)

    start_time = df[time_col].min()
    end_time = df[time_col].max()

    test_span = pd.Timedelta(days=test_days)
    gap = pd.Timedelta(hours=gap_hours)

    results: list[FoldResult] = []

    for fold in range(n_folds):
        folds_from_end = n_folds - 1 - fold
        test_end = end_time - folds_from_end * test_span
        test_start = test_end - test_span
        train_end = test_start - gap

        if (train_end - start_time) < pd.Timedelta(days=min_train_days):
            continue

        train = df[df[time_col] <= train_end]
        test = df[(df[time_col] > test_start) & (df[time_col] <= test_end)]

        train = train.dropna(subset=feature_cols + [target_col])
        test = test.dropna(subset=feature_cols + [target_col])

        if len(train) == 0 or len(test) == 0:
            continue

        X_train, y_train = train[feature_cols], train[target_col]
        X_test, y_test = test[feature_cols], test[target_col]

        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        results.append(FoldResult(
            fold=fold,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            n_train=len(train),
            n_test=len(test),
            metrics={
                "mae": mae(y_test.values, pred),
                "mape": mape(y_test.values, pred),
            },
        ))

    return results


def summarize(results: list[FoldResult]) -> pd.DataFrame:
    """Turn a list of fold results into a readable table."""
    rows = [{
        "fold": r.fold,
        "train_end": r.train_end.date(),
        "test_end": r.test_end.date(),
        "n_train": r.n_train,
        "n_test": r.n_test,
        "mae": round(r.metrics["mae"], 1),
        "mape": round(r.metrics["mape"], 2),
    } for r in results]
    return pd.DataFrame(rows)