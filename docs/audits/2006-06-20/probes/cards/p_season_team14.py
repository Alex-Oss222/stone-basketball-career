import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.league_cards import _code
ROOT='/home/user/stone-basketball-career'
cards = pickle.load(open('cards.pkl','rb'))
lines = pickle.load(open('lines_2005_06.pkl','rb'))
reg = {p['registry_id']: p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
code = lambda c, p: 'MIA' if c == 'Miami Heat' else _code(c, {}, p)
for rid, c in cards.items():
    t = next(t for t in c['tables'] if t[0] == '### Season')
    team = t[2][0][2]
    g = collections.Counter(code(r['team'], reg[rid]) for r in lines.get(rid, []) if (r.get('line') or {}).get('appeared'))
    if g and team not in g:
        print(rid, reg[rid]['name'], 'card Team:', team, '| played for:', dict(g))
