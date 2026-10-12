import sys, json, pickle, collections
ROOT='/home/user/stone-basketball-career'
c = pickle.load(open('catalog_full.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
prof = {p['id']: p for p in c['players']}
m = json.load(open(ROOT+'/career/Dwyane_Wade/2005-06/League/league_moves.json'))['entries']
print(collections.Counter(e['kind'] for e in m))
last = {}
for e in sorted(m, key=lambda e: e['date']):
    if e['kind'] in ('ten_day','rest_of_season','minimum','roster_minimum','signing','waiver_claim','rest_of_season_signing') or 'contract' in e:
        last[e['bbr_id']] = e
rows = []
for b, e in last.items():
    p = prof.get(b)
    if not p: continue
    club = truth.get(b, (None,))[0]
    if club != e['to']: continue    # only players still with the signing club on the card date
    cur = p.get('current')
    rows.append((b, p['name'], e['kind'], e['date'], e['to'], p['team'], p['status'], cur['id'] if cur else None, cur.get('team') if cur else None))
print(len(rows))
mismatch = [r for r in rows if r[8] != r[4]]
print('current contract not with signing club:', len(mismatch))
for r in mismatch: print(r)
