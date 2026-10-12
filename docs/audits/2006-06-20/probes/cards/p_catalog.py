import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import club_truth
ROOT='/home/user/stone-basketball-career'
cat = json.load(open(ROOT+'/career/Dwyane_Wade/Contracts/catalog.json'))['players']
reg = {p['registry_id']: p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
truth = pickle.load(open('truth.pkl','rb'))
print('catalog', len(cat), 'not in registry:', [(p['player_id'], p['name'], p['team'], p['status']) for p in cat if p['player_id'] not in reg])
mism = []
for p in cat:
    rid = p['player_id']
    if rid not in truth: continue
    club = truth[rid][0] or 'Free agent'
    if p['team'] != club:
        mism.append((rid, p['name'], p['team'], club, truth[rid][1][:80], p['status']))
print('team mismatches', len(mism))
for m in mism: print(m)
st = collections.Counter(p['status'] for p in cat)
print(st.most_common(40))
