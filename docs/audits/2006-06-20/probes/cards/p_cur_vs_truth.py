import sys, json, pickle, collections
c = pickle.load(open('catalog_full.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
cats = collections.defaultdict(list)
for p in c['players']:
    if p['id'] not in truth: continue
    club, basis = truth[p['id']]
    cur = p.get('current')
    ct = cur.get('team') if cur else None
    if club and ct == club: cats['ok: current with holder'].append(p['name']); continue
    if club and not cur: cats['holder club, no current contract'].append((p['name'], club, p['status'])); continue
    if club and ct != club: cats['holder club, current contract with another club'].append((p['name'], club, ct, cur['id'])); continue
    if not club and cur: cats['no club (FA/out), current contract shown'].append((p['name'], ct, cur['id'], basis[:30])); continue
    cats['no club, no current'].append(p['name'])
for k, v in cats.items():
    print(k, len(v))
for k in ('holder club, current contract with another club',):
    for x in cats[k]: print('   ', x)
pickle.dump(dict(cats), open('cur_vs_truth.pkl','wb'))
