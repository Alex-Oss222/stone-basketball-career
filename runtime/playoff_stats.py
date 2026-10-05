"""2004 playoff statistics pages, from closed playoff results only.

The playoffs are a separate statistical record from the regular season (AGENTS.md, Stats and awards): these pages
read only `game_type == "playoff"` results — Miami's from its played notes under `08_Playoffs/<Round>/`, the league's
from `Stats_and_Awards/League/<season>/Playoffs/Games/` — and never mix them into a regular-season page. Each game
counts once. Pages are generated whole (no template) and checked by validation against a fresh build:

- `Stats_and_Awards/League/<season>/Playoffs/Playoff_Stats.md`: every player with a playoff game, by club (clubs in
  order of playoff wins), per-game production and shooting totals; then a table per round.
- `Stats_and_Awards/Team/<season>/Playoffs/Team_Playoff_Stats.md`: Miami's record by round and its players.

Percentages are recomputed from summed makes and attempts (`career_stats.aggregate`).
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from .career_stats import aggregate

ROOT = Path(__file__).resolve().parents[1]


def _active_season(root=None):
    """The career's live season (runtime/seasons.py), read from the repository a call works on."""
    from .seasons import active
    return active(root or ROOT)
PLAYER_DIR = Path("career/Dwyane_Wade")


def league_page_path(season):
    return PLAYER_DIR / f"Stats_and_Awards/League/{season}/Playoffs/Playoff_Stats.md"


def team_page_path(season):
    return PLAYER_DIR / f"Stats_and_Awards/Team/{season}/Playoffs/Team_Playoff_Stats.md"
MIAMI = "Miami Heat"
ROUND_LABELS = {"first_round": "First round", "conference_semifinals": "Conference semifinals",
                "conference_finals": "Conference finals", "finals": "NBA Finals"}
PROD = ["Player", "Club", "G", "GS", "MPG", "PPG", "RPG", "APG", "SPG", "BPG", "TOV/G", "FG", "FG%", "3P", "3P%", "FT", "FT%", "TS%"]


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def closed_playoff_results(root=ROOT, season=None, now=None):
    """Closed playoff results dated on or before the clock: [{result, request, note, source}] in date order."""
    season = season or _active_season(root)
    from .write_back import clock, miami_notes
    root = Path(root)
    now = now or clock(root)
    rows, seen = [], set()
    for info in miami_notes(root, season):
        if info["kind"] != "playoff" or info["meta"].get("status") != "played":
            continue
        if not info["result_path"] or not info["result_path"].is_file():
            continue
        result = _read(info["result_path"])
        if result.get("game_date", "") > now or not result.get("terminated"):
            continue
        request = _read(info["request_path"]) if info["request_path"].is_file() else None
        rows.append(dict(result=result, request=request, note=info["note"], source="miami"))
    folder = root / PLAYER_DIR / f"Stats_and_Awards/League/{season}/Playoffs/Games"
    for path in sorted(folder.glob("*.result.json")) if folder.is_dir() else []:
        result = _read(path)
        if result.get("game_type") != "playoff" or not result.get("terminated") or result.get("game_date", "") > now:
            continue
        request_path = path.with_name(path.name.replace(".result.json", ".request.json"))
        rows.append(dict(result=result, request=_read(request_path) if request_path.is_file() else None, note=None,
                         source="league"))
    out = []
    for row in sorted(rows, key=lambda r: (r["result"]["game_date"], r["result"]["event_id"])):
        if row["result"]["event_id"] in seen:
            raise ValueError(f"duplicate closed playoff result {row['result']['event_id']}")
        seen.add(row["result"]["event_id"])
        out.append(row)
    return out


def _round_of(record):
    """{event_id: round key} from the bracket record."""
    out = {}
    for s in (record or {}).get("series", []):
        for g in s["games"]:
            if g.get("event_id"):
                out[g["event_id"]] = s["round"]
    return out


def player_lines(rows, root=ROOT, season=None):
    """{(name, club): [career_stats records]} with each record's competition set to "playoff"."""
    season = season or _active_season(root)
    from .write_back import game_records
    from .award_decisions import registry_names
    names = registry_names(root, season)
    lines = defaultdict(list)
    for row in rows:
        for side, pid, _bbr, record in game_records(dict(row, note=row["note"]), root, season):
            record = dict(record, competition="playoff")
            lines[(names.get(pid, pid), row["result"][side])].append(record)
    return lines


def _pct(x):
    return "N/A" if x is None else f"{x:.3f}".lstrip("0") if x < 1 else "1.000"


def _n(x, places=1):
    return "N/A" if x is None else f"{x:.{places}f}"


def _row(name, club, s):
    t, pg, r = s["totals"], s["pg"], s["rates"]
    mk = lambda m, a: f"{t[m] or 0}-{t[a] or 0}"
    return [name, club, str(s["gp"]), str(s["gs"]), _n(pg["minutes"]), _n(pg["pts"]), _n(pg["reb"]), _n(pg["ast"]),
            _n(pg["stl"]), _n(pg["blk"]), _n(pg["tov"]), mk("fgm", "fga"), _pct(r["fg_pct"]), mk("tpm", "tpa"),
            _pct(r["three_pct"]), mk("ftm", "fta"), _pct(r["ft_pct"]), _pct(r["ts_pct"])]


def _table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                     + ["| " + " | ".join(r) + " |" for r in rows])


def _section(lines, keep=lambda rec: True, clubs_order=None):
    rows = []
    for (name, club), records in lines.items():
        s = aggregate([r for r in records if keep(r)])
        if s["gp"]:
            rows.append((club, name, s))
    order = {c: i for i, c in enumerate(clubs_order or [])}
    rows.sort(key=lambda x: (order.get(x[0], len(order)), x[0], -(x[2]["pg"]["minutes"] or 0), x[1]))
    return [_row(name, club, s) for club, name, s in rows]


def league_page(root=ROOT, season=None, now=None):
    season = season or _active_season(root)
    from .playoffs import read
    from .write_back import clock
    root = Path(root)
    now = now or clock(root)
    record = read(root, season)
    rows = closed_playoff_results(root, season, now)
    lines = player_lines(rows, root, season)
    rounds = _round_of(record)
    wins = defaultdict(int)
    for s in (record or {}).get("series", []):
        for c, w in s["wins"].items():
            wins[c] += w
    clubs = sorted(wins, key=lambda c: (-wins[c], c))
    out = [f"# {season} playoff statistics", "",
           f"Through {now}: {len(rows)} closed playoff game(s). Playoff games only, from closed results "
           "(`runtime/playoff_stats.py`); the regular season is a separate record. Clubs in order of playoff wins; "
           "percentages from summed makes and attempts. [Bracket and schedule](../Playoffs.md).", ""]
    if not rows:
        out += ["No playoff game has been played yet.", ""]
        return "\n".join(out)
    out += ["## All playoff games", "", _table(PROD, _section(lines, clubs_order=clubs)), ""]
    for key, label in ROUND_LABELS.items():
        ids = {e for e, r in rounds.items() if r == key}
        if not any(r["event_id"] in ids for recs in lines.values() for r in recs):
            continue
        out += [f"## {label}", "", _table(PROD, _section(lines, keep=lambda r, ids=ids: r["event_id"] in ids, clubs_order=clubs)), ""]
    return "\n".join(out).rstrip() + "\n"


def team_page(root=ROOT, season=None, now=None):
    season = season or _active_season(root)
    from .playoffs import read
    from .write_back import clock
    root = Path(root)
    now = now or clock(root)
    record = read(root, season)
    rows = [r for r in closed_playoff_results(root, season, now) if MIAMI in (r["result"]["home"], r["result"]["away"])]
    lines = {k: v for k, v in player_lines(rows, root, season).items() if k[1] == MIAMI}
    out = [f"# Miami Heat {season} playoff statistics", "",
           f"Through {now}: {len(rows)} closed Miami playoff game(s). Playoff games only (`runtime/playoff_stats.py`). "
           f"[League playoff statistics](../../../League/{season}/Playoffs/Playoff_Stats.md) · "
           f"[bracket](../../../League/{season}/Playoffs.md).", ""]
    series = [s for s in (record or {}).get("series", []) if MIAMI in s["clubs"]]
    if series:
        srows = []
        for s in series:
            other = next(c for c in s["clubs"] if c != MIAMI)
            state = (f"{'Won' if s['winner'] == MIAMI else 'Lost'} {s['wins'][MIAMI]}-{s['wins'][other]}" if s.get("winner")
                     else f"In progress {s['wins'][MIAMI]}-{s['wins'][other]}")
            srows.append([ROUND_LABELS[s["round"]], other, state])
        out += ["## Series", "", _table(["Round", "Opponent", "Result"], srows), ""]
    if not rows:
        out += ["No Miami playoff game has been played yet.", ""]
        return "\n".join(out).rstrip() + "\n"
    games = []
    for r in rows:
        res = r["result"]
        side = "home" if res["home"] == MIAMI else "away"
        other = "away" if side == "home" else "home"
        won = res["final_score"][side] > res["final_score"][other]
        games.append([res["game_date"], ("vs " if side == "home" else "at ") + res[other],
                      f"{'W' if won else 'L'} {res['final_score'][side]}-{res['final_score'][other]}"])
    out += ["## Games", "", _table(["Date", "Opponent", "Result"], games), ""]
    out += ["## Players", "", _table(PROD, _section(lines)), ""]
    return "\n".join(out).rstrip() + "\n"


def pages(root=ROOT, season=None, now=None):
    """{path: text} for both pages, or {} before the playoffs are seeded."""
    season = season or _active_season(root)
    from .playoffs import read
    root = Path(root)
    if read(root, season) is None:
        return {}
    close = root / f"career/Dwyane_Wade/{season}/season_close.json"
    if close.is_file():                     # a closed season's pages stand as of its close, whatever the clock says
        from .write_back import clock
        now = min(now or clock(root), json.loads(close.read_text(encoding="utf-8"))["close_date"])
    return {root / league_page_path(season): league_page(root, season, now), root / team_page_path(season): team_page(root, season, now)}


def write_pages(root=ROOT, season=None):
    season = season or _active_season(root)
    changed = 0
    for path, text in pages(root, season).items():
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            changed += 1
    return changed


def page_errors(root=ROOT, season=None):
    season = season or _active_season(root)
    root = Path(root)
    return [f"{path.relative_to(root)}: stale playoff statistics page (python scripts/write_back_results.py --write)"
            for path, text in pages(root, season).items()
            if not path.is_file() or path.read_text(encoding="utf-8") != text]
