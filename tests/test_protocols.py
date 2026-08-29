from datetime import datetime

import numpy as np
import pandas as pd

from horizon.adapters.base import DataSource
from horizon.models.base import Forecaster


class DummySource:
    name = "dummy"

    def fetch_observations(self, start: datetime, end: datetime) -> pd.DataFrame:
        return pd.DataFrame(columns=["entity_id", "ts_utuc", "target"])

    def fetch_covariates(self, start: datetime, end: datetime) -> pd.DataFrame:
        return pd.DataFrame(columns=["entity_id", "ts_utc", "feature", "value"])

    def fetch_external_baseline(self, start, end) -> pd.DataFrame | None:
        return None


class DummyForecaster:
    name = "dummy"

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        pass

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(X))

    def predict_quantiles(self, X, quantiles) -> np.ndarray:
        return np.zeros((len(X), len(quantiles)))


class Incomplete:
    name = "incomplete"

    def fit(self, X, y): ...
    def predict(self, X): ...


def test_dummy_source_satisfies_protocol():
    assert isinstance(DummySource(), DataSource)


def test_dummy_forecaster_satisifies_protocol():
    assert isinstance(DummyForecaster(), Forecaster)


def test_incomplete_forecaster_is_rejected():
    assert not isinstance(Incomplete(), Forecaster)
