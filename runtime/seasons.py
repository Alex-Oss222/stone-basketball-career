"""The season registry: where every season's world data lives and when its dated gates fall.

Every pipeline asks this module instead of naming a season, so the career rolls from one year to the next with no
season-specific code (the user's requirement, October 2026). A season is supported when its library files exist;
adding a season is a data import, never a code change.

Files: `library/<start>/league/nba_<YYYY>_<YY>_<kind>.json` for the season's own data (schedule, rosters, calendar,
conferences, playoff rules, award calendar, staffs, pace, jerseys, cap rules), and the prior season's real data the
next season is built on (`nba_<prev>_player_stats.json`, `..._league_environment.json`, `..._shot_environment.json`,
`..._defense.json`) in the same folder.

Dates: the calendar file's events by id, the schedule's first and last regular-season days, and the agreement's
fixed rules where the calendar is silent (the January 10 guarantee date, waivers clearing two days earlier, the
opening-day roster cut the day before opening night). Each fallback is named, so a season's calendar can override it.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
STATE = "current_state.json"


def start_year(season):
    return int(season[:4])


def label(start):
    return f"{start}-{str(start + 1)[-2:]}"


def next_season(season):
    return label(start_year(season) + 1)


def previous_season(season):
    return label(start_year(season) - 1)


def tag(season):
    """'2004-05' -> '2004_05' (file-name form)."""
    return season.replace("-", "_")


def library(season):
    return Path(f"library/{start_year(season)}/league")


def path(season, kind):
    """The season's own file of a kind: schedule, preseason_schedule, team_rosters, calendar, conferences,
    playoff_rules, season_awards, staffs, team_pace, jerseys, cap_rules, unsigned_status, unsigned_status_monthly."""
    return library(season) / f"nba_{tag(season)}_{kind}.json"


def prior_path(season, kind):
    """Real data of the season before, filed with the season it serves: player_stats, league_environment,
    shot_environment, defense."""
    return library(season) / f"nba_{tag(previous_season(season))}_{kind}.json"


def _read(root, rel):
    return json.loads((Path(root) / rel).read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def _cached(root, rel):
    return _read(root, rel)


def read(season, kind, root=ROOT):
    return _cached(str(root), str(path(season, kind)))


def exists(season, kind, root=ROOT):
    return (Path(root) / path(season, kind)).is_file()


# ---- dates

def regular_season(season, root=ROOT):
    """(first day, last day) of the regular season from its schedule."""
    games = read(season, "schedule", root)["games"]
    days = sorted(g["date"] for g in games)
    return days[0], days[-1]


def calendar(season, root=ROOT):
    """{event id: date} from the season's calendar file, or {} when the season has none."""
    if not exists(season, "calendar", root):
        return {}
    return {e["id"]: e["date"] for e in read(season, "calendar", root)["events"] if e.get("date")}


def _plus(day, days):
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def dates(season, root=ROOT):
    """Every dated gate a pipeline needs, from the calendar with the agreement's fixed rules as fallbacks."""
    first, last = regular_season(season, root)
    end = start_year(season) + 1
    cal = calendar(season, root)
    out = {
        "opening_night": cal.get("opening_night", first),
        "regular_season_end": cal.get("regular_season_end", last),
        "roster_cut": cal.get("roster_cut_to_15", _plus(cal.get("opening_night", first), -1)),
        "guarantee": cal.get("contract_guarantee_date", f"{end}-01-10"),     # 1999 and 2005 agreements: January 10
        "waive_by": cal.get("waive_by_before_guarantee", _plus(cal.get("contract_guarantee_date", f"{end}-01-10"), -3)),
        "playoffs_start": cal.get("playoffs_start"),
        "all_star_weekend": cal.get("all_star_weekend"),
        "ten_day_contracts_from": cal.get("ten_day_contracts_from", f"{end}-01-05"),
        "trade_deadline": cal.get("trade_deadline"),
        "training_camp_opens": cal.get("training_camp_opens"),
        "preseason": cal.get("preseason"),
        "season_close_window_end": f"{end}-06-30",
    }
    return out


def date_of(season, key, root=ROOT):
    value = dates(season, root).get(key)
    if value is None:
        raise ValueError(f"{season}: no {key} date (library calendar {path(season, 'calendar')})")
    return value


def season_of_date(day):
    """The season a date belongs to: July 1 starts a new league year."""
    d = date.fromisoformat(day)
    return label(d.year if d.month >= 7 else d.year - 1)


# ---- alignment

def conferences(season, root=ROOT):
    """{conference: [clubs]}."""
    return read(season, "conferences", root)["conferences"]


def divisions(season, root=ROOT):
    """{conference: {division: [clubs]}} from the conferences file or, for older seasons, the playoff rules."""
    data = read(season, "conferences", root)
    if data.get("divisions"):
        return data["divisions"]
    rules = read(season, "playoff_rules", root)["divisions"]
    return {conf: rules[conf] for conf in conferences(season, root)}


def conference_of(season, club, root=ROOT):
    return next(c for c, clubs in conferences(season, root).items() if club in clubs)


def clubs(season, root=ROOT):
    return sorted(c for cs in conferences(season, root).values() for c in cs)


# ---- the career

def season_dir(season, root=ROOT):
    return Path(root) / PLAYER / season


def live_seasons(root=ROOT):
    """Season folders with a current state, oldest first."""
    base = Path(root) / PLAYER
    return sorted(p.name for p in base.iterdir() if p.is_dir() and len(p.name) == 7 and p.name[4] == "-"
                  and (p / STATE).is_file())


def active(root=ROOT):
    """The career's live season: the latest folder with a current state. A scratch copy without any state (a test
    scaffold) follows the repository's own live season."""
    live = live_seasons(root) if (Path(root) / PLAYER).is_dir() else []
    if live:
        return live[-1]
    return live_seasons(ROOT)[-1]


def state_path(season=None, root=ROOT):
    return season_dir(season or active(root), root) / STATE


def state(season=None, root=ROOT):
    return json.loads(state_path(season, root).read_text(encoding="utf-8"))


def clock(root=ROOT):
    return state(None, root)["current_date"]


def supported(season, root=ROOT):
    """Missing library files a season needs before it can be played (empty when ready)."""
    need = [path(season, k) for k in ("schedule", "preseason_schedule", "team_rosters", "calendar", "conferences",
                                      "playoff_rules", "season_awards", "team_pace", "staffs")]
    need += [prior_path(season, k) for k in ("player_stats", "league_environment", "shot_environment")]
    return [str(p) for p in need if not (Path(root) / p).is_file()]
