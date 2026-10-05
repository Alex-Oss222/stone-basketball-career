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
    """Miami's current register on the date: [(roster entry, availability, role)]."""
    from .miami_cards import injured_on, role_in
    from .rotation_reviews import rotation_in_force
    season = season or _season(root)
    roster = _read(Path(root) / team_dir(season) / "Team/Roster/roster.json")
    try:
        rotation, _depth = rotation_in_force(on, root, season, require_review=False)
    except (OSError, ValueError, KeyError):
        rotation = {}
    out = []
    for p in roster["players"]:
        if any(w in (p.get("status") or "") for w in GONE):
            continue
        hurt = injured_on(root, p["name"], on)
        if hurt:
            kind = "injured" if hurt["reason"].startswith("injury") else "inactive reserve"
            avail = f"Injured list since {hurt['placed']}, {kind}"
        elif p.get("status") == "free_agent_rights_held":
            avail = "Unsigned; Miami holds his free-agent rights"
        else:
            avail = "Available"
        role = role_in(rotation, p["name"]) if rotation and p.get("status") != "free_agent_rights_held" else "N/A"
        out.append((p, avail, role))
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


def blocks(root, on):
    from .seasons import dates, start_year
    root = Path(root)
    season = _season(root)
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
    signed = [r for r in reg if r[0].get("status") != "free_agent_rights_held"]
    listed = [r for r in signed if r[1].startswith("Injured list")]
    standings_link = lambda frm: Path("../" * len(frm.parent.parts)).joinpath(STANDINGS).as_posix()
    team_readme = TEAM / "README.md"
    out = {}
    out[team_readme] = (f"**Status on {on}** (generated from dated records): Miami {record} "
                        f"([standings]({standings_link(team_readme)})). {len(signed)} players under contract, "
                        f"{len(listed)} on the injured list. Head coach {_read(root / TEAM / 'team_config.json').get('head_coach', 'N/A')}; the staff rotation in force and "
                        f"the register are in [Team](Team/README.md).")
    out[TEAM / "Team/README.md"] = (
        f"**Status on {on}:** {len(signed)} under contract ({len(signed) - len(listed)} active, {len(listed)} on the "
        f"injured list), Miami {record}. The [register](Roster/README.md) labels every player's control and "
        f"availability; expired, released and voided contracts stay on it as history.")
    rows = [[f"[{p['name']}]({p['player_card']})", "/".join(p.get("positions") or []), p["status"].replace("_", " "), a, role]
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


def refresh(root=ROOT, write=True, on=None):
    """Rewrite every generated block on the clock. Returns the changed paths."""
    root = Path(root)
    if on is None:
        from .write_back import clock
        on = clock(root)
    changed = []
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
