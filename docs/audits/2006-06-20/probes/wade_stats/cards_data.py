import json
from compare import games, CAREER, STATS, age_on
d = json.load(open(CAREER / 'Stats_and_Awards/player_cards_data.json'))
bad = []
for p in d['periods']:
    comp, s, kind = p['competition'], p['season'], p['kind']
    if kind == 'game':
        sel = [g for g in games if g['comp'] == comp and g['event_id'] == p['source_games'][0]['id']]
    else:
        sel = [g for g in games if g['comp'] == comp and g['season'] == s and p['start'] <= g['date'] <= p['end']]
    played = [g for g in sel if g['status'] == 'played']
    missing = any(g['cov'] == 'missing' for g in played)
    ap = [g for g in played if g['cov'] == 'played']
    if p['games'] != len(played): bad.append(('games', p['id'], p['games'], len(played)))
    if missing:
        if p['appearances'] is not None: bad.append(('app-missing', p['id'], p['appearances']))
        continue
    if p['appearances'] != len(ap): bad.append(('app', p['id'], p['appearances'], len(ap)))
    for k in STATS:
        v = sum(g['row'][k] for g in ap)
        if abs((p['box'][k] or 0) - v) > 1e-6: bad.append(('box', p['id'], k, p['box'][k], v))
    if {x['id'] for x in p['source_games']} != {g['event_id'] for g in sel}: bad.append(('src', p['id']))
    ia = p['identity'].get('age')
    if ia is not None and ia != age_on(p['end']): bad.append(('age', p['id'], ia, age_on(p['end'])))
print('periods', len(d['periods']), 'bad', len(bad))
for b in bad[:20]: print(b)
print('identity keys', list(d['periods'][0]['identity'].keys()))
