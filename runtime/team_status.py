"""Dated team-status blocks for Miami's team desk and the league standings page.

The team READMEs were written at the June 26, 2003 import. Write-back refreshes one generated block in each, on the
career clock, from the owning records only:
- the register (`Team/Roster/roster.json`), the injured list (`Transactions/injured_list.json`) and the rotation in
  force (`rotation_reviews.rotation_in_force`): who is on Miami's books, who is available, who starts (the depth
  chart itself, with injured starters marked, is `roster_moves.py`'s);
- closed results (`standings.standings_on`): Miami's record and the league standings by conference;
- `Finances/finance.json`: the live cap position.
Text outside the markers is never touched. Nothing here decides anything; it is a projection of dated records.
"""
import json
from pathlib import Path
import re

from .miami_register import RIGHTS_ONLY      # rights Miami holds without a contract

ROOT = Path(__file__).resolve().parents[1]
FIRST_SEASON = "2003-04"                     # the season whose June 26, 2003 import text the first refresh migrated


def _season(root=None):
    from .seasons import active
    return active(root or ROOT)


def team_dir(season):
    return Path(f"career/Dwyane_Wade/{season}/00_Team")


def standings_page(season):
    return Path(f"career/Dwyane_Wade/Stats_and_Awards/League/{season}/Standings.md")


TEAM = team_dir(FIRST_SEASON)
START, END = "<!-- team-status:start -->", "<!-- team-status:end -->"
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")
# Stale import text the first refresh replaces with the generated block (one-time migration).
STALE = {
    TEAM / "README.md": [r"Snapshot date: June 26, 2003\.\n", r"\nThe snapshot stops at the draft\.[^\n]*\n"],
    TEAM / "Team/README.md": [r"Snapshot date: June 26, 2003\.\n", r"\nThe roster includes players still under 2002-03 control[^\n]*\n"],
    TEAM / "Team/Roster/README.md": [r"\[roster\.json\]\(roster\.json\) is the machine-readable June 26, 2003 register\.\n",
                                     r"\nThis is not a finalized opening-night roster\.[^\n]*\n"],
    TEAM / "Finances/README.md": [r"June 26, 2003 · 2003-04 through 2010-11 · AI/GM record\n", r"\nThe cap sheet records approximately[^\n]*\n"],
}


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _money(x):
    return "N/A" if x is None else f"-${-x:,}" if x < 0 else f"${x:,}"


def put(text, block):
    """Replace the generated block, or on first use put it where the stale import text stood (else after the title)."""
    body = f"{START}\n\n{block.strip()}\n\n{END}"
    if START in text:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: body, text, count=1, flags=re.S)
    return None


def migrate(text, patterns, block):
    out = put(text, block)
    if out is not None:
        return out
    body = f"{START}\n\n{block.strip()}\n\n{END}\n"
    placed = False
    for pat in patterns:
        if re.search(pat, text):
            text = re.sub(pat, (lambda _: "\n" + body) if not placed else (lambda _: "\n"), text, count=1)
            placed = True
    if not placed:
        lines = text.split("\n", 1)
        text = lines[0] + "\n\n" + body + ("\n" + lines[1] if len(lines) > 1 else "")
    return re.sub(r"\n{3,}", "\n\n", text)




def register(root, on, season=None):
    """Miami's current register on the date: [(roster entry, availability, role)]. A rights holder without a contract
    (RIGHTS_ONLY) is labelled as such and has no role, and so, from July 1, is a player whose contract ended on June 30
    (`ended`), whatever the injured list still shows; positions are the register's on the date
    (`miami_register.positions_on`)."""
    from .miami_cards import injured_on, role_in
    from .miami_register import positions_on
    from .rotation_reviews import rotation_in_force
    season = season or _season(root)
    roster = _read(Path(root) / team_dir(season) / "Team/Roster/roster.json")
    try:
        rotation, _depth = rotation_in_force(on, root, season, require_review=False)
    except (OSError, ValueError, KeyError):
        rotation = {}
    over = ended(root, on, season)
    out = []
    for p in roster["players"]:
        if any(w in (p.get("status") or "") for w in GONE):
            continue
        p = dict(p, positions=positions_on(p, on))
        if p["name"] in over:
            out.append((p, f"Contract ended June 30, {int(season[:4]) + 1}", "N/A"))
            continue
        hurt = injured_on(root, p["name"], on, season)
        if hurt:
            kind = "injured" if hurt["reason"].startswith("injury") else "inactive reserve"
            avail = f"Injured list since {hurt['placed']}, {kind}"
        elif p.get("status") == "free_agent_rights_held":
            avail = "Unsigned; Miami holds his free-agent rights"
        elif p.get("status") == "unsigned_draft_rights":
            avail = "Unsigned draft rights; not on the roster"
        else:
            avail = "Available"
        role = role_in(rotation, p["name"]) if rotation and p.get("status") not in RIGHTS_ONLY else "N/A"
        out.append((p, avail, role))
    return out


def _ending(root, on, season):
    """The contract-sheet rows of the register's contracts that end on June 30 of the season, from the day after the
    regular season (`seasons.dates`): a contract with no salary after the season in `Finances/contract_schedules.json`.
    In season, and without a contract sheet, there are none."""
    from .seasons import dates
    if on <= dates(season, root)["regular_season_end"]:
        return []
    path = Path(root) / team_dir(season) / "Finances/contract_schedules.json"
    if not path.is_file():
        return []
    out = []
    for c in _read(path)["players"]:
        if any(w in (c.get("status") or "") for w in GONE) or "unsigned" in (c.get("status") or ""):
            continue
        sched = c.get("schedule") or {}
        if not sched.get(season) or any(v for s, v in sched.items() if s > season):
            continue
        out.append(c)
    return out


def ended(root, on, season=None):
    """Names whose contract ended on June 30 of the season, from July 1 until the rollover makes the next season live
    (the last date this season's desk is shown): no longer under contract, so neither counted nor listed as injured."""
    season = season or _season(root)
    return set() if on <= f"{int(season[:4]) + 1}-06-30" else {c["player"] for c in _ending(root, on, season)}


ROUTES = {"bird": "Bird rights", "early_bird": "Early Bird rights", "non_bird": "Non-Bird rights",
          "mid_level": "mid-level exception", "cap_room": "cap room", "minimum": "minimum"}


def _terms(e):
    years = e.get("years")
    return (f"${e['salary']:,}" + (f" x {years} season{'s' if years != 1 else ''}" if years else "")
            + (f", {ROUTES.get(e['route'], e['route'].replace('_', ' '))}" if e.get("route") else ""))


SUMMER = {
    "qualifying_offer": lambda e: f"{e['club']} tendered a ${e['amount']:,} qualifying offer on {e['date']} (restricted free agent)",
    "qualifying_offer_accepted": lambda e: f"accepted {e['club']}'s ${e['salary']:,} qualifying offer on {e['date']} (one season)",
    "offer_sheet": lambda e: f"signed an offer sheet with {e['club']} on {e['date']} ({_terms(e)})",
    "offer_sheet_matched": lambda e: f"{e['club']} matched it",
    "offer_sheet_not_matched": lambda e: f"{e['club']} did not match; he joined {e['to']}",
    "re_sign": lambda e: f"re-signed with {e['club']} on {e['date']} ({_terms(e)})",
    "signing": lambda e: f"signed with {e['club']} on {e['date']} ({_terms(e)})",
    "camp_signing": lambda e: f"signed with {e['club']} at the {e['date']} roster fill ({_terms(e)})",
    "renounce": lambda e: f"{e['club']} renounced his rights on {e['date']}"
                          + (" and withdrew its qualifying offer" if e.get("qualifying_offer_withdrawn") else ""),
    "trade": lambda e: f"traded to {e['club']} on {e['date']}",
}


def summer_outcomes(root, season, on):
    """{bbr_id and name: the summer's outcome} from the closed market record that opened the next season
    (`free_agency_2004.record_for`): each of the player's market events dated on or before `on`, in order, then where the
    close left him (the unsigned pool, out of the league). None until that record exists and `on` has reached its close:
    the market writes it once, on its September 30 close, and a page never replays the market."""
    from .free_agency_2004 import record_for
    from .seasons import next_season
    path = Path(root) / record_for(next_season(season))
    if not path.is_file():
        return None
    record = _read(path)
    if on < record["to"]:
        return None
    out = {}

    def add(row, text):
        for key in {row.get("bbr_id"), row.get("player")} - {None}:
            out.setdefault(key, []).append(text)
    for e in record["events"]:
        if e["date"] <= on:
            add(e, SUMMER.get(e["kind"], lambda e: f"{e['kind'].replace('_', ' ')} on {e['date']}")(e))
    for p in record.get("unsigned_pool") or []:
        add(p, f"unsigned when the market closed on {record['to']}; "
               + (f"{p['rights']} holds his rights" if p.get("rights") else "no club holds his rights"))
    for p in record.get("left_the_league") or []:
        add(p, f"left the league ({p['basis']})")
    return {k: "; ".join(v) for k, v in out.items()}


def expiring(root, on, season=None):
    """{player: label} for the register's contracts that end on June 30 of the season (`_ending`), from the day after the
    regular season. Through June 30 the label reads "expiring"; a rookie-scale contract ending is labelled with the club's
    qualifying-offer decision, which makes him a restricted free agent if tendered. From July 1 until the rollover the
    contract has ended (the final audit, R3): "contract ended June 30; free agent", then the summer's outcome from the
    closed market record (`summer_outcomes`: re-signed, qualifying offer, offer sheet matched, signed elsewhere, unsigned)
    once the market has closed, before that a line saying it is recorded at the close. The register's `status` is never
    changed (the front office reads it); this is a label on the desk only."""
    from .seasons import next_season
    season = season or _season(root)
    end_year = int(season[:4]) + 1
    close = f"{end_year}-06-30"
    rows = _ending(root, on, season)
    if not rows:
        return {}
    if on > close:
        outcomes = summer_outcomes(root, season, on)
        reg = Path(root) / team_dir(season) / "Team/Roster/roster.json"
        bbr = {p["name"]: p.get("bbr_id") for p in (_read(reg)["players"] if reg.is_file() else [])}
    out = {}
    for c in rows:
        rookie = c.get("status") == "under_rookie_contract"
        if on <= close:
            label = f"expiring June 30, {end_year}"
            if rookie:
                label += (f"; rookie scale: Miami's qualifying-offer decision is due by June 30, {end_year} (tendered, he is a "
                          f"restricted free agent for {next_season(season)})")
        elif outcomes is None:
            label = (f"contract ended June 30, {end_year}; free agent; "
                     + ("rookie scale: Miami's June 30 qualifying-offer decision and his summer outcome are" if rookie
                        else "his summer outcome is") + f" recorded when the summer market closes ({end_year}-09-30)")
        else:
            told = (outcomes.get(c.get("bbr_id") or bbr.get(c["player"]) or c["player"]) or outcomes.get(c["player"])
                    or "no summer market event recorded")
            if rookie and "qualifying offer" not in told:
                told = "rookie scale: Miami made no qualifying offer (unrestricted); " + told
            label = f"contract ended June 30, {end_year}; free agent; {told}"
        out[c["player"]] = label
    return out


def standings_rows(root, on, season=None):
    from .seasons import conferences
    from .standings import standings_on
    season = season or _season(root)
    table = standings_on(on, root, season)
    confs = conferences(season, root)
    out = {}
    for conf, clubs in confs.items():
        rows = sorted(clubs, key=lambda c: (-table.get(c, {}).get("pct", 0.0), -table.get(c, {}).get("wins", 0), c))
        lead = table.get(rows[0], {"wins": 0, "losses": 0})
        out[conf] = []
        for i, c in enumerate(rows, 1):
            t = table.get(c, {"wins": 0, "losses": 0, "pct": 0.0})
            gb = ((lead["wins"] - t["wins"]) + (t["losses"] - lead["losses"])) / 2
            out[conf].append([str(i), f"**{c}**" if c == "Miami Heat" else c, str(t["wins"]), str(t["losses"]),
                              f"{t['pct']:.3f}"[1:] if t["pct"] < 1 else "1.000", "—" if gb == 0 else f"{gb:g}"])
    return out, table


def _table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                     + ["| " + " | ".join(r) + " |" for r in rows])


def blocks(root, on, season=None):
    """{page: generated block} on the date, for the live season or, to regenerate a closed season's frozen blocks once,
    the season named."""
    from .seasons import dates, start_year
    root = Path(root)
    season = season or _season(root)
    TEAM, STANDINGS = team_dir(season), standings_page(season)
    LEAGUE_DIR = STANDINGS.parent
    gates = dates(season, root)
    reg = register(root, on, season)
    conf_rows, table = standings_rows(root, on, season)
    mia = table.get("Miami Heat", {"wins": 0, "losses": 0})
    east = [r[1].strip("*") for r in conf_rows.get("East", [])]
    place = east.index("Miami Heat") + 1 if "Miami Heat" in east else None
    ordinal = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
    record = f"{mia['wins']}-{mia['losses']}" + (f", {ordinal(place)} in the East" if place else "")
    over = ended(root, on, season)
    signed = [r for r in reg if r[0].get("status") not in RIGHTS_ONLY and r[0]["name"] not in over]
    listed = [r for r in signed if r[1].startswith("Injured list")]
    ending = expiring(root, on, season)
    end = int(season[:4]) + 1
    ends = (f" {len(over)} contracts ended on June 30, {end}; they are not counted (labelled on the register)." if over
            else f" {len(ending)} of the contracts end on June 30, {end} (labelled on the register)." if ending else "")
    standings_link = lambda frm: Path("../" * len(frm.parent.parts)).joinpath(STANDINGS).as_posix()
    team_readme = TEAM / "README.md"
    out = {}
    out[team_readme] = (f"**Status on {on}** (generated from dated records): Miami {record} "
                        f"([standings]({standings_link(team_readme)})). {len(signed)} players under contract, "
                        f"{len(listed)} on the injured list.{ends} Head coach {_read(root / TEAM / 'team_config.json').get('head_coach', 'N/A')}; the staff rotation in force and "
                        f"the register are in [Team](Team/README.md).")
    out[TEAM / "Team/README.md"] = (
        f"**Status on {on}:** {len(signed)} under contract ({len(signed) - len(listed)} active, {len(listed)} on the "
        f"injured list), Miami {record}.{ends} The [register](Roster/README.md) labels every player's control and "
        f"availability; expired, released and voided contracts stay on it as history. Rights held without a contract are "
        f"not counted.")
    rows = [[f"[{p['name']}]({p['player_card']})", "/".join(p.get("positions") or []),
             ending[p["name"]] if p["name"] in over else
             p["status"].replace("_", " ") + (f", {ending[p['name']]}" if p["name"] in ending else ""), a, role]
            for p, a, role in reg]
    out[TEAM / "Team/Roster/README.md"] = (
        f"[roster.json](roster.json) is the machine-readable register (team-control record dated {_read(root / TEAM / 'Team/Roster/roster.json')['as_of']}). "
        f"Availability below is on {on}, from the [injured list](../../Transactions/injured_list.json); role is the staff "
        f"rotation in force.\n\n" + _table(["Player", "Pos", "Control", f"Availability on {on}", "Staff role"], rows) +
        "\n\nPlayers whose contracts ended, were released or voided remain in roster.json with their labels as history.")
    fin = _read(root / TEAM / "Finances/finance.json")
    out[TEAM / "Finances/README.md"] = (
        f"{season} through {start_year(season) + 7}-{str(start_year(season) + 8)[-2:]} · AI/GM record · live position from [finance.json](finance.json) (as of {fin.get('as_of')}), "
        f"shown on {on}\n\nCounted salary {_money(fin.get('known_counted_salary'))} against the published "
        f"{_money(fin.get('live_official_salary_cap'))} cap: cap room {_money(fin.get('cap_room'))} "
        f"({fin.get('cap_status', 'N/A').replace('_', ' ')}). Tax threshold: "
        f"{_money(fin.get('live_official_tax_threshold')) if fin.get('live_official_tax_threshold') else 'not published at this date'}. "
        f"Contract guarantee review: {gates['waive_by']} keep-or-waive, {gates['guarantee']} kept contracts guaranteed.")
    page = [f"# {season} standings", "", f"Through {on}, from closed simulated results only (`runtime/standings.py`). "
            f"Real {season} standings are never used. Ties are ordered by wins, then name; tiebreakers are not applied.", ""]
    if (root / LEAGUE_DIR / "playoffs.json").is_file():
        page += ["The playoffs are seeded: [bracket, seeds and schedule](Playoffs.md).", ""]
    for conf, crows in conf_rows.items():
        page += [f"## {conf}ern Conference", "", _table(["#", "Club", "W", "L", "Pct", "GB"], crows), ""]
    out[STANDINGS] = "\n".join(page)
    return out


# A closed season's register blocks, which `refresh` (the live season only) leaves as its last live day wrote them.
REGISTER_PAGES = ("README.md", "Team/README.md", "Team/Roster/README.md")


def regenerate_closed(root, season, on, write=True):
    """Rewrite a closed season's register blocks (REGISTER_PAGES) through `blocks` as of `on`, its last live day (the
    rollover's eve). Run once by hand for a season whose frozen blocks predate a fix: the final audit (R3) regenerated
    2004-05's as of 2005-09-30, which had counted the eight contracts that ended on June 30, 2005 as under contract.
    Returns the changed paths."""
    root = Path(root)
    changed = []
    for rel, block in blocks(root, on, season).items():
        if rel not in {team_dir(season) / page for page in REGISTER_PAGES} or not (root / rel).is_file():
            continue
        old = (root / rel).read_text(encoding="utf-8")
        new = put(old, block)
        if new is not None and new != old:
            changed.append(root / rel)
            if write:
                (root / rel).write_text(new, encoding="utf-8")
    return changed


TEAM_STATS = Path("career/Dwyane_Wade/Stats_and_Awards/Team")


def team_stats_readme(root):
    """`Stats_and_Awards/Team/README.md`: the hub of Miami's statistics, with a row for every season on file, its
    regular-season and playoff records from Miami's played game notes (`write_back.miami_notes`, whose results
    validation ties to the result files) and the bracket (`playoffs.json`)."""
    from .playoff_stats import ROUND_LABELS
    from .playoffs import read as bracket
    from .seasons import live_seasons
    from .write_back import miami_notes
    root = Path(root)
    seasons = [s for s in live_seasons(root) if (root / TEAM_STATS / s / "Team_Stats.md").is_file()]
    rows = []
    for season in seasons:
        played = [(i["kind"], str(i["meta"].get("result", ""))[:1]) for i in miami_notes(root, season)
                  if i["meta"].get("status") == "played"]
        rw, rl, pw, pl = (played.count((kind, x)) for kind in ("regular", "playoff") for x in ("W", "L"))
        series = [s for s in ((bracket(root, season) or {}).get("series") or []) if "Miami Heat" in s["clubs"]]
        if series:
            last = series[-1]
            reach = (f"{'won' if last['winner'] == 'Miami Heat' else 'lost'} in the {ROUND_LABELS[last['round']].lower()}"
                     if last.get("winner") else f"{ROUND_LABELS[last['round']].lower()} in progress")
            if (bracket(root, season) or {}).get("champion") == "Miami Heat":
                reach = "NBA champion"
            playoffs = f"[{pw}-{pl}, {reach}]({season}/Playoffs/Team_Playoff_Stats.md)"
        elif (bracket(root, season) or {}).get("series"):
            playoffs = "Did not qualify"
        else:
            playoffs = "Not started"
        rows.append([f"[{season}]({season}/Team_Stats.md)", f"{rw}-{rl}" if rw + rl else "Not started", playoffs,
                     f"[roster.json](../../{season}/00_Team/Team/Roster/roster.json)"])
    live = seasons[-1] if seasons else _season(root)
    return "\n".join([
        "# Miami Heat | Team statistics", "",
        f"[Stats hub](../README.md) · [{live} team record]({live}/Team_Stats.md) · "
        f"[Roster and control](../../{live}/00_Team/Team/Roster/roster.json)", "",
        "Miami's year, month and week pages separate player production from shooting detail. The team record sits first. "
        "Per-game columns are labeled explicitly, and player cards and control status are available in the detail section.", "",
        "## Seasons", "",
        "Records from Miami's played game notes and the playoff bracket (generated, `runtime/team_status.py`); each playoff "
        "record links Miami's playoff statistics page.", "",
        _table(["Season", "Regular season", "Playoffs", "Register"], rows), "",
        "## Coverage", "",
        "Each season's register is a team-control record, not a finalized active roster: it labels contracts, options, "
        "rights held without a contract and departures. Only closed Miami games enter these tables, and a period's page "
        "lists only the players Miami held under contract in it; a not-started page lists the register's players under "
        "contract and names the rights it holds.", "",
        "Preserve departures on earlier pages and on the season line for their Miami games. Add arrivals from their first "
        "applicable period. A team record counts each game once; summing player G would overcount games. Keep playoffs "
        "separate: each season's playoff games are on its playoff page.", "",
        "## Updating", "",
        "Use the [shared statistics rules](../README.md) for denominators, DNPs and weighted rollups. Reconcile team scoring "
        "with the player lines. Where the kernel records unassigned team turnovers, team TOV includes those in addition to "
        "individual TOV; never attribute them to a player to force a match. Averages with no appearances and percentages "
        "with no attempts remain N/A.", ""])


def refresh(root=ROOT, write=True, on=None):
    """Rewrite every generated block on the clock. Returns the changed paths."""
    root = Path(root)
    if on is None:
        from .write_back import clock
        on = clock(root)
    changed = []
    readme = root / TEAM_STATS / "README.md"
    text = team_stats_readme(root)
    if readme.parent.is_dir() and (not readme.is_file() or readme.read_text(encoding="utf-8") != text):
        changed.append(readme)
        if write:
            readme.write_text(text, encoding="utf-8")
    standings = standings_page(_season(root))
    for rel, block in blocks(root, on).items():
        path = root / rel
        if rel == standings:
            new = block + "\n"
            old = path.read_text(encoding="utf-8") if path.is_file() else None
        else:
            if not path.is_file():
                continue
            old = path.read_text(encoding="utf-8")
            new = migrate(old, STALE.get(rel, []), block)
        if new != old:
            changed.append(path)
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new, encoding="utf-8")
    return changed
