import pickle, json, collections
ROOT='/home/user/stone-basketball-career'
c = pickle.load(open('catalog_full.pkl','rb'))
by_bbr = {}
for p in c['players']:
    by_bbr[p['identity'].get('bbr_id') or p['id']] = p
by_bbr.setdefault('wadedw01', next(p for p in c['players'] if p['name']=='Dwyane Wade'))
res = collections.Counter(); bad = []
for s in ('2004-05','2005-06'):
    d = json.load(open(f'{ROOT}/career/Dwyane_Wade/{s}/League/option_decisions.json'))
    for x in d['decisions']:
        p = by_bbr.get(x['bbr_id'])
        if not p: res['no profile'] += 1; continue
        shown = [(h['id'], o) for h in p['history'] for o in h['options'] if o.get('season') == x['option_season']]
        if not shown:
            res['option not on page'] += 1; bad.append((s, x['player'], x['club'], x['option_season'], x['kind'], x['decision'], x['applied']))
        elif not any(o.get('outcome') == x['decision'] for _, o in shown):
            res['option shown, outcome missing/different'] += 1; bad.append((s, x['player'], x['option_season'], x['decision'], [o.get('outcome') for _, o in shown]))
        else:
            res['ok'] += 1
print(res)
for b in bad: print(b)
