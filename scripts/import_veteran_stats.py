#!/usr/bin/env python3
"""Rebuild the 2003 veteran baseline. No requests are created and no games run."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.player_stats import (CUTOFF, GRADE_LABELS, MODEL_VERSION, RATINGS_PATH,
                                 STATS_PATH, RatingIndex, build_ratings, read_json, sha256)

LEAGUE = Path("library/2003/league")
TEAM = Path("career/Dwyane_Wade/2003-04/00_Team/Team")
ENV_PATH = LEAGUE / "nba_2002_03_league_environment.json"
AUDIT_PATH = LEAGUE / "nba_2003_veteran_import_report.json"
SOURCE_LINK = "../../../../../../" + str(STATS_PATH)
METHOD_LINK = "../../../../../../docs/statistical_ratings.md"


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def outputs(root=ROOT):
    data = read_json(root / STATS_PATH)
    ratings = build_ratings(data, sha256(root / STATS_PATH))
    index = RatingIndex(ratings)
    env = read_json(root / ENV_PATH)
    env["averages"] = data["league_averages"][0]["averages"]
    env["verification"] = {
        "status": "imported_source",
        "method": "Supplied Basketball-Reference league averages and pinned mirror provenance; player totals and recomputable rates validated locally. External ESPN cross-check was reported by the data collector, not independently repeated by this importer.",
        "source_file": str(STATS_PATH), "source_sha256": ratings["source_sha256"],
        "sources": data["league_averages"][0]["sources"],
    }
    # 29 teams x 82 games. The player source's combined rows are counted once.
    team_games = 29 * 82
    player_tov = ratings["source_totals"]["turnovers"] / team_games
    residual = env["averages"]["tov"] - player_tov
    if not 0 <= residual < 1:
        raise ValueError("team/player turnover gap needs review")
    env["team_turnovers_per_game"] = residual
    env["team_turnover_note"] = "Inferred residual: published team TOV minus summed individual TOV / (29 * 82). Includes source rounding; treated as unassigned team turnovers, not player turnovers."
    env["player_turnovers_per_game"] = player_tov
    env["player_rating_model"] = MODEL_VERSION
    env["player_rate_baselines"] = ratings["rate_baselines"]
    roster = read_json(root / TEAM / "Roster/roster.json")
    matches, missing = {}, []
    for p in roster["players"]:
        found = index.lookup(p["name"], p.get("bbr_id"))
        if found:
            matches[p["id"]] = found["bbr_id"]
            p["bbr_id"] = found["bbr_id"]
        else:
            missing.append(p["name"])
    clubs = read_json(root / LEAGUE / "nba_2003_end_of_season.json")["clubs"]
    rows = [p for c in clubs.values() for p in c["players"]]
    unmatched = [{"player_id": p["player_id"], "bbr_id": p.get("bbr_id")}
                 for p in rows if not p.get("bbr_id") or not index.lookup(p["player_id"], p["bbr_id"])]
    audit = {
        "as_of": CUTOFF, "model_version": MODEL_VERSION,
        "source_file": str(STATS_PATH), "source_sha256": ratings["source_sha256"],
        "record_count": len(data["records"]),
        "under_100_minutes": sum(r["totals"]["minutes"] < 100 for r in data["records"]),
        "combined_traded_player_rows": sum(len(r["team_codes"]) > 1 for r in data["records"]),
        "null_advanced_fields": {r["bbr_id"]: [k for k,v in r["advanced"].items() if v is None]
                                 for r in data["records"] if None in r["advanced"].values()},
        "checks_passed": ["unique player and season", "completed 2002-03 season only", "count consistency",
                          "points reconcile", "TS%, 3PAr, FTr and TOV% agree with totals within source rounding",
                          "source URLs present", "all grades and rates reproducible"],
        "miami_card_matches": matches, "miami_without_2002_03_record": missing,
        "league_roster_rows": len(rows), "league_rows_without_verified_id_match": unmatched,
        "coverage_note": "All 428 source players get profiles, including veterans absent from the end-of-season roster snapshot. The duplicate Ken Johnson row with no BRef ID is not a new player; baseline rotations already deduplicate names. Roster membership and the 407-player current-season tracking registry are not expanded by this import.",
        "excluded": "2003 draft class; later-season statistics; unsourced shot-location skills and awards",
        "source_totals": ratings["source_totals"],
    }
    return {RATINGS_PATH: dump(ratings), ENV_PATH: dump(env), AUDIT_PATH: dump(audit),
            TEAM / "Roster/roster.json": dump(roster)}, data, ratings, audit


def pct(value):
    return "N/A" if value is None else f"{100*value:.1f}%"


def stat_row(r):
    t = r["totals"]
    def pg(key):
        return f"{t[key]/t['games']:.1f}" if t["games"] else "N/A"
    def shooting(made, attempted):
        return pct(t[made]/t[attempted]) if t[attempted] else "N/A"
    values = ["2002-03", ", ".join(r["team_codes"]), str(t["games"]), str(t["games_started"]),
              pg("minutes"), pg("points"), f"{(t['offensive_rebounds']+t['defensive_rebounds'])/t['games']:.1f}",
              *[pg(k) for k in ("assists", "steals", "blocks", "turnovers")],
              shooting("field_goals_made", "field_goals_attempted"),
              shooting("three_pointers_made", "three_pointers_attempted"),
              shooting("free_throws_made", "free_throws_attempted")]
    return "| " + " | ".join(values) + " |"


def grade_block(r, profile):
    t, o = r["totals"], profile["observed"]
    sample = "Very small sample" if t["minutes"] < 100 else "Sample"
    lines = ["<!-- veteran-grades:start -->", "**Statistical estimates, 20–80.** 50 is the median of players with at least 500 minutes; higher is better for the named statistic. These are estimates from prior production, not staff scouting grades.",
             f"**{sample}:** {t['games']} games, {t['minutes']:,} minutes in 2002-03. Small samples are pulled toward the league baseline.",
             "| Statistic | Grade | Recorded 2002-03 evidence |", "| --- | ---: | --- |"]
    counts = {"two_point_pct": (t["field_goals_made"]-t["three_pointers_made"], t["field_goals_attempted"]-t["three_pointers_attempted"]),
              "three_point_pct": (t["three_pointers_made"], t["three_pointers_attempted"]),
              "free_throw_pct": (t["free_throws_made"], t["free_throws_attempted"])}
    labels = {"true_shooting_pct": "TS", "assist_pct": "AST", "turnover_pct": "TOV",
              "offensive_rebound_pct": "ORB", "defensive_rebound_pct": "DRB", "steal_pct": "STL", "block_pct": "BLK"}
    for key, label in GRADE_LABELS.items():
        grade = profile["grades"][key]
        evidence = pct(o[key])
        if key in counts:
            evidence += f" ({counts[key][0]}/{counts[key][1]})"
        else:
            evidence = f"{labels[key]} {evidence}"
        if key == "turnover_pct":
            evidence += "; lower is better"
        lines.append(f"| {label} | {grade if grade is not None else 'Not assessed'} | {evidence} |")
    lines += [f"**Tendencies:** usage {pct(o['usage_pct'])}; threes {pct(o['three_point_attempt_rate'])} of field-goal attempts; {o['free_throw_attempt_rate']:.3f} free-throw attempts per field-goal attempt.",
              "**Not assessed:** overall ability, physical tools, shot creation, rim versus midrange finishing, passing decisions, off-ball play, on-ball defense, screen navigation, help defense and rim protection. Steals and blocks alone do not establish defensive ability.",
              f"[Source totals and rates]({SOURCE_LINK}) · [How grades and engine estimates are calculated]({METHOD_LINK}) · BRef ID: `{r['bbr_id']}`.",
              "<!-- veteran-grades:end -->"]
    return "\n\n".join(lines[:3]) + "\n\n" + "\n".join(lines[3:15]) + "\n\n" + "\n\n".join(lines[15:])


def card_outputs(data, ratings, audit, root=ROOT):
    state = read_json(root / "career/Dwyane_Wade/2003-04/current_state.json")
    if state["current_date"] != CUTOFF:
        raise ValueError("opening-card import is limited to the June 26 checkpoint; preserve later assessments")
    records = {r["bbr_id"]: r for r in data["records"]}
    result = {}
    for slug, pid in audit["miami_card_matches"].items():
        path = TEAM / "Player_Cards" / f"{slug}.md"
        text = (root/path).read_text(encoding="utf-8")
        r, profile = records[pid], ratings["players"][pid]
        t, a = r["totals"], r["advanced"]
        offense = f"**Offense:** In 2002-03: {t['points']/t['games']:.1f} points and {t['assists']/t['games']:.1f} assists per game; {pct(a['true_shooting_pct'])} true shooting at {pct(a['usage_pct'])} usage."
        defense = f"**Defense:** In 2002-03: {t['steals']/t['games']:.1f} steals and {t['blocks']/t['games']:.1f} blocks per game. Matchup defense and coverage execution are unassessed."
        # Replace only the original empty scouting statements, never a staff report.
        text = text.replace("**Offense:** Not assessed from the current repository evidence beyond the carried roster and depth role.", offense)
        text = text.replace("**Defense:** Not assessed from the current repository evidence beyond position and depth assignment.", defense)
        text = text.replace("**Best traits:** Not assessed.\n\n", "").replace("**Main weaknesses:** Not assessed.\n\n", "")
        block = grade_block(r, profile)
        if "<!-- veteran-grades:start -->" in text:
            text = re.sub(r"<!-- veteran-grades:start -->.*?<!-- veteran-grades:end -->", lambda _: block, text, flags=re.S)
        else:
            start, end = text.index("## Player grades"), text.index("## Changes and coaching notes")
            if "**Overall:** Not assessed." not in text[start:end]:
                raise ValueError(f"{slug}: existing staff assessment requires manual preservation")
            text = text[:start] + "## Player grades\n\n" + block + "\n\n" + text[end:]
        note = f"| June 26, 2003 | Added 2002-03 statistical estimates; no change to role or availability. | [Prior-season record]({SOURCE_LINK}) |"
        if note not in text:
            pos = text.index("## Sources and uncertainty")
            text = text[:pos].rstrip() + "\n" + note + "\n\n" + text[pos:]
        start, end = text.index("## Regular-season statistics by year"), text.index("## Playoff statistics by year")
        section = text[start:end]
        section = re.sub(r"\*\*Coverage:\*\*[^\n]*", "**Coverage:** 2002-03 regular season imported. Earlier seasons are not yet imported; 2003-04 has not started.", section)
        row = stat_row(r)
        if "| 2002-03 |" in section:
            section = re.sub(r"^\| 2002-03 \|[^\n]*", lambda _: row, section, count=1, flags=re.M)
        else:
            section = section.replace("| 2003-04 |", row + "\n| 2003-04 |", 1)
        details = ["<!-- veteran-details:start -->", "### Additional statistics", "",
                   "| Season | FGM | FGA | 3PM | 3PA | FTM | FTA | ORB | DRB | PF |",
                   "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                   "| 2002-03 | " + " | ".join(f"{t[k]/t['games']:.1f}" for k in (
                       "field_goals_made", "field_goals_attempted", "three_pointers_made", "three_pointers_attempted",
                       "free_throws_made", "free_throws_attempted", "offensive_rebounds", "defensive_rebounds", "personal_fouls")) + " |",
                   "<!-- veteran-details:end -->"]
        detail_block = "\n".join(details)
        if "<!-- veteran-details:start -->" in section:
            section = re.sub(r"<!-- veteran-details:start -->.*?<!-- veteran-details:end -->", lambda _: detail_block, section, flags=re.S)
        else:
            section = section.replace("\nSource:", "\n" + detail_block + "\n\nSource:", 1)
        source = f"Source: [2002-03 totals and advanced rates]({SOURCE_LINK}), `{pid}`. Team codes are Basketball-Reference codes."
        section = re.sub(r"^Source:[^\n]*", lambda _: source, section, flags=re.M)
        text = text[:start] + section + text[end:]
        result[path] = text
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only stale-output check")
    parser.add_argument("--update-cards", action="store_true", help="Import the opening Miami veteran grades and 2002-03 rows")
    args = parser.parse_args()
    generated, data, ratings, audit = outputs()
    if args.update_cards:
        generated.update(card_outputs(data, ratings, audit))
    stale = [str(p) for p, text in generated.items() if not (ROOT/p).exists() or (ROOT/p).read_text(encoding="utf-8") != text]
    if args.check:
        if stale:
            raise SystemExit("Stale import outputs: " + ", ".join(stale))
    else:
        for p, text in generated.items():
            (ROOT/p).write_text(text, encoding="utf-8")
    print(f"{len(ratings['players'])} veteran profiles; {len(audit['miami_card_matches'])} Miami matches; {audit['under_100_minutes']} samples under 100 minutes. "
          + ("Generated outputs are current." if args.check else f"Updated {len(stale)} files."))


if __name__ == "__main__":
    main()
