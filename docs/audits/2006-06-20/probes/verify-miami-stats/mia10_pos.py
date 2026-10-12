import json, re
from pathlib import Path
R=Path('/home/user/stone-basketball-career'); C=R/'career/Dwyane_Wade'
reg={p.get('bbr_id'):p for p in json.load(open(C/'Stats_and_Awards/League/player_registry.json'))['players'] if p.get('bbr_id')}
for s in ['2005-06']:
    for p in json.load(open(C/s/'00_Team/Team/Roster/roster.json'))['players']:
        r=reg.get(p.get('bbr_id'))
        if r and r.get('position') and p['positions'][0] not in r['position'].replace('-','/').split('/'):
            print(s, p['name'], p['positions'], r['position'], p.get('status'))
# pages count
n=0
for pg in (C/'Stats_and_Awards/Team/2005-06').rglob('Team_Stats.md'):
    if re.search(r'^\| Sebastian Telfair \| SF \|', pg.read_text(), re.M): n+=1
print('team pages with Telfair SF', n)
reqs=[f for f in (C/'2005-06').rglob('*.request.json') if '"Sebastian Telfair"' in f.read_text()]
sf=0
for f in reqs:
    d=json.loads(f.read_text())
    for side in ('home','away'):
        for p in d.get(side,{}).get('players',[]) if isinstance(d.get(side),dict) else []:
            if p.get('player_id')=='Sebastian Telfair' and p.get('position')=='SF': sf+=1
print('requests with Telfair', len(reqs), 'SF lines', sf)
