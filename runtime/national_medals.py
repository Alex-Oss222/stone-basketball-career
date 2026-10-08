"""FIBA team medals for every player on a medal-winning national team's locked tournament roster.

The user's rule (2005 offseason framework, section 6):

* A tournament's medals are decided once it is officially closed and its final ranking is canonical
  (`national.after_games`: `closed`, `closed_on` and `ranking` in the tournament record): 1st place = gold medal, 2nd =
  silver medal, 3rd = bronze medal, 4th or below = no medal.
* A medal belongs to every player on that team's official locked roster for the tournament (`rosters` in the record,
  locked the day before the first game by `national.lock_rosters`), including roster members who played no minutes. A
  player never selected, one who withdrew before the lock, or anyone not on that tournament's roster gets none.
* A medal never implies the MVP or the All-Tournament Team; those stay the tournament's separate performance awards
  (`national.decide_awards`).
* The same rule runs for every simulated FIBA edition, with no user step.

The register (`career/Dwyane_Wade/FIBA/<family>/<edition>/medals.json`, beside the tournament record) is derived: it is
rebuilt from the closed record and its closed results, and a rebuild writes the same file, so a medal is never
duplicated. Each medal carries a stable id `<edition_id>-<country slug>-<bbr_id or FIBA identity>-<medal>`, the player,
his country, the tournament and edition, the team's final place, the award date (the day the tournament closed) and the
result that decided the place (the final for first and second, the third-place game for third; the tournament record's
ranking when no single game decided it).

Identity, in order: the locked roster's NBA id (an NBA player with a season behind him on the date); else the
researched roster's id when the league player registry already tracks that player; else the registry's one player with
the same name and birth date; else none, and the medal keeps his FIBA identity, name and country. The registry is read
as the league knew it on the close: only its original rows (no `added_on`) and the rows added on or before that day.
The identities are resolved once, at the close, and frozen into the tournament record (`medal_identities`,
`national.after_games`); every rebuild reads them from there, so a registry row added or repaired after the close
(`write_back.extend_registry`, `repair_registry`: a later NBA debut) never renames a medal or changes its id
(hindsight). The NBA nationality file is not used to name a player: it lists NBA careers through 2007-08, later than
the clock (hindsight).

Wade's own medal stays where it always was, in `career/Dwyane_Wade/awards.json` (`national.record_wade_honors`, id
`<edition_id>-<medal>`); the register sits beside it and validation requires the two to agree both ways. Readers:
`medals_for` (one player's medals on or before a date) and `register_medals` (every medal on or before a date).
"""
import json
import os
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
MEDAL_KEYS = {1: "gold", 2: "silver", 3: "bronze"}
REGISTRY = Path("career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json")
LOCKED = "locked roster (NBA player on the date)"
FIBA_ONLY = "FIBA identity (no NBA id on the date)"
RULE = ("1st gold, 2nd silver, 3rd bronze, 4th or below none; every player on the team's locked tournament roster, "
        "minutes played or not; awarded on the day the tournament closed (runtime/national_medals.py)")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _slug(text):
    """ASCII, lower case, words joined by hyphens ('Puerto Rico' = 'puerto-rico', 'Nájera' = 'najera')."""
    folded = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def _key(name):
    from .write_back import _key as key
    return key(name)


def register_path(e):
    from .national import folder
    return folder(e) / "medals.json"


def page_path(e):
    from .national import folder
    return folder(e) / "README.md"


def player_slug(bbr_id, fiba_key, name):
    """The player's part of a medal id: his NBA id, else his FIBA identity's name and birth date, else his name."""
    if bbr_id:
        return bbr_id
    if fiba_key:
        return _slug(fiba_key.split(":", 2)[-1])
    return _slug(name)


def medal_id(edition_id, country, bbr_id, fiba_key, name, medal):
    return f"{edition_id}-{_slug(country)}-{player_slug(bbr_id, fiba_key, name)}-{medal}"


# -- sources ----------------------------------------------------------------------------------------------------------
def deciding_results(rec, closed):
    """{place: result path} for the places a single game decided: the final's for first and second, the third-place
    game's for third. A place without one cites the tournament record's ranking."""
    out = {}
    for stage, places in (("final", (1, 2)), ("third_place", (3,))):
        g = next((x for x in rec["games"].values() if x["stage"] == stage), None)
        r = closed.get(int(g["number"])) if g else None
        if r:
            for place in places:
                out[place] = r["result"]
    return out


def appearances(closed, root=ROOT):
    """{(team, player): games with minutes} over the tournament's closed results (evidence only: a medal does not
    depend on it)."""
    out = {}
    for r in closed.values():
        res = _read(Path(root) / r["result"])
        for side in ("home", "away"):
            for p in res["player_stats"][side]:
                if (p.get("minutes") or 0) > 0:
                    out[(res[side], p["player_id"])] = out.get((res[side], p["player_id"]), 0) + 1
    return out


class Identity:
    """A locked-roster player's NBA id, FIBA identity and the basis for them (see the module rule), as the league knew
    him on `on` (default: the close): the registry's original rows (no `added_on`) and the rows added on or before that
    day, never a later NBA debut. Called once, at the close (`freeze`)."""

    def __init__(self, e, rec, root=ROOT, on=None):
        from .national import editions
        self.e, self.rec, self.root = e, rec, Path(root)
        self.on = on or rec.get("closed_on") or e["last_game"]
        self._editions = None if not rec.get("roster_sources") else editions(root)
        path = self.root / REGISTRY
        data = _read(path) if path.is_file() else {"players": []}
        rows = data["players"] if isinstance(data, dict) else data
        rows = [r for r in rows if (r.get("added_on") or "") <= self.on]
        self.tracked = {r["bbr_id"] for r in rows if r.get("bbr_id")}
        self.by_name_birth = {}
        for r in rows:
            if r.get("bbr_id") and r.get("birth_date"):
                self.by_name_birth.setdefault((_key(r["name"]), r["birth_date"]), set()).add(r["bbr_id"])

    def researched(self, team, p):
        """The player's entry in the real roster the team plays (this edition's, or an earlier one's)."""
        source = (self.rec.get("roster_sources") or {}).get(team)
        rosters = self._editions[source]["rosters"] if source else self.e["rosters"]
        players = (rosters.get(team) or {}).get("players") or []
        for field, value in (("fiba_key", p.get("fiba_key")), ("bbr_id", p.get("bbr_id"))):
            if value:
                hit = next((x for x in players if x.get(field) == value), None)
                if hit:
                    return hit
        named = [x for x in players if _key(x.get("name", "")) == _key(p["player"])]
        return named[0] if len(named) == 1 else {}

    def __call__(self, team, p):
        entry = self.researched(team, p)
        fiba = p.get("fiba_key") or entry.get("fiba_key")
        if p.get("bbr_id"):
            return p["bbr_id"], fiba, LOCKED
        if entry.get("bbr_id") in self.tracked:
            return entry["bbr_id"], fiba, "researched roster id, tracked by the league player registry on the close"
        hits = self.by_name_birth.get((_key(p["player"]), entry.get("birth_date"))) if entry.get("birth_date") else None
        if hits and len(hits) == 1:
            return next(iter(hits)), fiba, "league player registry on the close (same name and birth date)"
        return None, fiba, FIBA_ONLY


def freeze(e, rec, root=ROOT):
    """Every medal team's locked players' identities, resolved once on the close (`Identity`) and kept in the tournament
    record as `medal_identities`: {team: [{player, bbr_id, fiba_key, identity_basis}] in locked-roster order}. The
    register reads them from the record, so nothing the registry learns after the close renames a medal."""
    ident = Identity(e, rec, root)
    out = {}
    for team in rec["ranking"][:len(MEDAL_KEYS)]:
        out[team] = []
        for p in ((rec.get("rosters") or {}).get(team) or {}).get("players") or []:
            bbr, fiba, basis = ident(team, p)
            out[team].append({"player": p["player"], "bbr_id": bbr, "fiba_key": fiba, "identity_basis": basis})
    return out


# -- the register -----------------------------------------------------------------------------------------------------
def assemble(e, rec, sources, played):
    """The register for a closed record: `sources` {place: result path}, `played` {(team, player): games}; each
    player's identity from the record's frozen `medal_identities` (`freeze`), else the locked roster's own fields."""
    from .national import MEDALS, record_path
    frozen = rec.get("medal_identities") or {}
    closed_on = rec.get("closed_on") or e["last_game"]
    record = record_path(e).as_posix()
    medals, teams = [], []
    for place, team in enumerate(rec["ranking"][:len(MEDAL_KEYS)], start=1):
        medal = MEDAL_KEYS[place]
        roster = ((rec.get("rosters") or {}).get(team) or {}).get("players") or []
        kept = frozen.get(team) or []
        source = sources.get(place) or f"{record}#ranking"
        teams.append({"place": place, "medal": medal, "country": team, "players": len(roster), "source_result": source})
        for i, p in enumerate(roster):
            x = kept[i] if i < len(kept) and kept[i].get("player") == p["player"] else None   # a mismatch: identity_errors
            bbr, fiba, basis = ((x["bbr_id"], x["fiba_key"], x["identity_basis"]) if x else
                                (p.get("bbr_id"), p.get("fiba_key"), LOCKED if p.get("bbr_id") else FIBA_ONLY))
            medals.append({"id": medal_id(e["edition_id"], team, bbr, fiba, p["player"], medal), "player": p["player"],
                           "bbr_id": bbr, "fiba_key": fiba, "identity_basis": basis, "country": team, "medal": medal,
                           "name": MEDALS[place], "place": place, "edition_id": e["edition_id"], "tournament": e["name"],
                           "family": e["family"], "edition": e["edition"], "competition": e["game_type"],
                           "period_start": e["first_game"], "period_end": e["last_game"], "awarded_on": closed_on,
                           "games_played": played.get((team, p["player"]), 0), "source_result": source,
                           "source_record": record, "page": page_path(e).as_posix()})
    medals.sort(key=lambda m: (m["place"], _key(m["player"]), m["id"]))
    seen = set()
    for m in medals:
        if m["id"] in seen:
            raise ValueError(f"{e['edition_id']}: two locked-roster players share the medal id {m['id']}; "
                             "the researched roster needs a birth date or an NBA id to tell them apart")
        seen.add(m["id"])
    return {"schema_version": 1, "kind": "fiba_medal_register", "edition_id": e["edition_id"], "tournament": e["name"],
            "family": e["family"], "edition": e["edition"], "closed_on": closed_on, "rule": RULE,
            "source_record": record, "teams": teams, "medals": medals}


def closed(rec):
    """Officially closed with a canonical final ranking."""
    return bool(rec and rec.get("closed") and rec.get("ranking") and rec.get("rosters"))


def build(e, rec, root=ROOT):
    """The edition's register from its closed record (with its frozen identities) and closed results, or None before
    the close. A record closed before its identities were frozen resolves them on its close day (`freeze`)."""
    if not closed(rec):
        return None
    from .national import results
    if "medal_identities" not in rec:
        rec = dict(rec, medal_identities=freeze(e, rec, root))
    done = results(e, rec, root)
    return assemble(e, rec, deciding_results(rec, done), appearances(done, root))


def read(e, root=ROOT):
    path = Path(root) / register_path(e)
    return _read(path) if path.is_file() else None


def write(e, rec, root=ROOT):
    """Write (or rewrite, unchanged) the register of a closed edition. Returns it, or None before the close."""
    from .national import _write
    register = build(e, rec, root)
    if register is not None:
        _write(Path(root) / register_path(e), register)
    return register


def write_all(root=ROOT):
    """Rebuild every closed edition's register (idempotent); a closed record without frozen identities gets them first,
    resolved on its close day (`freeze`). Returns the register paths written."""
    from .national import _write, editions, read_record, record_path
    out = []
    for e in editions(root).values():
        rec = read_record(e, root)
        if closed(rec) and "medal_identities" not in rec:
            rec["medal_identities"] = freeze(e, rec, root)
            _write(Path(root) / record_path(e), rec)
        if write(e, rec, root) is not None:
            out.append(Path(root) / register_path(e))
    return out


# -- readers ----------------------------------------------------------------------------------------------------------
def register_medals(root=ROOT, on=None):
    """Every medal in every register, awarded on or before `on` (None: all), in award order."""
    from .national import WORLD
    out = []
    for path in sorted((Path(root) / WORLD).glob("*/*/medals.json")):
        out += [m for m in _read(path).get("medals", []) if on is None or m["awarded_on"] <= on]
    return sorted(out, key=lambda m: (m["awarded_on"], m["edition_id"], m["place"], m["id"]))


def medals_for(bbr_id=None, name=None, on=None, root=ROOT):
    """One player's medals awarded on or before `on`: by NBA id where the medal has one, else by name (accents and
    punctuation folded). A medal never appears before its tournament closed."""
    out = []
    for m in register_medals(root, on):
        if bbr_id and m.get("bbr_id"):
            if m["bbr_id"] == bbr_id:
                out.append(m)
        elif name and _key(m["player"]) == _key(name):
            out.append(m)
    return out


def honor_text(m):
    """'<tournament>: gold medal (<country>, 1st)'."""
    return f"{m['tournament']}: {m['name']} ({m['country']}, {_ordinal(m['place'])})"


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def link(m, from_dir, root=ROOT):
    """A relative link from a page's folder to the tournament page's medal table."""
    return os.path.relpath(Path(root) / m["page"], Path(from_dir)).replace(os.sep, "/") + "#medals"


# -- validation -------------------------------------------------------------------------------------------------------
def identity_errors(e, rec):
    """The frozen identities (`medal_identities`): none before the close; after it, present, for exactly the medal
    teams, one per locked player in locked-roster order, each keeping the locked roster's own NBA id and FIBA key."""
    eid = e["edition_id"]
    frozen = (rec or {}).get("medal_identities")
    if not closed(rec):
        return [f"{eid}: medal identities frozen before the tournament closed"] if frozen is not None else []
    if frozen is None:
        return [f"{eid}: closed but its medal identities were not frozen at the close "
                "(python scripts/national_day.py --medals; runtime/national_medals.py)"]
    errors = []
    teams = rec["ranking"][:len(MEDAL_KEYS)]
    if sorted(frozen) != sorted(teams):
        errors.append(f"{eid}: medal identities frozen for {sorted(frozen)}, not the medal teams {sorted(teams)}")
    for team in teams:
        roster = (rec["rosters"].get(team) or {}).get("players") or []
        kept = frozen.get(team) or []
        if [x.get("player") for x in kept] != [p["player"] for p in roster]:
            errors.append(f"{eid}: {team}'s frozen medal identities do not follow its locked roster")
            continue
        for p, x in zip(roster, kept):
            for field in ("bbr_id", "fiba_key"):
                if p.get(field) and x.get(field) != p[field]:
                    errors.append(f"{eid}: {p['player']}'s frozen medal {field} {x.get(field)} is not the locked "
                                  f"roster's {p[field]}")
    return errors


def edition_errors(e, rec, have, fresh, clock=None, wade_awards=None):
    """One edition's register against its record: none before the close; after it, frozen identities
    (`identity_errors`) and a register complete and equal to a fresh build; every medal for a locked-roster player of a
    medal team, awarded on the close and not after the clock; Wade's medal in the register and in awards.json
    (`wade_awards`: the ids there) both ways."""
    from .national import WADE_BBR
    eid = e["edition_id"]
    claimed = [k for k in MEDAL_KEYS.values() if f"{eid}-{k}" in (wade_awards or ())]
    if not closed(rec):
        errors = identity_errors(e, rec)
        if have is not None:
            errors.append(f"{eid}: medal register written before the tournament closed")
        return errors + [f"{eid}: awards.json has Wade's {k} medal but the tournament has not closed" for k in claimed]
    errors = identity_errors(e, rec)
    held = [m["medal"] for m in fresh["medals"] if m.get("bbr_id") == WADE_BBR]
    for k in claimed:
        if held.count(k) != 1:
            errors.append(f"{eid}: awards.json has Wade's {k} medal but the medal register does not")
    for m in fresh["medals"]:
        if m.get("bbr_id") == WADE_BBR and wade_awards is not None and f"{eid}-{m['medal']}" not in wade_awards:
            errors.append(f"{eid}: Wade's {m['name']} is in the medal register but not in awards.json")
    if have is None:
        return errors + [f"{eid}: closed {rec.get('closed_on') or e['last_game']} but has no medal register "
                         f"({register_path(e).as_posix()}; runtime/national_medals.py)"]
    closed_on = rec.get("closed_on") or e["last_game"]
    locked = {(team, p["player"]) for team, r in rec["rosters"].items() for p in r["players"]}
    want = {m["id"]: m for m in fresh["medals"]}
    got = {}
    for m in have.get("medals", []):
        mid = m.get("id")
        if mid in got:
            errors.append(f"{eid}: medal {mid} recorded twice")
        got[mid] = m
        if (m.get("country"), m.get("player")) not in locked:
            errors.append(f"{eid}: medal {mid} for {m.get('player')}, who is not on {m.get('country')}'s locked roster")
        if (m.get("awarded_on") or "") < closed_on:
            errors.append(f"{eid}: medal {mid} dated {m.get('awarded_on')}, before the tournament closed {closed_on}")
        if clock and (m.get("awarded_on") or "9999") > clock:
            errors.append(f"{eid}: medal {mid} dated {m.get('awarded_on')}, after the career date {clock}")
    for mid in sorted(set(want) - set(got)):
        errors.append(f"{eid}: medal register lacks {mid} ({want[mid]['player']}, {want[mid]['country']})")
    for mid in sorted(set(got) - set(want)):
        m = got[mid]
        if (m.get("country"), m.get("player")) in locked:
            errors.append(f"{eid}: medal {mid} is not the medal {m.get('country')}'s final place earns")
    for mid in sorted(set(want) & set(got)):
        if want[mid] != got[mid]:
            errors.append(f"{eid}: medal {mid} differs from a fresh build of the closed record")
    if {k: v for k, v in have.items() if k != "medals"} != {k: v for k, v in fresh.items() if k != "medals"}:
        errors.append(f"{eid}: medal register header differs from a fresh build of the closed record")
    return errors


def medal_errors(root=ROOT, clock=None):
    """Every edition's register (`edition_errors`), and no register for an edition the pipeline does not know."""
    from .national import PLAYER, WORLD, editions, read_record
    root = Path(root)
    errors, known = [], set()
    awards = root / PLAYER / "awards.json"
    wade_awards = {a["id"] for a in _read(awards)["awards"]} if awards.is_file() else None
    for e in editions(root).values():
        known.add(register_path(e).as_posix())
        rec = read_record(e, root)
        errors += edition_errors(e, rec, read(e, root), build(e, rec, root), clock, wade_awards)
    for path in sorted((root / WORLD).glob("*/*/medals.json")):
        if path.relative_to(root).as_posix() not in known:
            errors.append(f"{path.relative_to(root)}: medal register for no known edition")
    return errors
