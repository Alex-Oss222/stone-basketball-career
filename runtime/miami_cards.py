"""Keep Miami's personnel cards current with the season (Player_Cards/*.md).

The cards were written at the June 26, 2003 import, at each rollover and on each arrival. This refresh rewrites only the
dated, record-owned parts of each card, from the owning records, for every season on file:

- **Role** and "Not yet established" (the live season's register players only): the latest dated rotation (camp
  `Depth_Chart/rotation.json`, then each `Depth_Chart/Reviews/<date>/rotation.json`) and the injured list
  (`Transactions/injured_list.json`), with one "Changes and coaching notes" row per rotation review that set his role.
  A player whose draft rights are unsigned is not on the roster and has no role: his earlier "Staff rotation of ..."
  rows, which named him a reserve, are rewritten to "not on the roster" (the one coaching-note rewrite).
- the header: the "Statistics through" date (the live season's register players), a position under a dated register
  correction (`miami_register.positions_on`), the age at the opening assessment from the register's birth date, and
  the Contract/control line when the register's control text has changed (`signing.card_control_line`);
- the yearly statistics block, generated whole: for a card with a Basketball-Reference id the 2002-03 row from the
  league's statistics file (`prior_rows`; a card line the file has no record of is dropped), other earlier rows kept as
  imported; then every simulated season to the card's: his Miami row from closed Miami results
  (`write_back.miami_lines`) and, for an earlier season he did not spend whole with Miami, his line with every club
  from the league's closed season totals (`Stats_and_Awards/League/<season>/season_totals.json`); one playoff row per
  season and club from closed playoff results (`playoff_stats.player_lines`, the playoff pages' aggregation); a
  coverage line naming every row; full club names in the Team(s) column and one percentage format (45.2%);
- **Awards and honors**: honors earned in the simulated league through the card date: Wade's from `awards.json`, every
  other player's from the closed award decisions, All-Star selections and FIBA medal registers (the league cards'
  honors at rank 1, `league_cards.CardContext`).

The card date is the career date for the live season's register players. A player no longer on the register, and every
card of a closed season, keeps the date the card states: only its header facts, statistics and honors are regenerated
through that date. A card never refreshed since its import (a date written as "June 26, 2003") stands as written.
Grades, scouting text and sources are never touched, nor are coaching notes apart from a rights holder's rotation rows. `refresh` also keeps each register's contract term
clauses equal to its contract sheet (`refresh_control_texts`) and writes each later season's card index
(`Player_Cards/README.md`; the 2003-04 one is the import's).
"""
from datetime import date
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIRST_SIMULATED = "2003-04"
MIAMI = "Miami Heat"


def _season(root=None):
    from .seasons import active
    return active(root or ROOT)


def team_dir(season):
    return Path(f"career/Dwyane_Wade/{season}/00_Team/Team")
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")
COLUMNS = ["Season", "Team(s)", "G", "GS", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "FG%", "3P%", "FT%"]
START, END = "<!-- yearly-statistics:start -->", "<!-- yearly-statistics:end -->"
SIMULATED_SOURCE = ("Simulated seasons from closed results: Miami's games (Miami Heat rows), and an earlier season's line with "
                    "every club from the league's closed season totals (`Stats_and_Awards/League/<season>/season_totals.json`).")
PRIOR_SEASON, PRIOR_FILE = "2002-03", "nba_2002_03_player_stats.json"
PRIOR_SOURCE = f"2002-03 from the [league statistics file](../../../../../../library/2003/league/{PRIOR_FILE})."
NO_PRIOR_SOURCE = f"2002-03: no record in the [league statistics file](../../../../../../library/2003/league/{PRIOR_FILE})."
# The June 2003 veteran import's label clause; every Team(s) cell now carries club names.
CODES_CLAUSE = ". Team codes are Basketball-Reference codes"
RIGHTS_ROLE = "not on the roster (unsigned draft rights); no rotation role"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rotations(root, season=None):
    """[(date, rotation dict, relative source)] oldest first: the camp rotation, then each review's."""
    from .seasons import dates
    root = Path(root)
    season = season or _season(root)
    TEAM = team_dir(season)
    out = []
    camp = root / TEAM / "Depth_Chart/rotation.json"
    if camp.is_file():
        data = _read(camp)
        out.append((data.get("as_of", dates(season, root)["roster_cut"]), data, "../Depth_Chart/rotation.json"))
    for path in sorted((root / TEAM / "Depth_Chart/Reviews").glob("*/rotation.json")):
        data = _read(path)
        out.append((data.get("as_of", path.parent.name), data, f"../Depth_Chart/Reviews/{path.parent.name}/rotation.json"))
    return sorted(out, key=lambda r: r[0])


def role_in(rotation, name):
    starters = {v: k for k, v in (rotation.get("starters") or {}).items()}
    if not starters and rotation.get("players"):
        # A camp rotation lists its starting five first, one per position (rotation.json).
        first = rotation["players"][:5]
        if len({p.get("position") for p in first}) == 5:
            starters = {p["player_id"]: p["position"] for p in first}
    row = next((p for p in rotation.get("players", []) if p["player_id"] == name), None)
    if name in starters:
        return f"starter at {starters[name]}, staff plan {row['minutes']:.0f} minutes" if row else f"starter at {starters[name]}"
    if row and row.get("minutes"):
        return f"rotation at {row.get('position', 'N/A')}, staff plan {row['minutes']:.0f} minutes"
    return "reserve outside the planned rotation"


def injured_on(root, name, on, season=None):
    season = season or _season(root)
    ledger = Path(root) / f"career/Dwyane_Wade/{season}/00_Team/Transactions/injured_list.json"
    if not ledger.is_file():
        return None
    for e in _read(ledger)["entries"]:
        if e["player"] == name and e["placed"] <= on and (e["activated"] is None or e["activated"] > on):
            return e
    return None


def _pct(made, att):
    return f"{100 * made / att:.1f}%" if att else "N/A"


def season_row(records, season):
    played = [r for r in records if r.get("line") and r["line"].get("appeared")]
    g = len(played)
    if not g:
        return None
    t = lambda k: sum(r["line"].get(k) or 0 for r in played)
    gs = sum(1 for r in played if r["line"].get("started"))
    per = lambda k: f"{t(k) / g:.1f}"
    return [season, MIAMI, str(g), str(gs), f"{t('seconds') / 60 / g:.1f}", per("pts"), per("reb"), per("ast"), per("stl"),
            per("blk"), per("tov"), _pct(t("fgm"), t("fga")), _pct(t("tpm"), t("tpa")), _pct(t("ftm"), t("fta"))]


def club_names(codes):
    """The Team(s) cell for a list of clubs: full names (a library code such as 'SAC' through `schedule.ALIASES`),
    joined as the league's season totals join them."""
    from .schedule import ALIASES
    return ", ".join(ALIASES.get(c, c) for c in codes or []) or "N/A"


def totals_row(season, label, t):
    """A row from a season-totals record (the league's closed season totals, or the 2002-03 statistics file)."""
    g = t.get("games") or 0
    per = lambda v: "N/A" if not g else f"{(v or 0) / g:.1f}"
    three_m = t.get("three_point_field_goals_made", t.get("three_pointers_made"))
    three_a = t.get("three_point_field_goals_attempted", t.get("three_pointers_attempted"))
    return [season, label, str(g), str(t["games_started"]) if t.get("games_started") is not None else "N/A",
            per(t.get("minutes")), per(t.get("points")), per((t.get("offensive_rebounds") or 0) + (t.get("defensive_rebounds") or 0)),
            per(t.get("assists")), per(t.get("steals")), per(t.get("blocks")), per(t.get("turnovers")),
            _pct(t.get("field_goals_made") or 0, t.get("field_goals_attempted")), _pct(three_m or 0, three_a),
            _pct(t.get("free_throws_made") or 0, t.get("free_throws_attempted"))]


def percent_cell(cell):
    """One percentage format in the FG%, 3P% and FT% columns: an imported decimal (0.461, .461, 1.000) as 46.1%;
    anything else unchanged."""
    if re.fullmatch(r"[01]?\.\d+", cell or "") and float(cell) <= 1:
        return f"{100 * float(cell):.1f}%"
    return cell


def _iso(text):
    """An ISO date from a card's date cell ('2006-06-20' or 'October 1, 2004'), else None."""
    text = (text or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    m = re.fullmatch(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", text)
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
    if m and m.group(1) in months:
        return f"{m.group(3)}-{months.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    return None


def _key(name):
    from .write_back import _key as key
    return key(name)


def _table(rows):
    return "\n".join(["| " + " | ".join(COLUMNS) + " |", "| " + " | ".join(["---", "---"] + ["---:"] * 12) + " |"]
                     + ["| " + " | ".join(r) + " |" for r in rows])


class Sources:
    """Closed results and records the cards read, loaded once per run (each season's in full, cut by card date)."""

    def __init__(self, root):
        from .seasons import live_seasons
        self.root = Path(root)
        self.live = _season(root)
        self.seasons = [s for s in live_seasons(root) if FIRST_SIMULATED <= s <= self.live] or [self.live]
        self._lines, self._playoffs, self._totals, self._honors, self._prior = {}, {}, {}, None, None

    def miami(self, season):
        """{name key: [records]} of Miami's closed regular-season games of the season."""
        if season not in self._lines:
            from .write_back import miami_lines
            lines, _ = miami_lines(self.root, season, "9999-12-31")
            out = {}
            for name, records in lines.items():
                out.setdefault(_key(name), []).extend(records)
            self._lines[season] = out
        return self._lines[season]

    def playoffs(self, season):
        """{name key: {club: [records]}} of the season's closed playoff games, every club's."""
        if season not in self._playoffs:
            # A season without playoff results reads empty; a broken record raises (never an empty card section).
            from .playoff_stats import closed_playoff_results, player_lines
            out = {}
            for (name, club), records in player_lines(closed_playoff_results(self.root, season, "9999-12-31"),
                                                      self.root, season).items():
                out.setdefault(_key(name), {}).setdefault(club, []).extend(records)
            self._playoffs[season] = out
        return self._playoffs[season]

    def totals(self, season):
        """{bbr_id: record} of a closed season's simulated totals, else {}."""
        if season not in self._totals:
            from .season_evidence import totals_path
            path = self.root / totals_path(season)
            self._totals[season] = {r["bbr_id"]: r for r in _read(path)["records"]} if path.is_file() else {}
        return self._totals[season]

    def prior(self, bbr):
        """His 2002-03 record from the league's statistics file, or None."""
        if self._prior is None:
            path = self.root / "library/2003/league/nba_2002_03_player_stats.json"
            self._prior = {r["bbr_id"]: r for r in _read(path)["records"]} if path.is_file() else {}
        return self._prior.get(bbr)

    def honors(self, name, through):
        """[(season, label, announced, source path from the repository root)] earned through `through`, by date."""
        if name == "Dwyane Wade":
            path = self.root / "career/Dwyane_Wade/awards.json"
            awards = _read(path)["awards"] if path.is_file() else []
            out = [(a["season"], f"{a['name']} ({a['period_start']} to {a['period_end']})", a["awarded_on"],
                    "career/Dwyane_Wade/" + a["source"]) for a in awards
                   if a.get("status") == "earned" and a["awarded_on"] <= through]
            return sorted(out, key=lambda h: (h[2], h[1]))
        if self._honors is None:
            from .league_cards import CardContext
            self._honors = CardContext(self.root).honors      # a broken award record raises: no card loses its honors
        from .seasons import season_of_date
        out = []
        for h in self._honors.get(_key(name), []):
            if h.get("rank") != 1 or h.get("superseded") or h["announced_on"] > through:
                continue
            label = f"{h.get('conference', '')} {h['name']}".strip()
            if h.get("medal"):
                label += f" ({h['medal']['country']})"
            elif h.get("period_start") != h.get("period_end"):
                label += f" ({h['period_start']} to {h['period_end']})"
            out.append((season_of_date(h["announced_on"]), label, h["announced_on"],
                        h["filed_on"] + (f"#{h['anchor']}" if h.get("anchor") else "")))
        return sorted(out, key=lambda h: (h[2], h[1]))


def _rows_in(block):
    """The rows of the first statistics table (Season, Team(s), ...) in `block`; the veteran details table is not one."""
    m = re.search(r"^\| Season \| Team\(s\) \|[^\n]*\n\| ---[^\n]*\n((?:\|[^\n]*\n?)*)", block, flags=re.M)
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in (m.group(1).splitlines() if m else [])
            if re.match(r"^\| \d{4}-\d{2} \|", line)]


def _source_line(old, simulated, prior_note):
    """The regular-season Source line: the imported part of the card's own line (one with a library link), the 2002-03
    note (`PRIOR_SOURCE` when the row comes from the league statistics file and the imported part does not already link
    it, `NO_PRIOR_SOURCE` when the file has no record of him), then the simulated seasons."""
    text = old[len("Source: "):] if old.startswith("Source: ") else ""
    text = text.split(PRIOR_SOURCE)[-1].split(NO_PRIOR_SOURCE)[-1].split("Simulated seasons from closed results")[0]
    pre = text.split(";")[0].strip().rstrip(".").replace(CODES_CLAUSE, "")
    keep = "](" in pre and not (prior_note == NO_PRIOR_SOURCE and PRIOR_FILE in pre)   # no credit for a dropped row
    note = prior_note if prior_note and not (prior_note == PRIOR_SOURCE and keep and PRIOR_FILE in pre) else None
    parts = ([pre + "."] if keep else []) + ([note] if note else []) + ([SIMULATED_SOURCE] if simulated else [])
    return "Source: " + " ".join(parts) if parts else old


def prior_rows(src, imported, bbr, source):
    """(rows, note) of the seasons before 2003-04 for a card with a Basketball-Reference id. The 2002-03 row is the
    league statistics file's line (`totals_row`, club names): cards written before the dated label fix carried a later
    season's line under the 2002-03 label (Mihm, Joe Smith, P.J. Brown, Marshall, Harpring, Raja Bell, Lamond Murray;
    the review of the audit of 2006-06-20). A card line the file has no record of is dropped, unless it is an empty
    (G 0) record; earlier imported seasons stand."""
    rows = [r for r in imported if r[0] < PRIOR_SEASON]
    line = src.prior(bbr)
    if line:
        return rows + [totals_row(PRIOR_SEASON, club_names(line.get("team_codes")), line["totals"])], PRIOR_SOURCE
    kept = [r for r in imported if r[0] == PRIOR_SEASON and r[2] == "0"]
    dropped = len(kept) < len([r for r in imported if r[0] == PRIOR_SEASON])
    return rows + kept, (NO_PRIOR_SOURCE if dropped or NO_PRIOR_SOURCE in source else None)


def yearly_block(src, player, text, season, through, wade=False):
    """The card's yearly statistics block (between the markers), generated from closed results through `through`."""
    from .career_stats import aggregate
    from .seasons import dates, read as season_file
    block = text[text.index(START) + len(START):text.index(END)]
    regular = block.split("## Playoff statistics by year")[0]
    details = re.search(r"<!-- veteran-details:start -->.*?<!-- veteran-details:end -->", regular, flags=re.S)
    source = next((line for line in regular.splitlines() if line.startswith("Source: ")), "")
    key, bbr = _key(player["name"]), player.get("bbr_id") or ("wadedw01" if wade else None)
    rows = [r[:11] + [percent_cell(c) for c in r[11:]] for r in _rows_in(regular) if r[0] < FIRST_SIMULATED]
    prior_note = None
    if not wade and bbr:
        rows, prior_note = prior_rows(src, rows, bbr, source)
    if wade:
        cover = ["No NBA season before 2003-04 (the alternate-history Wade; the historical Wade's statistics are never imported)"]
    elif rows and rows[0][2] not in ("0", "N/A"):
        cover = [f"{rows[0][0]} regular season from the league record; earlier seasons are not imported"]
    elif rows:
        cover = [f"{rows[0][0]}: no appearance in the league record; earlier seasons are not imported"]
    elif prior_note == NO_PRIOR_SOURCE:
        cover = ["2002-03: no appearance in the league statistics file; earlier seasons are not imported"]
    else:
        cover = ["No 2002-03 NBA record on this card"]
    simulated = False
    for s in [x for x in src.seasons if x <= season]:
        upto = through if s == season else "9999-12-31"
        mia = season_row([r for r in src.miami(s).get(key, []) if r["date"] <= upto], s)
        # his season with every club: an earlier season's, or the card's own once its regular season is over
        ended = s < season or through > dates(s, src.root)["regular_season_end"]
        league = src.totals(s).get(bbr) if ended and bbr else None
        clubs = club_names(league.get("team_codes")) if league else ""
        whole = bool(league) and (not mia or (league["totals"].get("games") or 0) > int(mia[2]))
        simulated = simulated or bool(mia) or whole
        if mia:
            rows.append(mia)
        if whole:
            rows.append(totals_row(s, clubs + (" (season, every club)" if mia else ""), league["totals"]))
        if s == season:
            if through < dates(s, src.root)["opening_night"]:
                cover.append(f"{s} had not started on {through}")
            elif mia:
                cover.append(f"{s}: {mia[2]} closed Miami game(s) through {through}"
                             + (f", and his season with every club ({clubs}) from the league record" if whole else ""))
            elif whole:
                cover.append(f"{s}: no Miami appearance through {through}; {clubs} from the league record")
            else:
                cover.append(f"{s}: no Miami appearance through {through}")
            if not mia and not whole:
                rows.append([s, MIAMI, "0"] + ["N/A"] * 11)        # G 0: an empty appearance record from Miami's results
                simulated = True
        elif mia and whole:
            cover.append(f"{s}: {mia[2]} Miami game(s), and his season with every club ({clubs}) from the league record")
        elif mia:
            cover.append(f"{s}: {mia[2]} Miami game(s) from closed results")
        elif whole:
            cover.append(f"{s}: {clubs} from the league record")
    out = ["", "## Regular-season statistics by year", "",
           "G and GS are counts. MIN and all other counting statistics are per game. Percentages use total makes divided "
           "by total attempts.", "", f"**Coverage:** {'; '.join(cover)}.", "", _table(rows), ""]
    if details:
        out += [details.group(0), ""]
    new_source = _source_line(source, simulated, prior_note)
    if new_source:
        out += [new_source, ""]
    out += ["## Playoff statistics by year", ""]
    prow = []
    pct = lambda v: "N/A" if v is None else f"{v:.1%}"
    n = lambda v, k=1: "N/A" if v is None else f"{v:.{k}f}"
    for s in [x for x in src.seasons if x <= season]:
        upto = through if s == season else "9999-12-31"
        for club, records in sorted(src.playoffs(s).get(key, {}).items(), key=lambda kv: (kv[0] != MIAMI, kv[0])):
            a = aggregate([r for r in records if r["date"] <= upto])
            if not a["gp"]:
                continue
            pg, rt = a["pg"], a["rates"]
            prow.append([s, club, str(a["gp"]), n(a["gs"], 0), n(pg["minutes"]), n(pg["pts"]), n(pg["reb"]), n(pg["ast"]),
                         n(pg["stl"]), n(pg["blk"]), n(pg["tov"]), pct(rt["fg_pct"]), pct(rt["three_pct"]), pct(rt["ft_pct"])])
    try:
        openers = min(season_file(season, "playoff_rules", src.root)["calendar"]["first_round"]["openers"])
    except (OSError, KeyError, ValueError):
        openers = None
    waiting = f" The {season} playoffs had not started on {through}." if openers and through < openers else ""
    if prow:
        out += [f"**Coverage:** playoff games from closed results through {through}, every club's (`runtime/playoff_stats.py`, "
                f"the playoff pages' aggregation); playoff history before 2003-04 is not imported.{waiting}", "",
                _table(prow), ""]
    else:
        out += [f"**Coverage:** no appearance in a closed simulated playoff game through {through}; playoff history before "
                f"2003-04 is not imported.{waiting}", ""]
    return "\n".join(out) + "\n"


def awards_section(src, player, through, card_dir):
    """The card's last section: honors earned in the simulated league through `through`."""
    honors = src.honors(player["name"], through)
    basis = ("`awards.json`" if player["name"] == "Dwyane Wade" else
             "the league's closed award decisions, All-Star selections and FIBA medal registers")
    head = ["## Awards and honors", ""]
    if not honors:
        return "\n".join(head + [f"No honor earned in the simulated league through {through} (from {basis}). Awards "
                                 "before 2003-04 are not imported.", ""])
    rows = ["| Season / year | Award or honor | Announced | Source |", "| --- | --- | --- | --- |"]
    for season, label, announced, path in honors:
        target, _, anchor = path.partition("#")
        link = Path(os.path.relpath(src.root / target, card_dir)).as_posix() + (f"#{anchor}" if anchor else "")
        rows.append(f"| {season} | {label} | {announced} | [Record]({link}) |")
    return "\n".join(head + [f"{len(honors)} honor(s) earned in the simulated league through {through}, from {basis}. "
                             "Awards before 2003-04 are not imported.", ""] + rows + [""])


def _role_lines(new, root, season, now, p, rots):
    """The live season's Role, "Not yet established" and rotation notes for a register player."""
    name = p["name"]
    rights = p.get("status") == "unsigned_draft_rights"
    latest = [r for r in rots if r[0] <= now]
    if not latest:
        return new
    day, rot, src = latest[-1]
    if rights:
        new = re.sub(r"^\*\*Role:\*\*.*$", lambda _: f"**Role:** {RIGHTS_ROLE[0].upper() + RIGHTS_ROLE[1:]} (register, {now}).",
                     new, count=1, flags=re.M)
        new = re.sub(r"^- \*\*Not yet established:\*\*.*$",
                     "- **Not yet established:** a contract; the staff assigns no role while his draft rights are unsigned.",
                     new, count=1, flags=re.M)
        # The staff's rotations never planned him: their earlier notes named him a reserve.
        new = re.sub(r"^(\| (\d{4}-\d{2}-\d{2}) \| Staff rotation of \2: )[^|]*\.( \| \[Rotation\]\([^)]*\) \|)$",
                     lambda m: m.group(1) + RIGHTS_ROLE + "." + m.group(3), new, flags=re.M)
    else:
        role = role_in(rot, name)
        hurt = injured_on(root, name, now, season)
        extra = (f" On the injured list since {hurt['placed']} ({hurt['reason']})." if hurt else "")
        new = re.sub(r"^\*\*Role:\*\*.*$",
                     lambda _: f"**Role:** {role[0].upper() + role[1:]} (staff rotation dated {day}, [record]({src})).{extra}",
                     new, count=1, flags=re.M)
        new = re.sub(r"^- \*\*Not yet established:\*\*.*$",
                     f"- **Not yet established:** closing role and Miami staff grades beyond the camp review. "
                     f"Rotation role and minute target: staff rotation dated {day}.", new, count=1, flags=re.M)
    # One dated note per staff rotation that set his role (idempotent: a date already noted is skipped).
    for rday, rrot, rsrc in latest:
        marker = f"Staff rotation of {rday}"
        if marker in new or "## Changes and coaching notes" not in new:
            continue
        note = f"| {rday} | {marker}: {RIGHTS_ROLE if rights else role_in(rrot, name)}. | [Rotation]({rsrc}) |"
        new = re.sub(r"(## Changes and coaching notes\n\n\| Date \|[^\n]*\n\| ---[^\n]*\n(?:\|[^\n]*\n)*)",
                     lambda m: m.group(1) + note + "\n", new, count=1)
    return new


def _header(new, p, through, roster_as_of):
    """Header facts from the register: a dated position correction, the age at assessment, the control line."""
    from .miami_register import positions_on
    from .signing import card_control_line
    from .valuation import age_on
    if p.get("positions_corrected_from"):
        pos = " / ".join(positions_on(p, through))
        new = re.sub(r"(\*\*Position:\*\* )[^\n]*?( {2})?$", lambda m: m.group(1) + pos + (m.group(2) or ""), new, count=1, flags=re.M)
    opened = _iso((re.search(r"\*\*Opening assessment:\*\* ([^·\n]*)", new) or [None, ""])[1])
    if p.get("date_of_birth") and opened and "**Age at assessment:** N/A" in new:
        new = new.replace("**Age at assessment:** N/A", f"**Age at assessment:** {age_on(p['date_of_birth'], opened)}", 1)
    m = re.search(r"^\*\*Contract/control:\*\* (.*?) \(register, [^)]*\) \[Finance record\]", new, flags=re.M)
    if p.get("control") and m and m.group(1) != p["control"]:
        new = re.sub(r"^\*\*Contract/control:\*\*[^\n]*$", lambda _: card_control_line(p["control"], roster_as_of), new,
                     count=1, flags=re.M)
    return new


def control_texts(root, season):
    """(register, names changed): the season's register with each contract term clause ('N season(s) from S, $T
    scheduled ($X in S)', `rollover.contract_head`) recomputed from the season's contract sheet. A schedule repaired after
    the rollover wrote the text left it short (Brian Grant's and Caron Butler's 2004-05 rows, found by the audit of
    2006-06-20). Text only: no decision reads it."""
    from .rollover import CONTRACT_HEAD, contract_head
    base = Path(root) / f"career/Dwyane_Wade/{season}/00_Team"
    path, sheet_path = base / "Team/Roster/roster.json", base / "Finances/contract_schedules.json"
    if not path.is_file():
        return None, []
    register = _read(path)
    if not sheet_path.is_file():
        return register, []
    sheet = _read(sheet_path)["players"]
    by_id = {c["bbr_id"]: c for c in sheet if c.get("bbr_id")}
    by_name = {c["player"]: c for c in sheet}
    changed = []
    for p in register["players"]:
        m = CONTRACT_HEAD.search(p.get("control") or "")
        entry = (by_id.get(p.get("bbr_id")) if p.get("bbr_id") else None) or by_name.get(p["name"])
        if not m or not entry:
            continue
        head = contract_head(entry.get("schedule") or {}, m.group(2))
        if head != m.group(0):
            p["control"] = p["control"].replace(m.group(0), head, 1)
            changed.append(p["name"])
    return register, changed


def refresh_control_texts(root=ROOT, season=None, write=True):
    """`control_texts` written to the register. Returns the names changed."""
    season = season or _season(root)
    register, changed = control_texts(root, season)
    if changed and write:
        path = Path(root) / team_dir(season) / "Roster/roster.json"
        path.write_text(json.dumps(register, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def card_index(root, season, roster, on):
    """`Player_Cards/README.md` of a season: every card on its register with its position on `on` and control status
    (generated)."""
    from .miami_register import positions_on
    rows = []
    for p in roster["players"]:
        card = Path(p.get("player_card", "")).name
        if (Path(root) / team_dir(season) / "Player_Cards" / card).is_file():
            rows.append(f"| [{p['name']}]({card}) | {'/'.join(positions_on(p, on))} | {(p.get('status') or '').replace('_', ' ')} |")
    return "\n".join([f"# Miami Heat player cards | {season}", "",
                      "<!-- contract-navigation:start -->",
                      "[Current contracts and contract history for every tracked player](../../../../Contracts/index.html)",
                      "<!-- contract-navigation:end -->", "",
                      f"Every player on the {season} team-control [register](../Roster/roster.json) has a personnel card in the "
                      "[template](TEMPLATE.md)'s section order: scouting report, player grades, changes and coaching notes, "
                      "sources and uncertainty, regular-season statistics, playoff statistics, then awards. A player who left "
                      "keeps his card as it stood on his last date; statistics and honors come from closed results and award "
                      "records only (`runtime/miami_cards.py`). Pos and control are the register's.", "",
                      "| Player | Pos | Control |", "| --- | --- | --- |", *rows, ""])


def refresh(root=ROOT, write=True):
    """Refresh every season's register cards, control texts and card index. Returns the changed paths."""
    root = Path(root)
    from .write_back import clock
    now = clock(root)
    src = Sources(root)
    changed = []
    for season in src.seasons:
        TEAM = team_dir(season)
        roster, fixed = control_texts(root, season)
        if roster is None:
            continue
        if fixed:
            changed.append(root / TEAM / "Roster/roster.json")
            if write:
                refresh_control_texts(root, season)
        rots = rotations(root, season) if season == src.live else []
        for p in roster["players"]:
            card = root / TEAM / "Player_Cards" / Path(p.get("player_card", "")).name
            if not card.is_file() or card.name in ("TEMPLATE.md", "README.md"):
                continue
            text = card.read_text(encoding="utf-8")
            if START not in text or END not in text or "## Awards and honors" not in text:
                continue
            new = text
            if season == src.live and not any(w in (p.get("status") or "") for w in GONE):
                through = now
                new = _role_lines(new, root, season, now, p, rots)
                new = re.sub(r"\*\*Statistics through:\*\* [^\n·]*", f"**Statistics through:** {now} ", new, count=1)
            else:
                stated = re.search(r"\*\*Statistics through:\*\* ([^\n·]*)", text)
                through = stated.group(1).strip() if stated else ""
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", through):
                    continue                           # never refreshed since its import: it stands as written
            new = _header(new, p, through, roster.get("as_of"))
            new = (new[:new.index(START) + len(START)] + "\n" + yearly_block(src, p, new, season, through, p["name"] == "Dwyane Wade")
                   + new[new.index(END):])
            new = new[:new.index("## Awards and honors")] + awards_section(src, p, through, card.parent)
            if new != text:
                changed.append(card)
                if write:
                    card.write_text(new, encoding="utf-8")
        index = root / TEAM / "Player_Cards/README.md"
        if season != FIRST_SIMULATED:
            text = card_index(root, season, roster, now)
            if not index.is_file() or index.read_text(encoding="utf-8") != text:
                changed.append(index)
                if write:
                    index.write_text(text, encoding="utf-8")
    return changed


def sync_register_roles(root=ROOT, write=True, season=None):
    """Miami's register `working_role` follows the staff's latest dated rotation and the injured list on the career date
    (the user's request, October 2026: no stale arrival or camp labels once the staff has set roles). Returns the names
    whose label changed."""
    from .seasons import state
    season = season or _season(root)
    path = Path(root) / team_dir(season) / "Roster/roster.json"
    if not path.is_file():
        return []
    register = _read(path)
    on = state(season, root)["current_date"]
    dated = [r for r in rotations(root, season) if r[0] <= on]
    if not dated:
        return []
    as_of, rotation, _ = dated[-1]
    changed = []
    for p in register["players"]:
        status = p.get("status") or ""
        if any(w in status for w in GONE):
            label = f"Left Miami ({status.replace('_', ' ')})"
        elif status == "unsigned_draft_rights":
            label = "Unsigned draft rights (not on the roster)"
        elif injured_on(root, p["name"], on, season):
            label = f"Injured list ({role_in(rotation, p['name'])} when healthy; rotation {as_of})"
        else:
            role = role_in(rotation, p["name"])
            label = role[0].upper() + role[1:] + f" (rotation {as_of})"
        if p.get("working_role") != label:
            p["working_role"] = label
            changed.append(p["name"])
    if changed and write:
        path.write_text(json.dumps(register, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed
