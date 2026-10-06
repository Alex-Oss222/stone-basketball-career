#!/usr/bin/env python3
"""Build the engine-ready FIBA editions (`library/fiba/engine/<edition id>.json`) from the researched files.

    python scripts/build_fiba_engine.py            build every configured edition
    python scripts/build_fiba_engine.py --check    report editions whose built file differs from a fresh build

Each built edition holds (`runtime/national_engine.py`, `runtime/national.py`):
* the normalized event (`runtime/fiba_editions.py`): groups, every game with its teams or bracket slots, rosters;
* the USA's selection mode and the places earned in earlier simulated editions (`qualification`);
* `environment`: the previous senior FIBA tournament's real per-game averages, gated by its publication date, in the
  NBA engine's environment form, with FIBA player-rate baselines from that tournament's players;
* `translation`: an NBA player's rates in FIBA terms, fitted on anchors (players with an NBA season and the FIBA
  tournament that followed it, both before the edition): a logit shift for two- and three-point percentages and a
  ratio for every other rate, each shrunk toward no change by the anchors' minutes;
* `fiba_profiles`: every rostered non-NBA player's FIBA rates from his senior tournaments before the edition, shrunk
  toward a replacement prior by sample, and his defense (a share of his team's defensive margin);
* `minutes`: each such player's minutes per game in those tournaments (the coach's trust).
Nothing reads the edition's own results. The configuration below records every judgement.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.fiba_editions import fiba_key, normalize              # noqa: E402
from runtime.player_stats import RATE_KEYS                         # noqa: E402

OUT = Path("library/fiba/engine")
STATS = Path("library/fiba/player_tournament_stats")
ENVIRONMENTS = Path("library/fiba/fiba_environments.json")
MODEL = "fiba-2006.1"
PRIOR_MINUTES = 120              # a FIBA player's rates: shrinkage toward the replacement prior (minutes)
PRIOR_ATTEMPTS = {"two_point_pct": 60, "three_point_pct": 30, "free_throw_pct": 20, "three_point_attempt_rate": 20,
                  "free_throw_attempt_rate": 30, "turnovers_per_fga": 60}
PRIOR_SHOOTING_GAP = 0.01        # the prior's two- and three-point percentages below the tournament average
PRIOR_SHARE = 0.95               # the prior's usage, assist, rebound, steal and block rates as a share of average
ANCHOR_PRIOR_MINUTES = 400       # translation: anchors' minutes needed for a full-weight shift (judgement)
TOURNAMENT_YEARS = 3             # a player's tournaments within this many years before the edition count
DEFENSE_SHRINK_GAMES = 8         # a team's defensive margin is shrunk by games played toward zero
RECENT_MONTHS = 15               # tournaments within this many months count fully, older ones at half weight

# Editions to build (the slug names events, requests and draws). `qualification` lists places earned in an earlier
# simulated edition: the k-th simulated qualifier takes the k-th real slot (`runtime/national.resolve_field`).
CONFIG = {
    "continental_qualifier_2005": {
        "raw": "library/2005/fiba/fiba_2005_americas_championship.json", "slug": "amc05", "tiebreak": "fiba_2004",
        "usa": {"selection": "real", "basis": "USA Basketball sent professionals from leagues other than the NBA in 2005 "
                "(library/2005/fiba/fiba_2005_americas_championship.json usa_participation); no NBA player was invited"},
        "baseline": "olympics_2004"},
    "world_cup_finals_2006": {
        "raw": "library/2006/fiba/fiba_2006_world_championship.json", "slug": "wc06", "tiebreak": "fiba_2004",
        "host": "Japan", "usa": {"selection": "committee"}, "baseline": "olympics_2004",
        "qualification": [{"source": "continental_qualifier_2005", "exclude": ["Argentina"], "ranks": [1, 2, 3, 4],
                           "slots": ["Brazil", "Venezuela", "United States", "Panama"], "wildcards": ["Puerto Rico"],
                           "basis": "library/2006/fiba/fiba_2006_qualification.json: four Americas places besides the 2004 "
                                    "Olympic champion (Argentina); the real qualifiers name the group slots only"}]},
    "continental_qualifier_2007": {
        "pending": "needs library/fiba/player_tournament_stats/fiba_2006_world_championship.json and the 2007 continental "
                   "championships (roadmap N1)",
        "raw": "library/2007/fiba/fiba_2007_americas_championship.json", "slug": "amc07", "tiebreak": "fiba_2004",
        "usa": {"selection": "committee"}, "baseline": "fiba_2006_world_championship"},
    "olympic_qualifier_2008": {
        "pending": "needs library/fiba/player_tournament_stats/fiba_2006_world_championship.json and the 2007 continental "
                   "championships (roadmap N1)",
        "raw": "library/2008/fiba/fiba_2008_olympic_qualifying_tournament.json", "slug": "oqt08", "tiebreak": "fiba_2004",
        "usa": {"selection": "committee"}, "baseline": "fiba_2006_world_championship",
        "qualification": [{"source": "continental_qualifier_2007", "ranks": [3, 4, 5],
                           "slots": ["Puerto Rico", "Brazil", "Canada"],
                           "basis": "2007 Americas places 3-5 go to the qualifying tournament"}]},
    "olympic_finals_2008": {
        "pending": "needs library/fiba/player_tournament_stats/fiba_2006_world_championship.json and the 2007 continental "
                   "championships (roadmap N1)",
        "raw": "library/2008/fiba/olympics_2008.json", "slug": "oly08", "tiebreak": "fiba_2004", "host": "China",
        "usa": {"selection": "committee"}, "baseline": "fiba_2006_world_championship",
        "qualification": [{"source": "continental_qualifier_2007", "ranks": [1, 2], "slots": ["United States", "Argentina"],
                           "basis": "2007 Americas places 1-2"},
                          {"source": "olympic_qualifier_2008", "ranks": [1, 2, 3], "slots": ["Germany", "Croatia", "Greece"],
                           "basis": "the qualifying tournament's first three places"}]},
}


def _read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _v(x):
    return x.get("value") if isinstance(x, dict) and "value" in x else x


# -- statistics -------------------------------------------------------------------------------------------------------
def tournaments(before, root=ROOT):
    """Researched per-player tournament files published before `before`, newest first."""
    folder = Path(root) / STATS
    out = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("published_after", "9999") <= before:
            out.append(data)
    return sorted(out, key=lambda d: d["published_after"], reverse=True)


def _team_totals(data):
    """{team: totals} from the file's team totals, else summed from its players."""
    teams = {}
    for t in data.get("team_totals") or []:
        teams[t["team"]] = t
    for p in data["players"]:
        if p["team"] in teams and teams[p["team"]].get("fga") is not None:
            continue
        t = teams.setdefault(p["team"], {"team": p["team"], "_summed": True})
        for k in ("minutes", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf", "pts"):
            t[k] = (t.get(k) or 0) + (p.get(k) or 0)
        t["games"] = max(t.get("games") or 0, p.get("games") or 0)
    return teams


def player_rates(p, team, league):
    """A player's rates in the NBA engine's definitions (Basketball-Reference formulas), from tournament totals; the
    opponents' totals are the tournament's average team (judgement: per-opponent totals are not researched)."""
    mp, tm_mp = p.get("minutes") or 0, (team.get("games") or 1) * 200
    if not league.get("fga"):                 # a partial record (FIBA Asia 2003 and 2005): free throws only
        return {k: None for k in RATE_KEYS} | {"free_throw_pct": p["ftm"] / p["fta"] if p.get("fta") else None}
    if mp <= 0:
        return None
    f = lambda k: p.get(k) or 0
    t = lambda k: team.get(k) or 0
    two_a, two_m = f("fga") - f("tpa"), f("fgm") - f("tpm")
    poss_team = t("fga") + 0.44 * t("fta") + t("tov")
    share = tm_mp / 5 / mp
    return {
        "two_point_pct": two_m / two_a if two_a else None,
        "three_point_pct": f("tpm") / f("tpa") if f("tpa") else None,
        "free_throw_pct": f("ftm") / f("fta") if f("fta") else None,
        "usage_pct": (f("fga") + 0.44 * f("fta") + f("tov")) * share / poss_team if poss_team else None,
        "assist_pct": f("ast") / ((mp / (tm_mp / 5)) * t("fgm") - f("fgm")) if t("fgm") else None,
        "offensive_rebound_pct": f("orb") * share / (t("orb") + league["drb"] * (team.get("games") or 1)),
        "defensive_rebound_pct": f("drb") * share / (t("drb") + league["orb"] * (team.get("games") or 1)),
        "steal_pct": f("stl") * share / (league["poss"] * (team.get("games") or 1)),
        "block_pct": f("blk") * share / ((league["fga"] - league["tpa"]) * (team.get("games") or 1)),
        "three_point_attempt_rate": f("tpa") / f("fga") if f("fga") else None,
        "free_throw_attempt_rate": f("fta") / f("fga") if f("fga") else None,
        "turnovers_per_fga": f("tov") / f("fga") if f("fga") else None,
        "fouls_per_minute": f("pf") / mp if p.get("pf") is not None else None,
    }


def league_averages(data):
    """Per team-game averages of a tournament (from its team totals)."""
    teams = _team_totals(data).values()
    games = sum(t.get("games") or 0 for t in teams)
    avg = {k: sum(t.get(k) or 0 for t in teams) / games for k in ("fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb",
                                                                  "ast", "stl", "blk", "tov", "pf", "pts")}
    avg["poss"] = avg["fga"] + 0.44 * avg["fta"] - avg["orb"] + avg["tov"]
    return avg


# -- the edition ------------------------------------------------------------------------------------------------------
def build(edition_id, cfg, root=ROOT):
    raw = _read(cfg["raw"])
    e = normalize(raw)
    e.update(edition_id=edition_id, slug=cfg["slug"], tiebreak=cfg["tiebreak"], usa=dict(cfg["usa"]),
             qualification=cfg.get("qualification", []), source_file=cfg["raw"],
             source_sha256=hashlib.sha256((Path(root) / cfg["raw"]).read_bytes()).hexdigest())
    if cfg.get("host"):
        e["host"] = cfg["host"]
    if e["usa"]["selection"] == "committee":
        e["rosters"].setdefault("United States", {"coach": None, "players": []})["players"] = []
    env, trans = environment(cfg["baseline"], e["first_game"], root)
    e["environment"], e["translation"] = env, trans
    from runtime.era import ability_season
    ability = ability_season(e["first_game"])
    index = None
    # Players of every earlier configured edition too: a simulated qualifier without a real roster here plays his
    # latest real roster (runtime/national.latest_roster), and each needs a profile for this edition.
    e["_all_rosters"] = []
    for other_id, other in CONFIG.items():
        o = e if other_id == edition_id else normalize(_read(other["raw"]))
        if o["first_game"] > e["first_game"] or other.get("pending"):
            continue
        for team, roster in o["rosters"].items():
            if team == "United States" and other["usa"]["selection"] == "committee":
                continue                                   # the committee's players are NBA players
            e["_all_rosters"].append((team, roster["players"]))
    e["fiba_profiles"], e["minutes"] = fiba_profiles_all(e, env, ability, index, root)
    del e["_all_rosters"]
    return e


def fiba_profiles_all(e, env, ability, index, root=ROOT):
    """FIBA profiles for this edition's rosters and every earlier configured edition's (each player under his team)."""
    profiles, minutes = {}, {}
    for team, players in e["_all_rosters"]:
        sub = dict(e, _all_rosters={team: {"players": players}})
        p, m = fiba_profiles(sub, env, ability, index, root)
        profiles.update(p)
        minutes.update(m)
    return profiles, minutes


SHIFT_KEYS = ("two_point_pct", "three_point_pct")
ATTEMPTS = {"two_point_pct": ("fgm2", "fga2"), "three_point_pct": ("tpm", "tpa"), "free_throw_pct": ("ftm", "fta")}
ANCHOR_PRIOR_ATTEMPTS = {"two_point_pct": 300, "three_point_pct": 150}
WADE_BBR = "wadedw01"


def _stats(slug, root=ROOT):
    return json.loads((Path(root) / STATS / f"{slug}.json").read_text(encoding="utf-8"))


def _usable(p):
    """A tournament record that may feed the simulation: never the real Wade's (alternate history)."""
    return p.get("bbr_id") != WADE_BBR and not p.get("protagonist_real_history") and (
        (p.get("minutes") or 0) > 0 or p.get("fta") is not None)


def _logit(x):
    x = min(1 - 1e-6, max(1e-6, x))
    return math.log(x / (1 - x))


def rate_baselines(data):
    """Minute-weighted average player rates in a tournament (pooled for percentages): the FIBA baselines."""
    league = league_averages(data)
    teams = _team_totals(data)
    rows = [(p, player_rates(p, teams[p["team"]], league)) for p in data["players"] if _usable(p)]
    out = {}
    for k in RATE_KEYS:
        if k in ATTEMPTS:
            made, att = ATTEMPTS[k]
            m = sum((p["fgm"] - p["tpm"]) if made == "fgm2" else (p.get(made) or 0) for p, _ in rows)
            a = sum((p["fga"] - p["tpa"]) if att == "fga2" else (p.get(att) or 0) for p, _ in rows)
            out[k] = m / a
            continue
        num = math.fsum(r[k] * p["minutes"] for p, r in rows if r and r.get(k) is not None)
        den = math.fsum(p["minutes"] for p, r in rows if r and r.get(k) is not None)
        out[k] = num / den
    return out


def environment(baseline, first_game, root=ROOT):
    """The previous tournament's averages in the engine's environment form, and the NBA-to-FIBA translation."""
    data = _stats(baseline, root)
    if data["published_after"] > first_game:
        raise ValueError(f"{baseline} is not published before {first_game}")
    a = league_averages(data)
    env = {
        "schema_version": 1, "league": "FIBA", "kind": "league_environment", "baseline": baseline,
        "season": baseline, "published_after": data["published_after"], "unit": "per team per 40-minute game",
        "purpose": f"Calibration for national games: the real averages of {data['tournament']}, the last senior FIBA "
                   "tournament completed before the edition (the repository's environment policy).",
        "averages": {"pace": round(a["poss"], 3), "points": round(a["pts"], 3), "fga": round(a["fga"], 3),
                     "fg_pct": round(a["fgm"] / a["fga"], 5), "three_pa": round(a["tpa"], 3),
                     "three_pct": round(a["tpm"] / a["tpa"], 5), "fta": round(a["fta"], 3),
                     "ft_pct": round(a["ftm"] / a["fta"], 5), "orb": round(a["orb"], 3), "drb": round(a["drb"], 3),
                     "ast": round(a["ast"], 3), "stl": round(a["stl"], 3), "blk": round(a["blk"], 3),
                     "tov": round(a["tov"], 3), "pf": round(a["pf"], 3)},
        "engine_assumptions": {"status": "provisional structural assumptions, as the NBA environments",
                               "home_edge_points_per_game": 3.0, "and_one_share_of_fta": 0.12},
        "team_turnovers_per_game": 0.0,
        "team_turnover_note": "FIBA's records keep no separate team turnovers; every turnover is a player's.",
        "player_turnovers_per_game": round(a["tov"], 3),
        "player_rating_model": MODEL,
        "player_rate_baselines": {k: round(v, 6) for k, v in rate_baselines(data).items()},
        "source": f"{STATS.as_posix()}/{baseline}.json",
        "verification": {"status": "derived_from_sourced_totals",
                         "method": "per team-game means of the tournament's team totals (FIBA statistics service)"},
    }
    return env, translation(first_game, env, root)


def translation(first_game, env, root=ROOT):
    """NBA rates to FIBA terms, fitted on anchors: every non-Wade player with an NBA season (from
    library/careers/nba_player_careers.json, the season that ended before the tournament) and a senior FIBA
    tournament published before the edition. Shooting: pooled FIBA makes against the anchors' NBA percentages on the
    same attempts, as a logit shift; every other rate: the minute-weighted ratio of FIBA to NBA. Each is shrunk toward
    no change by the anchors' sample."""
    careers = json.loads((Path(root) / "library/careers/nba_player_careers.json").read_text(encoding="utf-8"))["players"]
    pairs = []
    for data in tournaments(first_game, root):
        year = int(data["dates"]["end"][:4])
        season = f"{year - 1}-{str(year)[-2:]}"
        teams, league = _team_totals(data), league_averages(data)
        for p in data["players"]:
            nba = (careers.get(p.get("bbr_id") or "") or {}).get("seasons", {}).get(season)
            if not _usable(p) or not nba or (nba.get("minutes") or 0) < 300:
                continue
            fiba = player_rates(p, teams[p["team"]], league)
            pairs.append((p, fiba, nba["rates"], data["slug"]))
    shift, ratio, sample = {}, {}, {}
    for k in SHIFT_KEYS:
        made, att = ATTEMPTS[k]
        use = [(p, n) for p, _, n, _ in pairs if n.get(k) is not None and p.get("fga") is not None]
        m = sum((p["fgm"] - p["tpm"]) if made == "fgm2" else p[made] for p, _ in use)
        a = sum((p["fga"] - p["tpa"]) if att == "fga2" else p[att] for p, _ in use)
        expected = sum(((p["fga"] - p["tpa"]) if att == "fga2" else p[att]) * n[k] for p, n in use) / a
        raw = _logit(m / a) - _logit(expected)
        shift[k] = round(raw * a / (a + ANCHOR_PRIOR_ATTEMPTS[k]), 5)
        sample[k] = a
    for k in ("three_point_attempt_rate", "free_throw_attempt_rate", "turnovers_per_fga", "usage_pct", "assist_pct",
              "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct", "fouls_per_minute"):
        use = [(p["minutes"], f[k], n.get(k)) for p, f, n, _ in pairs if f.get(k) is not None and n.get(k)]
        minutes = sum(m for m, _, _ in use)
        raw = sum(m * f for m, f, _ in use) / sum(m * n for m, _, n in use)
        ratio[k] = round(1 + (raw - 1) * minutes / (minutes + ANCHOR_PRIOR_MINUTES), 5)
        sample[k] = minutes
    return {"model_version": MODEL, "shift": shift, "ratio": ratio, "anchors": len(pairs),
            "anchor_tournaments": sorted({t for *_, t in pairs}), "sample": sample,
            "method": "scripts/build_fiba_engine.translation"}


def _months(first, last):
    return (int(last[:4]) - int(first[:4])) * 12 + int(last[5:7]) - int(first[5:7])


def _match(p, roster_player, team):
    from runtime.player_stats import alias
    if p["team"] != team:
        return False
    if roster_player.get("birth_date") and p.get("birth_date"):
        return p["birth_date"] == roster_player["birth_date"] or alias(p["name"]) == alias(roster_player["name"])
    return alias(p["name"]) == alias(roster_player["name"])


def _defense(data):
    """{team: defensive margin per 100 possessions against the tournament average, shrunk by games}."""
    teams = _team_totals(data)
    poss = {t: (r["fga"] + 0.44 * r["fta"] - r["orb"] + r["tov"]) for t, r in teams.items() if r.get("fga")}
    if not poss or not all(teams[t].get("opp_pts") is not None for t in poss):
        return {}
    allowed = {t: teams[t]["opp_pts"] / poss[t] * 100 for t in poss}
    avg = sum(teams[t]["opp_pts"] for t in poss) / sum(poss.values()) * 100
    return {t: (avg - allowed[t]) * teams[t]["games"] / (teams[t]["games"] + DEFENSE_SHRINK_GAMES) for t in poss}


def fiba_profiles(e, env, ability, index, root=ROOT):
    """Every rostered player in FIBA terms. Whether a player with an NBA id plays on his translated NBA profile instead
    is decided when the rosters lock (`runtime/national.lock_rosters`: an NBA profile for the ability season)."""
    base = env["player_rate_baselines"]
    prior = dict(base)
    # The prior: a rostered national-team player without senior tournament records (usually a domestic-league
    # regular) plays a little below the tournament's average player (judgement, checked against the calibration run).
    for k in ("two_point_pct", "three_point_pct"):
        prior[k] = base[k] - PRIOR_SHOOTING_GAP
    prior["free_throw_pct"] = base["free_throw_pct"] - 0.02
    for k in ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct"):
        prior[k] = base[k] * PRIOR_SHARE
    sources = tournaments(e["first_game"], root)
    sources = [d for d in sources if int(d["dates"]["end"][:4]) >= int(e["first_game"][:4]) - TOURNAMENT_YEARS]
    digest = hashlib.sha256("".join(sorted(d["slug"] for d in sources)).encode()
                            + json.dumps(base, sort_keys=True).encode()).hexdigest()
    profiles, minutes = {}, {}
    for team, roster in e["_all_rosters"].items():
        for rp in roster["players"]:
            rows = []
            for data in sources:
                recency = 1.0 if _months(data["published_after"], e["first_game"]) <= RECENT_MONTHS else 0.5
                teams, league = _team_totals(data), league_averages(data)
                d = _defense(data)
                for p in data["players"]:
                    if _usable(p) and _match(p, rp, team):
                        rows.append((p, player_rates(p, teams[p["team"]], league), recency, d.get(team, 0.0)))
            rates = {}
            for k in RATE_KEYS:
                if k in ATTEMPTS:
                    made, att = ATTEMPTS[k]
                    m = sum(w * ((p["fgm"] - p["tpm"]) if made == "fgm2" else (p.get(made) or 0)) for p, _, w, _ in rows
                            if p.get("fga") is not None or k == "free_throw_pct")
                    a = sum(w * ((p["fga"] - p["tpa"]) if att == "fga2" else (p.get(att) or 0)) for p, _, w, _ in rows
                            if p.get("fga") is not None or k == "free_throw_pct")
                    n = PRIOR_ATTEMPTS[k]
                    rates[k] = (m + prior[k] * n) / (a + n)
                    continue
                use = [(w * p["minutes"], r[k]) for p, r, w, _ in rows if r and r.get(k) is not None]
                mins = sum(m for m, _ in use)
                n = PRIOR_ATTEMPTS.get(k, PRIOR_MINUTES)
                rates[k] = (sum(m * v for m, v in use) + prior[k] * n) / (mins + n)
            played = [(p["minutes"], p["games"], d) for p, _, _, d in rows if p.get("minutes") and p.get("games")]
            mins = sum(m for m, _, _ in played)
            defense = sum(m * d for m, _, d in played) / mins / 5 if mins else 0.0
            profiles[rp["fiba_key"]] = {
                "fiba_key": rp["fiba_key"], "model_version": MODEL, "as_of": e["first_game"],
                "season_end_year": int(ability[:4]) + 1, "source_sha256": digest,
                "rates": {k: round(max(0.0, v), 6) for k, v in rates.items()}, "defense": round(max(-6, min(6, defense)), 4)}
            games = sum(g for _, g, _ in played)
            if games:
                minutes[rp["fiba_key"]] = round(mins / games, 2)
    return profiles, minutes


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for edition_id, cfg in CONFIG.items():
        if cfg.get("pending"):
            print(f"pending: {edition_id} ({cfg['pending']})")
            continue
        built = build(edition_id, cfg)
        path = ROOT / OUT / f"{edition_id}.json"
        text = json.dumps(built, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            continue
        stale.append(edition_id)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    print(("stale: " if args.check else "built: ") + (", ".join(stale) or "none"))
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
