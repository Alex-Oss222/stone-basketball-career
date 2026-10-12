import json, collections
R='/home/user/stone-basketball-career'
rows=json.load(open('id04_rows.json'))
ids={r[0] for r in rows}-{'fosteje01','artesro01','mariosh01'}
print(len(ids))
mv=json.load(open(f'{R}/career/Dwyane_Wade/2005-06/League/league_moves.json'))['entries']
hit=collections.defaultdict(list)
for e in mv:
    if e.get('bbr_id') in ids: hit[e['bbr_id']].append((e['date'],e['kind'],e.get('to'),(e.get('contract') or {}).get('until')))
signers={k:v for k,v in hit.items() if any(x[1] in('ten_day','rest_of_season','claim') for x in v)}
print('with 2005-06 in-season deals', len(signers))
for k,v in sorted(signers.items()): print(k, v[-3:])
