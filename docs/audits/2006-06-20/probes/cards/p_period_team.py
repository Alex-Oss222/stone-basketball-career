import sys, json, re, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import league_cards
from runtime.league_cards import periods, _read, _code
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
cards = pickle.load(open('cards.pkl','rb'))
lines = pickle.load(open('lines_2005_06.pkl','rb'))
reg = {p['registry_id']: p for p in json.load(open(ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
config = _read(ROOT, 'foundation/season_structure.json')
pers = periods(config, '2005-06', ROOT)
print(len(pers), pers[0].keys())
def code(club, p): return 'MIA' if club == 'Miami Heat' else _code(club, {}, p)
bad_rows = collections.Counter(); players = set(); ex = []
fullname = collections.Counter()
for rid, c in cards.items():
    recs = [r for r in lines.get(rid, []) if (r.get('line') or {}).get('appeared')]
    p = reg[rid]
    for heading, kind in (('### Season','season'),('### Month','month'),('### Week','week')):
        t = next(t for t in c['tables'] if t[0] == heading)
        ps = [x for x in pers if x['kind'] == kind]
        for per, row in zip(ps, t[2]):
            team = row[2]
            if len(team) > 4: fullname[team] += 1
            inper = [r for r in recs if per['start'] <= r['date'] <= per['end']]
            if not inper: continue
            clubs = {code(r['team'], p) for r in inper}
            if team not in clubs:
                bad_rows[kind] += 1; players.add(rid)
                if len(ex) < 15: ex.append((rid, p['name'], per['label'], team, sorted(clubs)))
print('rows whose Team is not a club he played for in that period:', dict(bad_rows), 'players', len(players))
for e in ex: print('  ', e)
print('full names in Team code column:', fullname.most_common(10))
