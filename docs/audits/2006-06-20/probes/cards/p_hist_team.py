import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import write_back
from runtime.league_cards import _code
ROOT='/home/user/stone-basketball-career'
reg = {p['registry_id']: p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
def code(club, p): return 'MIA' if club == 'Miami Heat' else _code(club, {}, p)
lines25 = pickle.load(open('lines_2005_06.pkl','rb'))
for season in ('2003-04', '2004-05', '2005-06'):
    if season == '2005-06':
        lines = lines25
        cards = pickle.load(open('cards.pkl','rb'))
        rows = {}
        for rid, c in cards.items():
            t = next(t for t in c['tables'] if t[0] == '## Regular-season statistics by year')
            for r in t[2]:
                if r[0] == '2005-06': rows[rid] = r
    else:
        lines, _ = write_back.closed_lines(season=season)
        pickle.dump(lines, open(f'lines_{season}.pkl','wb'))
        cl = json.load(open(f'{ROOT}/career/Dwyane_Wade/Stats_and_Awards/League/{season}/card_lines.json'))['players']
        rows = {k: v['regular'] for k, v in cl.items() if 'regular' in v}
    multi = 0; wrong = 0; ex = []
    for rid, row in rows.items():
        p = reg.get(rid)
        recs = [r for r in lines.get(rid, []) if (r.get('line') or {}).get('appeared')]
        g = collections.Counter(code(r['team'], p) for r in recs)
        if len(g) > 1:
            multi += 1
            if len(ex) < 6: ex.append((rid, row[1], dict(g)))
        elif g and row[1] not in g:
            wrong += 1
            if len(ex) < 12: ex.append(('WRONG', rid, row[1], dict(g)))
    print(season, 'rows', len(rows), 'multi-club rows showing one club:', multi, 'single-club rows naming another club:', wrong)
    for e in ex: print('   ', e)
