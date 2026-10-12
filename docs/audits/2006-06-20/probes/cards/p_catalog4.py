import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
c = pickle.load(open('catalog_full.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
ended = []
for p in c['players']:
    cur = p.get('current')
    if not cur: continue
    seasons = [r['season'] for r in cur['salary_rows'] if r['amount_kind'] != 'prior_season_salary_reference' and r.get('salary') is not None or r['amount_kind'] in ('contract_salary','team_option','player_option') ]
    seasons = sorted(set(r['season'] for r in cur['salary_rows'] if r['amount_kind'] != 'prior_season_salary_reference'))
    last = cur.get('end_season') or (seasons[-1] if seasons else None)
    if last and last < '2005-06':
        ended.append((p['id'], p['name'], p['team'], cur['id'], cur['status'], cur.get('team'), last, cur.get('expiry_date'), (truth.get(p['id']) or (None,''))[0]))
print(len(ended))
for e in ended: print(e)
