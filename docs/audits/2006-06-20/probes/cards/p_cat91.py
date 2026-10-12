import pickle, json, collections, glob
ROOT='/home/user/stone-basketball-career'
cats = pickle.load(open('cur_vs_truth.pkl','rb'))
c = pickle.load(open('catalog_full.pkl','rb'))
prof = {p['name']: p for p in c['players']}
moves = collections.defaultdict(list)
for s in ('2003-04','2004-05','2005-06'):
    try:
        for e in json.load(open(f'{ROOT}/career/Dwyane_Wade/{s}/League/league_moves.json'))['entries']:
            moves[e.get('bbr_id')].append((e['date'], e['kind'], e.get('from'), e.get('to')))
    except FileNotFoundError: pass
mk = collections.defaultdict(list)
for f in sorted(glob.glob(f'{ROOT}/career/Dwyane_Wade/*/10_Free_Agency/free_agency_*.json')):
    for e in json.load(open(f))['events']:
        mk[e.get('bbr_id')].append((e['date'], e['kind'], e.get('from'), e.get('club')))
reasons = collections.Counter()
ex = collections.defaultdict(list)
for name, holder, ct, cid in cats['holder club, current contract with another club']:
    p = prof[name]; b = p['identity'].get('bbr_id') or p['id']
    signed = p['current']['signed_on'] or ''
    lm = [m for m in moves.get(b, []) if m[0] >= signed]
    if ct and ct.replace('New Orleans Hornets','New Orleans/Oklahoma City Hornets') == holder:
        r = 'club renamed only'
    elif lm:
        r = 'in-season league move after signing: ' + lm[-1][1]
    else:
        later_mk = [m for m in mk.get(b, []) if m[0] >= signed]
        r = 'summer market after signing: ' + later_mk[-1][1] if later_mk else 'other'
    reasons[r] += 1; ex[r].append((name, holder, ct, cid))
for r, n in reasons.most_common(): print(n, r, ex[r][:4])
