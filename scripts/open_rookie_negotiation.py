#!/usr/bin/env python3
"""Open Wade's rookie-contract negotiation with Miami's first offer (roadmap item 5).

Run only when the career clock reaches the offer date (July 1, 2003 or later):
  python scripts/open_rookie_negotiation.py --write 2003-07-01
Writes career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json.
Later entries (Wade's answers, Miami's responses, the signing) are appended to the same log;
validation checks every entry against the rookie scale and the date order.
"""
import json
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.front_office import rookie_offer
from runtime import signing
from scripts.refresh_career_views import refresh_career_views

LOG = Path("career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json")


def open_negotiation(day, root=ROOT):
    """Record the first offer on the reached career date, leaving Wade's answer open."""
    root = Path(root)
    date.fromisoformat(day)
    state = json.loads((root / signing.STATE).read_text(encoding="utf-8"))
    if day < "2003-07-01":
        raise ValueError("The rookie offer cannot open before July 1, 2003.")
    if day != state["current_date"]:
        raise ValueError("The offer date must match the current career date; this command does not advance time.")
    if (root / LOG).exists():
        raise ValueError("The negotiation is already open; append the player's answer to the existing log.")
    if state.get("contract_status") != "draft_rights_unsigned":
        raise ValueError("The rookie offer requires Wade's unsigned draft-rights state.")
    offer = rookie_offer(5)
    writer = signing.Writer(root)
    writer.files[LOG] = {
        "player": "Dwyane Wade", "team": "Miami Heat", "pick": 5,
        "agreement": "1999 CBA rookie scale (library/2003/league/nba_1999_cba_rules.json)",
        "entries": [{"date": day, "party": "miami", "action": "offer", "terms": offer["terms"],
                     "note": f"{offer['reason']}. Intended signing timing: {offer['timing']}."}],
    }
    writer.files[signing.STATE] = state
    if "rookie_contract_offer" not in state.setdefault("pending_player_decisions", []):
        state["pending_player_decisions"].append("rookie_contract_offer")
    signing.note_event(writer, LOG.parent.parent / "note.md", day,
                       f"Miami offers Wade his rookie contract at {offer['terms']['percent_of_scale']}% of scale. "
                       "Wade's response is pending in `Wade_Rookie_Contract/negotiation_log.json`; "
                       "[open the detailed negotiation](../../Milestones/index.html#contract_negotiation).")
    (root / LOG).parent.mkdir(parents=True, exist_ok=True)
    writer.commit()
    return root / LOG


def main(argv=None, root=ROOT):
    argv = sys.argv if argv is None else argv
    if len(argv) != 3 or argv[1] != "--write":
        raise SystemExit("Writes career records: run as --write YYYY-MM-DD when the clock reaches the offer date.")
    try:
        path = open_negotiation(argv[2], root)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    refreshed = refresh_career_views(root)
    print(f"Opened {path.relative_to(root)}")
    print(f"Updated {len(refreshed)} detailed career views; open career/Dwyane_Wade/Milestones/index.html#contract_negotiation.")


if __name__ == "__main__":
    main()
