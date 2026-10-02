from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .guards import assert_allowed_seasons, assert_output_isolated
from .io import read_raw, write_csv
from .transforms import (
    build_coverage_evidence,
    build_ol_evidence,
    build_pass_disruption,
    build_role_evidence,
    build_team_defense,
    build_team_offense_line_context,
    defensive_call_policy,
)


def _concat(raw: Path, dataset: str, seasons: Iterable[int]) -> pd.DataFrame:
    frames = [read_raw(raw, dataset, int(s)) for s in seasons]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def build_evidence(workspace: Path, seasons: Iterable[int]) -> dict[str, str]:
    seasons = assert_allowed_seasons(seasons)
    workspace = workspace.expanduser().resolve()
    assert_output_isolated(workspace)
    raw = workspace / "raw"
    derived = workspace / "derived"
    derived.mkdir(parents=True, exist_ok=True)

    players = read_raw(raw, "players", None)
    depth = _concat(raw, "depth_charts", seasons)
    rosters = _concat(raw, "weekly_rosters", seasons)
    injuries = _concat(raw, "injuries", seasons)
    player_stats = _concat(raw, "player_stats", seasons)
    pbp = _concat(raw, "pbp", seasons)
    snap_seasons = [s for s in seasons if s >= 2012]
    snaps = _concat(raw, "snap_counts", snap_seasons) if snap_seasons else pd.DataFrame()

    role = build_role_evidence(depth, rosters, injuries, snaps if not snaps.empty else None, players)
    disruption = build_pass_disruption(player_stats, role)
    coverage = build_coverage_evidence(player_stats, role)
    defense = build_team_defense(pbp)
    ol_context = build_team_offense_line_context(pbp)
    ol = build_ol_evidence(role, ol_context)
    calls = defensive_call_policy()

    join_issues = role.loc[
        role["id_match_status"].isin(["UNMATCHED_PFR_ID", "MISSING_ID"])
    ].copy()
    issue_cols = [c for c in [
        "season", "team", "player_id", "pfr_id", "player_name", "position",
        "measurement", "id_match_status", "source_dataset", "data_origin"
    ] if c in join_issues.columns]
    join_issues = join_issues[issue_cols]

    products = {
        "role_availability": role,
        "pass_disruption": disruption,
        "coverage_observables": coverage,
        "team_defense": defense,
        "offensive_line_evidence": ol,
        "defensive_call_policy": calls,
        "join_issues": join_issues,
    }
    paths: dict[str, str] = {}
    for name, df in products.items():
        path = derived / f"{name}.csv"
        write_csv(df, path)
        paths[name] = str(path)

    validation_rows = []
    for name, df in products.items():
        key = ["season", "team"]
        if "player_id" in df.columns:
            key.append("player_id")
        usable_key = [c for c in key if c in df.columns]
        duplicate_rows = int(df.duplicated(usable_key, keep=False).sum()) if usable_key and not df.empty else 0
        validation_rows.append(
            {
                "product": name,
                "rows": int(len(df)),
                "duplicate_key_rows": duplicate_rows,
                "missing_player_id_rows": int(df["player_id"].isna().sum()) if "player_id" in df.columns else 0,
                "min_season": int(pd.to_numeric(df["season"], errors="coerce").min()) if "season" in df.columns and not df.empty else None,
                "max_season": int(pd.to_numeric(df["season"], errors="coerce").max()) if "season" in df.columns and not df.empty else None,
            }
        )
    validation = pd.DataFrame(validation_rows)
    validation_path = derived / "validation_report.csv"
    write_csv(validation, validation_path)
    paths["validation_report"] = str(validation_path)

    contract = {
        "version": 1,
        "data_origin": "REAL_PUBLIC_HISTORICAL",
        "allowed_seasons": list(seasons),
        "simulation_data_used": False,
        "hindsight_rule": "Consumers must filter season <= career_clock_season before fit/evaluation.",
        "2010_2011_role": "Depth-chart role proxy plus weekly roster/injury evidence. No invented snap counts.",
        "2012_2014_role": "Observed PFR snap counts when player ID mapping succeeds; depth chart remains corroborating evidence.",
        "pass_rush": "Observed sacks, QB hits, TFL, forced fumbles. No hurries/pressures are invented.",
        "coverage": "Observed interceptions and passes defended. Targets/receptions/yards allowed are intentionally null.",
        "offensive_line": "Player role plus team protection/rushing context; team results are not assigned as individual credit.",
        "defensive_calls": "Calls may be recorded, but call-specific modifiers remain disabled without charted causal evidence.",
        "files": paths,
    }
    contract_path = derived / "EVIDENCE_CONTRACT.json"
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    paths["contract"] = str(contract_path)
    return paths
