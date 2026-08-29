from datetime import datetime
from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataSource(Protocol):
    name: str

    def fetch_observations(self, start: datetime, end: datetime) -> pd.DataFrame: ...

    def fetch_covariates(self, start: datetime, end: datetime) -> pd.DataFrame: ...

    def fetch_external_baseline(
        self, start: datetime, end: datetime
    ) -> pd.DataFrame | None: ...
