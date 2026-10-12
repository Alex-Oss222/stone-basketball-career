"""season_totals.json (written at season close) vs independent aggregation of the same closed regular-season results."""
import sys, json
sys.path.insert(0, '.')
import indep
season = sys.argv[1]
reg = {p['name']: p for p in indep.registry()}
mine, _ = indep.lines(season, rows=indep.results(season))
st = json.loads((indep.LEAGUE / season / 'season_totals.json').read_text())['records']
st = {r['bbr_id']: r for r in st}
exp = {}
for name, recs in mine.items():
    g, gs, t = indep.agg(recs, '0000', '9999')
    if g: exp[reg[name]['bbr_id']] = (name, g, gs, t)
missing = [(v[0], v[1]) for b, v in exp.items() if b not in st]
extra = [b for b in st if b not in exp]
diff = []
for b, (name, g, gs, t) in exp.items():
    if b not in st: continue
    s = st[b]['totals']
    if s['games'] != g or s['points'] != t['pts'] or s['games_started'] != gs or s['field_goals_attempted'] != t['fga']:
        diff.append((name, b, 'file G/GS/PTS/FGA', s['games'], s['games_started'], s['points'], s['field_goals_attempted'], 'results', g, gs, t['pts'], t['fga']))
print('players with appearances', len(exp), 'in file', len(st))
print('missing from file', len(missing), missing[:20])
print('in file but no appearance', extra[:10])
print('differences', len(diff))
for d in diff[:20]: print('  ', d)
