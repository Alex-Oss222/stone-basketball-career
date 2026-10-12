import sys, json, collections
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime import player_contracts as pc
R='/home/user/stone-basketball-career'
cat=pc.build_contract_catalog(R, 'career/Dwyane_Wade')
ps=cat['players']
print(collections.Counter(p['status'] for p in ps).most_common(12))
d=[p for p in ps if p['id']=='divacvl01'][0]
print(d['status'], d['current'], d['control']['status'])
