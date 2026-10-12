import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
ROOT='/home/user/stone-basketball-career'
from runtime.player_contracts import build_contract_catalog
c = build_contract_catalog(ROOT, 'career/Dwyane_Wade')
pickle.dump(c, open('catalog_full.pkl','wb'))
p0 = next(p for p in c['players'] if p['id']=='houstal01')
print(json.dumps({k:v for k,v in p0.items() if k not in ('sources','identity')}, default=str, indent=1)[:4000])
