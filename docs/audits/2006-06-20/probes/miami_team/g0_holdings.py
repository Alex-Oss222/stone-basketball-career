"""For every G=0 row on a Miami Team_Stats.md page, check whether Miami held the player at any time in the page's
period (holdings.json, non-void) and whether that holding was a contract or rights only (register status)."""
import sys, re, json, ast
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from collect import *

TEAM = CAREER / 'Stats_and_Awards/Team'
out = defaultdict(list)
for season in SEASONS:
    hold = json.loads((CAREER / season / '00_Team/Team/Roster/holdings.json').read_text())['entries']
    reg = {p['name']: p for p in json.loads((CAREER / season / '00_Team/Team/Roster/roster.json').read_text())['players']}
    for page in sorted((TEAM / season).rglob('Team_Stats.md')):
        start, end = scope_of_page(page.relative_to(TEAM / season), season)
        text = page.read_text()
        m = re.search(r'\| Player \| Pos \| G \|.*?\n((?:\|.*\|\n)+)', text)
        rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in m.group(1).splitlines()[1:]]
        for r in rows:
            if r[2] != '0':
                continue
            name = r[0]
            ivs = [(e['from'], e['until']) for e in hold if e['player'] == name and not e.get('void')]
            overlap = [iv for iv in ivs if iv[0] <= end and (iv[1] is None or iv[1] > start)]
            status = reg.get(name, {}).get('status')
            out[(season, name, status, tuple(ivs))].append((str(page.relative_to(TEAM / season).parent), bool(overlap)))
for k, v in sorted(out.items()):
    bad = [p for p, ok in v if not ok]
    print(k, 'pages', len(v), 'not-held pages', len(bad), bad[:40])
