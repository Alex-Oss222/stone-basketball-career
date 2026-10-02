from __future__ import annotations

import math
from functools import reduce

import numpy as np
import pandas as pd

from .guards import tag_real_evidence
from .normalize import OL_POSITIONS, first_existing, normalize_position, normalize_team, numeric


def _regular_season(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("season_type", "game_type"):
        if col in df.columns:
            return df.loc[df[col].astype("string").str.upper().eq("REG")].copy()
    return df.copy()


def _season_col(df: pd.DataFrame) -> pd.Series:
    if "season" not in df.columns:
        raise ValueError("Missing season column")
    return pd.to_numeric(df["season"], errors="coerce").astype("Int64")


def _depth_role(depth: pd.DataFrame) -> pd.DataFrame:
    depth = _regular_season(depth)
    depth["season"] = _season_col(depth)
    team_col = first_existing(depth, ["club_code", "team"])
    if not team_col:
        raise ValueError("Depth chart data missing team/club_code")
    depth["team"] = normalize_team(depth[team_col])
    if "gsis_id" not in depth.columns:
        raise ValueError("Depth chart data missing gsis_id")
    depth["player_id"] = depth["gsis_id"].astype("string")
    name_col = first_existing(depth, ["full_name", "football_name", "player_name"])
    pos_col = first_existing(depth, ["position", "pos_abb", "pos_name"])
    depth["player_name"] = depth[name_col].astype("string") if name_col else pd.NA
    depth["position"] = normalize_position(depth[pos_col]) if pos_col else pd.NA
    depth["week"] = numeric(depth.get("week"), depth.index)
    depth["depth_team_n"] = numeric(depth.get("depth_team"), depth.index)

    keys = ["season", "team", "player_id"]
    base = (
        depth.groupby(keys, dropna=False)
        .agg(
            player_name=("player_name", "first"),
            position=("position", "first"),
            depth_weeks_listed=("week", lambda s: s.dropna().nunique()),
            median_depth_team=("depth_team_n", "median"),
        )
        .reset_index()
    )

    for n in (1, 2, 3):
        counts = (
            depth.loc[depth["depth_team_n"].eq(n)]
            .groupby(keys, dropna=False)["week"]
            .nunique()
            .rename(f"depth{n}_weeks")
            .reset_index()
        )
        base = base.merge(counts, on=keys, how="left")
    for c in ("depth1_weeks", "depth2_weeks", "depth3_weeks"):
        base[c] = base[c].fillna(0).astype(int)

    denom = base["depth_weeks_listed"].replace(0, np.nan)
    base["depth1_share"] = base["depth1_weeks"] / denom
    base["depth2_share"] = base["depth2_weeks"] / denom

    base["depth_role"] = np.select(
        [
            base["depth1_share"].ge(0.5),
            base["depth1_weeks"].gt(0) | base["depth2_share"].ge(0.5),
            base["depth_weeks_listed"].gt(0),
        ],
        ["starter_depth", "rotation_depth", "reserve_depth"],
        default="unknown",
    )
    return base


def _roster_availability(rosters: pd.DataFrame) -> pd.DataFrame:
    rosters = _regular_season(rosters)
    rosters["season"] = _season_col(rosters)
    team_col = first_existing(rosters, ["team", "club_code", "team_abbr"])
    id_col = first_existing(rosters, ["gsis_id", "player_id"])
    week_col = first_existing(rosters, ["week", "week_number"])
    if not team_col or not id_col or not week_col:
        raise ValueError("Weekly roster data requires team, gsis/player ID, and week")
    rosters["team"] = normalize_team(rosters[team_col])
    rosters["player_id"] = rosters[id_col].astype("string")
    rosters["week_n"] = numeric(rosters[week_col], rosters.index)
    name_col = first_existing(rosters, ["full_name", "player_name", "display_name"])
    pos_col = first_existing(rosters, ["position", "pos"])
    status_col = first_existing(rosters, ["status", "roster_status"])
    rosters["player_name"] = rosters[name_col].astype("string") if name_col else pd.NA
    rosters["position"] = normalize_position(rosters[pos_col]) if pos_col else pd.NA
    if status_col:
        rosters["roster_status"] = rosters[status_col].astype("string")
    else:
        rosters["roster_status"] = pd.NA

    keys = ["season", "team", "player_id"]
    out = (
        rosters.groupby(keys, dropna=False)
        .agg(
            roster_player_name=("player_name", "first"),
            roster_position=("position", "first"),
            rostered_weeks=("week_n", lambda s: s.dropna().nunique()),
            roster_statuses=("roster_status", lambda s: "|".join(sorted({str(x) for x in s.dropna()}))),
        )
        .reset_index()
    )
    return out


def _injury_availability(injuries: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "season", "team", "player_id", "injury_report_weeks", "out_report_weeks",
        "doubtful_report_weeks", "questionable_report_weeks", "dnp_practice_weeks",
    ]
    if injuries.empty:
        return pd.DataFrame(columns=columns)
    injuries = _regular_season(injuries)
    if injuries.empty:
        return pd.DataFrame(columns=columns)
    injuries["season"] = _season_col(injuries)
    team_col = first_existing(injuries, ["team", "club_code"])
    id_col = first_existing(injuries, ["gsis_id", "player_id"])
    if not team_col or not id_col:
        raise ValueError("Injury data requires team and gsis/player ID")
    injuries["team"] = normalize_team(injuries[team_col])
    injuries["player_id"] = injuries[id_col].astype("string")
    injuries["week_n"] = numeric(injuries.get("week"), injuries.index)
    status = injuries.get("report_status", pd.Series(pd.NA, index=injuries.index, dtype="string")).astype("string").str.upper()
    practice = injuries.get("practice_status", pd.Series(pd.NA, index=injuries.index, dtype="string")).astype("string").str.upper()
    injuries["is_out"] = status.str.contains(r"\bOUT\b", na=False)
    injuries["is_doubtful"] = status.str.contains("DOUBT", na=False)
    injuries["is_questionable"] = status.str.contains("QUESTION", na=False)
    injuries["did_not_practice"] = practice.str.contains("DID NOT|DNP", na=False)

    keys = ["season", "team", "player_id"]
    rows = []
    for key, g in injuries.groupby(keys, dropna=False):
        def unique_weeks(mask: pd.Series) -> int:
            return int(g.loc[mask, "week_n"].dropna().nunique())

        rows.append(
            {
                "season": key[0],
                "team": key[1],
                "player_id": key[2],
                "injury_report_weeks": int(g["week_n"].dropna().nunique()),
                "out_report_weeks": unique_weeks(g["is_out"]),
                "doubtful_report_weeks": unique_weeks(g["is_doubtful"]),
                "questionable_report_weeks": unique_weeks(g["is_questionable"]),
                "dnp_practice_weeks": unique_weeks(g["did_not_practice"]),
            }
        )
    return pd.DataFrame(rows)


def _snap_role(snaps: pd.DataFrame, players: pd.DataFrame | None = None) -> pd.DataFrame:
    snaps = _regular_season(snaps)
    snaps["season"] = _season_col(snaps)
    snaps["team"] = normalize_team(snaps["team"])
    snaps["pfr_id"] = snaps["pfr_player_id"].astype("string")
    snaps["player_name"] = snaps["player"].astype("string")
    snaps["position"] = normalize_position(snaps["position"])

    for c in ("offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps", "st_pct"):
        snaps[c] = numeric(snaps.get(c), snaps.index)

    keys = ["season", "team", "pfr_id"]
    out = (
        snaps.groupby(keys, dropna=False)
        .agg(
            snap_player_name=("player_name", "first"),
            snap_position=("position", "first"),
            snap_games=("week", lambda s: pd.to_numeric(s, errors="coerce").dropna().nunique()),
            offense_snaps=("offense_snaps", "sum"),
            defense_snaps=("defense_snaps", "sum"),
            st_snaps=("st_snaps", "sum"),
            mean_offense_pct=("offense_pct", "mean"),
            mean_defense_pct=("defense_pct", "mean"),
            mean_st_pct=("st_pct", "mean"),
        )
        .reset_index()
    )
    if players is not None and {"pfr_id", "gsis_id"}.issubset(players.columns):
        mapping = players[["pfr_id", "gsis_id"]].dropna().drop_duplicates("pfr_id")
        mapping["pfr_id"] = mapping["pfr_id"].astype("string")
        mapping["player_id"] = mapping["gsis_id"].astype("string")
        out = out.merge(mapping[["pfr_id", "player_id"]], on="pfr_id", how="left")
    else:
        out["player_id"] = pd.NA

    out["main_unit"] = np.select(
        [out["offense_snaps"].ge(out["defense_snaps"]) & out["offense_snaps"].ge(out["st_snaps"]),
         out["defense_snaps"].ge(out["offense_snaps"]) & out["defense_snaps"].ge(out["st_snaps"])],
        ["offense", "defense"],
        default="special_teams",
    )
    out["main_unit_mean_pct"] = np.select(
        [out["main_unit"].eq("offense"), out["main_unit"].eq("defense")],
        [out["mean_offense_pct"], out["mean_defense_pct"]],
        default=out["mean_st_pct"],
    )
    # nflverse/PFR snap percentage fields are normally fractions (1.00 = 100%).
    # Be tolerant of a future/source export that uses 0-100 percentages.
    pct_max = out["main_unit_mean_pct"].max(skipna=True)
    pct_scale = 100.0 if pd.notna(pct_max) and pct_max > 1.5 else 1.0
    out["snap_role"] = np.select(
        [
            out["main_unit_mean_pct"].ge(0.65 * pct_scale),
            out["main_unit_mean_pct"].ge(0.25 * pct_scale),
            out["main_unit_mean_pct"].gt(0),
        ],
        ["starter_usage", "rotation_usage", "reserve_usage"],
        default="unknown",
    )
    return out


def build_role_evidence(
    depth_charts: pd.DataFrame,
    weekly_rosters: pd.DataFrame,
    injuries: pd.DataFrame,
    snap_counts: pd.DataFrame | None = None,
    players: pd.DataFrame | None = None,
) -> pd.DataFrame:
    depth = _depth_role(depth_charts)
    roster = _roster_availability(weekly_rosters)
    injury = _injury_availability(injuries)
    out = depth.merge(roster, on=["season", "team", "player_id"], how="outer")
    out = out.merge(injury, on=["season", "team", "player_id"], how="left")

    out["player_name"] = out["player_name"].fillna(out.get("roster_player_name"))
    out["position"] = out["position"].fillna(out.get("roster_position"))
    for c in ["injury_report_weeks", "out_report_weeks", "doubtful_report_weeks", "questionable_report_weeks", "dnp_practice_weeks"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)

    if snap_counts is not None and not snap_counts.empty:
        snaps = _snap_role(snap_counts, players)
        snap_cols = [
            "season", "team", "player_id", "pfr_id", "snap_games", "offense_snaps", "defense_snaps", "st_snaps",
            "mean_offense_pct", "mean_defense_pct", "mean_st_pct", "main_unit", "main_unit_mean_pct", "snap_role",
        ]
        out = out.merge(snaps[snap_cols], on=["season", "team", "player_id"], how="outer")
        out["measurement"] = np.where(out["snap_games"].notna(), "SNAP_OBSERVED", "DEPTH_CHART_PROXY")
        out["role_class"] = out["snap_role"].fillna(out["depth_role"])
        out["id_match_status"] = np.select(
            [
                out["player_id"].notna() & out["pfr_id"].notna(),
                out["player_id"].isna() & out["pfr_id"].notna(),
                out["player_id"].notna(),
            ],
            ["PFR_TO_GSIS_MATCHED", "UNMATCHED_PFR_ID", "GSIS_ONLY"],
            default="MISSING_ID",
        )
    else:
        out["measurement"] = "DEPTH_CHART_PROXY"
        out["role_class"] = out["depth_role"]
        out["id_match_status"] = np.where(out["player_id"].notna(), "GSIS_ONLY", "MISSING_ID")

    out["not_reported_out_weeks"] = (out.get("rostered_weeks", 0).fillna(0) - out.get("out_report_weeks", 0).fillna(0)).clip(lower=0)
    return tag_real_evidence(out, "role_availability_public")


def build_pass_disruption(player_stats: pd.DataFrame, role_evidence: pd.DataFrame | None = None) -> pd.DataFrame:
    stats = _regular_season(player_stats)
    stats["season"] = _season_col(stats)
    stats["team"] = normalize_team(stats["team"])
    stats["player_id"] = stats["player_id"].astype("string")

    metrics = ["def_sacks", "def_qb_hits", "def_tackles_for_loss", "def_fumbles_forced"]
    for c in metrics:
        if c not in stats.columns:
            stats[c] = np.nan
        stats[c] = numeric(stats[c], stats.index)

    name_col = first_existing(stats, ["player_display_name", "player_name"])
    keys = ["season", "team", "player_id"]
    out = stats.groupby(keys, dropna=False)[metrics].sum(min_count=1).reset_index()
    if name_col:
        names = stats.groupby(keys, dropna=False)[name_col].first().rename("player_name").reset_index()
        out = out.merge(names, on=keys, how="left")
    if "position" in stats.columns:
        pos = stats.groupby(keys, dropna=False)["position"].first().rename("position").reset_index()
        out = out.merge(pos, on=keys, how="left")

    if role_evidence is not None and "defense_snaps" in role_evidence.columns:
        snap = role_evidence[keys + ["defense_snaps"]].drop_duplicates(keys)
        out = out.merge(snap, on=keys, how="left")
        denom = out["defense_snaps"].replace(0, np.nan)
        for c in metrics:
            out[f"{c}_per_100_def_snaps"] = out[c] / denom * 100
        out["rate_denominator"] = np.where(denom.notna(), "DEFENSIVE_SNAPS", "UNAVAILABLE")
    else:
        out["rate_denominator"] = "UNAVAILABLE"
    return tag_real_evidence(out, "player_stats_defense")


def build_coverage_evidence(player_stats: pd.DataFrame, role_evidence: pd.DataFrame | None = None) -> pd.DataFrame:
    stats = _regular_season(player_stats)
    stats["season"] = _season_col(stats)
    stats["team"] = normalize_team(stats["team"])
    stats["player_id"] = stats["player_id"].astype("string")
    metrics = ["def_interceptions", "def_pass_defended", "def_tackles", "def_tackles_solo"]
    for c in metrics:
        if c not in stats.columns:
            stats[c] = np.nan
        stats[c] = numeric(stats[c], stats.index)
    keys = ["season", "team", "player_id"]
    out = stats.groupby(keys, dropna=False)[metrics].sum(min_count=1).reset_index()
    name_col = first_existing(stats, ["player_display_name", "player_name"])
    if name_col:
        names = stats.groupby(keys, dropna=False)[name_col].first().rename("player_name").reset_index()
        out = out.merge(names, on=keys, how="left")
    if "position" in stats.columns:
        pos = stats.groupby(keys, dropna=False)["position"].first().rename("position").reset_index()
        out = out.merge(pos, on=keys, how="left")

    if role_evidence is not None and "defense_snaps" in role_evidence.columns:
        snap = role_evidence[keys + ["defense_snaps"]].drop_duplicates(keys)
        out = out.merge(snap, on=keys, how="left")
        denom = out["defense_snaps"].replace(0, np.nan)
        out["interceptions_per_100_def_snaps"] = out["def_interceptions"] / denom * 100
        out["passes_defended_per_100_def_snaps"] = out["def_pass_defended"] / denom * 100
        out["rate_denominator"] = np.where(denom.notna(), "DEFENSIVE_SNAPS", "UNAVAILABLE")
    else:
        out["rate_denominator"] = "UNAVAILABLE"
    out["coverage_targets_allowed"] = np.nan
    out["coverage_yards_allowed"] = np.nan
    out["coverage_assignment_status"] = "NOT_AVAILABLE_FROM_PUBLIC_2010_2014_SOURCES"
    return tag_real_evidence(out, "player_stats_coverage_observables")


def _bool_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    x = numeric(df[col], df.index)
    return x.fillna(0).ne(0)


def build_team_defense(pbp: pd.DataFrame) -> pd.DataFrame:
    pbp = _regular_season(pbp)
    pbp["season"] = _season_col(pbp)
    if "defteam" not in pbp.columns:
        raise ValueError("PBP missing defteam")
    pbp["team"] = normalize_team(pbp["defteam"])
    pbp = pbp.loc[pbp["team"].notna()].copy()
    if "no_play" in pbp.columns:
        pbp = pbp.loc[~_bool_col(pbp, "no_play")].copy()

    epa = numeric(pbp.get("epa"), pbp.index)
    yards = numeric(pbp.get("yards_gained"), pbp.index)
    pass_attempt = _bool_col(pbp, "pass_attempt")
    sack = _bool_col(pbp, "sack")
    qb_dropback = _bool_col(pbp, "qb_dropback") if "qb_dropback" in pbp.columns else (pass_attempt | sack)
    rush = _bool_col(pbp, "rush_attempt")
    qb_hit = _bool_col(pbp, "qb_hit")
    interception = _bool_col(pbp, "interception")
    complete = _bool_col(pbp, "complete_pass")

    pbp["_epa"] = epa
    pbp["_yards"] = yards
    pbp["_dropback"] = qb_dropback
    pbp["_rush"] = rush
    pbp["_sack"] = sack
    pbp["_qb_hit"] = qb_hit
    pbp["_int"] = interception
    pbp["_complete"] = complete
    pbp["_pass_attempt"] = pass_attempt
    pbp["_pass_play"] = qb_dropback
    pbp["_expl_pass"] = pass_attempt & yards.ge(20)
    pbp["_expl_run"] = rush & yards.ge(10)
    pbp["_success"] = _bool_col(pbp, "success") if "success" in pbp.columns else epa.gt(0)
    pbp["_third_conv"] = _bool_col(pbp, "third_down_converted")
    pbp["_third_fail"] = _bool_col(pbp, "third_down_failed")

    rows = []
    for (season, team), g in pbp.groupby(["season", "team"], dropna=False):
        drop = g["_dropback"]
        rush_m = g["_rush"]
        third = g["_third_conv"] | g["_third_fail"]
        pass_attempts = g["_pass_attempt"]
        row = {
            "season": season,
            "team": team,
            "def_plays": int((drop | rush_m).sum()),
            "def_epa_per_play": g.loc[drop | rush_m, "_epa"].mean(),
            "success_rate_allowed": g.loc[drop | rush_m, "_success"].mean(),
            "opponent_dropbacks": int(drop.sum()),
            "pass_epa_allowed_per_dropback": g.loc[drop, "_epa"].mean(),
            "sacks": int(g.loc[drop, "_sack"].sum()),
            "sack_rate": g.loc[drop, "_sack"].mean() if drop.any() else np.nan,
            "qb_hits": int(g.loc[drop, "_qb_hit"].sum()),
            "qb_hit_rate": g.loc[drop, "_qb_hit"].mean() if drop.any() else np.nan,
            "interceptions": int(g.loc[drop, "_int"].sum()),
            "interception_rate_per_dropback": g.loc[drop, "_int"].mean() if drop.any() else np.nan,
            "completion_rate_allowed": g.loc[pass_attempts, "_complete"].mean() if pass_attempts.any() else np.nan,
            "explosive_pass_rate_allowed": g.loc[drop, "_expl_pass"].mean() if drop.any() else np.nan,
            "opponent_rushes": int(rush_m.sum()),
            "rush_epa_allowed_per_rush": g.loc[rush_m, "_epa"].mean(),
            "explosive_run_rate_allowed": g.loc[rush_m, "_expl_run"].mean() if rush_m.any() else np.nan,
            "third_down_conversion_rate_allowed": g.loc[third, "_third_conv"].mean() if third.any() else np.nan,
        }
        rows.append(row)
    return tag_real_evidence(pd.DataFrame(rows), "nflverse_pbp_team_defense")


def build_team_offense_line_context(pbp: pd.DataFrame) -> pd.DataFrame:
    pbp = _regular_season(pbp)
    pbp["season"] = _season_col(pbp)
    if "posteam" not in pbp.columns:
        raise ValueError("PBP missing posteam")
    pbp["team"] = normalize_team(pbp["posteam"])
    pbp = pbp.loc[pbp["team"].notna()].copy()
    if "no_play" in pbp.columns:
        pbp = pbp.loc[~_bool_col(pbp, "no_play")].copy()

    pbp["_epa"] = numeric(pbp.get("epa"), pbp.index)
    pbp["_dropback"] = _bool_col(pbp, "qb_dropback") if "qb_dropback" in pbp.columns else (_bool_col(pbp, "pass_attempt") | _bool_col(pbp, "sack"))
    pbp["_sack"] = _bool_col(pbp, "sack")
    pbp["_qb_hit"] = _bool_col(pbp, "qb_hit")
    pbp["_rush"] = _bool_col(pbp, "rush_attempt")
    pbp["_rush_success"] = _bool_col(pbp, "success") if "success" in pbp.columns else pbp["_epa"].gt(0)

    rows = []
    for (season, team), g in pbp.groupby(["season", "team"], dropna=False):
        drop = g["_dropback"]
        rush = g["_rush"]
        rows.append(
            {
                "season": season,
                "team": team,
                "team_dropbacks": int(drop.sum()),
                "team_sacks_allowed": int(g.loc[drop, "_sack"].sum()),
                "team_sack_rate_allowed": g.loc[drop, "_sack"].mean() if drop.any() else np.nan,
                "team_qb_hits_recorded": int(g.loc[drop, "_qb_hit"].sum()),
                "team_qb_hit_rate_recorded": g.loc[drop, "_qb_hit"].mean() if drop.any() else np.nan,
                "team_pass_epa_per_dropback": g.loc[drop, "_epa"].mean(),
                "team_rushes": int(rush.sum()),
                "team_rush_epa_per_rush": g.loc[rush, "_epa"].mean(),
                "team_rush_success_rate": g.loc[rush, "_rush_success"].mean() if rush.any() else np.nan,
            }
        )
    return tag_real_evidence(pd.DataFrame(rows), "nflverse_pbp_ol_team_context")


def build_ol_evidence(role_evidence: pd.DataFrame, team_context: pd.DataFrame) -> pd.DataFrame:
    role = role_evidence.copy()
    role["position"] = normalize_position(role["position"])
    role = role.loc[role["position"].isin(OL_POSITIONS)].copy()
    context_cols = [c for c in team_context.columns if c not in {"data_origin", "source_dataset"}]
    out = role.merge(team_context[context_cols], on=["season", "team"], how="left")
    out["individual_blocking_charting_status"] = "UNAVAILABLE_FREE_2010_2014"
    out["team_context_not_individual_credit"] = True
    return tag_real_evidence(out, "ol_role_plus_team_context")


def defensive_call_policy() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season_start": 2010,
                "season_end": 2014,
                "call_type": "coverage_shell_or_blitz",
                "effect_modifier": np.nan,
                "status": "NOT_ESTIMATED",
                "reason": "No free public 2010-2014 play-level coverage/rusher charting in the approved evidence set.",
                "engine_rule": "Record user call, apply no call-specific result modifier.",
                "data_origin": "REAL_PUBLIC_HISTORICAL",
                "source_dataset": "policy_guard",
            }
        ]
    )
