import pickle
c = pickle.load(open('catalog_full.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
n = 0
for p in c['players']:
    for h in p['history']:
        ah = h.get('assignment_history') or []
        if not ah: continue
        latest = max(ah, key=lambda a: a['date'])
        if latest['to'] != h['team']:
            n += 1
            print(p['id'], p['name'], h['id'], 'contract team:', h['team'], '| latest assignment:', latest['date'], latest['to'], '| current?', p['current'] and p['current']['id'] == h['id'], '| holder:', truth.get(p['id'], (None,))[0])
print(n)
