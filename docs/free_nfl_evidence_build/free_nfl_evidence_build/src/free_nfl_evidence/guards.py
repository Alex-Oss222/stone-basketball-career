from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

ALLOWED_SEASONS = frozenset(range(2010, 2015))
REAL_ORIGIN = "REAL_PUBLIC_HISTORICAL"


class DataGuardError(ValueError):
    pass


def assert_allowed_seasons(seasons: Iterable[int]) -> tuple[int, ...]:
    normalized = tuple(sorted({int(s) for s in seasons}))
    bad = [s for s in normalized if s not in ALLOWED_SEASONS]
    if bad:
        raise DataGuardError(
            f"Only 2010-2014 are allowed in this evidence build. Rejected: {bad}"
        )
    if not normalized:
        raise DataGuardError("At least one season is required.")
    return normalized


def assert_output_isolated(output_root: Path) -> None:
    """Refuse to write into a Git worktree unless caller deliberately chooses another path.

    The check walks upward from the output path. It protects the user's simulation repository
    from accidental writes. The standalone bundle itself has no dependency on a repository.
    """
    p = output_root.expanduser().resolve()
    for parent in (p, *p.parents):
        if (parent / ".git").exists():
            raise DataGuardError(
                f"Refusing to write inside Git worktree: {parent}. "
                "Choose a separate evidence workspace."
            )


def tag_real_evidence(df: pd.DataFrame, source_dataset: str) -> pd.DataFrame:
    out = df.copy()
    out["data_origin"] = REAL_ORIGIN
    out["source_dataset"] = source_dataset
    return out


def reject_simulation_frame(df: pd.DataFrame) -> None:
    """Reject frames explicitly marked as simulated.

    This is intentionally conservative. It does not guess from values or team names.
    """
    marker_cols = [
        c
        for c in df.columns
        if c.lower() in {"is_simulated", "simulated", "data_origin", "data_type"}
    ]
    for col in marker_cols:
        values = {str(v).strip().upper() for v in df[col].dropna().unique()}
        if col.lower() in {"is_simulated", "simulated"} and values & {"1", "TRUE", "YES", "Y"}:
            raise DataGuardError(f"Simulation-marked input rejected via column {col!r}.")
        if values & {"SIM", "SIMULATION", "SIMULATED", "SYNTHETIC", "SIM_DATA"}:
            raise DataGuardError(f"Simulation-marked input rejected via column {col!r}.")


def slice_as_of(df: pd.DataFrame, as_of_season: int) -> pd.DataFrame:
    """No-hindsight gate for consumers of the derived evidence."""
    as_of_season = int(as_of_season)
    if as_of_season not in ALLOWED_SEASONS:
        raise DataGuardError("as_of_season must be between 2010 and 2014.")
    if "season" not in df.columns:
        raise DataGuardError("Cannot apply no-hindsight gate: missing 'season' column.")
    seasons = pd.to_numeric(df["season"], errors="coerce")
    return df.loc[seasons <= as_of_season].copy()
