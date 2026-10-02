import math

import pandas as pd

from free_nfl_evidence.transforms import (
    build_coverage_evidence,
    build_pass_disruption,
    build_role_evidence,
    build_team_defense,
)


def test_2010_depth_role_without_fake_snaps():
    depth = pd.DataFrame(
        {
            "season": [2010, 2010, 2010, 2010],
            "club_code": ["MIA"] * 4,
            "week": [1, 2, 3, 4],
            "game_type": ["REG"] * 4,
            "depth_team": ["1", "1", "1", "2"],
            "gsis_id": ["p1"] * 4,
            "full_name": ["Player One"] * 4,
            "position": ["T"] * 4,
        }
    )
    roster = pd.DataFrame(
        {
            "season": [2010] * 4,
            "team": ["MIA"] * 4,
            "week": [1, 2, 3, 4],
            "game_type": ["REG"] * 4,
            "gsis_id": ["p1"] * 4,
            "full_name": ["Player One"] * 4,
            "position": ["T"] * 4,
            "status": ["ACT"] * 4,
        }
    )
    injuries = pd.DataFrame(
        {
            "season": [2010],
            "team": ["MIA"],
            "week": [4],
            "season_type": ["REG"],
            "gsis_id": ["p1"],
            "report_status": ["Questionable"],
            "practice_status": ["Limited"],
        }
    )
    out = build_role_evidence(depth, roster, injuries)
    row = out.iloc[0]
    assert row["role_class"] == "starter_depth"
    assert row["measurement"] == "DEPTH_CHART_PROXY"
    assert "offense_snaps" not in out.columns


def test_pass_rush_does_not_invent_pressures():
    stats = pd.DataFrame(
        {
            "season": [2010], "season_type": ["REG"], "team": ["MIA"], "player_id": ["p1"],
            "player_display_name": ["Player One"], "position": ["DE"],
            "def_sacks": [7], "def_qb_hits": [10], "def_tackles_for_loss": [12], "def_fumbles_forced": [2],
        }
    )
    out = build_pass_disruption(stats)
    assert out.loc[0, "def_sacks"] == 7
    assert out.loc[0, "rate_denominator"] == "UNAVAILABLE"
    assert "pressures" not in out.columns


def test_coverage_marks_missing_assignment_data():
    stats = pd.DataFrame(
        {
            "season": [2011], "season_type": ["REG"], "team": ["MIA"], "player_id": ["p2"],
            "player_display_name": ["Player Two"], "position": ["CB"],
            "def_interceptions": [4], "def_pass_defended": [11], "def_tackles": [55], "def_tackles_solo": [44],
        }
    )
    out = build_coverage_evidence(stats)
    assert math.isnan(out.loc[0, "coverage_targets_allowed"])
    assert out.loc[0, "coverage_assignment_status"].startswith("NOT_AVAILABLE")


def test_team_defense_metrics_from_pbp():
    pbp = pd.DataFrame(
        {
            "season": [2010] * 4,
            "season_type": ["REG"] * 4,
            "defteam": ["MIA"] * 4,
            "epa": [-0.5, 0.4, -0.8, 0.2],
            "yards_gained": [5, 25, -7, 3],
            "qb_dropback": [1, 1, 1, 0],
            "pass_attempt": [1, 1, 0, 0],
            "sack": [0, 0, 1, 0],
            "qb_hit": [0, 1, 1, 0],
            "interception": [0, 1, 0, 0],
            "complete_pass": [1, 0, 0, 0],
            "rush_attempt": [0, 0, 0, 1],
            "success": [0, 1, 0, 1],
            "third_down_converted": [0, 0, 0, 1],
            "third_down_failed": [0, 0, 1, 0],
            "no_play": [0, 0, 0, 0],
        }
    )
    out = build_team_defense(pbp)
    row = out.iloc[0]
    assert row["opponent_dropbacks"] == 3
    assert row["sacks"] == 1
    assert abs(row["sack_rate"] - 1 / 3) < 1e-9


def test_snap_fraction_scale_classifies_starter_usage():
    depth = pd.DataFrame(
        {
            "season": [2012], "club_code": ["KC"], "week": [1], "game_type": ["REG"],
            "depth_team": ["1"], "gsis_id": ["g1"], "full_name": ["Guard One"], "position": ["G"],
        }
    )
    roster = pd.DataFrame(
        {
            "season": [2012], "team": ["KC"], "week": [1], "game_type": ["REG"],
            "gsis_id": ["g1"], "full_name": ["Guard One"], "position": ["G"], "status": ["ACT"],
        }
    )
    injuries = pd.DataFrame(
        columns=["season", "team", "week", "season_type", "gsis_id", "report_status", "practice_status"]
    )
    snaps = pd.DataFrame(
        {
            "season": [2012], "team": ["KC"], "week": [1], "game_type": ["REG"],
            "player": ["Guard One"], "pfr_player_id": ["GuarOn00"], "position": ["G"],
            "offense_snaps": [60], "offense_pct": [0.90], "defense_snaps": [0], "defense_pct": [0.0],
            "st_snaps": [0], "st_pct": [0.0],
        }
    )
    players = pd.DataFrame({"pfr_id": ["GuarOn00"], "gsis_id": ["g1"]})
    out = build_role_evidence(depth, roster, injuries, snaps, players)
    row = out.loc[out["player_id"].eq("g1")].iloc[0]
    assert row["measurement"] == "SNAP_OBSERVED"
    assert row["role_class"] == "starter_usage"
