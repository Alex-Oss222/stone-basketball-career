import sys, json, re, os
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import defaultdict
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
reg = json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
CARDS = ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/Players'
by=defaultdict(list)
for p in reg:
    t=(CARDS/f"{p['registry_id']}.md").read_text()
    j=re.search(r'\*\*Jersey:\*\* ([^·]+)', t).group(1).strip()
    club=re.search(r'\*\*Club on this date:\*\* ([^·]+)', t).group(1).strip()
    if club=='Free agent' or '(draft rights)' in club or j=='Unassigned': continue
    by[(club,j)].append(p['name'])
d={k:v for k,v in by.items() if len(v)>1}
clubs={k[0] for k in d}
print(len(d), sum(len(v) for v in d.values()), len(clubs), 'miami' , [k for k in d if k[0]=='Miami Heat'])
for k in sorted(d)[:60]: print(k, d[k])
