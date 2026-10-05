#!/usr/bin/env python3
"""Import a season's salary list (Patricia Bender's, from the NBA rosters of a date in that season) as world data.

    python scripts/import_salaries.py --season 2004-05 --write

Writes `library/<start>/league/nba_<YYYY>_<YY>_salaries.json`: per club, each player's listed salary, its note
(minimum, released, prorated) and his Basketball-Reference id where the name matches the registry, the season's real
rosters or the 2004 offseason files. Use is restricted by AGENTS.md: a later source may reconstruct the term of a
contract that already existed, never reveal a later choice. `runtime/contract_terms.py` therefore reads a 2004-05
salary only for a player who did not sign, re-sign, receive an offer sheet or sign his rookie contract in the 2004
offseason, and never for an option year.
"""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
URLS = {"2004-05": "https://www.eskimo.com/~pbender/misc/salaries05.txt"}
ALIASES = {"Portland Trailblazers": "Portland Trail Blazers", "Seattle Sonics": "Seattle SuperSonics"}
SPELLING = {"Chris Jeffries": "Chris Jefferies", "Aleksandar Pavlovic": "Sasha Pavlovic", "Dorrell Wright": "Dorell Wright",
            "Maurice Williams": "Mo Williams", "Amare Stoudemire": "Amar'e Stoudemire", "DJ Mbenga": "D.J. Mbenga"}


def name_index(root=ROOT):
    from runtime.player_stats import alias
    out = {}
    registry = json.loads((root / "career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json").read_text(encoding="utf-8"))
    for p in registry["players"] if isinstance(registry, dict) else registry:
        if p.get("bbr_id"):
            out.setdefault(alias(p["name"]), p["bbr_id"])
    for season_dir, name in (("2003", "nba_2003_04_team_rosters.json"), ("2004", "nba_2004_05_team_rosters.json")):
        for club in json.loads((root / f"library/{season_dir}/league/{name}").read_text(encoding="utf-8"))["clubs"].values():
            for p in club["players"]:
                if p.get("bbr_id"):
                    out.setdefault(alias(p["player_id"]), p["bbr_id"])
    for rel in ("library/2004/league/nba_2004_prospect_evidence.json",):
        data = json.loads((root / rel).read_text(encoding="utf-8"))
        for p in data["players_drafted"] + data["undrafted_candidates"]["players"]:
            if p.get("bbr_id"):
                out.setdefault(alias(p["player_id"]), p["bbr_id"])
    return out


def parse(text):
    clubs, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^(\S[\w .]+?)\s+Total: \$([\d,]+)\s*$", line)
        if m:
            current = ALIASES.get(m.group(1).strip(), m.group(1).strip())
            clubs[current] = {"listed_total": int(m.group(2).replace(",", "")), "players": []}
            continue
        m = re.match(r"^\s+(.+?)\s*\.{2,}\s*\$([\d,]+)\s*(\[(.*)\])?\s*$", line)
        if m and current:
            clubs[current]["players"].append({"player": m.group(1).strip(), "salary": int(m.group(2).replace(",", "")),
                                              "note": (m.group(4) or "").strip() or None})
    return clubs


def main():
    from runtime.player_stats import alias
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--season", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    with urlopen(URLS[args.season], timeout=60) as r:
        text = r.read().decode("latin-1")
    clubs = parse(text)
    index = name_index()
    unmatched = 0
    for club in clubs.values():
        for p in club["players"]:
            p["bbr_id"] = index.get(alias(SPELLING.get(p["player"], p["player"])))
            unmatched += p["bbr_id"] is None
    start = int(args.season[:4])
    data = {"schema_version": 1, "league": "NBA", "kind": "season_salaries", "season": args.season,
            "source": URLS[args.season], "source_basis": text.strip().splitlines()[2].strip() if len(text.splitlines()) > 2 else None,
            "use": __doc__.split("\n\n", 2)[2].strip(), "clubs": clubs}
    path = ROOT / f"library/{start}/league/nba_{start}_{str(start + 1)[-2:]}_salaries.json"
    print(f"{sum(len(c['players']) for c in clubs.values())} rows, {len(clubs)} clubs, {unmatched} without an id")
    if args.write:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"written {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
