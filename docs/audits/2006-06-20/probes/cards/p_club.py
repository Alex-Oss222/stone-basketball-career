import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import club_truth
cards = pickle.load(open('cards.pkl', 'rb'))
reg = {p['registry_id']: p for p in json.load(open('/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
dates = collections.Counter(c['date'] for c in cards.values()); print(dates)
on = '2006-06-20'
mism = []
truth = {}
for rid, c in cards.items():
    p = reg[rid]
    club, basis = club_truth.holder(p.get('bbr_id'), p['name'], on)
    truth[rid] = (club, basis)
    lab = c['label']
    exp = 'Free agent' if club is None else club
    if lab != exp:
        mism.append((rid, p['name'], lab, exp, basis))
print('club mismatches', len(mism))
for x in mism[:30]: print(x)
pickle.dump(truth, open('truth.pkl','wb'))
print(collections.Counter('FA' if v[0] is None else 'club' for v in truth.values()))
