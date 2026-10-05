"""The 2004 NBA Draft for simulated Miami (roadmap 17), on June 24, 2004.

Other clubs' picks follow history (`library/2004/league/nba_2004_draft_class.json`): the selecting club, with any
draft-night rights move that does not involve Miami. Real Miami's draft-night transactions are skipped (AGENTS.md
rule 1): Toronto keeps No. 39 (Albert Miralles), and No. 47 is Miami's own pick. Miami owns its own first- and
second-round picks and Dallas's second-rounder, No. 53, acquired in the August 22, 2001 Tim Hardaway trade, before the
career began (`00_Team/Finances/draft_picks.json`).

Miami picks on draft-night evidence only (`library/2004/league/nba_2004_prospect_evidence.json`): pre-draft mock drafts
published on or before June 24, 2004, college statistics and measurements; never a later NBA result. The front office
takes the best available player by the consensus mock slot (lower is better), moved up NEED_SLOTS when his position
group (G, F, C) has fewer than two Miami players under contract for 2004-05 (judgement). A pick is available when no
real pick before Miami's slot took him and Miami has not already taken him. Ties keep the better single mock slot.

Conflict rule: if Miami takes a player history gave to another club at a later pick, that club receives the rights to
the player history gave Miami at Miami's slot (the displaced club's pick is not lost). Miami's real draftee whom Miami
does not take and no conflict places has no previous NBA club and starts as a free agent (rule 1).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT_DATE = "2004-06-24"
CLASS = Path("library/2004/league/nba_2004_draft_class.json")
EVIDENCE = Path("library/2004/league/nba_2004_prospect_evidence.json")
ROSTERS = Path("library/2004/league/nba_2004_05_team_rosters.json")
TEAM = Path("career/Dwyane_Wade/2003-04/00_Team")
RECORD = Path("career/Dwyane_Wade/2003-04/09_Draft/draft_2004.json")
MIAMI, MIA = "Miami Heat", "MIA"
NEED_SLOTS = 3
GROUP = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def club_names(root=ROOT):
    names = {v["code"]: club for club, v in _read(Path(root) / ROSTERS)["clubs"].items()}
    names[MIA] = MIAMI
    return names


def picks(root=ROOT):
    return sorted(_read(Path(root) / CLASS)["picks"], key=lambda p: p["overall"])


def miami_slots(root=ROOT):
    """Miami's 2004 picks by overall number: its own, plus picks it owned before the career began."""
    out = []
    for p in picks(root):
        if p["original_owner"] == MIA and not p["pick_traded_before_draft"]:
            out.append(p["overall"])
        elif p["selecting_club"] == MIA and p["pick_traded_before_draft"] and _before_career(p.get("pick_acquisition") or ""):
            out.append(p["overall"])
    return out


def _before_career(note):
    import re
    years = [int(y) for y in re.findall(r"\b(19\d\d|200\d)\b", note)]
    return bool(years) and max(years) <= 2002


def real_holder(p, names):
    """The club that holds the real pick's rights in the simulation: draft-night moves involving Miami are skipped."""
    move = p.get("draft_night_rights_move")
    if move and move.get("to_club") and MIA not in (move["to_club"], p["selecting_club"]):
        return names.get(move["to_club"])
    if p["selecting_club"] == MIA:
        return names.get(p["original_owner"]) if p["overall"] not in miami_slots() else MIAMI
    return names.get(p["selecting_club"])


def evidence(root=ROOT):
    """{bbr_id: prospect} with consensus slot, best single mock slot and position group."""
    data = _read(Path(root) / EVIDENCE)
    out = {}
    for p in data["players_drafted"] + data["undrafted_candidates"]["players"]:
        r = p.get("pre_draft_rankings") or {}
        slots = [r.get(k) for k in ("vitale_espn_2004_06_22", "hrr_2004_06_24", "nbadraft_net_2004_mock") if isinstance(r.get(k), (int, float))]
        pos = (p.get("position") or {}).get("value") if isinstance(p.get("position"), dict) else p.get("position")
        out[p.get("bbr_id") or p["player_id"]] = {
            "player": p["player_id"], "bbr_id": p.get("bbr_id"), "position": pos,
            "group": GROUP.get((pos or "F").split("/")[0], "F"),
            "consensus": r.get("consensus_mock_mean_slot") or 99.0, "best_mock": min(slots) if slots else 99}
    return out


def miami_groups(root=ROOT):
    """Players under contract with Miami for 2004-05, counted by position group."""
    sheet = _read(Path(root) / TEAM / "Finances/contract_schedules.json")
    roster = {p["name"]: p for p in _read(Path(root) / TEAM / "Team/Roster/roster.json")["players"]}
    counts = {"G": 0, "F": 0, "C": 0}
    for p in sheet["players"]:
        if (p.get("schedule") or {}).get("2004-05") and p.get("status") not in ("renounced", "released", "traded", "signed_elsewhere",
                                                                                  "voided", "waived", "team_option_declined", "player_option_declined"):
            positions = (roster.get(p["player"]) or {}).get("positions") or ["F"]
            counts[GROUP.get(positions[0], "F")] += 1
    return counts


def decide(root=ROOT):
    """Miami's picks, in slot order, and the displaced rights: (choices, displaced {bbr_id: club})."""
    names, ev, groups = club_names(root), evidence(root), miami_groups(root)
    slots = miami_slots(root)
    real = picks(root)
    taken, choices, displaced, moved = set(), [], {}, {}
    for slot in slots:
        before = {p["bbr_id"] for p in real if p["overall"] < slot and p["overall"] not in slots}
        before |= {b for b, k in moved.items() if k < slot}          # a displaced player, taken at the displaced pick
        pool = [e for k, e in ev.items() if k not in before and k not in taken]
        score = lambda e: (e["consensus"] - (NEED_SLOTS if groups.get(e["group"], 0) < 2 else 0), e["best_mock"])
        pick = min(pool, key=score)
        taken.add(pick["bbr_id"] or pick["player"])
        groups[pick["group"]] = groups.get(pick["group"], 0) + 1
        history = next(p for p in real if p["overall"] == slot)
        row = {"slot": slot, "round": history["round"], "player": pick["player"], "bbr_id": pick["bbr_id"], "position": pick["position"],
               "consensus_mock_slot": pick["consensus"], "need_adjusted": groups[pick["group"]] - 1 < 2,
               "history_at_slot": {"player": history["player"], "bbr_id": history["bbr_id"]}}
        real_pick = next((p for p in real if p["bbr_id"] == pick["bbr_id"]), None)
        if real_pick and real_pick["overall"] != slot and real_pick["overall"] not in slots:
            holder = real_holder(real_pick, names)
            displaced[history["bbr_id"]] = holder
            moved[history["bbr_id"]] = real_pick["overall"]
            row["displaced"] = {"club": holder, "real_pick": real_pick["overall"], "receives": history["player"]}
        choices.append(row)
    return choices, displaced


def displaced_rights(root=ROOT):
    """{bbr_id: club} from the recorded draft (empty before it is recorded)."""
    path = Path(root) / RECORD
    if not path.is_file():
        return {}
    return {bbr: club for bbr, club in _read(path)["displaced_rights"].items()}


def record(root=ROOT, clock=None):
    """Write the draft record on or after the draft date. Returns it, or None before the date or once written."""
    from .write_back import clock as career_clock
    root = Path(root)
    clock = clock or career_clock(root)
    path = root / RECORD
    if clock < DRAFT_DATE or path.is_file():
        return None
    choices, displaced = decide(root)
    data = {"schema_version": 1, "kind": "miami_draft", "draft": "2004 NBA Draft", "date": DRAFT_DATE, "decided_by": "ai_gm",
            "rule": __doc__.split("\n\n", 1)[1].strip(), "miami_slots": miami_slots(root), "choices": choices,
            "displaced_rights": displaced, "evidence": EVIDENCE.as_posix(), "class": CLASS.as_posix()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return data
