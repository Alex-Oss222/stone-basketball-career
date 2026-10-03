#!/usr/bin/env python3
"""Training camp and preseason, stage by stage (docs/front_office.md, training camp).

  python scripts/run_camp.py --write 2003-09-30     invites and camp injury draws
  python scripts/run_camp.py --write 2003-10-05     apply the draws, write the seven preseason requests
  python scripts/run_camp.py --write 2003-10-24     depth chart, rotation and Wade's grade from the box scores
  python scripts/run_camp.py --write 2003-10-27     cut to fifteen, promise check

Each run does every stage due by the date that is not done, and stops when a draw or a game
result is still missing (`scripts/collect_results.py` fetches them from the engine).
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import camp, signing                      # noqa: E402
from runtime.decisions import decision_errors          # noqa: E402
from runtime.gm import FrontOffice                     # noqa: E402
from runtime.market import Market                      # noqa: E402
from runtime.valuation import read                     # noqa: E402
from scripts.refresh_career_views import refresh_career_views # noqa: E402

INVITE_DAY, PRESEASON_DAY, EVALUATION_DAY, CUT_DAY = "2003-09-30", "2003-10-05", "2003-10-24", "2003-10-27"


class CampRun:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.writer = signing.Writer(root)
        self.pending = []

    def load_camp(self):
        path = self.root / camp.CAMP_ROSTER
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def save_camp(self, data):
        (self.root / camp.CAMP_ROSTER).parent.mkdir(parents=True, exist_ok=True)
        (self.root / camp.CAMP_ROSTER).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def decision(self, packet):
        errors = decision_errors(packet)
        if errors:
            raise ValueError(f"{packet['event_id']}: " + "; ".join(errors))
        folder = self.root / camp.CAMP / "Decisions"
        folder.mkdir(parents=True, exist_ok=True)
        request, result = folder / f"{packet['event_id']}.decision.json", folder / f"{packet['event_id']}.decision.result.json"
        if not request.exists():
            request.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
        if result.exists():
            return json.loads(result.read_text(encoding="utf-8"))["outcome"]
        self.pending.append(packet["event_id"])
        return None

    # -- stages --------------------------------------------------------------------------------
    def invites(self, day):
        data = self.load_camp()
        if data:
            return data
        market = Market(day, self.root)
        fo = FrontOffice(day, market, self.root)
        invitees = camp.invite(day, fo, market, self.root)
        data = camp.camp_roster(day, fo, invitees)
        sheet, roster, holdings = self.writer.load(signing.TEAM / "Finances/contract_schedules.json"), self.writer.load(signing.TEAM / "Team/Roster/roster.json"), self.writer.load(signing.TEAM / "Team/Roster/holdings.json")
        stats = {r["bbr_id"]: r for r in read("library/2003/league/nba_2002_03_player_stats.json", self.root)["records"]}
        for r in invitees:
            identity = signing.league_identity(self.root, r["bbr_id"])
            control = f"Camp contract from {signing.long_date(day)}: non-guaranteed minimum ${r['salary']:,}, guaranteed if still on the roster on {camp.GUARANTEE_DATE}."
            sheet["players"].append({"player": r["player"], "bbr_id": r["bbr_id"], "status": "camp_contract", "schedule": {camp.SEASON: r["salary"]},
                                     "amount_kind": {camp.SEASON: "contract_salary"}, "guaranteed": {camp.SEASON: 0}, "guarantee_date": camp.GUARANTEE_DATE,
                                     "signed_date": day, "route": "minimum", "notes": control, "sources": ["04_Training_Camp/camp_roster.json"]})
            roster["players"].append({"id": signing.slug(r["player"]), "name": r["player"], "positions": [r["position"]], "date_of_birth": identity.get("birth_date"),
                                      "status": "camp_contract", "control": control, "working_role": "Camp invitee",
                                      "player_card": f"../Player_Cards/{signing.slug(r['player'])}.md", "bbr_id": r["bbr_id"]})
            self.writer.text(signing.TEAM / f"Team/Player_Cards/{signing.slug(r['player'])}.md",
                             signing.player_card(r["player"], identity, day, control, "../../../04_Training_Camp/camp_roster.json", stats.get(r["bbr_id"])))
            holdings["entries"].append({"player": r["player"], "bbr_id": r["bbr_id"], "from": day, "until": None, "basis": f"camp contract {day} (camp_roster.json)"})
        sheet["as_of"] = roster["as_of"] = day
        self.save_camp(data)
        signing.note_event(self.writer, camp.CAMP / "note.md", day,
                           f"Camp opens with {len(data['players'])} players: {len(invitees)} invitees on non-guaranteed minimums ({', '.join(r['player'] for r in invitees) or 'none'}). Record: `camp_roster.json`.")
        signing.set_state(self.writer, day, area="04_Training_Camp", note="04_Training_Camp/note.md", last_event=f"{day}-camp-opens")
        return data

    def injuries(self, day, data):
        if data.get("injuries_applied"):
            return True
        roster = {p["name"]: p for p in read(signing.TEAM / "Team/Roster/roster.json", self.root)["players"]}
        for p in data["players"]:
            born = roster.get(p["player"], {}).get("date_of_birth") or signing.league_identity(self.root, p.get("bbr_id")).get("birth_date")
            age = camp.age_on(born, day) if born else None
            outcome = self.decision(camp.injury_packet(p, age))
            if outcome == "injured":
                p["injured_through"] = "2003-10-24"
        if self.pending:
            return False
        hurt = [p["player"] for p in data["players"] if p.get("injured_through")]
        data["injuries_applied"] = day
        signing.note_event(self.writer, camp.CAMP / "note.md", day, "Camp injury draws: " + (", ".join(hurt) + " miss the preseason" if hurt else "nobody is hurt") + ".")
        return True

    def preseason(self, day, data):
        depth = read(signing.TEAM / "Team/Depth_Chart/depth_chart.json", self.root)
        market = Market(day, self.root)
        values = camp.prior_values(data, market.valuation)
        written = camp.preseason_requests(data, depth, values, self.root)
        if written:
            signing.note_event(self.writer, camp.PRESEASON / "note.md", day, f"{len(written)} preseason game requests written from the camp rotation; the engine plays them.")
            signing.set_state(self.writer, day, area="05_Preseason", note="05_Preseason/note.md", last_event=f"{day}-preseason-requests")
        return written

    def evaluate(self, day, data):
        if data.get("evaluated"):
            return True
        results = camp.preseason_results(self.root)
        expected = len(camp.miami_preseason_games(self.root))
        if len(results) < expected:
            self.pending.append(f"preseason results {len(results)}/{expected}")
            return False
        market = Market(day, self.root)
        fo = FrontOffice(day, market, self.root)
        scores, lines = camp.staff_scores(data, market.valuation, results)
        winners = {}
        for packet in camp.battle_packets(data, scores, day):
            outcome = self.decision(packet)
            if outcome is not None:
                winners[packet["event_id"].split("-")[2].upper()] = outcome
        if self.pending:
            return False
        depth = camp.depth_chart_from(data, scores, winners, day)
        grade = camp.wade_grade(lines)
        grades = camp.grades_record([grade], day)
        rotation = camp.season_rotation(data, depth, scores, day, {"Dwyane Wade": grade["grade"]})
        self.writer.files[signing.TEAM / "Team/Depth_Chart/depth_chart.json"] = depth
        self.writer.files[camp.ROTATION] = rotation
        self.writer.files[camp.GRADES] = grades
        data["staff_scores"], data["evaluated"] = scores, day
        starters = ", ".join(f"{pos} {depth['positions'][pos][0]}" for pos in camp.POSITIONS if depth["positions"][pos])
        signing.note_event(self.writer, camp.CAMP / "note.md", day,
                           f"Staff decision from {len(results)} preseason games: starters {starters}" + (f"; battles drawn: {winners}" if winners else "") +
                           f". Wade's perimeter-defense grade {grade['grade']} ({grade['evidence'][1]}). Records: `../00_Team/Team/Depth_Chart/depth_chart.json`, `rotation.json`, `../00_Team/Team/defensive_grades.json`.")
        self.writer.text(camp.CAMP / "Wade_Camp_Review.md", wade_page(day, grade, lines.get("Dwyane Wade"), rotation))
        signing.set_state(self.writer, day, area="04_Training_Camp", note="04_Training_Camp/note.md", last_event=f"{day}-camp-decision")
        return True

    def cut(self, day, data):
        if data.get("cut_done"):
            return True
        market = Market(day, self.root)
        fo = FrontOffice(day, market, self.root)
        scores = data.get("staff_scores") or camp.prior_values(data, market.valuation)
        names = camp.cut_list(data, scores, fo)
        sheet, roster, holdings = self.writer.load(signing.TEAM / "Finances/contract_schedules.json"), self.writer.load(signing.TEAM / "Team/Roster/roster.json"), self.writer.load(signing.TEAM / "Team/Roster/holdings.json")
        for name in names:
            for p in data["players"]:
                if p["player"] == name:
                    p["status"] = "released"
            data["cuts"].append({"player": name, "date": day, "score": scores[name]})
            signing.depart(self.writer, name, day, "released", f"released at the cut to {camp.ROSTER_MAX} (non-guaranteed camp contract; no dead money)")
            for e in holdings["entries"]:
                if e["player"] == name and e["until"] is None:
                    e["until"] = day
        depth = self.writer.load(signing.TEAM / "Team/Depth_Chart/depth_chart.json")
        for pos, group in depth["positions"].items():
            depth["positions"][pos] = [n for n in group if n not in names]
        rotation = read(camp.ROTATION, self.root)
        promises = camp.promise_check(fo, rotation, day)
        self.writer.files[camp.PROMISES] = {"schema_version": 1, "owner": "ai_gm", "as_of": day,
                                            "purpose": "Promised roles (from signings) against the written rotation; a broken promise is evidence for the player's later decisions.",
                                            "promises": promises}
        data["cut_done"] = day
        data["status"] = "closed"
        broken = [r["player"] for r in promises if not r["kept"]]
        signing.note_event(self.writer, camp.CAMP / "note.md", day,
                           f"Cut to {camp.ROSTER_MAX}: {', '.join(names) or 'no release needed'}. Promise check: " +
                           (f"broken for {', '.join(broken)}" if broken else "every promised role is in the rotation") + ". Record: `promise_log.json`.", status="completed")
        signing.set_state(self.writer, day, area="04_Training_Camp", note="04_Training_Camp/note.md", last_event=f"{day}-camp-cut")
        return True

    # -- driver ---------------------------------------------------------------------------------
    def write(self, until):
        stops = []
        data = None
        if until >= INVITE_DAY:
            data = self.invites(INVITE_DAY)
            if not self.injuries(INVITE_DAY, data):
                stops.append("awaiting camp injury draws: " + ", ".join(self.pending))
        if not stops and until >= PRESEASON_DAY and data:
            self.preseason(PRESEASON_DAY, data)
        if not stops and until >= EVALUATION_DAY and data:
            if not self.evaluate(EVALUATION_DAY, data):
                stops.append("awaiting " + ", ".join(self.pending))
        if not stops and until >= CUT_DAY and data:
            self.cut(CUT_DAY, data)
        if data:
            self.save_camp(data)
        self.writer.commit()
        return stops


def wade_page(day, grade, line, rotation):
    minutes = next((p["minutes"] for p in rotation["players"] if p["player_id"] == "Dwyane Wade"), 0)
    played = f"{line['games']} preseason games, {line['minutes']:.0f} minutes, {line['stl']} steals, {line['blk']} blocks" if line else "no preseason minutes"
    return f"""# Camp and role review | Dwyane Wade

![Training camp: assignment, evidence and player response](../../../../docs/templates/player_milestones/assets/camp.svg)

[Live detailed camp review](../../Milestones/index.html#training_camp) · [Shooting and Awards](../../Stats_and_Awards/player_cards.html) · [Camp note](note.md) · [Depth chart](../00_Team/Team/Depth_Chart/depth_chart.json) · [Rotation](../00_Team/Team/Depth_Chart/rotation.json)

| Player / age | Position / club | Review date | Availability |
| --- | --- | --- | --- |
| Dwyane Wade; 19 | SG / PG; Miami Heat | {signing.long_date(day)} | cleared |

**Your next decision:** respond to the staff assignment below, ask for reps or feedback (append your instruction under "Your reply").

**Coach's current assignment:** {minutes:.0f} minutes a game in the written rotation (rotation.json, {day}); provisional until opening night.

**Next evaluation:** opening night, October 28, 2003.

## What the staff is evaluating

| Responsibility | Current assignment | Evidence from completed work | Next opportunity |
| --- | --- | --- | --- |
| Ball handling | secondary handler next to the point guard | preseason box scores (`../05_Preseason/`) | regular-season possessions |
| Defensive assignment | guards; perimeter-defense grade **{grade['grade']}** (50 is average) | {grade['evidence'][0]}; {played} | reviewed after the first month |
| Rotation / units | {minutes:.0f} minutes in the written rotation | staff scores in `camp_roster.json` | opening night |
| Conditioning / availability | cleared | camp injury draw: healthy | — |

Camp observations and scrimmage totals are not NBA regular-season statistics.

## What do you want to say?

| Choice | Player instruction | What the staff decides |
| --- | --- | --- |
| Seek an opportunity | "I'd like reps at {{responsibility}}. What would I need to show?" | Whether to grant the trial and its evaluation criteria |
| Request specific feedback | "Show me the possessions where {{issue}} needs work." | Which evidence and correction to communicate |
| Work within the assignment | "My focus is {{task}}. Let's review it after {{event}}." | Actual role and future rotation changes |
| Challenge the assessment constructively | "I disagree about {{point}} because {{evidence}}." | Whether the evidence changes the assessment |

**Your reply:** _open_

**Staff response:** _not yet_

**Next checkpoint:** opening night, October 28, 2003; the grade is reviewed after the first month of games.

The grade is the scheduled perimeter-defense assessment (camp README): the profile's defensive scouting plus camp evidence. It does not add an offensive boost or promote him into the rotation; his place comes from the staff scores like everyone's.
"""


def main(argv):
    if len(argv) != 3 or argv[1] != "--write":
        raise SystemExit(__doc__)
    stops = CampRun().write(argv[2])
    refreshed = refresh_career_views(ROOT)
    print("\n".join(stops) if stops else f"camp stages through {argv[2]} written")
    print(f"Updated {len(refreshed)} detailed career views; open career/Dwyane_Wade/Milestones/index.html#training_camp.")


if __name__ == "__main__":
    main(sys.argv)
