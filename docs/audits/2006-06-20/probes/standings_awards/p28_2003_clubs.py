import json, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime import league_cards
from runtime.seasons import conferences as align
reg=json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
byname={p['name']:p for p in reg}
conf={t:c for c,ts in align('2003-04',R).items() for t in ts}
dec=json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/2003-04/award_decisions.json'))['decisions']
n=0
for d in dec:
    for x in d['shortlist']:
        p=byname.get(x['player'])
        if not p: print('no registry',x['player']); continue
        try:
            c=league_cards.club_on(p,d['period_end'],root=R)['club']
        except Exception as e:
            print('err',x['player'],e); continue
        n+=1
        if c!=x['team']: print(d['id'],x['player'],'shown',x['team'],'club_on',c,'conf',conf.get(c),'award conf',d['conference'])
print('checked',n)
