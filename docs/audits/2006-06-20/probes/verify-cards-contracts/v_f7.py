import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import Counter
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
cat = pickle.load(open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','rb'))
P={p['id']:p for p in cat['players']}
byb={}
for p in cat['players']:
    b=(p.get('identity') or {}).get('bbr_id') or p['id']; byb[b]=p
res=Counter(); detail=[]
for s in ('2004-05','2005-06'):
    for d in json.load(open(f'career/Dwyane_Wade/{s}/League/option_decisions.json'))['decisions']:
        p=byb.get(d['bbr_id']) or P.get(d['bbr_id'])
        if not p: res['no profile']+=1; continue
        opts=[(h['id'],o) for h in p['history'] for o in h['options'] if o.get('season')==d['option_season']]
        if not opts: res[f'{s} option missing']+=1; detail.append((s,d['player'],'missing',d['decision']))
        elif any(o.get('outcome') for _,o in opts):
            ok=any((o.get('outcome') or '').startswith(d['decision'][:4]) for _,o in opts)
            res[f'{s} outcome shown {"match" if ok else "differs"}']+=1
        else: res[f'{s} option listed no outcome']+=1; detail.append((s,d['player'],'no outcome',d['decision']))
print(res)
for x in detail: print(' ',x)
w=P.get('wadedw01') or byb.get('wadedw01')
print('WADE current', w['current']['id'], [(r['season'], r['salary'], r['amount_kind']) for r in w['current']['salary_rows']], w['current']['options'], w['current']['original_term_seasons'])
