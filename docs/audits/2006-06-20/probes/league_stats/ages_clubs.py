"""Age column vs registry birth date at min(page end, clock); club column vs runtime.club_truth.holder at the same date;
header counts vs rows."""
import sys, re, json
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import parse_pages, indep
from compare_pages_lib import scope
from pathlib import Path
from datetime import date
from collections import Counter, defaultdict
season = sys.argv[1]; clock = '2006-06-20'
LEAGUE = indep.LEAGUE
reg = indep.registry()
birth = {p['name']: p.get('birth_date') for p in reg}
def age(b, on):
    b = date.fromisoformat(b); d = date.fromisoformat(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))
bad = []
hdr = []
for page in sorted((LEAGUE / season).rglob('League_Stats.md')):
    if 'Playoffs' in page.parts: continue
    s, e = scope(page, season)
    on = min(e, clock)
    text, groups = parse_pages.parse(page)
    n = 0
    for pos, gd in groups.items():
        m = re.match(r'.* · (\d+) players', gd['summary'])
        if m and int(m.group(1)) != len(gd['rows']):
            hdr.append((str(page.relative_to(LEAGUE)), pos, m.group(1), len(gd['rows'])))
        for row in gd['rows']:
            n += 1
            exp = str(age(birth[row['name']], on)) if birth.get(row['name']) else 'N/A'
            if row['Age'] != exp:
                bad.append((str(page.relative_to(LEAGUE)), row['name'], row['Age'], exp, on))
    m = re.search(r'^(\d+) tracked players', text, re.M)
    if m and int(m.group(1)) != n:
        hdr.append((str(page.relative_to(LEAGUE)), 'header', m.group(1), n))
print('age mismatches', len(bad)); [print('  ', b) for b in bad[:20]]
print('header/summary count mismatches', len(hdr)); [print('  ', h) for h in hdr[:8]]
