#!/usr/bin/env python3
"""Correct camp signings made on wrong availability, then refill Miami's open roster spots.

    python scripts/correct_camp_signings.py --write 2003-10-27

1. Void. A camp contract is void when its player was not truly available on the day Miami signed him:
   his real club re-signed or traded him on or before that day, he was not a free agent at all, or he
   was a restricted free agent (a camp contract bypasses his club's right to match). The researched
   moves are in `library/2003/league/nba_2003_offseason_transactions.json`. A voided player leaves
   Miami's books; under rule 2 he is back with his real club. Played preseason games keep their inputs.
2. Refill (`runtime/refill.py`). Open spots are filled from players truly available on the date. Wade's
   requests are weighed by his standing. The front office's override and each player's answer are
   engine draws, never chosen and never re-rolled.
3. Rotation. The staff writes a new rotation from the corrected roster with the camp's staff scores.

Each run does what is due and stops when a draw is still missing (`python scripts/draw_decisions.py`).
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import camp, refill, signing, standing                  # noqa: E402
from runtime.contract_archive import archive_contract                 # noqa: E402
from runtime.decisions import decision_errors                         # noqa: E402
from runtime.gm import FrontOffice                                    # noqa: E402
from runtime.market import Market                                     # noqa: E402
from runtime.valuation import read                                    # noqa: E402
from scripts.refresh_career_views import refresh_career_views         # noqa: E402

RECORD = camp.CAMP / "signing_corrections.json"
REQUESTS = Path("career/Dwyane_Wade/2003-04/01_Free_Agency/wade_requests.json")


class Correction:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.writer = signing.Writer(root)
        self.pending = []

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

    def record(self):
        path = self.root / RECORD
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    # -- 1. void ---------------------------------------------------------------------------------
    def invalid(self, data):
        rows = []
        for p in data["players"]:
            if p.get("kind") != "invite" or p.get("status") == "voided":
                continue
            signed = data["opened"]
            market = Market(signed, self.root)
            bbr = p.get("bbr_id")
            reason = None
            if bbr not in market.players:
                reason = "he was not a free agent on that date (world data corrected)"
            else:
                e = market.exit(bbr)
                if e and e[0] <= signed:
                    reason = f"{e[1]} had already {'re-signed' if e[2]['kind'] == 're_sign' else 'acquired'} him on {e[0]} ({e[2]['kind']})"
                elif market.restricted(bbr):
                    reason = "he was a restricted free agent; a camp contract bypassed his club's right to match"
            if bbr not in market.players:
                rows_e = [r for r in read("library/2003/league/nba_2003_offseason_transactions.json", self.root)["signings"] if r.get("bbr_id") == bbr]
                if rows_e:
                    reason += f"; real move: {rows_e[0]['kind']} to {rows_e[0]['to']} on {rows_e[0]['date']}"
            if reason:
                rows.append({"player": p["player"], "bbr_id": bbr, "signed": signed, "status_before": p["status"], "reason": reason})
        return rows

    def void(self, day, data, rows):
        holdings = self.writer.load(signing.TEAM / "Team/Roster/holdings.json")
        for r in rows:
            signing.depart(self.writer, r["player"], day, "voided",
                           f"camp contract of {signing.long_date(r['signed'])} voided: {r['reason']}; he returns to his real club (rule 2 no longer applies)")
            for e in holdings["entries"]:
                if e["player"] == r["player"] and e["until"] is None:
                    e["until"] = day
                    e["basis"] = e.get("basis", "") + f"; voided {day} (signing_corrections.json)"
            for p in data["players"]:
                if p["player"] == r["player"]:
                    p["status"] = "voided"
            if r["player"] in data.get("staff_scores", {}):
                pass

    # -- 2. refill -------------------------------------------------------------------------------
    def refill(self, day, data, rec):
        market = Market(day, self.root)
        fo = FrontOffice(day, market, self.root)
        roster = self.writer.load(signing.TEAM / "Team/Roster/roster.json")
        spots = refill.open_spots(roster)
        rec["refill"] = {"spots": spots, "picks": [], "requests": [], "answers": []}   # rebuilt each run from the stored draws
        if spots <= 0:
            return True
        positions = fo._positions()
        for r in read(camp.STATS_PATH, self.root)["records"]:
            if r.get("position"):
                positions.setdefault(r["bbr_id"], str(r["position"]).split("-")[0])
        ident = self.root / refill.IDENTITIES
        for p in (json.loads(ident.read_text(encoding="utf-8"))["players"] if ident.is_file() else []):
            positions.setdefault(p["bbr_id"], p["position"])
        wanted = [q for q in read(REQUESTS, self.root)["requests"]
                  if q.get("subject") == "free_agent_target" and q.get("requested") == "pursue" and q["date"] <= day]
        ranked = refill.candidates(day, fo, market, positions, self.root, requested={q["player"] for q in wanted})
        rec["refill"]["ranking"] = [{k: c[k] for k in ("player", "position", "value", "value_known", "fit", "score", "wade_request")} for c in ranked[:8]]
        picks = ranked[:spots]
        snap = standing.standing_on(self.root, day)["standing"]
        for q in wanted:
            row = next((c for c in ranked if c["player"] == q["player"]), None)
            if row is None or row in picks:
                tie = row is not None and any(c is not row and c["score"] == row["score"] and ranked.index(c) >= spots for c in ranked)
                rec["refill"]["requests"].append({"player": q["player"], "request_date": q["date"],
                                                  "outcome": ("picked by the rule; the request broke a tie at the last spot" if tie else "picked by the rule")
                                                  if row else "not available as an unrestricted free agent"})
                continue
            packet = refill.request_packet(day, q, row, picks[-1] if picks else None, snap)
            outcome = self.decision(packet)
            if outcome is None:
                return False
            rec["refill"]["requests"].append({"player": q["player"], "request_date": q["date"], "standing": snap,
                                              "decision_event": packet["event_id"], "options": packet["options"], "outcome": outcome})
            if outcome == "sign":
                picks = picks[:-1] + [row] if picks else [row]
        # Each pick answers; a decline passes the spot to the next candidate the rule ranks.
        queue = picks + [c for c in ranked if c not in picks]
        signed = []
        for row in queue:
            if len(signed) >= spots:
                break
            outcome = self.decision(refill.answer_packet(day, row))
            if outcome is None:
                return False
            rec["refill"]["answers"].append({"player": row["player"], "outcome": outcome, "event": f"{day}-refill-answer-{row['bbr_id']}"})
            if outcome == "accept":
                signed.append(row)
        rec["refill"]["picks"] = [dict(r) for r in signed]
        self.sign(day, data, signed)
        return True

    def sign(self, day, data, rows):
        sheet = self.writer.load(signing.TEAM / "Finances/contract_schedules.json")
        roster = self.writer.load(signing.TEAM / "Team/Roster/roster.json")
        holdings = self.writer.load(signing.TEAM / "Team/Roster/holdings.json")
        depth = self.writer.load(signing.TEAM / "Team/Depth_Chart/depth_chart.json")
        stats = {r["bbr_id"]: r for r in read(camp.STATS_PATH, self.root)["records"]}
        for r in rows:
            identity = signing.league_identity(self.root, r["bbr_id"])
            control = (f"Signed {signing.long_date(day)}: non-guaranteed minimum ${r['salary']:,}, guaranteed if still on the roster on "
                       f"{camp.GUARANTEE_DATE} (roster refill, signing_corrections.json).")
            sheet["players"].append({"player": r["player"], "bbr_id": r["bbr_id"], "status": "camp_contract", "schedule": {camp.SEASON: r["salary"]},
                                     "amount_kind": {camp.SEASON: "contract_salary"}, "guaranteed": {camp.SEASON: 0}, "guarantee_date": camp.GUARANTEE_DATE,
                                     "signed_date": day, "route": "minimum", "notes": control, "sources": [str(RECORD.relative_to(camp.BASE))]})
            archive_contract(self.writer, sheet["players"][-1], day, event="signed", source=str(RECORD), player_id=r["bbr_id"], signing_team="Miami Heat")
            roster["players"].append({"id": signing.slug(r["player"]), "name": r["player"], "positions": [r["position"]],
                                      "date_of_birth": identity.get("birth_date"), "status": "camp_contract", "control": control,
                                      "working_role": "Roster refill", "player_card": f"../Player_Cards/{signing.slug(r['player'])}.md", "bbr_id": r["bbr_id"]})
            self.writer.text(signing.TEAM / f"Team/Player_Cards/{signing.slug(r['player'])}.md",
                             signing.player_card(r["player"], identity, day, control, "../../../04_Training_Camp/signing_corrections.json", stats.get(r["bbr_id"])))
            holdings["entries"].append({"player": r["player"], "bbr_id": r["bbr_id"], "from": day, "until": None, "basis": f"refill signing {day} (signing_corrections.json)"})
            depth["positions"].setdefault(r["position"], []).append(r["player"])
            data["players"].append({"player": r["player"], "bbr_id": r["bbr_id"], "positions": [r["position"]], "status": "camp_contract",
                                    "kind": "refill", "contract": {"salary": r["salary"], "guaranteed": 0, "guarantee_date": camp.GUARANTEE_DATE},
                                    "value": r["value"], "fit": r["fit"], "injured_through": None})
            signing.note_event(self.writer, signing.PHASE / "note.md", day, f"Miami signs {r['player']}: {control}")
        sheet["as_of"] = roster["as_of"] = depth["as_of"] = day

    # -- 3. rotation -----------------------------------------------------------------------------
    def rotation(self, day, data):
        market = Market(day, self.root)
        depth = self.writer.load(signing.TEAM / "Team/Depth_Chart/depth_chart.json")
        scores = dict(camp.prior_values(data, market.valuation, self.root), **(data.get("staff_scores") or {}))
        live = {"players": [p for p in data["players"] if camp.playable(p.get("status")) and p.get("status") != "released"]}
        grades = {g["player"]: g["grade"] for g in read(camp.GRADES, self.root)["players"]}
        rotation = camp.season_rotation(live, depth, scores, day, grades)
        self.writer.files[camp.ROTATION] = rotation
        return rotation

    def write(self, day):
        data = json.loads((self.root / camp.CAMP_ROSTER).read_text(encoding="utf-8"))
        rec = self.record() or {"schema_version": 1, "owner": "ai_gm", "date": day,
                                "purpose": "Camp signings voided because the player was not truly available on the signing date, the refill of the open roster spots, and the new rotation (scripts/correct_camp_signings.py).",
                                "voided": None}
        if rec["voided"] is None:
            rows = self.invalid(data)
            self.void(day, data, rows)
            rec["voided"] = rows
            self.writer.commit()
            signing.note_event(self.writer, camp.CAMP / "note.md", day,
                               "Camp signings corrected: " + ("; ".join(f"{r['player']} voided ({r['reason']})" for r in rows) or "none") +
                               ". Record: `signing_corrections.json`.")
        done = True if rec.get("rotation_written") else self.refill(day, data, rec)
        if done and not rec.get("rotation_written"):
            self.writer.commit()
            rotation = self.rotation(day, data)
            rec["rotation_written"] = day
            r = rec["refill"]
            asked = "; ".join(f"Wade's request for {q['player']}: {q['outcome']}" for q in r["requests"]) or "no request pending"
            signing.note_event(self.writer, camp.CAMP / "note.md", day,
                               f"Roster refill: {r['spots']} open spot(s); signed {', '.join(p['player'] for p in r['picks']) or 'nobody'}. {asked}. "
                               "New rotation: " + ", ".join(f"{p['player_id']} {p['minutes']:g}" for p in rotation["players"]) + ".")
        (self.root / camp.CAMP_ROSTER).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        self.writer.files[RECORD] = rec
        self.writer.commit()
        if done:
            self.writer.commit()
            signing.refresh_finance(self.writer, FrontOffice(day, Market(day, self.root), self.root), day)
            signing.set_state(self.writer, day, area="04_Training_Camp", note="04_Training_Camp/note.md", last_event=f"{day}-camp-signings-corrected")
            self.writer.commit()
        return done


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", required=True, metavar="DATE")
    args = parser.parse_args()
    c = Correction()
    done = c.write(args.write)
    print("correction complete" if done else f"awaiting draws: {', '.join(c.pending)}")
    print(f"Updated {len(refresh_career_views(ROOT))} detailed career views.")


if __name__ == "__main__":
    main()
