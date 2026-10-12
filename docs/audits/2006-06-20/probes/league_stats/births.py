"""Registry birth dates vs every other birth-date source in the repo (by bbr_id)."""
import json, glob
from pathlib import Path
from collections import defaultdict
ROOT = Path('/home/user/stone-basketball-career')
reg = json.loads((ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']
src = defaultdict(set)
def walk(o, path):
    if isinstance(o, dict):
        b = o.get('bbr_id'); d = o.get('birth_date') or o.get('date_of_birth') or o.get('born')
        if isinstance(b, str) and isinstance(d, str) and len(d) == 10 and d[4] == '-':
            src[b].add((d, path))
        for v in o.values(): walk(v, path)
    elif isinstance(o, list):
        for v in o: walk(v, path)
for p in list(ROOT.glob('library/**/*.json')) + list(ROOT.glob('career/Dwyane_Wade/*/00_Team/Team/Roster/roster.json')):
    try: walk(json.loads(p.read_text()), str(p.relative_to(ROOT)))
    except Exception: pass
c = json.loads((ROOT / 'library/careers/nba_player_careers.json').read_text())['players']
for b, e in c.items():
    for k in ('birth_date', 'born', 'date_of_birth'):
        if e.get(k): src[b].add((e[k], 'careers:' + k))
bad = []
for p in reg:
    s = src.get(p['bbr_id'], set())
    others = {d for d, _ in s}
    if others and p['birth_date'] not in others:
        bad.append((p['name'], p['bbr_id'], p['birth_date'], sorted(s)[:3]))
    elif len(others) > 1:
        bad.append(('CONFLICT', p['name'], p['bbr_id'], p['birth_date'], sorted(s)[:4]))
print(len(bad))
for b in bad[:40]: print(b)
print('no other source:', sum(1 for p in reg if not src.get(p['bbr_id'])))
