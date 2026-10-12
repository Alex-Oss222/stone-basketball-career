import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
from runtime.player_contracts import build_contract_catalog
cat = build_contract_catalog(ROOT, 'career/Dwyane_Wade')
pickle.dump(cat, open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','wb'))
print(cat['as_of'], len(cat['players']))
# compare with on-disk catalog summary
disk = json.load(open('career/Dwyane_Wade/Contracts/catalog.json'))
dd = {p['player_id']:p for p in disk['players']}
diff=0
for p in cat['players']:
    d=dd.get(p['id'])
    cur = p['current']['id'] if p['current'] else None
    if not d or d['team']!=p['team'] or d['current_contract_id']!=cur: diff+=1
print('diff vs disk', diff)
