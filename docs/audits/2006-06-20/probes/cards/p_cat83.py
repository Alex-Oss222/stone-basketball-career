import pickle, json, collections, glob
ROOT='/home/user/stone-basketball-career'
cats = pickle.load(open('cur_vs_truth.pkl','rb'))
c = pickle.load(open('catalog_full.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
prof = {p['name']: p for p in c['players']}
moves = collections.defaultdict(list)
for s in ('2003-04','2004-05','2005-06'):
    try:
        for e in json.load(open(f'{ROOT}/career/Dwyane_Wade/{s}/League/league_moves.json'))['entries']:
            moves[e.get('bbr_id')].append((e['date'], e['kind'], e.get('from'), e.get('to')))
    except FileNotFoundError: pass
reasons = collections.Counter(); ex = collections.defaultdict(list)
for name, ct, cid, basis in cats['no club (FA/out), current contract shown']:
    p = prof[name]; b = p['identity'].get('bbr_id') or p['id']; cur = p['current']
    seasons = sorted(r['season'] for r in cur['salary_rows'] if r['amount_kind'] != 'prior_season_salary_reference')
    last = seasons[-1] if seasons else None
    lm = [m for m in moves.get(b, []) if m[0] >= (cur['signed_on'] or '')]
    if last and last < '2005-06':
        r = f'last recorded salary season {last} (< 2005-06)'
    elif lm:
        r = 'league move after signing: ' + lm[-1][1]
    else:
        r = 'contract runs into 2005-06+, ' + ('out of league' if 'out of' in truth[p['id']][1] else 'unsigned')
    reasons[r] += 1; ex[r].append((name, ct, cid, last))
for r, n in reasons.most_common(): print(n, r, ex[r][:6])
