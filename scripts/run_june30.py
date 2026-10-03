#!/usr/bin/env python3
"""Miami's June 30, 2003 decisions (roadmap item 4). Run only when the career clock reaches June 30.

Writes into career/Dwyane_Wade/2003-04/01_Free_Agency/June_30/:
  front_office_decisions.json      rule-based team-option and qualifying-offer decisions, with reasons
  *.decision.json                  engine-drawn decisions: Carter's player option, and any rule decision
                                   Wade's logged request may overturn
Push, let Railway draw, read /decisions/<event_id>, then close the June 30 event in the phase note.

Wade's requests are read from 01_Free_Agency/wade_requests.json (optional).
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.front_office import (age_on, estimated_market_value, player_option_probability, qualifying_offer,
                                  request_override, team_option)
from runtime.standing import standing_on
from scripts.refresh_career_views import refresh_career_views

DATE = "2003-06-30"
SEASON = ROOT / "career/Dwyane_Wade/2003-04"
OUT = SEASON / "01_Free_Agency/June_30"
REQUESTS = SEASON / "01_Free_Agency/wade_requests.json"


def slug(name):
    return name.lower().replace(" ", "_").replace(".", "")


def build(root=ROOT):
    season = root / "career/Dwyane_Wade/2003-04"
    roster = {p["name"]: p for p in json.loads((season / "00_Team/Team/Roster/roster.json").read_text())["players"]}
    sheet = json.loads((season / "00_Team/Finances/contract_schedules.json").read_text())["players"]
    rights = {p["player"]: p for p in json.loads((season / "00_Team/Finances/free_agent_rights.json").read_text())["players"]}
    ratings = json.loads((root / "library/2003/league/nba_2003_veteran_ratings.json").read_text())["players"]
    minimums = json.loads((root / "library/2003/league/nba_1999_cba_minimum_salary_scale.json").read_text())["seasons"]["2003-04"]
    mid_level = json.loads((root / "library/2003/league/nba_2003_04_cap_rules.json").read_text())["exceptions"]["mid_level"]
    requests_path = season / "01_Free_Agency/wade_requests.json"
    requests = json.loads(requests_path.read_text())["requests"] if requests_path.exists() else []
    wants = {(r["subject"], r["player"]): r for r in requests}
    wade = standing_on(root, DATE)["standing"]        # Wade's computed standing on the date (runtime/standing.py)

    def minutes(name):
        bbr = roster[name].get("bbr_id")
        return (ratings.get(bbr) or {}).get("sample", {}).get("minutes", 0)

    decisions, draws = [], []
    for p in sheet:
        name = p["player"]
        if p["status"] == "team_option_pending":
            d = team_option(name, minutes(name), age_on(roster[name]["date_of_birth"], DATE))
            d.update(kind="team_option", salary=p["schedule"]["2003-04"])
            decisions.append(d)
        elif p["status"] == "player_option_pending":
            # Years of service set his minimum salary; they must be recorded on Miami's sheet, never guessed.
            seasons = p.get("years_of_service")
            mins = minutes(name)
            if seasons is None:
                raise ValueError(f"{name}: record years_of_service on contract_schedules.json before June 30")
            minimum = minimums["10_plus" if seasons >= 10 else str(seasons)]
            value = estimated_market_value(mins, minimum, mid_level)
            stay = player_option_probability(p["schedule"]["2003-04"], value)
            draws.append({"event_id": f"{DATE}-{slug(name)}-player-option", "date": DATE,
                          "question": f"Does {name} exercise his 2003-04 player option of ${p['schedule']['2003-04']:,}?",
                          "decider": f"{name} (simulated player)",
                          "options": {"exercise": stay, "decline": round(1 - stay, 3)},
                          "basis": (f"Option ${p['schedule']['2003-04']:,} against an estimated market value of ${round(value):,} "
                                    f"({mins} minutes in 2002-03; minimum plus a minutes-proportional share of the "
                                    f"${mid_level:,} mid-level). runtime/front_office.py, provisional.")})
    for name, r in rights.items():
        if r["restricted_free_agency_eligible"] and r["qualifying_offer"]:
            d = qualifying_offer(name, minutes(name), age_on(roster[name]["date_of_birth"], DATE), r["qualifying_offer"])
            d["kind"] = "qualifying_offer"
            decisions.append(d)
    for d in decisions:
        wish = wants.get((d["kind"], d["player"]))
        chance = request_override(d["decision"], wish and wish["requested"], d["margin"], wade)
        d["wade_request"] = wish
        if chance > 0:
            d["status"] = "pending_engine_draw"
            draws.append({"event_id": f"{DATE}-{slug(d['player'])}-{d['kind'].replace('_', '-')}-wade-request", "date": DATE,
                          "question": f"Does Wade's request change Miami's {d['kind'].replace('_', ' ')} decision on {d['player']}?",
                          "decider": "Miami front office",
                          "options": {d["decision"]: round(1 - chance, 3), wish["requested"]: chance},
                          "basis": (f"Rule decision '{d['decision']}' (margin {d['margin']:.2f}); Wade's standing "
                                    f"'{wade}'. Chance = standing weight x (1 - margin).")})
        else:
            d["status"] = "final"
    return {"date": DATE, "team": "Miami Heat", "owner": "ai_gm", "decisions": decisions}, draws


def main():
    if "--write" not in sys.argv:
        raise SystemExit("Writes career records: run with --write only when the career clock reaches June 30.")
    package, draws = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "front_office_decisions.json").write_text(json.dumps(package, indent=1) + "\n")
    for d in draws:
        (OUT / f"{d['event_id']}.decision.json").write_text(json.dumps(d, indent=1) + "\n")
    refreshed = refresh_career_views(ROOT)
    print(f"{len(package['decisions'])} rule decisions, {len(draws)} engine draws written to {OUT.relative_to(ROOT)}")
    print(f"Updated {len(refreshed)} detailed career views; open career/Dwyane_Wade/Milestones/index.html.")


if __name__ == "__main__":
    main()
