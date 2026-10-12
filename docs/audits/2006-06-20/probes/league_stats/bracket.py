"""playoffs.json series games/wins vs closed playoff results; Playoffs.md game lines vs results."""
import sys, json, re
sys.path.insert(0, '.')
import indep
season = sys.argv[1]
ROOT = indep.ROOT; LEAGUE = indep.LEAGUE
res = {}
for p in (LEAGUE / season / 'Playoffs/Games').glob('*.result.json'):
    r = json.loads(p.read_text()); res[r['event_id']] = r
for note in (ROOT / f'career/Dwyane_Wade/{season}/08_Playoffs').rglob('Game_*.result.json'):
    r = json.loads(note.read_text()); res[r['event_id']] = r
rec = json.loads((LEAGUE / season / 'playoffs.json').read_text())
probs = []
for s in rec['series']:
    wins = {c: 0 for c in s['clubs']}
    for g in s['games']:
        r = res.get(g.get('event_id'))
        if g.get('result'):
            if not r: probs.append(('no result file', s['id'], g['game'])); continue
            fs = r['final_score']; w = r['home'] if fs['home'] > fs['away'] else r['away']
            wins[w] += 1
            label = f"{r['away']} {fs['away']}, {r['home']} {fs['home']}"
            if g['result'] != label or g['winner'] != w or g['date'] != r['game_date'] or g['home'] != r['home']:
                probs.append(('game mismatch', s['id'], g['game'], g['result'], label))
        elif r:
            probs.append(('result exists but game open', s['id'], g['game']))
    if wins != s['wins']: probs.append(('wins', s['id'], s['wins'], wins))
    if s.get('winner') and max(wins.values()) != 4: probs.append(('winner without 4', s['id']))
print(season, 'series', len(rec['series']), 'problems', probs[:10])
page = (LEAGUE / season / 'Playoffs.md').read_text()
print('champion', rec['champion'])
