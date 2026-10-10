#!/usr/bin/env python3
"""Build the engine-ready All-Star weekend files (`library/all_star/engine/<season>-<game_type>.json`) from the research.

    python scripts/build_all_star_engine.py            build every configured game not locked yet
    python scripts/build_all_star_engine.py --check    report unlocked games whose built file differs from a fresh build

A locked game's file is never rewritten (`all_star_games.lock` records its sha256 and validation refuses a change): its
request was frozen against it and the engine replays the game from it, so a research correction or a builder change
reaches only the games locked after it. `--check` lists such a file as kept.

Each built file holds (`runtime/all_star_engine.py`, `runtime/all_star_games.py`):
* the game: season, type, date (the season's All-Star calendar, `library/<year>/league/nba_<season>_all_star.json`)
  and event id;
* `environment`: the real editions of the same game published before it (`library/all_star/games`: the five most
  recent All-Star Games, the Rookies-versus-Sophomores games from 2001, up to five; an `excluded` edition never counts),
  their team totals per 48 minutes (All-Star Game) or per 40 (Rookie Challenge) in the NBA engine's environment form,
  with player-rate baselines from the anchors' own rates in those games and the half-court clock factor (CLOCK_FACTOR).
  The previous year's edition must be researched (a year without the game is in NO_GAME), so a later game is never
  built on an older baseline;
* `translation`: an NBA player's rates in exhibition terms, fitted on anchors (every player of those editions with at
  least ANCHOR_MINUTES minutes in the season the game belongs to, `library/all_star/anchor_seasons.json`, which must
  hold every played line's season; never the real Wade): a logit shift for two-point, three-point and free-throw percentages from pooled makes against the anchors'
  season percentages on the same attempts, the three-point and free-throw shifts lightly shrunk toward no change
  (PRIOR_ATTEMPTS; 73 to 230 attempts each); a ratio for three-point attempts, free-throw attempts and turnovers per
  field goal attempt pooled by attempts, for fouls pooled by minutes, and for usage, assist, rebound, steal and block
  rates minute-weighted (the FIBA method). The two-point shift and the ratios stay unshrunk: their samples are large
  (450 to 910 two-point attempts, 560 to 1,140 field goal attempts, 1,200 to 2,500 minutes), every edition differs from
  the NBA in the same direction, so a pull toward no change is a known bias (in the calibration probe 2 to 4% too few
  points and 10 to 20% too many free throws), and the baselines are the anchors' own rates in the games, so only the
  raw ratio keeps the anchors' translated mean on them;
* `minutes`: the coaches' minutes by rank, the baseline editions' minutes averaged by rank (starters and reserves apart
  where the box records them), each team-game first scaled to regulation, then normalized to the game's 240 or 200
  team minutes and rounded to whole minutes.
Nothing reads the game's own result or any later edition. The configuration below records every judgement.
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

from runtime.all_star_engine import MODEL_VERSION, RATIO_KEYS, SHIFT_KEYS, engine_path              # noqa: E402
from runtime.era import exhibition_rules                                                          # noqa: E402
from runtime.player_stats import RATE_KEYS                                                         # noqa: E402

GAMES_DIR = Path("library/all_star/games")
ANCHORS = Path("library/all_star/anchor_seasons.json")
BASELINE_EDITIONS = 5             # the most recent real editions of the same game before it
ANCHOR_MINUTES = 300              # an anchor's season needs this many minutes
PRIOR_ATTEMPTS = 100              # light shrinkage of the three-point and free-throw shifts toward no change: FIBA's
                                  # heavier priors and minute weighting distorted these small samples (25% too many
                                  # turnovers and free throws in the probe); the rest stays unshrunk (module docstring)
SHRUNK_SHIFTS = ("three_point_pct", "free_throw_pct")
DEFENSE_INTENSITY = 0.0           # the fit already contains the defense played in the real games (docs/engine_model.md)
CLOCK_FACTOR = 0.97               # half-court possession seconds: holding for a period's last shot, the four-second
                                  # floor and the late-game clock cost about 2% of possessions at exhibition pace (11 to
                                  # 12 seconds against the NBA's 15.5; the calibration probe, docs/engine_model.md)
AND_ONE_SHARE = 0.12              # the NBA environments' structural assumption, unchanged
WADE_BBR = "wadedw01"
SHAPE = {"all_star": {"starters": 5, "reserves": 7, "full": 48, "overtime": 5},
         "rookie_challenge": {"starters": 5, "reserves": 4, "full": 40, "overtime": 2}}
LABELS = {"all_star": "All-Star Game", "rookie_challenge": "Rookie Challenge"}
SLUG = {"all_star": "all-star-game", "rookie_challenge": "rookie-challenge"}
NO_GAME = {1999: "the 1998-99 lockout cancelled the All-Star weekend"}
# Games to build: (season, game type). Each reads its date from the season's All-Star calendar.
CONFIG = [("2003-04", "rookie_challenge"), ("2003-04", "all_star"), ("2004-05", "rookie_challenge"),
          ("2004-05", "all_star"), ("2005-06", "rookie_challenge"), ("2005-06", "all_star")]


def _read(path, root=ROOT):
    return json.loads((Path(root) / path).read_text(encoding="utf-8"))


def game_date(season, game_type, root=ROOT):
    from runtime.seasons import path
    key = "all_star_game" if game_type == "all_star" else "rookie_challenge"
    return _read(path(season, "all_star"), root)["dates"][key]["value"]


def event_id(game_type, day):
    return f"{day}-{SLUG[game_type]}"


def editions(root=ROOT):
    """Every researched real edition: {(year, game type): data}."""
    folder = Path(root) / GAMES_DIR
    return {(d["year"], d["game_type"]): d for d in (json.loads(p.read_text(encoding="utf-8"))
                                                     for p in sorted(folder.glob("*.json")))}


def baseline(game_type, day, root=ROOT):
    """The real editions of the same game published on or before the day, the most recent BASELINE_EDITIONS. Refuses
    when the previous year's real edition is not researched: the newest researched ones would be an older baseline."""
    found = editions(root)
    last = int(day[:4]) - 1
    while last in NO_GAME:
        last -= 1
    if (last, game_type) not in found:
        raise ValueError(f"the real {last} {LABELS[game_type]} is not researched (library/all_star/games): a game on "
                         f"{day} would be built on older editions")
    usable = [d for (_, kind), d in sorted(found.items())
              if kind == game_type and d["published_after"] <= day and not d.get("excluded")]
    if not usable:
        raise ValueError(f"no real {game_type} edition is published before {day}")
    return usable[-BASELINE_EDITIONS:]


def _usable(p):
    """An edition line that may feed a fit: played, and never the real Wade's (alternate history)."""
    return p["minutes"] > 0 and p.get("bbr_id") != WADE_BBR and not p.get("protagonist_real_history")


def regulation_share(game_type, g):
    """Regulation's share of an edition's length (its overtimes at the era's length): totals and minutes are scaled to
    regulation by it. The box's summed team minutes are not used, as a rounding (the 2001 Rookies' 203) would bias it."""
    shape = SHAPE[game_type]
    return shape["full"] / (shape["full"] + g["overtimes"] * shape["overtime"])


def _poss(t):
    return t["fga"] + 0.44 * t["fta"] - t["orb"] + t["tov"]


def game_rates(p, team, opp):
    """A player's rates in one game (Basketball-Reference formulas, as fractions), from his team's and his opponents'
    totals in that game."""
    mp, five = p["minutes"], team["team_minutes"] / 5
    t, o = team["totals"], opp["totals"]
    teammates_fgm = (mp / five) * t["fgm"] - p["fgm"]               # field goals made by his teammates while he played
    return {"usage_pct": (p["fga"] + 0.44 * p["fta"] + p["tov"]) * five / (mp * (t["fga"] + 0.44 * t["fta"] + t["tov"])),
            "assist_pct": p["ast"] / teammates_fgm if teammates_fgm > 0 else None,
            "offensive_rebound_pct": p["orb"] * five / (mp * (t["orb"] + o["drb"])),
            "defensive_rebound_pct": p["drb"] * five / (mp * (t["drb"] + o["orb"])),
            "steal_pct": p["stl"] * five / (mp * _poss(o)),
            "block_pct": p["blk"] * five / (mp * (o["fga"] - o["tpa"]))}


def season_rates(row):
    """An anchor's season rates in the engine's definitions."""
    f = lambda k: row[k] or 0
    return {"two_point_pct": f("x2p") / f("x2pa") if f("x2pa") else None,
            "three_point_pct": f("x3p") / f("x3pa") if f("x3pa") else None,
            "free_throw_pct": f("ft") / f("fta") if f("fta") else None,
            "three_point_attempt_rate": f("x3pa") / f("fga") if f("fga") else None,
            "free_throw_attempt_rate": f("fta") / f("fga") if f("fga") else None,
            "turnovers_per_fga": f("tov") / f("fga") if f("fga") else None,
            "fouls_per_minute": f("pf") / row["minutes"],
            **{k: row[k] for k in ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct",
                                   "steal_pct", "block_pct")}}


def anchors(games, root=ROOT):
    """[(line, game rates, season rates, edition id)] for every anchor line of the baseline editions. Refuses a played
    line without its season in the anchor file: an unresearched season would silently shrink the fit."""
    seasons = _read(ANCHORS, root)["players"]
    out = []
    for g in games:
        for side, team in g["teams"].items():
            opp = next(t for s, t in g["teams"].items() if s != side)
            for p in team["players"]:
                if not _usable(p):
                    continue
                row = seasons.get(p.get("bbr_id") or "", {}).get(g["season"])
                if not row:
                    raise ValueError(f"{p['player']} ({g['year']} {LABELS[g['game_type']]}): no {g['season']} season in {ANCHORS}")
                if row["minutes"] < ANCHOR_MINUTES:
                    continue
                out.append((p, game_rates(p, team, opp), season_rates(row), f"{g['year']}-{g['game_type']}"))
    return out


def _logit(x):
    x = min(1 - 1e-6, max(1e-6, x))
    return math.log(x / (1 - x))


SHOTS = {"two_point_pct": (lambda p: p["fgm"] - p["tpm"], lambda p: p["fga"] - p["tpa"]),
         "three_point_pct": (lambda p: p["tpm"], lambda p: p["tpa"]),
         "free_throw_pct": (lambda p: p["ftm"], lambda p: p["fta"])}
PER_ATTEMPT = {"three_point_attempt_rate": "tpa", "free_throw_attempt_rate": "fta", "turnovers_per_fga": "tov"}


def translation(pairs):
    """NBA season rates to exhibition terms, fitted on the anchors (see the module docstring)."""
    shift, ratio, raw, sample = {}, {}, {}, {}
    for k in SHIFT_KEYS:
        made, att = SHOTS[k]
        use = [(p, s) for p, _, s, _ in pairs if s[k] is not None]
        m, a = sum(made(p) for p, _ in use), sum(att(p) for p, _ in use)
        expected = sum(att(p) * s[k] for p, s in use) / a
        raw[k] = _logit(m / a) - _logit(expected)
        shift[k] = round(raw[k] * (a / (a + PRIOR_ATTEMPTS) if k in SHRUNK_SHIFTS else 1), 5)
        sample[k] = a
    for k, count in PER_ATTEMPT.items():
        use = [(p, s) for p, _, s, _ in pairs if s[k] is not None]
        raw[k] = sum(p[count] for p, _ in use) / sum(p["fga"] * s[k] for p, s in use)
        sample[k] = sum(p["fga"] for p, _ in use)
    minutes = sum(p["minutes"] for p, _, _, _ in pairs)
    raw["fouls_per_minute"] = sum(p["pf"] for p, _, _, _ in pairs) / sum(p["minutes"] * s["fouls_per_minute"] for p, _, s, _ in pairs)
    sample["fouls_per_minute"] = round(minutes, 1)
    for k in ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct"):
        use = [(p["minutes"], g[k], s[k]) for p, g, s, _ in pairs if s[k] and g[k] is not None]
        raw[k] = sum(m * x for m, x, _ in use) / sum(m * n for m, _, n in use)
        sample[k] = round(sum(m for m, _, _ in use), 1)
    ratio = {k: round(raw[k], 5) for k in RATIO_KEYS}
    assert set(ratio) == set(RATIO_KEYS)
    return {"model_version": MODEL_VERSION, "shift": shift, "ratio": ratio,
            "raw": {k: round(v, 5) for k, v in raw.items()}, "anchors": len(pairs),
            "shrinkage": {"prior_attempts": PRIOR_ATTEMPTS, "shrunk": list(SHRUNK_SHIFTS),
                          "unshrunk": "the two-point shift and every ratio (module docstring)"},
            "anchor_games": sorted({e for *_, e in pairs}), "sample": sample,
            "method": "scripts/build_all_star_engine.translation"}


def rate_baselines(pairs):
    """The anchors' rates in the games: pooled for percentages and per-attempt rates, minute-weighted otherwise."""
    lines = [p for p, _, _, _ in pairs]
    total = lambda f: sum(f(p) for p in lines)
    out = {k: total(made) / total(att) for k, (made, att) in SHOTS.items()}
    out.update({k: total(lambda p: p[c]) / total(lambda p: p["fga"]) for k, c in PER_ATTEMPT.items()})
    out["fouls_per_minute"] = total(lambda p: p["pf"]) / total(lambda p: p["minutes"])
    for k in ("usage_pct", "assist_pct", "offensive_rebound_pct", "defensive_rebound_pct", "steal_pct", "block_pct"):
        use = [(p["minutes"], g[k]) for p, g, _, _ in pairs if g[k] is not None]
        out[k] = sum(m * x for m, x in use) / sum(m for m, _ in use)
    assert set(out) == set(RATE_KEYS)
    return {k: round(out[k], 6) for k in RATE_KEYS}


def environment(game_type, day, games, pairs):
    """The baseline editions' team totals per regulation game, in the engine's environment form."""
    full = SHAPE[game_type]["full"]
    sums, n = defaultdict(float), 0
    for g in games:
        scale = regulation_share(game_type, g)
        for team in g["teams"].values():
            for k, v in team["totals"].items():
                sums[k] += v * scale
            n += 1
    a = {k: v / n for k, v in sums.items()}
    label = f"{SLUG[game_type].replace('-', '_')}_{games[0]['year']}_{games[-1]['year']}"
    return {
        "schema_version": 1, "league": "NBA All-Star Weekend", "kind": "league_environment", "season": label,
        "baseline": [f"{g['year']}-{g['game_type']}" for g in games], "published_after": games[-1]["published_after"],
        "unit": f"per team per {full}-minute game",
        "purpose": (f"Calibration for the {LABELS[game_type]}: the real averages of the editions published before it "
                    "(the repository's environment policy), each team-game scaled to regulation (`regulation_share`)."),
        "averages": {"pace": round(_poss(a), 3), "points": round(a["pts"], 3), "fga": round(a["fga"], 3),
                     "fg_pct": round(a["fgm"] / a["fga"], 5), "three_pa": round(a["tpa"], 3),
                     "three_pct": round(a["tpm"] / a["tpa"], 5), "fta": round(a["fta"], 3),
                     "ft_pct": round(a["ftm"] / a["fta"], 5), "orb": round(a["orb"], 3), "drb": round(a["drb"], 3),
                     "ast": round(a["ast"], 3), "stl": round(a["stl"], 3), "blk": round(a["blk"], 3),
                     "tov": round(a["tov"], 3), "pf": round(a["pf"], 3)},
        "engine_assumptions": {"status": "structural assumptions, as the NBA environments, for a neutral exhibition",
                               "home_edge_points_per_game": 0.0, "and_one_share_of_fta": AND_ONE_SHARE,
                               "defense_intensity": DEFENSE_INTENSITY,
                               "defense_note": "Individual defensive values are off: the translation is fitted on real "
                                               "exhibition games and already contains the defense played in them.",
                               "possession_seconds_factor": CLOCK_FACTOR,
                               "clock_note": "The half-court possession is shortened: holding for a period's last shot, "
                                             "the four-second floor and the late-game clock were balanced at NBA "
                                             "possession lengths and cost about 2% of possessions at exhibition pace."},
        "team_turnovers_per_game": 0.0,
        "team_turnover_note": "The published team totals equal the players' sums; every turnover is a player's.",
        "player_rating_model": MODEL_VERSION,
        "player_rate_baselines": rate_baselines(pairs),
        "source": GAMES_DIR.as_posix(),
        "verification": {"status": "derived_from_sourced_totals",
                         "method": "per team-game means of the editions' published team totals (Basketball-Reference)"},
    }


def minutes_template(game_type, games):
    """The coaches' minutes by rank: starters and reserves apart where the box records them (the All-Star Game), else
    every player by minutes (the Rookie Challenge, whose top five by minutes stand for its starters)."""
    shape = SHAPE[game_type]
    total, ranks = 5 * shape["full"], defaultdict(list)
    for g in games:
        scale = regulation_share(game_type, g)
        for team in g["teams"].values():
            played = [p for p in team["players"] if p["minutes"] > 0]
            if all(p["role"] for p in team["players"]):
                groups = [("starter", shape["starters"]), ("reserve", shape["reserves"])]
                lists = [sorted((p["minutes"] for p in played if p["role"] == role), reverse=True) for role, _ in groups]
            else:
                ordered = sorted((p["minutes"] for p in played), reverse=True)
                lists = [ordered[:shape["starters"]], ordered[shape["starters"]:]]
                groups = [("starter", shape["starters"]), ("reserve", shape["reserves"])]
            slot = 0
            for values, (_, size) in zip(lists, groups):
                values = (values + [0.0] * size)[:size]
                for v in values:
                    ranks[slot].append(v * scale)
                    slot += 1
    means = [sum(ranks[i]) / len(ranks[i]) for i in range(len(ranks))]
    scaled = [m * total / sum(means) for m in means]
    whole = [math.floor(x) for x in scaled]
    for i in sorted(range(len(scaled)), key=lambda i: (-(scaled[i] - whole[i]), i))[:total - sum(whole)]:
        whole[i] += 1                                     # largest remainders, so the template sums to the game
    return {"starters": whole[:shape["starters"]], "reserves": whole[shape["starters"]:], "team_minutes": total,
            "basis": "the baseline editions' minutes averaged by rank, each team-game scaled to regulation"}


def build(season, game_type, root=ROOT):
    day = game_date(season, game_type, root)
    rules = exhibition_rules(game_type, day)
    if rules["season"] != season:
        raise ValueError(f"{season} {game_type}: its date {day} is in {rules['season']}")
    games = baseline(game_type, day, root)
    pairs = anchors(games, root)
    env = environment(game_type, day, games, pairs)
    last_anchor_season = max(g["season"] for g in games)
    published = f"{int(last_anchor_season[:4]) + 1}-06-30"       # the anchors' seasons close with their league year
    if published > day or env["published_after"] > day:
        raise ValueError(f"{season} {game_type}: a baseline is not published before {day}")
    sources = {p.as_posix(): hashlib.sha256((Path(root) / p).read_bytes()).hexdigest()
               for p in [GAMES_DIR / f"{g['year']}-{g['game_type']}.json" for g in games] + [ANCHORS]}
    return {"schema_version": 1, "kind": "all_star_engine_game", "season": season, "game_type": game_type,
            "name": LABELS[game_type], "game_date": day, "event_id": event_id(game_type, day),
            "model_version": MODEL_VERSION, "rules": {k: v for k, v in rules.items() if k != "season"},
            "environment": env, "translation": dict(translation(pairs), published_after=published),
            "minutes": minutes_template(game_type, games), "sources": sources,
            "method": "scripts/build_all_star_engine.py; runtime/all_star_engine.py"}


def locked(season, game_type, root=ROOT):
    """Whether the game is locked (`all_star_games.json`): its engine file is then fixed."""
    from runtime.all_star_games import read_record
    return game_type in read_record(root, season)["games"]


def refresh(root=ROOT, write=True):
    """(stale, kept): configured games whose file differs from a fresh build (written when `write`), and locked games
    whose file differs but is kept as their request was frozen against it (module docstring)."""
    stale, kept = [], []
    text = lambda season, game_type: json.dumps(build(season, game_type, root), indent=1, ensure_ascii=False,
                                                sort_keys=True) + "\n"
    for season, game_type in CONFIG:
        path = Path(root) / engine_path(season, game_type)
        if path.is_file() and locked(season, game_type, root):
            try:
                same = path.read_text(encoding="utf-8") == text(season, game_type)
            except ValueError:                           # the research no longer builds it: the file stands all the same
                same = False
            if not same:
                kept.append(f"{season}-{game_type}")
            continue
        fresh = text(season, game_type)
        if path.is_file() and path.read_text(encoding="utf-8") == fresh:
            continue
        stale.append(f"{season}-{game_type}")
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(fresh, encoding="utf-8")
    return stale, kept


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale, kept = refresh(ROOT, write=not args.check)
    print(("stale: " if args.check else "built: ") + (", ".join(stale) or "none"))
    if kept:
        print("kept (locked; a fresh build differs): " + ", ".join(kept))
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
