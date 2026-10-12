import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime.player_contracts import build_contract_catalog
root = Path('/home/user/stone-basketball-career')
cat = build_contract_catalog(root, root/'career/Dwyane_Wade', '2006-06-20')
byid = {p['id']: p for p in cat['players']}
decs = []
for f in ['2004-05', '2005-06']:
    d = json.load(open(root/f'career/Dwyane_Wade/{f}/League/option_decisions.json'))
    decs += [x for x in d['decisions'] if x.get('applied')]
from collections import Counter
cnt = Counter(); missing = []
for x in decs:
    p = byid.get(x['bbr_id'])
    if not p:
        cnt['no profile'] += 1; continue
    found = None
    for c in p['history']:
        for o in c['options']:
            if o.get('season') == x['option_season']:
                found = o
    key = (x['decision'], 'shown' if found else 'missing', (found or {}).get('outcome'))
    cnt[key] += 1
    if not found and x['decision'] == 'exercise':
        missing.append((x['bbr_id'], x['player'], x['club'], x['option_season'], x['kind']))
print(cnt)
print(len(missing)); print(missing[:15])
print('--- shown samples')
n=0
for x in decs:
    p = byid.get(x['bbr_id'])
    if not p: continue
    for c in p['history']:
        for o in c['options']:
            if o.get('season') == x['option_season']:
                if n < 8:
                    print(x['player'], x['decision'], x['applied'], '| contract', c['id'], c['status'], '| option', o)
                n+=1
