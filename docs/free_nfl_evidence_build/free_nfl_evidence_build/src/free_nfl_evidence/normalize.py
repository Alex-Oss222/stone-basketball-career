from __future__ import annotations

import numpy as np
import pandas as pd

TEAM_ALIASES = {
    "JAC": "JAX",
    "STL": "LA",
    "SD": "LAC",
    "OAK": "LV",
}

OL_POSITIONS = {
    "C", "G", "T", "OL", "OT", "OG", "LT", "RT", "LG", "RG",
}


def normalize_team(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.upper().str.strip()
    return s.replace(TEAM_ALIASES)


def numeric(series: pd.Series | None, index=None) -> pd.Series:
    if series is None:
        return pd.Series(np.nan, index=index, dtype="float64")
    return pd.to_numeric(series, errors="coerce")


def first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def normalize_position(series: pd.Series) -> pd.Series:
    return series.astype("string").str.upper().str.strip()
