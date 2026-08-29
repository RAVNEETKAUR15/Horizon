from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd


@runtime_checkable
class Forecaster(Protocol):
    name: str

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None: ...
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...
    def predict_quantiles(
        self, X: pd.DataFrame, quantiles: list[float]
    ) -> np.ndarray: ...
