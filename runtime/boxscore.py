"""Plain-text box score for a resolved game."""


def _row(name, r):
    return (f"{name:<24} {r['minutes']:>5.1f} {r['pts']:>4} {r['fgm']:>3}-{r['fga']:<3} "
            f"{r['tpm']:>2}-{r['tpa']:<3} {r['ftm']:>2}-{r['fta']:<3} {r['orb']:>3} {r['drb']:>3} "
            f"{r['ast']:>3} {r['stl']:>3} {r['blk']:>3} {r['tov']:>3} {r['pf']:>3}")


def render(result):
    home, away = result["home"], result["away"]
    score = result["final_score"]
    lines = [
        f"{away} {score['away']} at {home} {score['home']}" + (f" ({result['overtimes']}OT)" if result["overtimes"] else ""),
        f"{result['game_date']}  {result['season']} {result['game_type']}  event {result['event_id']}",
        f"Kernel {result['kernel']}, calibrated on {result['calibration']['baseline_season']} "
        f"({result['calibration']['status']})",
        "",
        "Period   " + " ".join(f"{i + 1:>4}" for i in range(result["periods"])) + "     T",
    ]
    for side, name in (("away", away), ("home", home)):
        lines.append(f"{name[:8]:<8} " + " ".join(f"{p:>4}" for p in result["period_scores"][side]) + f"  {score[side]:>4}")
    header = f"{'':<24} {'MIN':>5} {'PTS':>4} {'FG':^7} {'3P':^6} {'FT':^6} {'OR':>3} {'DR':>3} {'AST':>3} {'STL':>3} {'BLK':>3} {'TO':>3} {'PF':>3}"
    for side, name in (("away", away), ("home", home)):
        lines += ["", name, header]
        for r in result["player_stats"][side]:
            if r["seconds"] > 0:
                lines.append(_row(r["player_id"] + (" (DQ)" if r["fouled_out"] else ""), r))
        team = dict(result["team_stats"][side], minutes=result["game_seconds"] * 5 / 60)
        lines.append(_row("TEAM", team))
    return "\n".join(lines) + "\n"
