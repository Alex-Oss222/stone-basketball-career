#!/usr/bin/env python3
"""Import a completed season's real league averages as the next season's calibration environment.

  python scripts/import_league_environment.py --season 2004-05 --write
  python scripts/import_league_environment.py --season 2004-05 --page NBA_2005.html --check

Reads the League Average rows of the Per Game, Totals and Advanced team tables on the Basketball-Reference season
page (https://www.basketball-reference.com/leagues/NBA_<end>.html; --page reads a saved copy) and writes
`library/<end>/league/nba_<YYYY>_<YY>_league_environment.json` in the shape of the 2003-04 file. The rating model
label, player-rate baselines and team/player turnover split are left to `scripts/build_season_baseline.py`, which
adds them once the season's player totals are registered (`omitted_keys` names them until then). The engine
assumptions are carried unchanged from the previous environment file. League averages only: no team or player
result enters the file.
"""
import argparse
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SEASONS = {
    "2003-04": {"published_after": "2004-04-14", "retrieved_on": "2026-10-05"},
    "2004-05": {"published_after": "2005-04-20", "retrieved_on": "2026-10-06"},
}
AVERAGES = (("points", "pts", 1), ("fga", "fga", 1), ("fg_pct", "fg_pct", 3), ("three_pa", "fg3a", 1),
            ("three_pct", "fg3_pct", 3), ("fta", "fta", 1), ("ft_pct", "ft_pct", 3), ("orb", "orb", 1),
            ("drb", "drb", 1), ("ast", "ast", 1), ("stl", "stl", 1), ("blk", "blk", 1), ("tov", "tov", 1),
            ("pf", "pf", 1))


def years(season):
    start = int(season[:4])
    return start, start + 1


def stem(season):
    start, end = years(season)
    return f"nba_{start}_{str(end)[-2:]}"


def output_path(season):
    return Path(f"library/{years(season)[1]}/league/{stem(season)}_league_environment.json")


def page_url(season):
    return f"https://www.basketball-reference.com/leagues/NBA_{years(season)[1]}.html"


def read_page(season, page=None):
    if page:
        return Path(page).read_text(encoding="utf-8")
    request = Request(page_url(season), headers={"User-Agent": "Mozilla/5.0 (research import)"})
    with urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8")


def league_average(html, table):
    """{data-stat: text} of the League Average row of a team table (Basketball-Reference hides some tables in
    HTML comments)."""
    html = html.replace("<!--", "").replace("-->", "")
    start = html.find(f'id="{table}"')
    if start < 0:
        raise ValueError(f"table {table} not found")
    body = html[start:html.index("</table>", start)]
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        if "League Average" in row:
            return dict(re.findall(r'data-stat="([^"]+)"[^>]*>([^<]*)<', row))
    raise ValueError(f"no League Average row in {table}")


def _f(value):
    return float(value.replace(",", ""))


def build(season, html, root=ROOT):
    start, end = years(season)
    spec = SEASONS[season]
    per_game = league_average(html, "per_game-team")
    totals = league_average(html, "totals-team")
    adv = league_average(html, "advanced-team")
    pace, mp = _f(adv["pace"]), _f(per_game["mp"])
    averages = {"pace": pace}
    for key, stat, digits in AVERAGES:
        averages[key] = round(_f(per_game[stat]), digits)
    fga, fg, fg3, fta, ft, tov = (int(_f(totals[k])) for k in ("fga", "fg", "fg3", "fta", "ft", "tov"))
    pts = _f(per_game["pts"])
    ortg = round(pts / (pace * mp / 240) * 100, 1)
    if abs(ortg - _f(adv["off_rtg"])) > 0.15:
        raise ValueError(f"ORtg {adv['off_rtg']} does not match points and pace ({ortg})")
    checks = {"ft_per_fga": round(ft / fga, 3), "efg_pct": round((fg + 0.5 * fg3) / fga, 3),
              "tov_pct": round(100 * tov / (fga + 0.44 * fta + tov), 1)}
    for key, value in checks.items():
        published = _f(adv["ft_rate" if key == "ft_per_fga" else key])
        if abs(value - published) > (0.15 if key == "tov_pct" else 0.0015):
            raise ValueError(f"{key} {published} does not match the Totals row ({value})")
    for key, stat, digits in AVERAGES:
        if digits == 1 and abs(_f(totals[stat]) / int(totals["g"]) - averages[key]) > 0.1:
            raise ValueError(f"per-game {stat} does not match the Totals row")
    previous = json.loads((root / output_path(f"{start - 1}-{str(start)[-2:]}")).read_text(encoding="utf-8"))
    following = f"{end}-{str(end + 1)[-2:]}"
    return {
        "schema_version": 1, "league": "NBA", "season": season, "kind": "league_environment",
        "purpose": f"Calibration baseline for the {following} game engine. A season is simulated on the environment of the last completed season, never on its own final averages.",
        "published_after": spec["published_after"], "unit": "per team per game",
        "verification": {
            "status": "imported_source",
            "method": f"Read from the Basketball-Reference {season} season page League Average rows (Per Game, Totals and Advanced team tables) by scripts/import_league_environment.py. Per-game values cross-checked against the Totals row; ORtg recomputed from points and pace; eFG%, FT/FGA and TOV% recomputed from the Totals row. Player-rate baselines and the team-turnover residual are added by scripts/build_season_baseline.py from the season's player totals.",
            "sources": [{"table": "league_averages", "url": page_url(season), "provider": "Basketball-Reference",
                         "retrieved_on": spec["retrieved_on"],
                         "notes": "League Average row of the Per Game Stats team table; pace and four factors from the Advanced Stats team table League Average row."}],
        },
        "averages": averages,
        "engine_assumptions": dict(previous["engine_assumptions"],
                                   note=f"Copied unchanged from the {previous['season']} file's structure; not researched."),
        "extra_sourced_values": {
            "offensive_rating": _f(adv["off_rtg"]), "efg_pct": _f(adv["efg_pct"]), "tov_pct": _f(adv["tov_pct"]),
            "orb_pct": _f(adv["orb_pct"]), "ft_per_fga": _f(adv["ft_rate"]), "ts_pct": _f(adv["ts_pct"]),
            "fta_per_fga": _f(adv["fta_per_fga_pct"]), "three_pa_rate": _f(adv["fg3a_per_fga_pct"]),
            "minutes_per_game": mp, "fg": _f(per_game["fg"]), "three_p": _f(per_game["fg3"]),
            "two_p": _f(per_game["fg2"]), "two_pa": _f(per_game["fg2a"]), "two_pct": _f(per_game["fg2_pct"]),
            "ft": _f(per_game["ft"]), "trb": _f(per_game["trb"]),
            "status": "sourced", "source": page_url(season),
            "derived_checks": {
                "status": "derived",
                "ft_per_fga_from_totals": f"{ft}/{fga} = {checks['ft_per_fga']:.3f}",
                "efg_from_totals": f"({fg} + 0.5*{fg3})/{fga} = {checks['efg_pct']:.3f}",
                "tov_pct_from_totals": f"{tov}/({fga} + 0.44*{fta} + {tov}) = {checks['tov_pct'] / 100:.3f}",
                "ortg_from_pace": f"{per_game['pts']} / ({adv['pace']} * {per_game['mp']}/240) * 100 = {ortg}",
            },
        },
        "omitted_keys": {
            "team_turnovers_per_game": f"added by scripts/build_season_baseline.py from the {season} player totals",
            "player_turnovers_per_game": "same",
            "player_rating_model": "repo-internal",
            "player_rate_baselines": f"added by scripts/build_season_baseline.py from the {season} player totals",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="print the parsed averages; write nothing")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--season", required=True, choices=sorted(SEASONS))
    parser.add_argument("--page", help="a saved copy of the Basketball-Reference season page")
    args = parser.parse_args()
    data = build(args.season, read_page(args.season, args.page))
    if args.check:
        print(json.dumps(data["averages"]))
        return 0
    target = ROOT / output_path(args.season)
    if target.is_file() and "omitted_keys" not in json.loads(target.read_text(encoding="utf-8")):
        print(f"{output_path(args.season)} is already completed by build_season_baseline.py; not overwritten.")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output_path(args.season)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
