import sys, json, collections
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime import player_contracts as pc
R='/home/user/stone-basketball-career'
cat=pc.build_contract_catalog(R, 'career/Dwyane_Wade')
ps=cat['players']; print(len(ps), cat['as_of'])
undert={'under contract','under contract unverified','minimum contract unverified','under rookie contract','under contract guarantee amended'}
sel=[p for p in ps if p['status'] in undert and p['current'] is None]
print('under-type & no current:', len(sel), collections.Counter(p['status'] for p in sel))
# salary evidence for 2005-06+ and 2006-07+
led={}
for s in ('2004-05','2005-06'):
    for c in json.load(open(f'{R}/career/Dwyane_Wade/{s}/League/contracts.json'))['contracts']:
        led.setdefault(c.get('bbr_id'),[]).append((s,c))
inv=json.load(open(R+'/library/2003/league/nba_2003_contracts.json'))
print(list(inv.keys())[:8])
