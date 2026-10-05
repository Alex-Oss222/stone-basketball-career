"""Import every player's real All-Star selections before the career began (1985 through 2003).

Fans voted All-Star starters largely on reputation, and a player's past selections were public knowledge on the career
date, so they are evidence the simulated fan ballot may read (`runtime/all_star.py`). Only games played before June
26, 2003 are imported; nothing after it is read.

A selection is a player on a conference roster (Basketball-Reference's East/West tables) or a selected player who did
not play through injury (its notes: "Did not play due to injury"). Starters are the five listed first. There was no
game in 1999 (lockout). Selections before 1985 are not imported: they reach only players who had left the league by
2003-04 or whose later selections already mark them.

Usage: python scripts/import_all_star_history.py [--cache DIR] [--write]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "library/2003/league/nba_all_star_history_1985_2003.json"
YEARS = [y for y in range(1985, 2004) if y != 1999]
URL = "https://www.basketball-reference.com/allstar/NBA_{year}.html"


def fetch(year, cache):
    path = Path(cache) / f"NBA_{year}.html" if cache else None
    if path and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    import ssl
    ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
    req = urllib.request.Request(URL.format(year=year), headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, context=ctx, timeout=60).read().decode("utf-8", errors="replace")
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    time.sleep(4)
    return html


def parse(html):
    """[(bbr_id, conference, starter, played)] for one game."""
    out = []
    for conf in ("East", "West"):
        i = html.find(f'id="{conf}"')
        if i < 0:
            raise ValueError(f"no {conf} table")
        seg = html[i:html.index("</table>", i)]
        ids = list(dict.fromkeys(re.findall(r'data-append-csv="([a-z0-9]+)"', seg)
                                 or re.findall(r"/players/[a-z]/([a-z0-9]+)\.html", seg)))
        out += [(b, conf, n < 5, True) for n, b in enumerate(ids)]
    seen = {b for b, *_ in out}
    text = html.replace("\n", " ")
    for m in re.finditer(r'/players/[a-z]/([a-z0-9]+)\.html">[^<]*</a>\s*\((East|West)\):\s*Did not play due to injury', text):
        if m.group(1) not in seen:
            out.append((m.group(1), m.group(2), False, False))
            seen.add(m.group(1))
    return out


def build(cache=None):
    players = {}
    for year in YEARS:
        for bbr, conf, starter, played in parse(fetch(year, cache)):
            p = players.setdefault(bbr, {"bbr_id": bbr, "selections": 0, "starts": 0, "years": []})
            p["selections"] += 1
            p["starts"] += starter
            p["years"].append(year)
    return {"schema_version": 1, "kind": "all_star_history", "through": "2003-02-09",
            "years": YEARS, "rule": __doc__.split("\n\n")[1].replace("\n", " ") + " " + __doc__.split("\n\n")[2].replace("\n", " "),
            "source": URL.format(year="<year>"),
            "players": sorted(players.values(), key=lambda p: p["bbr_id"])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    data = build(args.cache)
    if args.write:
        OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data['players'])} players, {sum(p['selections'] for p in data['players'])} selections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
