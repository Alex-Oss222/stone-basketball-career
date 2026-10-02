from __future__ import annotations

from pathlib import Path

import pandas as pd

from .guards import reject_simulation_frame


def find_raw_file(raw_root: Path, dataset: str, season: int | None = None) -> Path:
    suffix = "global" if season is None else str(season)
    candidates = [
        raw_root / f"{dataset}_{suffix}.csv.gz",
        raw_root / f"{dataset}_{suffix}.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"No raw file found for {dataset} {suffix} in {raw_root}")


def read_raw(raw_root: Path, dataset: str, season: int | None = None, **kwargs) -> pd.DataFrame:
    path = find_raw_file(raw_root, dataset, season)
    df = pd.read_csv(path, low_memory=False, **kwargs)
    reject_simulation_frame(df)
    return df


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
