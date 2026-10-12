import pickle, collections
c = pickle.load(open('catalog_full.pkl','rb'))
CLOSED = ('voided','released','waived','traded','free_agent_expiring','expired_or_unresolved','renounced','team_option_declined','player_option_declined')
out = []
for p in c['players']:
    hs = [h for h in p['history'] if h['status'] not in CLOSED]
    for i in range(len(hs)):
        for j in range(i+1, len(hs)):
            a = {r['season'] for r in hs[i]['salary_rows'] if r['amount_kind'] != 'prior_season_salary_reference'}
            b = {r['season'] for r in hs[j]['salary_rows'] if r['amount_kind'] != 'prior_season_salary_reference'}
            ov = sorted(x for x in a & b if x >= '2005-06')
            if ov:
                out.append((p['name'], p['team'], hs[i]['id'], hs[i]['status'], hs[j]['id'], hs[j]['status'], ov, p['current']['id'] if p['current'] else None))
print(len(out))
for o in out: print(o)
