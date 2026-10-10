"""League player cards: one dated personnel card per registry player, in Markdown and HTML.

A card shows only evidence dated on or before its date: the registry identity, the
club holding the player on that date (``club_on``), the sourced photo, the contract or
draft-rights line that existed at the checkpoint, the recorded 2002-03 line or the 2003
draft entry, and the simulated 2003-04 statistics, which stay N/A until closed games
exist. Later transactions and the historical Wade are never used as evidence.

Club colours come from ``library/2003/league/nba_team_colors_2002_2014.json`` (presentation
only). The dated club follows the registry's source club or draft rights, then Miami's
holdings (rule 2), Miami's departures ledger (rule 3) and the world's real moves with
rule 1 (a real move to Miami never happens). Free agents use the placeholder colours.
"""
from __future__ import annotations

from datetime import date
from html import escape
import json
from pathlib import Path
import re

from .stable_json import stable
from .career_stats import aggregate
from .shot_chart import NBA_GEOMETRY, ZONES, aggregate_shots
from .shot_events import build_tracking_cohort, engine_result_shots, shot_source_type
from .stat_layout import PER_GAME_COLUMNS, markdown_table

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = Path("library/2003/league")
COLORS_FILE = LIBRARY / "nba_team_colors_2002_2014.json"
END_OF_SEASON = LIBRARY / "nba_2003_end_of_season.json"
DRAFT_CLASS = LIBRARY / "nba_2003_draft_class.json"
PLAYER_STATS = LIBRARY / "nba_2002_03_player_stats.json"
CONTRACTS = LIBRARY / "nba_2003_contracts.json"
TRANSACTIONS = LIBRARY / "nba_2003_offseason_transactions.json"
PLAYER_DIR = Path("career/Dwyane_Wade")
LEAGUE_DIR = PLAYER_DIR / "Stats_and_Awards/League"
CARDS_DIR = LEAGUE_DIR / "Players"
FIRST_SEASON = "2003-04"                     # the season the registry was imported for (its club and rights labels)


def _season(root=None):
    from .seasons import active
    return active(root or ROOT)


def _roster_dir(season):
    return PLAYER_DIR / season / "00_Team/Team/Roster"


def holdings_path(season):
    return _roster_dir(season) / "holdings.json"


def departures_path(season):
    return _roster_dir(season) / "departures.json"


def miami_roster_path(season):
    return _roster_dir(season) / "roster.json"


def miami_cards_dir(season):
    return PLAYER_DIR / season / "00_Team/Team/Player_Cards"


def card_lines_path(season):
    """Every registry player's closed regular-season and playoff rows for a season, written when it closes."""
    return LEAGUE_DIR / season / "card_lines.json"
CONTRACT_RECORDS = PLAYER_DIR / "Contracts/contract_records.json"
TEMPLATE = Path("runtime/assets/player_cards.html")
SILHOUETTE = "assets/silhouette.svg"
MIAMI = "Miami Heat"
MOVING_KINDS = {"signing", "sign_and_trade", "match_declined"}
POSITION_NAMES = {"PG": "Point guard", "SG": "Shooting guard", "SF": "Small forward",
                  "F": "Forward", "PF": "Power forward", "C": "Center"}
FINAL_SECTIONS = ["## Regular-season statistics by year", "## Playoff statistics by year", "## Awards and honors"]
FINAL_SEASON_LABEL = "## Awards and honors"


def _read(root, path):
    return json.loads((Path(root) / path).read_text(encoding="utf-8"))


def _day(value):
    return date.fromisoformat(value)


def _key(name):
    """Name key tolerant of punctuation, spacing and accents ('T.J.' = 'T. J.', 'Nájera' = 'Najera'): the write-back's."""
    from .write_back import _key as key
    return key(name)


# -- colours ------------------------------------------------------------------------------------------

def load_colors(root=ROOT):
    return _read(root, COLORS_FILE)


def club_colors(club, season_start_year, colors):
    """Colours of `club` for the season starting in `season_start_year`; placeholder when none holds."""
    placeholder = {"primary": colors["placeholder"]["primary"], "secondary": colors["placeholder"]["secondary"],
                   "club": club, "era": None}
    if not club:
        return placeholder
    for era in colors["eras"]:
        if era["club"] == club and era["from_year"] <= season_start_year < era["to_year"]:
            return {"primary": era["primary"], "secondary": era["secondary"], "club": club,
                    "era": (era["from_year"], era["to_year"])}
    return placeholder


# -- dated club ---------------------------------------------------------------------------------------

def _within(entry, on):
    return entry["from"] <= on and (entry.get("until") is None or on < entry["until"])


def _matches(player, *, bbr_id=None, name=None):
    if bbr_id and player.get("bbr_id") and bbr_id == player["bbr_id"]:
        return True
    return bool(name) and _key(name) == _key(player["name"])


def world_moves(player, transactions):
    """The player's dated real moves (rule 1 applied), oldest first: (date, club or None, basis, rights).

    `rights` is True when the move carries unsigned draft rights, False when it is a contract move.
    """
    moves = []
    for row in transactions.get("signings", []):
        if row.get("kind") not in MOVING_KINDS or not _matches(player, bbr_id=row.get("bbr_id"), name=row.get("player")):
            continue
        if row.get("to") == MIAMI:
            # Rule 1: a real move to Miami never happens; he stays where he was.
            continue
        moves.append((row["date"], row["to"], f'{row["kind"]} to {row["to"]} on {row["date"]} (world data)', False))
    for row in transactions.get("waivers", []):
        if row.get("club") != MIAMI and _matches(player, bbr_id=row.get("bbr_id"), name=row.get("player")):
            moves.append((row["date"], None, f'waived by {row["club"]} on {row["date"]} (world data)', False))
    for trade in transactions.get("trades", []):
        if trade.get("involves_miami"):
            continue  # rule 1
        for club, sides in trade["clubs"].items():
            for item in sides.get("in", []):
                item_name = re.sub(r"\s*\((draft rights|sign-and-trade)\)$", "", item)
                if _matches(player, name=item_name):
                    moves.append((trade["date"], club, f'traded to {club} on {trade["date"]} (world data)', item.endswith("(draft rights)")))
    return sorted(moves, key=lambda m: m[0])


def signings(root=ROOT):
    """name key -> earliest signing date in the career's contract records."""
    out = {}
    if (Path(root) / CONTRACT_RECORDS).is_file():
        for rec in _read(root, CONTRACT_RECORDS)["records"]:
            if rec.get("event") == "signed" and rec.get("recorded_on"):
                key = _key(rec["player"])
                out[key] = min(out.get(key, rec["recorded_on"]), rec["recorded_on"])
    return out


def signed_evidence(name, on, records=(), signed=None):
    """The dated evidence that a draft pick is under contract by `on`: (date, basis) or None.

    A signing in the career's contract records counts from its date. The world data does not record
    a real club's rookie signing date, but a box score lists only a club's roster, so a closed game
    that lists the pick (played, DNP or inactive) shows his contract was in force by that game; until
    then the June 26 draft-rights label stands."""
    when = (signed or {}).get(_key(name))
    if when and when <= on:
        return when, f"signed {when} (career contract record)"
    games = sorted((r["date"], r.get("team")) for r in records if r["date"] <= on)
    if games:
        when, club = games[0]
        return when, f"on the {club} roster in a closed game on {when}; signing date not recorded"
    return None


def club_on(player, on, *, holdings=None, departures=None, transactions=None, root=ROOT, signed=None):
    """The club holding a registry player on `on` (YYYY-MM-DD), with the basis of the answer.

    Order: the registry's source club or draft rights, the world's dated real moves up to the date
    (rule 1 skips any move to Miami and any trade involving Miami), Miami's departures ledger
    (rule 3), then Miami's holdings (rule 2: a player Miami holds on the date is Miami's).
    Returns {"club", "code", "basis", "rights"}; `club` is None for a free agent. `signed` is the
    pick's `signed_evidence`: once it is dated on or before `on`, he holds a contract, not rights.
    """
    from .seasons import live_season_on
    season = live_season_on(on, root) if on >= "2003-07-01" else FIRST_SEASON   # the summer stays with the closed season
    from .league_moves import opening_book
    if season != FIRST_SEASON and opening_book(season, root) is not None:
        return _club_in_book(player, on, season, root, transactions)
    if holdings is None:
        holdings = _read(root, holdings_path(season)) if (Path(root) / holdings_path(season)).is_file() else {"entries": []}
    if departures is None:
        departures = _read(root, departures_path(season)) if (Path(root) / departures_path(season)).is_file() else {"entries": []}
    if transactions is None:
        transactions = _read(root, TRANSACTIONS) if (Path(root) / TRANSACTIONS).is_file() else {}
    rights = player.get("cohort") == "2003_draft_rights"
    club = player.get("team_name")
    basis = "2003 draft rights" if rights else "end-of-2002-03 club (registry source)"
    # A Miami holding that has ended leaves him a free agent until a move dated after the release;
    # real moves skipped while Miami held him (rule 2) do not come back.
    released = max((e["until"] for e in holdings.get("entries", [])
                    if _matches(player, bbr_id=e.get("bbr_id"), name=e.get("player")) and e.get("until") and e["until"] <= on
                    and not e.get("void")),
                   default=None)
    if released:
        # His real career resumes: the club the season's real roster has him with on the date, as the games
        # place him (`rotations.real_rotation`); a later dated move below overrides it.
        club = _real_stint_club(player, on, root)
        basis = (f"Miami's holding ended on {released}; back on his real {season} path" if club else
                 f"Miami's holding ended on {released}; no later club recorded")
        rights = False
    for when, target, why, carries_rights in world_moves(player, transactions):
        if when > on:
            break
        if (released and when < released) or _any_holding(player, holdings, when):
            continue
        club, basis, rights = target, why, carries_rights
    for entry in departures.get("entries", []):
        if _matches(player, bbr_id=entry.get("bbr_id"), name=entry.get("player")) and _within(entry, on):
            club, basis, rights = entry["club"], f'sent by Miami to {entry["club"]} on {entry["from"]}', False
    from .club_replacements import read as read_replacements
    for entry in read_replacements(season, root)["entries"]:
        if _matches(player, bbr_id=entry.get("bbr_id"), name=entry.get("player")) and _within(entry, on):
            club, basis, rights = entry["club"], f'signed by {entry["club"]} on {entry["from"]} to replace {entry["replaces"]}', False
    entry = _any_holding(player, holdings, on)
    if entry:
        club, basis = MIAMI, f'held by Miami ({entry.get("basis", "holdings ledger")})'
        rights = entry.get("basis") == "draft rights"
    if rights and signed and signed[0] <= on:
        rights, basis = False, ("held by Miami; " if club == MIAMI else "under contract: ") + signed[1]
    return {"club": club, "code": _code(club, transactions, player), "basis": basis, "rights": rights}


def _club_in_book(player, on, season, root, transactions=None):
    """A season after the first: the one answer every reader shares (`runtime/club_truth.py`), the engine's own rosters."""
    from .club_truth import holder
    club, basis = holder(player.get("bbr_id"), player.get("name"), on, root)
    return {"club": club, "code": ("MIA" if club == MIAMI else _code(club, transactions or {}, player)) if club else None,
            "basis": basis, "rights": False}


def _real_stint_club(player, on, root=ROOT):
    """The club whose real-season stint covers `on` for the player (the games' roster rule), or None."""
    from .rotations import load_rosters, season_fraction
    from .seasons import season_of_date
    season = season_of_date(on)
    try:
        rosters, fraction = load_rosters(season, root), season_fraction(season, on, root)
    except (OSError, KeyError, ValueError):
        return None
    for club, entry in sorted(rosters.items()):
        for p in entry["players"]:
            if _matches(player, bbr_id=p.get("bbr_id"), name=p.get("player_id")):
                start, end = p.get("window") or p.get("span") or [0.0, 1.0]
                if start <= fraction < end or (end >= 1.0 and fraction >= start):
                    return club
    return None


def _any_holding(player, holdings, on):
    """Miami's holding on the date; a void entry (a camp contract that was never valid) is none."""
    for entry in holdings.get("entries", []):
        if entry.get("void"):
            continue
        if _matches(player, bbr_id=entry.get("bbr_id"), name=entry.get("player")) and _within(entry, on):
            return entry
    return None


_CODES = {}


def _code(club, transactions, player):
    if club is None:
        return None
    if club == player.get("team_name"):
        return player.get("team_code")
    if not _CODES:
        for path in (END_OF_SEASON, DRAFT_CLASS):
            try:
                for name, entry in _read(ROOT, path)["clubs"].items():
                    _CODES[name] = entry["code"]
            except (OSError, KeyError, ValueError):
                pass
    return _CODES.get(club, club)


# -- sources ------------------------------------------------------------------------------------------

def photo_sources(root=ROOT):
    """bbr_id -> headshot fields, from the end-of-season baseline first, then the draft class."""
    photos = {}
    for path in (END_OF_SEASON, DRAFT_CLASS):
        for club in _read(root, path)["clubs"].values():
            for p in club["players"]:
                if p.get("bbr_id") and p.get("headshot_url") and p["bbr_id"] not in photos:
                    photos[p["bbr_id"]] = {k: p.get(k) for k in ("headshot_url", "headshot_license", "headshot_license_url",
                                                                 "headshot_credit", "headshot_page", "jersey", "page_url")}
    return photos


def baseline_entries(root=ROOT):
    """bbr_id -> baseline roster entry (jersey, BBR page) from both league sources."""
    entries = {}
    for path in (END_OF_SEASON, DRAFT_CLASS):
        for club_name, club in _read(root, path)["clubs"].items():
            for p in club["players"]:
                if p.get("bbr_id") and p["bbr_id"] not in entries:
                    entries[p["bbr_id"]] = {**p, "club": club_name}
    return entries


def prior_lines(root=ROOT):
    return {r["bbr_id"]: r for r in _read(root, PLAYER_STATS)["records"]}


def draft_rights(root=ROOT):
    """name key -> (club, pick, status) for the 58 unsigned 2003 draft rights."""
    out = {}
    for club_name, club in _read(root, CONTRACTS)["clubs"].items():
        for d in club.get("draft_rights", []):
            out[_key(d["player"])] = {"club": club_name, "pick": d["pick"], "status": d["status"],
                                      "cap_hold": d.get("current_cap_hold")}
    return out


def contract_rows(root=ROOT):
    data = _read(root, CONTRACTS)
    rows = {}
    for club_name, club in data["clubs"].items():
        for p in club["players"]:
            if p.get("bbr_id"):
                rows[p["bbr_id"]] = {**p, "club": club_name}
    return rows, data["status_legend"]


def wade_contract_line(signed):
    if signed:
        return (f"Rookie-scale contract signed {signed[0]} (career contract record); "
                "terms and history are on the contract pages.")
    return "Draft rights held by Miami; no executed professional contract (career record)."


def contract_line(player, rows, legend, rights, signed=None, held=None):
    """Contract/control line from terms that existed at the checkpoint; never a later decision.

    A 2003 pick with `signed` evidence holds a contract whose terms the world data does not record."""
    if rights is None and signed and player.get("cohort") == "2003_draft_rights":
        return (f'Under contract with {held["club"]}: {signed[1]}. '
                "The world data does not record this rookie contract's terms.")
    if rights is not None:
        pick = rights["pick"]
        round_label = "first-round" if pick <= 29 else "second-round"
        hold = f' Draft cap hold ${rights["cap_hold"]:,}.' if rights.get("cap_hold") else " No individual draft cap hold."
        return f"Unsigned No. {pick} {round_label} draft rights held by {rights['club']}; no contract has been agreed.{hold}"
    row = rows.get(player["bbr_id"])
    if row is None:
        return "No 2003-04 contract term established in the league contract inventory as of June 26, 2003."
    status = row["status"]
    seasons = sorted(s for s, v in row.get("schedule", {}).items() if v is not None)
    label = {"under_contract": "Under contract", "under_rookie_contract": "Under rookie scale contract",
             "under_contract_unverified": "Listed under contract (continuity unverified)",
             "minimum_contract_unverified": "Minimum-salary contract (2003-04 status unverified)",
             "player_option_pending": "2003-04 player option pending", "team_option_pending": "2003-04 team option pending",
             "free_agent_expiring": "Contract expires June 30, 2003", "free_agent_unlisted": "Contract ended in 2002-03",
             "expired_or_unresolved": "No 2003-04 commitment established",
             "retired_salary_on_books": "Retired; salary carried on the club's books"}.get(status, status)
    parts = [label]
    if seasons and status not in {"free_agent_expiring", "free_agent_unlisted", "expired_or_unresolved"}:
        amount = row["schedule"].get("2003-04")
        parts.append(f"through {seasons[-1]}" + (f" (2003-04 scheduled ${amount:,})" if amount else ""))
    if status == "free_agent_expiring":
        rfa = row.get("rfa_eligible")
        parts.append("restricted free agency eligible" if rfa else "unrestricted" if rfa is False else "restriction not established")
    return "; ".join(parts) + f" (league contract inventory status `{status}`, as of June 26, 2003)."


# -- periods and statistics --------------------------------------------------------------------------

def week_bounds(year, month, week):
    import calendar
    last = calendar.monthrange(year, month)[1]
    start = 1 + (week - 1) * 7
    end = min(week * 7, last) if week < 4 else last
    return f"{year}-{month:02d}-{start:02d}", f"{year}-{month:02d}-{end:02d}"


def periods(config, season=None, root=ROOT):
    """Season, month and week periods of the regular season, from the season's calendar (runtime/seasons.py)."""
    from .seasons import month_weeks, start_year
    season = season or _season(root)
    import calendar
    months = month_weeks(season, root)
    first_month, last_month = months[0], months[-1]
    out = [dict(id="season", label=f"{season} regular season", kind="season",
                start=f"{first_month[2]}-{first_month[1]:02d}-01",
                end=f"{last_month[2]}-{last_month[1]:02d}-{calendar.monthrange(last_month[2], last_month[1])[1]:02d}",
                folder=f"{season}")]
    for name, month, year, folder, weeks in months:
        last = calendar.monthrange(year, month)[1]
        out.append(dict(id=f"month-{folder[:2]}", label=f"{name} {year}", kind="month",
                        start=f"{year}-{month:02d}-01", end=f"{year}-{month:02d}-{last:02d}", folder=f"{season}/{folder}"))
        for week in weeks:
            start, end = week_bounds(year, month, week)
            out.append(dict(id=f"week-{folder[:2]}-{week}", label=f"{name} {year} week {week} ({start[-2:]} to {end[-2:]})",
                            kind="week", start=start, end=end, folder=f"{season}/{folder}/Week_{week}"))
    return out


def period_statistics(records, shots, period):
    """Closed results of one period: box totals, rates and the shooting-zone aggregation."""
    selected = [r for r in records if period["start"] <= r["date"] <= period["end"]]
    ids = {r["event_id"] for r in selected}
    summary = aggregate(selected)
    selected_shots = [s for s in shots if s["game_id"] in ids]
    shooting = aggregate_shots(selected, selected_shots)
    tracked_ids = {r["event_id"] for r in selected if r.get("shot_tracking_available")}
    sources = _source_games(selected)
    cohort = build_tracking_cohort(selected, selected_shots, tracked_game_ids=tracked_ids,
                                   source_games=sources)
    source_type = shot_source_type(selected_shots, source_games=sources)
    return dict(summary=summary, shooting=shooting, selected=selected, shots=selected_shots,
                shot_source_type=source_type, **cohort)


def _source_games(records):
    return [dict(id=r["event_id"], date=r["date"], opponent=r.get("opponent"), status=r["status"],
                 appearance=r.get("appearance"), href=r.get("href"),
                 result_href=r.get("result_href"), shot_href=r.get("shot_href"),
                 shot_source_label=r.get("shot_source_label"),
                 shot_source_type=r.get("shot_source_type", "unavailable")) for r in records]


def _n(value, places=1):
    return "N/A" if value is None else f"{value:.{places}f}"


def _ratio(value):
    return "N/A" if value is None else f"{value:.3f}".removeprefix("0")


def per_game_row(label, age, team, pos, summary):
    a = summary
    pg, rates = a["pg"], a["rates"]
    return [label, age, team, "NBA", pos, _n(a["gp"], 0), _n(a["gs"], 0), _n(pg["minutes"]),
            _n(pg["fgm"]), _n(pg["fga"]), _ratio(rates["fg_pct"]), _n(pg["tpm"]), _n(pg["tpa"]), _ratio(rates["three_pct"]),
            _n(pg["two_pm"]), _n(pg["two_pa"]), _ratio(rates["two_pct"]), _ratio(rates["efg_pct"]),
            _n(pg["ftm"]), _n(pg["fta"]), _ratio(rates["ft_pct"]),
            *(_n(pg[k]) for k in ("orb", "drb", "reb", "ast", "stl", "blk", "tov", "pf", "pts")), _ratio(rates["ts_pct"]), "—"]


# -- rendering ----------------------------------------------------------------------------------------

def age_on(birth, on):
    if not birth:
        return None                       # not recorded (a dated registry addition without a sourced birth date): N/A
    b, d = _day(birth), _day(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def header_svg(player, club, colors, jersey, label):
    """Club-colour header: name, jersey, position and club, white text on the primary colour."""
    primary, secondary = colors["primary"], colors["secondary"]
    name = escape(player["name"])
    number = escape(f"#{jersey}" if jersey else "—")
    position = escape(POSITION_NAMES.get(player["position"], player["position"]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="180" viewBox="0 0 1280 180" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{name}</title><desc id="d">{name}, {escape(label)}, {position}, {number}.</desc>\n'
            f'<rect width="1280" height="180" rx="24" fill="{primary}"/>\n'
            f'<rect x="0" y="150" width="1280" height="30" fill="{secondary}" fill-opacity=".92"/>\n'
            f'<rect x="0" y="150" width="1280" height="6" fill="{secondary}"/>\n'
            f'<text x="48" y="78" font-family="sans-serif" font-size="54" font-weight="700" fill="#ffffff">{name}</text>\n'
            f'<text x="48" y="124" font-family="sans-serif" font-size="26" fill="#ffffff" fill-opacity=".92">{position} · {escape(label)}</text>\n'
            f'<text x="1232" y="112" font-family="sans-serif" font-size="96" font-weight="800" fill="#ffffff" fill-opacity=".95" text-anchor="end">{number}</text>\n'
            '</svg>\n')


def silhouette_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="400" viewBox="0 0 320 400" role="img" aria-labelledby="t">\n'
            '<title id="t">No sourced photo</title>\n'
            '<rect width="320" height="400" rx="18" fill="#1d1d1f"/>\n'
            '<circle cx="160" cy="150" r="70" fill="#c5c7cb" fill-opacity=".55"/>\n'
            '<path d="M40 400 C40 290 100 250 160 250 C220 250 280 290 280 400 Z" fill="#c5c7cb" fill-opacity=".55"/>\n'
            '<text x="160" y="380" font-family="sans-serif" font-size="18" fill="#c5c7cb" text-anchor="middle">No sourced photo</text>\n'
            '</svg>\n')


def _prior_row(line, label_team):
    t = line["totals"]
    g = t["games"]
    pct = lambda m, a: "N/A" if not a else f"{m / a:.1%}"
    per = lambda v: "N/A" if not g else f"{v / g:.1f}"
    reb = t["offensive_rebounds"] + t["defensive_rebounds"]
    return ["2002-03", label_team, str(g), str(t["games_started"]), per(t["minutes"]), per(t["points"]), per(reb),
            per(t["assists"]), per(t["steals"]), per(t["blocks"]), per(t["turnovers"]),
            pct(t["field_goals_made"], t["field_goals_attempted"]), pct(t["three_pointers_made"], t["three_pointers_attempted"]),
            pct(t["free_throws_made"], t["free_throws_attempted"])]


def _prior_summary(line):
    t = line["totals"]
    g = t["games"]
    if not g:
        return "no 2002-03 appearances"
    reb = t["offensive_rebounds"] + t["defensive_rebounds"]
    fg = f'{t["field_goals_made"] / t["field_goals_attempted"]:.1%}' if t["field_goals_attempted"] else "N/A"
    return (f'{g} G, {t["games_started"]} GS, {t["minutes"] / g:.1f} MPG, {t["points"] / g:.1f} PPG, {reb / g:.1f} RPG, '
            f'{t["assists"] / g:.1f} APG, {t["steals"] / g:.1f} SPG, {t["blocks"] / g:.1f} BPG, {t["turnovers"] / g:.1f} TOV, FG {fg}')


class CardContext:
    """Everything the builder reads once for all 407 cards."""

    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.registry = _read(root, LEAGUE_DIR / "player_registry.json")
        self.on = max(json.loads(p.read_text(encoding="utf-8"))["current_date"]
                      for p in (self.root / PLAYER_DIR).glob("*/current_state.json"))
        self.config = _read(root, "foundation/season_structure.json")
        self.colors = load_colors(root)
        self.photos = photo_sources(root)
        self.baseline = baseline_entries(root)
        self.prior = prior_lines(root)
        self.rights = draft_rights(root)
        self.signed = signings(root)
        self.contracts, self.legend = contract_rows(root)
        self.identity = _read(root, PLAYER_DIR / "professional_identity.json")
        from .seasons import live_seasons
        self.season = _season(root)
        self.seasons = [x for x in live_seasons(root)] if (self.root / PLAYER_DIR).is_dir() else [self.season]
        if self.season not in self.seasons:
            self.seasons.append(self.season)
        HOLDINGS, DEPARTURES = holdings_path(self.season), departures_path(self.season)
        MIAMI_ROSTER, MIAMI_CARDS = miami_roster_path(self.season), miami_cards_dir(self.season)
        self.miami_cards_dir = MIAMI_CARDS
        self.holdings = _read(root, HOLDINGS) if (self.root / HOLDINGS).is_file() else {"entries": []}
        self.departures = _read(root, DEPARTURES) if (self.root / DEPARTURES).is_file() else {"entries": []}
        self.transactions = _read(root, TRANSACTIONS)
        roster = _read(root, MIAMI_ROSTER)["players"]
        self.miami_cards = {_key(p["name"]): p["id"] for p in roster if (self.root / MIAMI_CARDS / f'{p["id"]}.md').is_file()}
        self.periods = periods(self.config, self.season, root)
        self.honors = {}
        from .season_awards import honors as season_honors
        from .seasons import dates
        for season in self.seasons:
            # Closed weekly and monthly award decisions (runtime/award_decisions.py): winners and shortlist placings.
            decisions = self.root / LEAGUE_DIR / season / "award_decisions.json"
            if decisions.is_file():
                for d in json.loads(decisions.read_text(encoding="utf-8"))["decisions"]:
                    if d["announced_on"] > self.on:
                        continue
                    for x in d["shortlist"]:
                        self.honors.setdefault(_key(x["player"]), []).append(dict(d, rank=x["rank"], line=x))
            # Closed All-Star selections (runtime/all_star.py): starters, reserves and injury replacements, from the
            # selection date (`all_star_honors`).
            selections = self.root / LEAGUE_DIR / season / "all_star.json"
            if selections.is_file():
                for key, rows in all_star_honors(self.registry["players"], json.loads(selections.read_text(encoding="utf-8")),
                                                 self.on, dates(season, root)["opening_night"]).items():
                    self.honors.setdefault(key, []).extend(rows)
            # Closed season awards (runtime/season_awards.py): winners, team selections and the next vote-getters, over
            # the decision's own period (the Finals MVP's starts with the Finals), else from opening night.
            record = self.root / LEAGUE_DIR / season / "season_awards.json"
            if not record.is_file():
                continue
            for d in json.loads(record.read_text(encoding="utf-8"))["decisions"]:
                if d["announced_on"] > self.on:
                    continue
                base = dict(conference="", period_start=d.get("period_start") or dates(season, root)["opening_night"],
                            period_end=d["evidence_through"],
                            announced_on=d["announced_on"], award=d["award"], filed_on=(LEAGUE_DIR / season / "Season_Awards.md").as_posix(),
                            annual=True)
                for player, name, _ in season_honors(d):
                    self.honors.setdefault(_key(player), []).append(dict(base, name=name, rank=1))
                for i, v in enumerate(d.get("tally", [])[:3]):
                    who = v.get("player")
                    if who and who not in d["winners"]:
                        self.honors.setdefault(_key(who), []).append(dict(base, name=d["name"], rank=i + 1))
        # FIBA team medals (runtime/national_medals.py): every player on a medal team's locked tournament roster, from
        # the day the tournament closed, matched to the registry by NBA id; a medal without one by its dated link to
        # the one registry row of the same player (`national_medals.links`), from the later of the award and the row's
        # added_on. Ambiguous candidates never link; they are kept on the context as `medal_ambiguous`.
        from .national_medals import links as medal_links, register_medals
        medals = register_medals(self.root, self.on)
        linked = medal_links(self.root, self.on, medals, self.registry["players"])
        self.medal_ambiguous = linked["ambiguous"]
        for key, rows in medal_honors(self.registry["players"], medals, linked["linked"]).items():
            self.honors.setdefault(key, []).extend(rows)
        # Closed playoff results (runtime/playoff_stats.py): each player's playoff records, by dated record name.
        self.playoff_lines = {}
        try:
            from .playoff_stats import closed_playoff_results, player_lines
            for (name, _club), recs in player_lines(closed_playoff_results(self.root, self.season, self.on), self.root, self.season).items():
                self.playoff_lines.setdefault(_key(name), []).extend(recs)
        except (OSError, KeyError):
            pass
        # Earlier simulated seasons: each card's closed rows, written when the season closed (`card_lines_path`).
        self.history = {}
        for season in self.seasons:
            path = self.root / card_lines_path(season)
            if season < self.season and path.is_file():
                self.history[season] = json.loads(path.read_text(encoding="utf-8"))["players"]
        self.template = (ROOT / TEMPLATE).read_text(encoding="utf-8")

    def club(self, player, signed=None):
        return club_on(player, self.on, holdings=self.holdings, departures=self.departures,
                       transactions=self.transactions, root=self.root, signed=signed)


def all_star_honors(players, record, on, opening):
    """{name key: [honor rows]} for one season's All-Star selections (`all_stars` in `League/<season>/all_star.json`,
    `runtime/all_star.py`): each starter, reserve and injury replacement selected on or before the card date `on`, with
    his conference and role, dated on the selection and linked to the season page's All-Stars table. Matched to the
    registry `players` by NBA id; an entry without one by name (the award records' key). An id the registry does not
    track stays on the All-Star page only. The period runs from opening night to the selection date, as Wade's own
    record does (`all_star._record_wade`)."""
    names = {p["bbr_id"]: p["name"] for p in players if p.get("bbr_id")}
    page = (LEAGUE_DIR / record["season"] / "All_Star.md").as_posix()
    out = {}
    for a in record.get("all_stars", []):
        if a["selected_on"] > on:
            continue
        name = names.get(a["bbr_id"]) if a.get("bbr_id") else a["player"]
        if name is None:
            continue
        out.setdefault(_key(name), []).append(dict(
            conference=a["conference"], name=f"All-Star ({a['role']})", period_start=opening, period_end=a["selected_on"],
            announced_on=a["selected_on"], award="all_star", filed_on=page, anchor="all-stars", rank=1, annual=True,
            selected=True, **({"replacing": a["replacing"]} if a.get("replacing") else {})))
    return out


def medal_honors(players, medals, linked=None):
    """{name key: [honor rows]} for registry players' FIBA medals (`national_medals.register_medals`): by NBA id, or, for
    a medal without one, by its dated link (`linked`: `national_medals.links(...)["linked"]`, read on the card date) to
    a registry row in `players`. Any other medal, or one for an id the registry does not track, stays on the tournament
    page only."""
    names = {p["bbr_id"]: p["name"] for p in players if p.get("bbr_id")}
    rows = {p.get("registry_id") or p.get("bbr_id"): p["name"] for p in players}
    out = {}
    for m in medals:
        link = None if m.get("bbr_id") else (linked or {}).get(m["id"])
        name = names.get(m["bbr_id"]) if m.get("bbr_id") else rows.get(link["registry_id"]) if link else None
        if name is None:
            continue
        out.setdefault(_key(name), []).append(dict(
            conference="", name=f"{m['tournament']} {m['name']}", period_start=m["period_start"],
            period_end=m["period_end"], announced_on=m["awarded_on"], award=f"fiba_{m['medal']}",
            filed_on=m["page"], anchor="medals", rank=1, medal=m, **({"link": link} if link else {})))
    return out


def card_data(ctx, player, records=(), shots=()):
    """The dated facts one card renders, shared by the Markdown and HTML outputs."""
    pid = player["registry_id"]
    signed = signed_evidence(player["name"], ctx.on, records, ctx.signed)
    held = ctx.club(player, signed)
    # A season starts in its first year; the card date belongs to that season's colours.
    season_year = int(ctx.season[:4])
    colors = club_colors(held["club"], season_year, ctx.colors)
    rights = ctx.rights.get(_key(player["name"])) if player.get("cohort") == "2003_draft_rights" else None
    photo = ctx.photos.get(pid)
    base = ctx.baseline.get(pid, {})
    wade = pid == "wadedw01"
    if wade:
        snap = ctx.identity["snapshots"][-1]
        jersey = snap.get("jersey")
        prior_program = snap.get("prior_program")
        entry = snap.get("entry")
        measurements = f'{ctx.identity["height_in_shoes"]} (in shoes) · {ctx.identity["weight_lb"]} lb · shoots {ctx.identity["shooting_hand"]}'
    else:
        from .jerseys import number_for
        jersey = number_for(pid, held["club"], ctx.root) if held["club"] else None
        jersey = jersey or base.get("jersey") or None              # real number for the season, else the 2002-03 one
        prior_program = None
        entry = None
        measurements = None
    if held["club"] is None:
        label = "Free agent"
    elif held["rights"]:
        label = f'{held["club"]} (draft rights)'
    else:
        label = held["club"]
    club_label = (f'{held["code"]} rights' if held["rights"] and held["code"] else held["code"]) if held["club"] else "FA"
    stats = {p["id"]: period_statistics(list(records), list(shots), p) for p in ctx.periods}
    closed = sum(1 for r in records if r.get("status") == "played")
    return dict(id=pid, player=player, on=ctx.on, club=held, label=label, club_label=club_label, colors=colors,
                rights=rights, photo=photo, jersey=jersey, prior_program=prior_program, entry=entry, measurements=measurements,
                age=age_on(player["birth_date"], ctx.on) if player.get("birth_date") else "N/A", prior=None if wade else ctx.prior.get(pid),
                contract=(contract_line(player, ctx.contracts, ctx.legend, rights if held["rights"] else None, signed, held)
                          if not wade else wade_contract_line(signed)),
                miami_card=("README.md" if wade else ctx.miami_cards.get(_key(player["name"]))),
                wade=wade, bbr_page=base.get("page_url"), stats=stats, closed=closed)


def _rel(from_dir, target):
    import os
    return Path(os.path.relpath(target, from_dir)).as_posix()


def _pct_cell(v):
    return "N/A" if v is None else f"{v:.1%}"


def _regular_row(ctx, data, team):
    """The card's regular-season row for the live season."""
    s = data["stats"]["season"]["summary"]
    pg, pct = s["pg"], _pct_cell
    return [ctx.season, team, str(s["gp"]), _n(s["gs"], 0), _n(pg["minutes"]), _n(pg["pts"]), _n(pg["reb"]), _n(pg["ast"]),
            _n(pg["stl"]), _n(pg["blk"]), _n(pg["tov"]), pct(s["rates"]["fg_pct"]), pct(s["rates"]["three_pct"]), pct(s["rates"]["ft_pct"])]


def _playoff_row(ctx, p):
    """The card's playoff row for the live season, or None without a playoff appearance."""
    playoff = getattr(ctx, "playoff_lines", {}).get(_key(p["name"]), [])
    ps = aggregate(playoff) if playoff else None
    if not (ps and ps["gp"]):
        return None
    clubs = "/".join(sorted({r["team"] for r in playoff}))
    pg, pct = ps["pg"], _pct_cell
    return [ctx.season, clubs, str(ps["gp"]), _n(ps["gs"], 0), _n(pg["minutes"]), _n(pg["pts"]), _n(pg["reb"]), _n(pg["ast"]),
            _n(pg["stl"]), _n(pg["blk"]), _n(pg["tov"]), pct(ps["rates"]["fg_pct"]), pct(ps["rates"]["three_pct"]),
            pct(ps["rates"]["ft_pct"])]


def markdown_card(ctx, data):
    p, pid = data["player"], data["id"]
    card_dir = ctx.root / CARDS_DIR
    lines = []
    lines.append(f'![{p["name"]}: {data["label"]}, {POSITION_NAMES.get(p["position"], p["position"])}](assets/{pid}_header.svg)\n')
    lines.append("<!-- photo -->")
    if data["photo"]:
        ph = data["photo"]
        lines.append(f'<img src="{ph["headshot_url"]}" alt="{escape(p["name"])}" width="160">\n')
        credit = f'*Photo: {ph.get("headshot_credit") or "credit not recorded"}, {ph.get("headshot_license") or "licence not recorded"}'
        if ph.get("headshot_page"):
            credit += f' ([source page]({ph["headshot_page"]}))'
        lines.append(credit + ".*")
    else:
        lines.append(f'<img src="{SILHOUETTE}" alt="No sourced photo of {escape(p["name"])}" width="160">\n')
        lines.append("*No sourced photo in the league baseline; a neutral silhouette is shown. Photos are never invented.*")
    lines.append("<!-- /photo -->\n")
    lines.append(f'# {p["name"]} | NBA player card\n')
    season_page = ctx.root / LEAGUE_DIR / ctx.season / "League_Stats.md"
    nav = [f'[Interactive card]({pid}.html)', f'[{ctx.season} league statistics]({_rel(card_dir, season_page)})',
           f'[Player registry]({_rel(card_dir, ctx.root / LEAGUE_DIR / "player_registry.json")})',
           f'[Card guide]({_rel(card_dir, ctx.root / "docs/player_cards.md")})']
    if data["miami_card"]:
        target = ctx.root / PLAYER_DIR / "README.md" if data["wade"] else ctx.root / ctx.miami_cards_dir / f'{data["miami_card"]}.md'
        nav.insert(1, f'[{"Career page" if data["wade"] else "Miami card"}]({_rel(card_dir, target)})')
    lines.append(" · ".join(nav) + "\n")
    lines.append(f"The interactive card is an HTML file: GitHub shows it as source, so open `{pid}.html` in a browser from a checkout to use the period selectors, the shot chart and the awards view. This page carries the same facts as text.\n")
    lines.append(f'**Card date:** {ctx.on} · **Club on this date:** {data["label"]} · **Basis:** {data["club"]["basis"]} · **League:** NBA  ')
    lines.append(f'**Position:** {p["position"]} ({POSITION_NAMES.get(p["position"], p["position"])}) · **Jersey:** {("#" + str(data["jersey"])) if data["jersey"] else "Unassigned"} · **Born:** {p["birth_date"]} · **Age on card date:** {data["age"]}  ')
    ids = f'**Registry ID:** `{pid}`'
    if data["bbr_page"]:
        ids += f' · [Basketball-Reference page]({data["bbr_page"]})'
    if p.get("espn_id"):
        ids += f' · ESPN ID {p["espn_id"]}'
    lines.append(ids + "\n")
    if data["measurements"]:
        lines.append(f'**Measurements (career profile, dated {ctx.identity["physical_profile_as_of"]}):** {data["measurements"]} · **Prior program:** {data["prior_program"]}\n')
    lines.append(f'**Contract/control:** {data["contract"]}\n')
    lines.append(f'**Contract pages:** [current contract and history](../../../Contracts/players/{pid}.html#contract) '
                 f'([text](../../../Contracts/players/{pid}.md)).\n')
    if data["wade"]:
        lines.append(f'**NBA entry:** {data["entry"]}. This is the simulation\'s alternate-history player; the historical Wade\'s statistics and biography are never used.\n')
    elif data["rights"]:
        r = data["rights"]
        none = "" if data["closed"] else " No NBA statistics exist for this player on the card date."
        lines.append(f'**2003 draft entry:** No. {r["pick"]} overall, rights held by {r["club"]} (draft of June 26, 2003).{none}\n')
    elif data["prior"]:
        pr = data["prior"]
        lines.append(f'**2002-03 (recorded, {"/".join(pr["team_codes"])}):** {_prior_summary(pr)}.\n')
    else:
        lines.append("**2002-03:** no record in the supplied 2002-03 statistics file.\n")
    lines.append(f'**Colours:** header uses {data["club"]["club"] or "the free-agent placeholder"} colours ({data["colors"]["primary"]} / {data["colors"]["secondary"]}) for the season starting {ctx.season[:4]}; presentation only.\n')
    lines.append("## Simulated statistics\n")
    lines.append(f'As of **{ctx.on}**: {data["closed"]} closed games feed this card. Per-game columns use the repository order; an unavailable value stays N/A, never zero. G and GS are counts; MP and counting statistics are per appearance; shooting uses .500 = 50.0%.\n')
    team = data["club_label"]
    pos = p["position"]
    for kind, heading in (("season", "Season"), ("month", "Month"), ("week", "Week")):
        rows = []
        for period in ctx.periods:
            if period["kind"] != kind:
                continue
            page = ctx.root / LEAGUE_DIR / period["folder"] / "League_Stats.md"
            label = f'[{period["label"]}]({_rel(card_dir, page)})' if page.is_file() else period["label"]
            rows.append(per_game_row(label, data["age"], team, pos, data["stats"][period["id"]]["summary"]))
        lines.append(f"### {heading}\n")
        if kind != "season":
            lines.append(f"<details>\n<summary>{heading} rows: {len(rows)} periods</summary>\n")
        lines.append(markdown_table(PER_GAME_COLUMNS, rows).rstrip() + "\n")
        if kind != "season":
            lines.append("</details>\n")
    lines.append("## Shooting zones\n")
    season_stats = data["stats"]["season"]
    season = season_stats["shooting"]
    cov = season["coverage"]
    lines.append(f'Aggregated with `runtime/shot_chart.py` over closed results of the {ctx.season} regular season. Coverage: **{cov["status"]}**; {cov["located_attempts"]} located attempts, {cov["unlocated_attempts"]} unlocated, {cov["outside_view_attempts"]} outside the view, {_n(cov["missing_attempts"], 0)} missing. Incomplete coverage leaves full-period zone rates unavailable; old box scores are never assigned locations.\n')
    tracked = season_stats["tracked"]
    if tracked is not None:
        cohort = season_stats["tracking_cohort"]
        lines.append(f'### Tracked games only\n\n{tracked["source_note"]} '
                     f'{cohort["games"]} of {cohort["total_games"]} closed games; '
                     f'{cohort["appearances"]} tracked appearances form the denominator below '
                     f'({cohort["start"]} to {cohort["end"]}).\n')
        season = tracked["shooting"]
    zone_rows = []
    for z in [*season["zones"], dict(id="total", label="All field goals", **season["totals"])]:
        zone_rows.append([z["label"], _n(z.get("fgm"), 0), _n(z.get("fga"), 0),
                          "N/A" if z.get("fg_pct") is None else f'{z["fg_pct"]:.1%}', _n(z.get("fg_ppg"), 2), _n(z.get("fga_per_game"), 2)])
    lines.append(markdown_table(["Zone", "FGM", "FGA", "FG%", "FG points / game", "FGA / game"], zone_rows).rstrip() + "\n")
    lines.append("## Regular-season statistics by year\n")
    lines.append("G and GS are counts. MIN and all other counting statistics are per game. Percentages use total makes divided by total attempts.\n")
    hist = ["Season", "Team(s)", "G", "GS", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "FG%", "3P%", "FT%"]
    rows = []
    started = (f"{ctx.season} is simulated: {data['closed']} closed regular-season games through {ctx.on}."
               if data["closed"] else f"{ctx.season} is simulated and has not started.")
    if data["prior"]:
        rows.append(_prior_row(data["prior"], "/".join(data["prior"]["team_codes"])))
        coverage = f"2002-03 regular season from the supplied statistics file; earlier seasons are not imported. {started}"
    elif data["wade"]:
        coverage = f"No NBA season before 2003-04. The historical Wade's statistics are never imported. {started}" if data["closed"] else "No NBA season before 2003-04. The historical Wade's statistics are never imported."
    elif data["rights"]:
        coverage = f"No NBA season before 2003-04 (2003 draft entry). {started}" if data["closed"] else "No NBA season before 2003-04 (2003 draft entry)."
    else:
        coverage = f"No 2002-03 record in the supplied statistics file. {started}"
    for season in sorted(ctx.history):                                   # earlier simulated seasons, as they closed
        row = ctx.history[season].get(data["id"], {}).get("regular")
        if row:
            rows.append(row)
    if ctx.history:
        coverage += " Earlier simulated seasons from their closed results."
    pct = _pct_cell
    rows.append(_regular_row(ctx, data, team))
    lines.append(f"**Coverage:** {coverage}\n")
    lines.append(markdown_table(hist, rows).rstrip() + "\n")
    lines.append("## Playoff statistics by year\n")
    bracket = _rel(ctx.root / CARDS_DIR, ctx.root / LEAGUE_DIR / ctx.season / "Playoffs.md")
    prow = _playoff_row(ctx, p)
    if prow:
        lines.append(f"**Coverage:** {ctx.season} playoffs from closed playoff results through {ctx.on} "
                     f"([bracket]({bracket}); `runtime/playoff_stats.py`). Prior playoff history is not imported into this card.\n")
    else:
        from .seasons import read as season_file
        openers = season_file(ctx.season, "playoff_rules", ctx.root)["calendar"]["first_round"]["openers"]
        started = ctx.on >= min(openers)                    # the season's first-round opening day
        lines.append(f"**Coverage:** {ctx.season} playoffs " + (f"([bracket]({bracket})): no playoff appearance through {ctx.on}."
                     if started else "have not started.") + " Prior playoff history is not imported into this card.\n")
        prow = [ctx.season, team, "0", *["N/A"] * (len(hist) - 3)]
    earlier = [ctx.history[x].get(data["id"], {}).get("playoff") for x in sorted(ctx.history)]
    lines.append(markdown_table(hist, [r for r in earlier if r] + [prow]).rstrip() + "\n")
    lines += awards_lines(ctx, p)
    return "\n".join(lines)


def awards_lines(ctx, p):
    """The card's final section: closed league award decisions, All-Star selections (`all_star_honors`) and FIBA team
    medals (`medal_honors`), by date."""
    lines = ["## Awards and honors\n"]
    honors = ctx.honors.get(_key(p["name"]), [])
    if not honors:
        lines.append(f"No simulated honor has been recorded for this player through {ctx.on}. Historical awards are not imported. Honors appear here only from a closed award decision in the league award records.\n")
    else:
        won = sum(1 for h in honors if h["rank"] == 1 and not h.get("medal"))
        medals = sum(1 for h in honors if h.get("medal"))
        if medals:
            lines.append(f"Simulated honors and shortlist placings through {ctx.on}, from closed award decisions "
                         f"({won} won), and {medals} FIBA team medal{'s' if medals > 1 else ''} from closed tournaments' "
                         "medal registers (every player on a medal team's locked roster). Historical awards are not imported.\n")
        else:
            lines.append(f"Simulated honors and shortlist placings through {ctx.on}, from closed award decisions "
                         f"({won} won). Historical awards are not imported.\n")
        rows = []
        for h in sorted(honors, key=lambda h: (h["announced_on"], h["award"])):
            page = _rel(ctx.root / CARDS_DIR, ctx.root / h["filed_on"]) + (f"#{h['anchor']}" if h.get("anchor") else "")
            if h.get("medal"):
                m = h["medal"]
                result = f"**{m['name'].capitalize()}** ({m['country']}, place {m['place']})"
                if h.get("link"):                      # won under his FIBA identity, linked once he is in the registry
                    result += f"; won as {m['player']} (FIBA identity), on this card from {h['link']['linked_on']}"
                rows.append([h["name"], f"{h['period_start']} to {h['period_end']}", h["announced_on"], result,
                             f"[Tournament]({page})"])
                continue
            result = ("**Selected**" if h.get("selected") or (h.get("annual") and "Team" in h["name"]) else "**Winner**") \
                if h["rank"] == 1 else (f"No. {h['rank']} in the vote" if h.get("annual") else f"Shortlist, No. {h['rank']}")
            if h.get("replacing"):
                result += f", replacing {h['replacing']}"
            rows.append([f"{h['conference']} {h['name']}".strip(), f"{h['period_start']} to {h['period_end']}", h["announced_on"], result,
                         f"[Decision]({page})"])
        lines.append(markdown_table(["Award", "Period", "Announced", "Result", "Record"], rows).rstrip() + "\n")
    return lines


def _empty_period(period, stat):
    summary, shooting = stat["summary"], stat["shooting"]
    out = dict(id=period["id"], label=period["label"], kind=period["kind"], season=period["folder"].split("/")[0], start=period["start"],
               end=period["end"], cutoff=period["end"], games=summary["closed"], appearances=summary["gp"], dnp=summary["dnp"],
               source_games=_source_games(stat["selected"]), shot_source_type=stat["shot_source_type"],
               tracked=stat["tracked"], tracking_cohort=stat["tracking_cohort"])
    if summary["closed"]:
        shots = {k: v for k, v in shooting.items() if k not in ("geometry", "notes")}
        out.update(box=summary["totals"], rates=summary["rates"], shooting=shots, shots=stat["shots"])
    return out


def award_notice(ctx, p):
    honors = ctx.honors.get(_key(p["name"]), [])
    annual = [f"{h['conference']} {h['name']}".strip() for h in honors if h.get("annual") and h["rank"] == 1]
    periodic = [f"{h['conference']} {h['name']} ({h['period_start']} to {h['period_end']})"
                for h in honors if h["rank"] == 1 and not h.get("annual") and not h.get("medal")]
    medals = [f"{h['name']} ({h['medal']['country']})" for h in honors if h.get("medal")]
    first = ("Season honors: " + "; ".join(annual) + ". ") if annual else \
        f"No annual award has been recorded for this player through {ctx.on}. "
    return first + ("Weekly and monthly honors won: " + "; ".join(periodic) + "." if periodic
                    else "Weekly and monthly honors stay in the league award records.") + \
        (" FIBA team medals: " + "; ".join(medals) + "." if medals else "")


def html_payload(ctx, data):
    p = data["player"]
    photo = data["photo"]["headshot_url"] if data["photo"] else "./" + SILHOUETTE
    identity = dict(name=p["name"], team=data["label"], jersey=data["jersey"], position=p["position"], age=data["age"],
                    photo_url=photo, initials="".join(w[0] for w in p["name"].split()[:2]).upper(),
                    status=f'Club on {ctx.on}: {data["label"]}', contract=data["contract"],
                    colors=dict(primary=data["colors"]["primary"], secondary=data["colors"]["secondary"]))
    if data["photo"]:
        identity["photo_credit"] = f'{data["photo"].get("headshot_credit")} · {data["photo"].get("headshot_license")}'
    notice = (f"LEAGUE PLAYER CARD · Evidence dated on or before {ctx.on}. Simulated statistics only; "
              "no real results from a simulated season, no later-career facts. Shot locations appear only from recorded closed results.")
    card_dir = ctx.root / CARDS_DIR
    links = dict(stats=_rel(card_dir, ctx.root / LEAGUE_DIR / ctx.season / "League_Stats.md"),
                 shooting=f'{data["id"]}.md#shooting-zones', awards=f'{data["id"]}.md#awards-and-honors',
                 definitions=_rel(card_dir, ctx.root / "docs/player_cards.md"),
                 contract=_rel(card_dir, ctx.root / PLAYER_DIR / "Contracts/players" / f'{data["id"]}.html') + "#contract")
    return dict(schema_version=1, mode="live", record_type="league_player_card", card_date=ctx.on,
                identity=identity, notice=notice, enabled_tabs=["shooting", "awards"], links=links,
                geometry=NBA_GEOMETRY, zones=ZONES, default_period="season",
                periods=[dict(_empty_period(period, data["stats"][period["id"]]), cutoff=min(ctx.on, period["end"]))
                         for period in ctx.periods],
                awards=dict(default_scenario="current", scenarios=[dict(
                    id="current", label=f"{ctx.season} season", season=ctx.season, cutoff=ctx.on,
                    notice=award_notice(ctx, p),
                    records=[])]))


def html_template(template):
    """Use the shared live renderer, retaining league colours and empty periods."""
    marker = "const DATA=JSON.parse(document.getElementById('player-card-data').textContent);"
    if template.count(marker) != 1 or template.count("__PLAYER_CARD_DATA__") != 1:
        raise ValueError("shared player-card template must contain one data token and initializer")
    text = template.replace(marker, marker +
        "const EMPTY_BOX={pts:0,fgm:0,fga:0,tpm:0,tpa:0,ftm:0,fta:0,orb:0,drb:0,ast:0,stl:0,blk:0,tov:0,pf:0,seconds:0,ft_points:0,two_pm:0,two_pa:0,reb:0};"
        "const EMPTY_SHOOTING=p=>({schema_version:1,scope:{start:p.start,end:p.end},games:0,recorded_appearances:0,dnp:0,closed_games:0,"
        "totals:{fgm:null,fga:null,tpm:null,tpa:null,fg_points:null,fg_pct:null,fg_ppg:null,fga_per_game:null},observed:{fgm:0,fga:0,tpm:0,tpa:0,fg_points:0},"
        "zones:DATA.zones.map(z=>({...z,fgm:null,fga:null,tpm:null,tpa:null,fg_points:null,fg_pct:null,fg_ppg:null,fga_per_game:null,coverage:'unavailable',observed_fgm:0,observed_fga:0,observed_fg_points:0})),"
        "bins:[],coverage:{status:'unavailable',located_attempts:0,unlocated_attempts:0,outside_view_attempts:0,missing_attempts:0,known_missing_attempts:0,recorded_attempts:0,box_fga:0,missing_box_games:[],missing_shot_games:[],location_fraction:null},source_refs:[]});"
        "DATA.periods=DATA.periods.map(p=>p.shooting?p:{...p,box:{...EMPTY_BOX},rates:{},shooting:EMPTY_SHOOTING(p)});"
        "if(DATA.identity.colors){document.documentElement.style.setProperty('--red',DATA.identity.colors.primary);document.documentElement.style.setProperty('--red-bright',DATA.identity.colors.secondary);const identityBox=document.querySelector('.identity');identityBox.style.background='linear-gradient(115deg,'+DATA.identity.colors.primary+' 0,#12151b 58%,'+DATA.identity.colors.primary+' 100%)';identityBox.style.borderColor=DATA.identity.colors.secondary;document.getElementById('player-number').style.color=DATA.identity.colors.secondary;}")
    # This renderer also serves illustrative fixtures. Live league cards never
    # use that branch; remove its example notice from the published document.
    return text.replace("FICTIONAL EXAMPLE · Same six sample appearances as the statistical reports. Shot locations demonstrate the interface; they are not recorded Wade shots or live career results.",
                        "League player card: saved closed-game evidence only.")


def html_card(ctx, data, template=None):
    template = template or html_template(ctx.template)
    payload = html_payload(ctx, data)
    encoded = json.dumps(stable(payload), separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    p = data["player"]
    text = template.replace("__PLAYER_CARD_DATA__", encoded)
    text = text.replace("<title>Player · Shooting, Contract &amp; Awards</title>",
                        f'<title>{escape(p["name"])} · NBA player card · {ctx.on}</title>')
    text = text.replace("<title>Player · Shooting, Contract & Awards</title>",
                        f'<title>{escape(p["name"])} · NBA player card · {ctx.on}</title>')
    text = text.replace('<h1 id="player-name">Player</h1>', f'<h1 id="player-name">{escape(p["name"])}</h1>')
    text = text.replace('<span class="portrait-initials" id="player-initials"></span>',
                        f'<span class="portrait-initials" id="player-initials">{escape(payload["identity"]["initials"])}</span>')
    return text


def index_page(ctx, cards):
    lines = [f"# NBA player cards | {ctx.season}\n",
             f'[League record guide](../README.md) · [{ctx.season} league statistics](../{ctx.season}/League_Stats.md) · [Player registry](../player_registry.json) · [Card guide]({_rel(ctx.root / CARDS_DIR, ctx.root / "docs/player_cards.md")})\n',
             f"Card date: **{ctx.on}**. {len(cards)} registry players, one Markdown card and one interactive HTML card each; {sum(1 for c in cards if c['photo'])} cards carry a sourced photo, the rest a neutral silhouette. Regenerate with `python scripts/build_league_cards.py --write`; the interactive card opens in a browser from a checkout (GitHub shows HTML as source).\n"]
    for pos in ctx.registry["positions"]:
        group = sorted((c for c in cards if c["player"]["position"] == pos), key=lambda c: c["player"]["name"])
        lines.append(f"<details>\n<summary>{pos} · {POSITION_NAMES.get(pos, pos)}s · {len(group)} players</summary>\n")
        rows = [[f'[{c["player"]["name"]}]({c["id"]}.md)', c["label"], str(c["age"]), "sourced" if c["photo"] else "silhouette",
                 f'[open]({c["id"]}.html)'] for c in group]
        lines.append(markdown_table(["Player", "Club on card date", "Age", "Photo", "Interactive"], rows).rstrip() + "\n")
        lines.append("</details>\n")
    return "\n".join(lines)


def closed_card_feeds(ctx):
    """Closed box records and trusted engine shots, keyed by the same registry identity.

    Resolve the box player once with the write-back's dated club/BBR mapping,
    then select events by that exact result side and player ID. Matching boxes
    alone never establishes shot ownership, and an old result gains no locations.
    """
    from .season_games import note_meta
    from .write_back import bbr_lookup, closed_results, game_records, identity_sources
    by_bbr = {p["bbr_id"]: p for p in ctx.registry["players"] if p.get("bbr_id")}
    unique_names, _ = identity_sources(ctx.root)
    by_name = {}
    for player in ctx.registry["players"]:
        by_name.setdefault(_key(player["name"]), []).append(player)
    lookup = bbr_lookup(ctx.root, ctx.season)
    lines, shots = {}, {}
    card_dir = ctx.root / CARDS_DIR
    for row in closed_results(ctx.root, ctx.season, ctx.on):
        result = row["result"]
        if row["note"] is not None:
            note = row["note"]
            source = note.parent / note_meta(note)["result_file"]
        else:
            source = ctx.root / LEAGUE_DIR / ctx.season / "Games" / f'{result["event_id"]}.result.json'
        events = engine_result_shots(result, source_ref=_rel(card_dir, source))
        tracked = bool(result.get("shot_tracking"))
        owners = set()
        events_by_player = {}
        for event in events:
            events_by_player.setdefault((event["side"], event["player_id"]), []).append(event)
        for side, player_id, bbr, record in game_records(row, ctx.root, ctx.season):
            known_bbr = lookup.get((result[side], _key(player_id)))
            if tracked and bbr and known_bbr and bbr != known_bbr:
                raise ValueError(f"{result['event_id']}: shot player identity disagrees with the club's recorded BBR ID")
            bbr = bbr or known_bbr or (player_id if player_id in by_bbr else None) or unique_names.get(_key(player_id))
            matches = by_name.get(_key(player_id), [])
            if (tracked and bbr and len(matches) == 1 and matches[0].get("bbr_id")
                    and matches[0]["bbr_id"] != bbr):
                raise ValueError(f"{result['event_id']}: shot player identity disagrees with the named registry player")
            player = by_bbr.get(bbr) if bbr else None
            if player is None:
                if tracked and len(matches) > 1:
                    raise ValueError(f"{result['event_id']}: ambiguous shot player identity {player_id}")
                player = matches[0] if matches else None
            if player is None:
                continue
            registry_id = player["registry_id"]
            if tracked and registry_id in owners:
                raise ValueError(f"{result['event_id']}: duplicate tracked registry player {registry_id}")
            owners.add(registry_id)
            if record.get("note") is not None:
                record["href"] = _rel(card_dir, record["note"])
            elif tracked:
                record["href"] = _rel(card_dir, source)
            if tracked:
                record.update(shot_tracking_available=True, shot_source_type="engine_generated",
                              result_href=_rel(card_dir, source), shot_href=_rel(card_dir, source),
                              shot_source_label="Simulated engine shot data")
            lines.setdefault(registry_id, []).append(record)
            shots.setdefault(registry_id, []).extend(events_by_player.get((side, player_id), ()))
    return lines, shots


def closed_records(ctx):
    """registry_id -> closed regular-season records on or before the card date."""
    return closed_card_feeds(ctx)[0]


def build_cards(root=ROOT, ctx=None):
    """All league card outputs as {path: text}; reads dated records only, writes nothing."""
    ctx = ctx or CardContext(root)
    folder = ctx.root / CARDS_DIR
    template = html_template(ctx.template)
    outputs = {folder / SILHOUETTE: silhouette_svg()}
    cards = []
    records, shots = closed_card_feeds(ctx)
    for player in ctx.registry["players"]:
        data = card_data(ctx, player, records.get(player["registry_id"], ()), shots.get(player["registry_id"], ()))
        cards.append(data)
        outputs[folder / f'{data["id"]}.md'] = markdown_card(ctx, data)
        outputs[folder / f'{data["id"]}.html'] = html_card(ctx, data, template)
        outputs[folder / "assets" / f'{data["id"]}_header.svg'] = header_svg(player, data["club"], data["colors"], data["jersey"], data["label"])
    outputs[folder / "README.md"] = index_page(ctx, cards)
    return outputs


def write_card_lines(root=ROOT):
    """At a season's close: every registry player's closed rows for the live season, kept for later seasons' cards
    (`card_lines_path`). Players without a regular-season appearance keep no row."""
    ctx = CardContext(root)
    records, shots = closed_card_feeds(ctx)
    out = {}
    for player in ctx.registry["players"]:
        data = card_data(ctx, player, records.get(player["registry_id"], ()), shots.get(player["registry_id"], ()))
        entry = {}
        if data["stats"]["season"]["summary"]["gp"]:
            entry["regular"] = _regular_row(ctx, data, data["club_label"])
        prow = _playoff_row(ctx, player)
        if prow:
            entry["playoff"] = prow
        if entry:
            out[data["id"]] = entry
    path = ctx.root / card_lines_path(ctx.season)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "season": ctx.season, "as_of": ctx.on,
                                "rule": "runtime/league_cards.write_card_lines at the season close", "players": out},
                               indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_cards(root=ROOT):
    outputs = build_cards(root)
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return outputs


def check_cards(root=ROOT):
    """Paths whose on-disk content differs from a fresh build (missing files included)."""
    stale = []
    for path, text in build_cards(root).items():
        try:
            if path.read_text(encoding="utf-8") != text:
                stale.append(path)
        except OSError:
            stale.append(path)
    return stale


def card_errors(root=ROOT):
    """Validation: every registry player has both cards, final sections in order, no invented photo URL."""
    root = Path(root)
    errors = []
    registry = _read(root, LEAGUE_DIR / "player_registry.json")
    folder = root / CARDS_DIR
    allowed = {v["headshot_url"] for v in photo_sources(root).values()}
    for player in registry["players"]:
        pid = player["registry_id"]
        md, html = folder / f"{pid}.md", folder / f"{pid}.html"
        if not md.is_file() or not html.is_file():
            errors.append(f"league card missing for {player['name']} ({pid})")
            continue
        text = md.read_text(encoding="utf-8")
        headings = re.findall(r"^## .+$", text, re.M)
        if headings[-3:] != FINAL_SECTIONS:
            errors.append(f"{md.relative_to(root)}: regular-season statistics, playoffs and awards must be the final sections")
        for src in re.findall(r'<img src="([^"]+)"', text):
            if src != SILHOUETTE and src not in allowed:
                errors.append(f"{md.relative_to(root)}: photo URL is not in the league baseline: {src}")
        if "__PLAYER_CARD_DATA__" in html.read_text(encoding="utf-8"):
            errors.append(f"{html.relative_to(root)}: card data not embedded")
    if not (folder / SILHOUETTE).is_file():
        errors.append("league cards: missing shared silhouette asset")
    return errors
