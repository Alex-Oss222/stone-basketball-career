import sys; sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import indep
from pathlib import Path
from runtime import write_back as wb
season = sys.argv[1] if len(sys.argv) > 1 else '2005-06'
root = Path('/home/user/stone-basketball-career')
now = wb.clock(root)
gl, unmatched = wb.closed_lines(root, season, now)
reg = wb.registry(root)
names = {p['registry_id']: p['name'] for p in reg['players']}
gen = {}
for rid, recs in gl.items():
    for r in recs:
        gen[(r['event_id'], r['team'], r['line']['seconds'] if r['line'] else None, r['line']['pts'] if r['line'] else None)] = names[rid]
mine, um = indep.lines(season, rows=indep.results(season, clock=now))
print('clock', now, 'gen unmatched', unmatched, 'mine unmatched', um[:5])
# compare per event/club
diff = 0
from collections import Counter
gcount = Counter((r['event_id'], names[rid]) for rid, recs in gl.items() for r in recs if r['line'] and r['line']['appeared'])
mcount = Counter((r['event'], n) for n, recs in mine.items() for r in recs if r['appeared'])
d1 = gcount - mcount; d2 = mcount - gcount
print('gen-only', len(d1), list(d1.items())[:10]); print('mine-only', len(d2), list(d2.items())[:10])
