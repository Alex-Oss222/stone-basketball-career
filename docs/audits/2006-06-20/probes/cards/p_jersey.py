import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import jerseys
ROOT='/home/user/stone-basketball-career'
cards = pickle.load(open('cards.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
reg = {p['registry_id']: p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
J = json.load(open(ROOT+'/library/2005/league/nba_2005_06_jerseys.json'))['players']
byclub = collections.defaultdict(list)
stats = collections.Counter(); ex = collections.defaultdict(list)
for rid, c in cards.items():
    club = truth[rid][0]
    j = c['jersey']
    if club: byclub[club].append((j, rid, reg[rid]['name']))
    real = [r for r in J.get(reg[rid].get('bbr_id') or '', []) if r['club'] == club]
    if club and club != 'Miami Heat':
        if real:
            want = '#' + real[-1]['number'].split(',')[-1].strip()
            if j != want: stats['non-Miami: differs from real number with this club'] += 1; ex['diff'].append((rid, club, j, want))
            else: stats['ok real'] += 1
        else:
            stats['non-Miami: no real number with this club'] += 1; ex['noreal'].append((rid, reg[rid]['name'], club, j))
mia = jerseys.miami_numbers(ROOT)
print('miami register numbers', mia)
for j, rid, name in byclub['Miami Heat']:
    want = mia.get(name)
    print('  MIA', name, j, 'register:', want)
print(stats)
print('diff examples', ex['diff'][:10])
dups = {}
for club, lst in byclub.items():
    cnt = collections.Counter(j for j, _, _ in lst if j and j != 'Unassigned')
    d = {k: [n for jj, _, n in lst if jj == k] for k, v in cnt.items() if v > 1}
    if d: dups[club] = d
print('clubs with duplicate card numbers', len(dups), sum(len(v) for v in dups.values()))
for k, v in dups.items(): print('  ', k, v)
pickle.dump(ex['noreal'], open('noreal.pkl','wb'))
print('no real number examples', len(ex['noreal']), ex['noreal'][:10])
