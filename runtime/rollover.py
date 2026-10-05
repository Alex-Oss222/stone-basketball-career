"""The season rollover: the closed season and the summer market become the next season's records (roadmap 18).

    python scripts/rollover.py --write

Runs once, on the day after the summer market closes (`free_agency_2004.PLACEMENT`), when the previous season is
closed (`season_close.json`) and the market's record exists. It never decides anything: every contract, signing and
departure was decided by the market's own rules and draws; this step only carries them into the new season's folder
in the shapes the in-season pipelines read.

1. League: the closed season's simulated totals (`season_evidence.write_totals`) and card lines; the new season's
   contract ledger (`league_contracts.write`) and opening rosters (`offseason.write`).
2. Miami (`<season>/00_Team`): the register, contracts, holdings, depth chart and cards of every player the market
   left with Miami; the club's unsigned draft picks as rights; the organization, team config and cap history carried
   over; departed players' holdings closed in the previous season's record on the day they left.
3. The season's folders: phase notes, a week note for every week of its calendar (`seasons.structure`), and the new
   `current_state.json`, which makes the season live (`seasons.active`). The previous season keeps its state.
4. In a fresh process (module constants follow the live season): Miami's finance summary and cap sheet, the
   statistics and award pages (`season_pages`), the views and reports.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
PLAYER = Path("career/Dwyane_Wade")
MIAMI = "Miami Heat"
WADE_ID = "dwyane_wade"
SIGN_KINDS = ("signing", "re_sign", "rookie_scale_signing", "camp_signing", "qualifying_offer_accepted", "offer_sheet_matched", "trade")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _long(day):
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class Rollover:
    def __init__(self, root=ROOT):
        from .free_agency_2004 import PLACEMENT, RECORD
        from .seasons import active, next_season
        self.root = Path(root)
        self.old = active(self.root)
        self.new = next_season(self.old)
        self.day = (date.fromisoformat(PLACEMENT).toordinal() + 1)
        self.day = date.fromordinal(self.day).isoformat()
        self.old_dir = self.root / PLAYER / self.old
        self.new_dir = self.root / PLAYER / self.new
        self.old_team, self.team = self.old_dir / "00_Team", self.new_dir / "00_Team"
        self.record_path = self.root / RECORD
        self.record = _read(self.record_path) if self.record_path.is_file() else None

    # -- gates -----------------------------------------------------------------------------------
    def blockers(self, clock):
        out = []
        if (self.new_dir / "current_state.json").is_file():
            out.append(f"{self.new} is already live")
        if not (self.old_dir / "season_close.json").is_file():
            out.append(f"{self.old} is not closed (season_close.json)")
        if self.record is None:
            out.append(f"the summer market has not closed ({self.record_path.relative_to(self.root)})")
        if clock < self.day:
            out.append(f"the rollover is dated {self.day}; the clock is {clock}")
        return out

    # -- identities ------------------------------------------------------------------------------
    def identities(self):
        """{bbr or id: {name, birth_date, position, ...}} for Miami's new season: the old register first."""
        from .free_agency_2004 import identity
        out = {b: dict(e) for b, e in identity(self.root).items()}
        draft = self.old_dir / "09_Draft/draft_2004.json"
        if draft.is_file():
            for p in _read(draft)["picks"]:
                if p.get("bbr_id"):
                    out.setdefault(p["bbr_id"], {"name": p["player"], "position": p.get("position"), "birth_date": p.get("birth_date")})
                    out[p["bbr_id"]].update(draft_pick=p["pick"], draft_round=p["round"], college=p.get("college"))
        for p in _read(self.old_team / "Team/Roster/roster.json")["players"]:
            key = p.get("bbr_id") or p["id"]
            e = out.setdefault(key, {})
            e.update(name=p["name"], register=p)
        return out

    def events(self):
        """{bbr: the event that put him on Miami} for the summer's Miami signings."""
        out = {}
        for e in self.record["events"]:
            if e.get("club") == MIAMI and e["kind"] in SIGN_KINDS:
                out[e["bbr_id"]] = e
        return out

    # -- Miami's records -------------------------------------------------------------------------
    def miami(self):
        """[(key, row, identity, event)] for every contract the market left with Miami."""
        ids, events = self.identities(), self.events()
        return [(r["bbr_id"], r, ids.get(r["bbr_id"], {"name": r["player"]}), events.get(r["bbr_id"])) for r in self.record["clubs"][MIAMI]]

    def unsigned_picks(self):
        """Miami's drafted players without a contract: rights held (second-round picks negotiate; a pick abroad stays)."""
        draft = self.old_dir / "09_Draft/draft_2004.json"
        if not draft.is_file():
            return []
        signed = {r["bbr_id"] for r in self.record["clubs"][MIAMI]}
        elsewhere = {r["bbr_id"] for c, rows in self.record["clubs"].items() if c != MIAMI for r in rows}
        return [p for p in _read(draft)["picks"] if p["club"] == MIAMI and p.get("bbr_id") not in signed | elsewhere]

    def contract_entries(self, ledger):
        old = {p.get("bbr_id") or (WADE_ID if p["player"] == "Dwyane Wade" else None): p
               for p in _read(self.old_team / "Finances/contract_schedules.json")["players"]}
        from .seasons import dates
        guarantee = dates(self.new, self.root)["guarantee"]
        out = []
        for key, row, ident, event in self.miami():
            name = ident.get("name") or row["player"]
            lg = ledger.get(key) or {}
            if row["route"] in ("existing", "option") and key in old:
                entry = deepcopy(old[key])
                entry["player"] = name
                entry["bbr_id"] = None if key == WADE_ID else key
                if row["route"] == "option":
                    kind = (event or {}).get("kind") or "team_option"
                    entry["status"] = f"{kind}_exercised" if kind in ("team_option", "player_option") else "under_contract"
                elif entry.get("status") not in ("under_rookie_contract",):
                    entry["status"] = "under_contract"
                entry.pop("guarantee_date", None) if entry.get("status") == "under_contract" else None
                if key == WADE_ID:
                    entry.pop("bbr_id", None)
                out.append(entry)
                continue
            sched = lg.get("schedule") or {self.new: row["salary"]}
            camp = (event or {}).get("kind") == "camp_signing"
            entry = {"player": name, "bbr_id": key,
                     "status": "under_rookie_contract" if row["route"] == "rookie_scale" else "camp_contract" if camp else "under_contract",
                     "schedule": dict(sched), "amount_kind": {s: "contract_salary" for s in sched},
                     "guaranteed": {s: (0 if camp and s == self.new else v) for s, v in sched.items()},
                     "signed_date": (event or {}).get("date") or self.day, "route": row["route"],
                     "original_term_seasons": len(sched),
                     "notes": (f"Signed {_long((event or {}).get('date') or self.day)} in the {self.new} summer market "
                               f"({(event or {}).get('kind', 'signing').replace('_', ' ')}, route {row['route']}); schedule from the league "
                               f"contract ledger (raises by route)."),
                     "sources": [self.record_path.relative_to(self.root).as_posix(), f"{self.new}/League/contracts.json"]}
            if camp:
                entry["guarantee_date"] = guarantee
            if lg.get("team_option"):
                entry["team_option_season"] = lg["team_option"]
            if (event or {}).get("from") and event["from"] != MIAMI:
                entry["previous_club"] = event["from"]
            out.append(entry)
        for p in self.unsigned_picks():
            out.append({"player": p["player"], "bbr_id": p.get("bbr_id"), "status": "unsigned_draft_rights", "schedule": {},
                        "amount_kind": {}, "draft_pick": p["pick"], "draft_round": p["round"],
                        "notes": f"No. {p['pick']} pick of the 2004 draft; Miami holds his rights, unsigned when the summer market closed.",
                        "sources": [f"{self.old}/09_Draft/draft_2004.json"]})
        return out

    def control_text(self, entry):
        s = entry.get("schedule") or {}
        if entry["status"] == "unsigned_draft_rights":
            return f"Unsigned draft rights: No. {entry.get('draft_pick')} pick of the 2004 draft."
        years = [k for k in sorted(s) if k >= self.new and s[k]]
        total = sum(s[k] for k in years)
        head = f"{len(years)} season(s) from {self.new}, ${total:,} scheduled (${s.get(self.new, 0):,} in {self.new})"
        if entry["status"] == "camp_contract":
            return f"Camp contract signed {_long(entry['signed_date'])}: {head}; non-guaranteed until {entry.get('guarantee_date')}."
        if entry.get("route") in (None, "existing") or "signed_date" not in entry or entry["signed_date"] < f"{self.new[:4]}-07-01":
            return f"Existing contract: {head}."
        return f"Signed {_long(entry['signed_date'])} ({entry.get('route')}): {head}."

    def register(self, entries, ids):
        old = {p.get("bbr_id") or p["id"]: p for p in _read(self.old_team / "Team/Roster/roster.json")["players"]}
        players = []
        for e in entries:
            key = e.get("bbr_id") or WADE_ID
            ident = ids.get(key, {})
            prev = old.get(key)
            if prev:
                p = deepcopy(prev)
            else:
                pos = ident.get("position") or "SF"
                p = {"id": slug(e["player"]), "name": e["player"], "positions": [x.strip() for x in str(pos).replace("-", "/").split("/") if x.strip()],
                     "date_of_birth": ident.get("birth_date"), "college": ident.get("college"), "working_role": "Unassigned arrival",
                     "player_card": f"../Player_Cards/{slug(e['player'])}.md", "bbr_id": key}
                p = {k: v for k, v in p.items() if v is not None}
            p["status"] = {"under_rookie_contract": "under_contract", "team_option_exercised": "team_option_exercised",
                           "player_option_exercised": "player_option_exercised"}.get(e["status"], e["status"])
            p["control"] = self.control_text(e)
            players.append(p)
        return {"schema_version": 1, "owner": "ai_gm", "as_of": self.day, "season": self.new, "team": MIAMI,
                "roster_kind": "team_control_register", "finalized_active_roster": False, "players": players,
                "sources": [self.record_path.relative_to(self.root).as_posix()]}

    def holdings(self, entries):
        """The new season's holdings, and the old record with every departed player's holding closed."""
        old = _read(self.old_team / "Team/Roster/holdings.json")
        keep = {e.get("bbr_id") for e in entries if e["status"] != "unsigned_draft_rights"}
        events = {e["bbr_id"]: e for e in self.record["events"] if e.get("bbr_id")}
        new_entries = []
        for h in old["entries"]:
            if h.get("until") is not None or h.get("void"):
                continue
            if h.get("bbr_id") in keep:
                new_entries.append(dict(h))
            else:
                left = events.get(h.get("bbr_id"))
                h["until"] = left["date"] if left and left.get("club") != MIAMI else f"{self.new[:4]}-07-01"
                h["basis"] = (h.get("basis", "") + f"; left Miami in the {self.new} summer market").lstrip("; ")
        held = {h.get("bbr_id") for h in new_entries}
        for e in entries:
            if e.get("bbr_id") in held or not e.get("bbr_id"):
                continue
            if e["status"] == "unsigned_draft_rights":
                # Miami holds his rights from the draft: he plays for no other club (world rule 2).
                new_entries.append({"player": e["player"], "bbr_id": e["bbr_id"], "from": "2004-06-24", "until": None,
                                    "basis": f"draft rights (No. {e.get('draft_pick')} pick), unsigned"})
                continue
            new_entries.append({"player": e["player"], "bbr_id": e["bbr_id"], "from": e.get("signed_date") or self.day,
                                "until": None, "basis": f"{e.get('route')} signing {e.get('signed_date')} ({self.new} summer market)"})
        new = dict(old, season=self.new, entries=new_entries)
        return new, old

    def depth_chart(self, register):
        """Last season's positional order for the players who stay; arrivals unassigned until camp decides."""
        reviews = sorted((self.old_team / "Team/Depth_Chart/Reviews").glob("*/depth_chart.json"))
        source = reviews[-1] if reviews else self.old_team / "Team/Depth_Chart/depth_chart.json"
        old = _read(source)
        names = {p["name"] for p in register["players"] if p["status"] != "unsigned_draft_rights"}
        positions = {pos: [n for n in order if n in names] for pos, order in old["positions"].items()}
        placed = {n for order in positions.values() for n in order}
        return {"schema_version": 1, "owner": "ai_gm", "as_of": self.day, "team": MIAMI, "status": "carried_over",
                "game_ready": False,
                "basis": f"{self.old} closing order ({source.relative_to(self.root).as_posix()}) for the players who stay; "
                         "training camp decides the new order.",
                "positions": positions,
                "unassigned_draft_rights": [{"name": p["name"], "positions": p["positions"], "status": "draft_rights_unsigned"}
                                            for p in register["players"] if p["status"] == "unsigned_draft_rights"],
                "unassigned_arrivals": [{"name": p["name"], "positions": p["positions"], "status": p["status"], "date": self.day}
                                        for p in register["players"] if p["name"] in names - placed],
                "unavailable": [], "departed": [], "corrections": []}

    def card(self, entry, ident, prior):
        """A new arrival's card in the template's section order; grades stay unassessed until evidence exists."""
        name = entry["player"]
        pos = " / ".join(ident.get("position", "N/A").replace("-", "/").split("/")) if ident.get("position") else "N/A"
        born = ident.get("birth_date")
        d = date.fromisoformat(self.day)
        age = (d.year - int(born[:4]) - ((d.month, d.day) < (int(born[5:7]), int(born[8:10])))) if born else "N/A"
        rows = ""
        if prior:
            t = prior["totals"]
            g = max(t.get("games") or 0, 1)

            def pct(m, a):
                return f"{t[m] / t[a]:.3f}" if t.get(a) else "N/A"
            rows = (f"| {self.old} | {', '.join(prior.get('team_codes') or []) or 'N/A'} | {t.get('games', 0)} | {t.get('games_started', 'N/A')} | "
                    f"{t['minutes'] / g:.1f} | {t['points'] / g:.1f} | {(t['offensive_rebounds'] + t['defensive_rebounds']) / g:.1f} | "
                    f"{t['assists'] / g:.1f} | {t['steals'] / g:.1f} | {t['blocks'] / g:.1f} | {t['turnovers'] / g:.1f} | "
                    f"{pct('field_goals_made', 'field_goals_attempted')} | {pct('three_point_field_goals_made', 'three_point_field_goals_attempted')} | "
                    f"{pct('free_throws_made', 'free_throws_attempted')} |\n")
        source = f"../../../../../../{self.record_path.relative_to(self.root).as_posix()}"
        return f"""# {name} | {self.new} Player Profile

**Team:** Miami Heat · **League:** NBA · **Position:** {pos}
**Age at assessment:** {age} · **Height:** N/A · **Weight:** N/A
**Opening assessment:** {_long(self.day)} · **Statistics through:** {_long(self.day)}

**Contract/control:** {self.control_text(entry)} (register, {self.day}) [Finance record](../../Finances/cap_sheet.md).

## Scouting report

**Role:** Arrival on {_long(self.day)}; Miami's coaching staff has not assigned a role. The depth chart lists him as an unassigned arrival.

**Offense:** Unassessed by Miami's staff; prior production is in the statistics below.

**Defense:** Unassessed.

## Player grades

Unassessed.

## Changes and coaching notes

| Date | Finding and effect on role or grade | Evidence |
| --- | --- | --- |
| {_long(self.day)} | Joined Miami for {self.new}. Card opened from the summer market record; no role assigned. | [Market record]({source}) |

## Sources and uncertainty

- **Assessment evidence:** [summer market record]({source}){', ' + self.old + ' simulated season totals' if prior else ''}.
- **Not yet established:** height, weight, role, staff grades.

<!-- yearly-statistics:start -->

## Regular-season statistics by year

G and GS are counts. MIN and all other counting statistics are per game. Percentages use total makes divided by total attempts.

**Coverage:** {self.old + ' from the simulated league record; ' if prior else ''}{self.new} not started.

| Season | Team(s) | G | GS | MIN | PTS | REB | AST | STL | BLK | TOV | FG% | 3P% | FT% |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{rows}| {self.new} | Miami Heat | 0 | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

Source: {self.old} from closed simulated results (`Stats_and_Awards/League/{self.old}/season_totals.json`); {self.new} from closed Miami game results.

## Playoff statistics by year

**Coverage:** No playoff appearances recorded for Miami.

<!-- yearly-statistics:end -->

## Awards and honors

| Season / year | Award or honor | Source |
| --- | --- | --- |
| — | No verified awards or honors recorded on this card. | — |
"""

    # -- folders ---------------------------------------------------------------------------------
    PHASES = {"01_Free_Agency": "Free Agency", "02_Summer_League": "Summer League", "03_Offseason": "Offseason",
              "04_Training_Camp": "Training Camp", "05_Preseason": "Preseason", "09_Draft": "Draft"}

    def phase_note(self, folder, title):
        summer = folder in ("01_Free_Agency", "02_Summer_League", "03_Offseason")
        status = "complete" if summer else "not_started"
        events = ""
        if folder == "01_Free_Agency":
            events = (f"- {self.day}: The {self.new[:4]} summer market closed on {_long(self.record['to'])}; its record is "
                      f"`../../{self.old}/10_Free_Agency/free_agency_2004.json`, carried into `../00_Team` by the rollover.\n")
        elif folder == "03_Offseason":
            events = f"- {self.day}: Wade's {self.new[:4]} summer is recorded in `../../{self.old}/03_Offseason/`.\n"
        return f"---\ntype: phase\nstatus: {status}\n---\n\n# {title}\n\n## Player decisions\n\n## Events\n{events}\n## Consequences\n"

    def week_note(self, month, week):
        days = {1: "1-7", 2: "8-14", 3: "15-21", 4: "22-end"}[week]
        return (f"---\ntype: regular_season_week\nstatus: not_started\nmonth: {month}\nweek: {week}\ndays: {days}\n---\n\n"
                f"# {month} Week {week}\n\n## Schedule\n\n## Player decisions\n\n## Games and events\n\n## Consequences\n")

    # -- the run ---------------------------------------------------------------------------------
    def run(self):
        from . import league_contracts, offseason, season_evidence
        from .league_cards import write_card_lines
        from .season_evidence import season_records
        from .seasons import structure
        written = []
        # 1. league
        written.append(season_evidence.write_totals(self.old, self.root))
        write_card_lines(self.root)
        written.append(league_contracts.write(self.new, self.root, self.record))
        if not (self.root / offseason.BOOK).is_file():
            offseason.write(self.root)
        ledger = league_contracts.read(self.new, self.root) or {}
        # 2. Miami
        ids = self.identities()
        entries = self.contract_entries(ledger)
        register = self.register(entries, ids)
        self.team.mkdir(parents=True, exist_ok=True)
        for rel in ("Organization", "Team/Player_Cards/TEMPLATE.md", "Finances/league_cap_history.json", "Finances/README.md",
                    "README.md", "Team/README.md", "Team/Roster/README.md", "Team/Depth_Chart/README.md"):
            src, dst = self.old_team / rel, self.team / rel
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            elif src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        config = _read(self.old_team / "team_config.json")
        config.update(season=self.new, as_of=self.day)
        config["projection"] = {"wins": None, "basis": "Set by the staff at training camp from the new roster."}
        _dump(self.team / "team_config.json", config)
        sheet = _read(self.old_team / "Finances/contract_schedules.json")
        sheet.update(as_of=self.day, players=entries)
        from .seasons import label
        sheet["horizon"] = [label(int(self.new[:4]) + i) for i in range(8)]
        _dump(self.team / "Finances/contract_schedules.json", sheet)
        _dump(self.team / "Team/Roster/roster.json", register)
        holdings, old_holdings = self.holdings(entries)
        _dump(self.team / "Team/Roster/holdings.json", holdings)
        _dump(self.old_team / "Team/Roster/holdings.json", old_holdings)
        _dump(self.team / "Team/Depth_Chart/depth_chart.json", self.depth_chart(register))
        rights = {"schema_version": 1, "owner": "ai_gm", "as_of": self.day, "team": MIAMI,
                  "purpose": f"Rights and cap holds for Miami's free agents of the {self.new[:4]} summer onward (none open on the rollover date; "
                             "the next summer's expiring contracts are added when that summer opens).",
                  "players": []}
        _dump(self.team / "Finances/free_agent_rights.json", rights)
        picks = _read(self.old_team / "Finances/draft_picks.json")
        picks.update(as_of=self.day, picks=[p for p in picks["picks"] if p["year"] > int(self.new[:4])])
        _dump(self.team / "Finances/draft_picks.json", picks)
        finance = _read(self.old_team / "Finances/finance.json")
        finance.update(as_of=self.day, season=self.new, pending_control_items=[], draft_rights=[])
        _dump(self.team / "Finances/finance.json", finance)
        prior = season_records(self.old, self.root)
        cards = self.team / "Team/Player_Cards"
        cards.mkdir(parents=True, exist_ok=True)
        for e, p in zip(entries, register["players"]):
            src = self.old_team / "Team/Player_Cards" / f"{p['id']}.md"
            dst = cards / f"{p['id']}.md"
            if src.is_file():
                text = src.read_text(encoding="utf-8")
                text = re.sub(r"^(# .*? \| )\d{4}-\d{2}( Player Profile)$", lambda m: m.group(1) + self.new + m.group(2), text, count=1, flags=re.M)
                dst.write_text(text, encoding="utf-8")
            else:
                key = e.get("bbr_id") or WADE_ID
                dst.write_text(self.card(e, ids.get(key, {}), prior.get(key)), encoding="utf-8")
        # 3. folders and state
        for folder, title in self.PHASES.items():
            note = self.new_dir / folder / "note.md"
            if not note.is_file():
                note.parent.mkdir(parents=True, exist_ok=True)
                note.write_text(self.phase_note(folder, title), encoding="utf-8")
        for folder in ("07_Play_In_Tournament", "08_Playoffs", "10_Free_Agency", "League"):
            (self.new_dir / folder).mkdir(parents=True, exist_ok=True)
        cfg = structure(self.new, self.root)
        for month, spec in cfg["regular_season"].items():
            for week in spec["weeks"]:
                note = self.new_dir / "06_Regular_Season" / spec["folder"] / f"Week_{week}" / "note.md"
                if not note.is_file():
                    note.parent.mkdir(parents=True, exist_ok=True)
                    note.write_text(self.week_note(month, week), encoding="utf-8")
        old_state = _read(self.old_dir / "current_state.json")
        wade = next(e for e in entries if not e.get("bbr_id"))
        state = {"schema_version": 1, "initialized": True, "season": self.new, "current_date": self.day,
                 "current_area": "04_Training_Camp", "current_note": "04_Training_Camp/note.md", "team": MIAMI,
                 "team_abbreviation": old_state.get("team_abbreviation", "MIA"), "draft": old_state.get("draft"),
                 "contract_status": old_state.get("contract_status") if wade["status"] in ("under_contract", "under_rookie_contract") else wade["status"],
                 "roster_status": "under_contract", "last_closed_event": old_state.get("last_closed_event"),
                 "pending_player_decisions": [], "rolled_over_from": self.old, "rolled_over_on": self.day}
        _dump(self.new_dir / "current_state.json", state)
        old_state["current_date"] = max(old_state["current_date"], self.day)
        old_state["closed"] = True
        _dump(self.old_dir / "current_state.json", old_state)
        return {"season": self.new, "day": self.day, "players": [p["name"] for p in register["players"]],
                "departed": [h["player"] for h in old_holdings["entries"] if h.get("until") and h["until"] >= f"{self.new[:4]}-06-30"
                             and h.get("basis", "").endswith("summer market")]}


def miami_summer(record, old_register):
    """Miami's summer in plain terms: re-signed, signed, drafted, traded in and out, and who left (for the report)."""
    held = {p.get("bbr_id"): p["name"] for p in old_register["players"] if p.get("bbr_id")}
    out = {"re_signed": [], "signed": [], "rookies": [], "traded_in": [], "traded_out": [], "options": [], "left": []}
    for e in record["events"]:
        if e.get("club") == MIAMI:
            if e["kind"] == "re_sign" or (e["kind"] in ("qualifying_offer_accepted", "offer_sheet_matched") and e.get("bbr_id") in held):
                out["re_signed"].append(e)
            elif e["kind"] in ("signing", "camp_signing", "offer_sheet_matched"):
                out["signed"].append(e)
            elif e["kind"] == "rookie_scale_signing":
                out["rookies"].append(e)
            elif e["kind"] == "trade":
                out["traded_in"].append(e)
            elif e["kind"] in ("team_option", "player_option", "early_termination_option"):
                out["options"].append(e)
        elif e["kind"] == "trade" and e.get("from") == MIAMI:
            out["traded_out"].append(e)
    stayed = {r["bbr_id"] for r in record["clubs"][MIAMI]}
    where = {r["bbr_id"]: (c, r) for c, rows in record["clubs"].items() for r in rows}
    for b, name in held.items():
        if b not in stayed:
            out["left"].append({"player": name, "bbr_id": b, "to": where.get(b, (None,))[0], "row": where.get(b, (None, None))[1]})
    return out
