#!/usr/bin/env python3
"""Open Wade's rookie-contract negotiation with Miami's first offer (roadmap item 5).

Run only when the career clock reaches the offer date (July 1, 2003 or later):
  python scripts/open_rookie_negotiation.py --write 2003-07-01
Writes career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json.
Later entries (Wade's answers, Miami's responses, the signing) are appended to the same log;
validation checks every entry against the rookie scale and the date order.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.front_office import rookie_offer

LOG = ROOT / "career/Dwyane_Wade/2003-04/01_Free_Agency/Wade_Rookie_Contract/negotiation_log.json"

if len(sys.argv) != 3 or sys.argv[1] != "--write":
    raise SystemExit("Writes career records: run as --write YYYY-MM-DD when the clock reaches the offer date.")
if LOG.exists():
    raise SystemExit("The negotiation is already open; append to the log instead.")
offer = rookie_offer(5)
LOG.parent.mkdir(parents=True, exist_ok=True)
LOG.write_text(json.dumps({
    "player": "Dwyane Wade", "team": "Miami Heat", "pick": 5,
    "agreement": "1999 CBA rookie scale (library/2003/league/nba_1999_cba_rules.json)",
    "entries": [{"date": sys.argv[2], "party": "miami", "action": "offer", "terms": offer["terms"],
                 "note": f"{offer['reason']}. Intended signing timing: {offer['timing']}."}],
}, indent=1) + "\n")
print(f"Opened {LOG.relative_to(ROOT)}")
