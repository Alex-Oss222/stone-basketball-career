"""Registry position vs every season's real roster position label (first listed slot)."""
import json, glob, re, collections
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
reg = json.loads((ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']
srcs = collections.defaultdict(list)
for path in sorted(ROOT.glob('library/*/league/nba_*_team_rosters.json')):
    d = json.loads(path.read_text())
    for club, c in d['clubs'].items():
        for p in c.get('players', []):
            if p.get('bbr_id') and p.get('position'):
                srcs[p['bbr_id']].append((d.get('season'), club, p['position'], p.get('minutes')))
def slot(l):
    return re.split(r'[-/]', l)[0].strip().upper()
odd = []
for p in reg:
    s = srcs.get(p['bbr_id'])
    if not s: continue
    slots = {slot(x[2]) for x in s}
    if p['position'] not in slots:
        odd.append((p['name'], p['position'], p.get('position_basis'), p['cohort'], sorted({(x[0], x[2]) for x in s})))
print(len(odd))
for o in odd: print(o)
