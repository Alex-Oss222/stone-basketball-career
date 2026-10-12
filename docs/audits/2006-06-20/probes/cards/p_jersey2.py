import sys, json, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import jerseys
ROOT='/home/user/stone-basketball-career'
cards = pickle.load(open('cards.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
reg = json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
rows = []
for p in reg:
    if p.get('bbr_id') and p['registry_id'] != p['bbr_id']:
        club = truth[p['registry_id']][0]
        if not club: continue
        by_bbr = jerseys.number_for(p['bbr_id'], club, ROOT)
        shown = cards[p['registry_id']]['jersey']
        rows.append((p['registry_id'], p['name'], club, shown, by_bbr))
wrong = [r for r in rows if r[4] and r[3] != '#' + str(r[4])]
print('registry_id != bbr_id with a club:', len(rows), '; card number differs from number_for(bbr_id):', len(wrong))
for r in wrong: print('  ', r)
