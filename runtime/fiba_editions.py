"""Researched FIBA edition files (`library/<year>/fiba/*.json`) normalized into the pipeline's form.

Two research layouts exist: the 2006 World Championship file (games numbered 1-80, `team_a`/`team_b` codes and a
`bracket_slot` text such as "A1 v B4" or "W69 v W70") and the other editions (`game_id`, `slot_a`/`slot_b` such as
"B1", "R4", "W-SF1", and a `bracket_slot` id such as "SF1"). Both become:

    {"groups": {gid: {"stage": "group_<gid>", "teams": [names or slots], "carry_from": [gids]}},
     "games": [{"number", "date", "venue", "stage", "home", "away", "home_slot", "away_slot"}],
     "rosters": {team name: {"coach", "players": [{"name", "position", "birth_date", "bbr_id"?, "fiba_key"}]}}, ...}

Slots: "A1" a group place, "W:<number>" / "L:<number>" a game's winner or loser. Nothing here reads a result.
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILY_TYPES = {("World_Cup", "Qualifiers"): "world_cup_qualifier", ("World_Cup", "Final_Tournament"): "world_cup_finals",
                ("Olympics", "Qualifiers"): "olympic_qualifier", ("Olympics", "Final_Tournament"): "olympic_finals",
                ("Continental_Cups", "Qualifiers"): "continental_qualifier",
                ("Continental_Cups", "Final_Tournament"): "continental_finals"}
STAGES = {"preliminary_round": "group", "group_stage": "group", "group_round": "group", "second_round": "group",
          "round_of_16": "round_of_16", "quarterfinal": "quarterfinal", "semifinal": "semifinal", "final": "final",
          "gold_medal": "final", "third_place": "third_place", "bronze_medal": "third_place"}


def _v(x):
    return x.get("value") if isinstance(x, dict) and "value" in x else x


def fiba_key(team, name, birth):
    """A non-NBA player's stable identity: country, ASCII name and birth date."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return f"fiba:{team.lower()}:{re.sub(r'[^a-z0-9]+', '-', ascii_name).strip('-')}:{birth or 'unknown'}"


def _names(raw):
    out = {}
    for t in raw["teams"]:
        code = t.get("fiba_code") or t.get("team")
        out[code] = t.get("name") or code
    return out


def _slot(text, names, by_bracket, second_round):
    """A researched slot reference in the pipeline's grammar."""
    text = text.strip()
    m = re.fullmatch(r"([WL])-?(\w+)", text)
    if m and (m.group(2) in by_bracket or m.group(2).isdigit()):
        ref = by_bracket.get(m.group(2), m.group(2))
        return f"{m.group(1)}:{ref}"
    if text in names:
        return names[text]
    if re.fullmatch(r"R\d", text) and second_round:
        return f"{second_round}{text[1:]}"
    return text


def normalize(raw):
    """The pipeline's edition (without the engine layers, which scripts/build_fiba_engine.py adds)."""
    names = _names(raw)
    family, stage = _v(raw["family"]), _v(raw.get("stage_kind")) or "Final_Tournament"
    edition = _v(raw["edition"]).split("_")[0] if isinstance(_v(raw["edition"]), str) else str(_v(raw["edition"]))
    sched = raw["schedule"]
    groups, games, by_bracket = {}, [], {}
    second_round = "R" if any(g["stage"] == "second_round" for g in sched) else None
    for i, g in enumerate(sched, 1):
        number = g.get("game_number") or i
        if g.get("bracket_slot") and not (" v " in g["bracket_slot"]):
            by_bracket[g["bracket_slot"]] = str(number)
    for i, g in enumerate(sched, 1):
        number = g.get("game_number") or i
        kind = STAGES.get(g["stage"]) or ("group" if g["stage"].startswith("group") else g["stage"])
        if kind == "group":
            gid = (g.get("group") or (second_round if g["stage"] == "second_round" else g["stage"].split("_")[-1]))
            st = f"group_{gid}"
            grp = groups.setdefault(gid, {"stage": st, "teams": [], "carry_from": []})
        else:
            st = kind
        if g.get("team_a"):
            home, away = names[g["team_a"]], names[g["team_b"]]
            hs = as_ = None
            if kind == "group":
                for t in (home, away):
                    if t not in grp["teams"]:
                        grp["teams"].append(t)
        else:
            if g.get("slot_a"):
                a, b = g["slot_a"], g["slot_b"]
            else:
                a, b = [x.strip() for x in g["bracket_slot"].split(" v ")]
            hs, as_ = _slot(a, names, by_bracket, second_round), _slot(b, names, by_bracket, second_round)
            home = away = None
            if kind == "group":
                for s in (hs, as_):
                    if s not in grp["teams"]:
                        grp["teams"].append(s)
        games.append({"number": int(number), "date": g["date"], "venue": g.get("venue") or g.get("city"),
                      "stage": st, "home": home, "away": away, "home_slot": hs, "away_slot": as_})
    if second_round:
        firsts = [gid for gid in groups if gid != second_round]
        groups[second_round]["carry_from"] = firsts
        groups[second_round]["teams"] = sorted(groups[second_round]["teams"])
        groups = {**{k: groups[k] for k in firsts}, second_round: groups[second_round]}
    # Knockout slots written as "A1 v B4" inside a winner reference (2006: "W(A1 v B4)") do not occur in games.
    return {"family": family, "stage": stage, "edition": edition, "game_type": FAMILY_TYPES[(family, stage)],
            "name": _v(raw.get("official_name")) or raw.get("slug"), "groups": groups, "games": games,
            "rosters": rosters(raw, names), "host": _host(raw, names),
            "first_game": min(g["date"] for g in games), "last_game": max(g["date"] for g in games)}


def _host(raw, names):
    h = raw.get("host")
    if isinstance(h, dict):
        country = _v(h.get("country"))
        return country
    return names.get(h, h)


def rosters(raw, names):
    """{team name: {"coach", "players"}}; the USA's real roster is kept apart (the committee picks the USA's)."""
    r = raw.get("rosters") or {}
    teams = r.get("teams", r) if isinstance(r, dict) else {}
    out = {}
    for code, entry in teams.items():
        if code in ("real_usa_roster_reference",) or not isinstance(entry, dict):
            continue
        name = names.get(code, entry.get("team", code))
        coach = _v(entry.get("head_coach"))
        coach = coach.get("name") if isinstance(coach, dict) else coach
        players = []
        for p in entry.get("players") or []:
            bbr = _v(p.get("bbr_id"))
            players.append({"name": p["name"], "position": _v(p.get("position")), "birth_date": _v(p.get("birth_date")),
                            "bbr_id": bbr or None, "fiba_key": fiba_key(code, p["name"], _v(p.get("birth_date")))})
        out[name] = {"coach": coach, "players": players}
    usa = r.get("real_usa_roster_reference") if isinstance(r, dict) else None
    if usa:
        out.setdefault(names.get("USA", "United States"), {"coach": None, "players": []})["real_reference"] = usa
    return out


def research_files(root=ROOT):
    return sorted(p for p in Path(root).glob("library/*/fiba/*.json") if json.loads(p.read_text(encoding="utf-8")).get("kind") == "fiba_edition")
