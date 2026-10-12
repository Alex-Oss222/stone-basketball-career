import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
ROOT='/home/user/stone-basketball-career'
cat = json.load(open(ROOT+'/career/Dwyane_Wade/Contracts/catalog.json'))['players']
truth = pickle.load(open('truth.pkl','rb'))
groups = collections.defaultdict(list)
for p in cat:
    rid = p['player_id']
    if rid not in truth: continue
    club, basis = truth[rid]
    key = ('club' if club else 'FA:' + ('out' if 'out of the league' in basis else 'unsigned'), p['status'], 'cur' if p['current_contract_id'] else 'nocur')
    groups[key].append((rid, p['name'], p['team'], club))
for k in sorted(groups): print(k, len(groups[k]), [x[1] for x in groups[k]][:8])
