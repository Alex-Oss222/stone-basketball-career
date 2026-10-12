import json, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
R='/home/user/stone-basketball-career'
from runtime import club_truth
reg=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))
reg=reg['players'] if isinstance(reg,dict) else reg
n2b={p['name']:p.get('bbr_id') for p in reg}
for s in ['2004-05','2005-06']:
    sa=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    n=0
    for x in sa['decisions']:
        if x['award'] in ('coy',): continue
        people=list(x.get('tally') or [])+[p for t in x.get('teams') or [] for p in t['players']]+list(x.get('others') or [])
        on=x['evidence_through']
        for p in people:
            b=n2b.get(p['player'])
            h=club_truth.holder(b,p['player'],on,R)[0]
            n+=1
            if h!=p['team']: print(s,x['award'],p['player'],'shown',p['team'],'holder on',on,h)
    print(s,'checked',n)
