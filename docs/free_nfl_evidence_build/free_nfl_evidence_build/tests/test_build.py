from pathlib import Path

import pandas as pd

from free_nfl_evidence.build import build_evidence


def _write(df, path):
    df.to_csv(path, index=False)


def test_end_to_end_2010_workspace(tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()

    _write(pd.DataFrame({"pfr_id": ["GuarOn00"], "gsis_id": ["g1"]}), raw / "players_global.csv")
    _write(
        pd.DataFrame(
            {
                "season": [2010], "club_code": ["KC"], "week": [1], "game_type": ["REG"],
                "depth_team": ["1"], "gsis_id": ["g1"], "full_name": ["Guard One"], "position": ["G"],
            }
        ),
        raw / "depth_charts_2010.csv",
    )
    _write(
        pd.DataFrame(
            {
                "season": [2010], "team": ["KC"], "week": [1], "game_type": ["REG"],
                "gsis_id": ["g1"], "full_name": ["Guard One"], "position": ["G"], "status": ["ACT"],
            }
        ),
        raw / "weekly_rosters_2010.csv",
    )
    _write(
        pd.DataFrame(
            {
                "season": [2010], "team": ["KC"], "week": [1], "season_type": ["REG"],
                "gsis_id": ["g1"], "report_status": ["Questionable"], "practice_status": ["Limited"],
            }
        ),
        raw / "injuries_2010.csv",
    )
    _write(
        pd.DataFrame(
            {
                "season": [2010, 2010], "week": [1, 1], "season_type": ["REG", "REG"],
                "team": ["KC", "KC"], "player_id": ["g1", "d1"],
                "player_display_name": ["Guard One", "Defender One"], "position": ["G", "DE"],
                "def_sacks": [0, 1], "def_qb_hits": [0, 2], "def_tackles_for_loss": [0, 1],
                "def_fumbles_forced": [0, 0], "def_interceptions": [0, 0],
                "def_pass_defended": [0, 0], "def_tackles": [0, 3], "def_tackles_solo": [0, 2],
            }
        ),
        raw / "player_stats_2010.csv",
    )
    _write(
        pd.DataFrame(
            {
                "season": [2010, 2010], "season_type": ["REG", "REG"],
                "posteam": ["KC", "DEN"], "defteam": ["DEN", "KC"],
                "epa": [0.2, -0.4], "yards_gained": [8, -6],
                "qb_dropback": [1, 1], "pass_attempt": [1, 0], "sack": [0, 1],
                "qb_hit": [0, 1], "interception": [0, 0], "complete_pass": [1, 0],
                "rush_attempt": [0, 0], "success": [1, 0],
                "third_down_converted": [0, 0], "third_down_failed": [0, 0], "no_play": [0, 0],
            }
        ),
        raw / "pbp_2010.csv",
    )

    paths = build_evidence(tmp_path, [2010])
    assert Path(paths["role_availability"]).exists()
    assert Path(paths["team_defense"]).exists()
    assert Path(paths["validation_report"]).exists()
    role = pd.read_csv(paths["role_availability"])
    assert role.loc[0, "measurement"] == "DEPTH_CHART_PROXY"
    assert role.loc[0, "data_origin"] == "REAL_PUBLIC_HISTORICAL"
