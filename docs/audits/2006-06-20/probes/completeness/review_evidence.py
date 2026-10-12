"""Fortnightly staff reviews: each review.json's per-player games, minutes and efficiency against Miami's closed
results dated strictly before the review date; and the score formula (prior*300 + eff*30)/(300 + minutes)."""
import glob, json, os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import results
W = '/home/user/stone-basketball-career/career/Dwyane_Wade'
eff = lambda p: p['pts'] + p['orb'] + p['drb'] + p['ast'] + p['stl'] + p['blk'] - (p['fga'] - p['fgm']) - (p['fta'] - p['ftm']) - p['tov']
n = 0; bad = []
for season in ('2003-04', '2004-05', '2005-06'):
    miami = [d for p, d, r in results(season, 'regular') if 'Miami Heat' in (d['home'], d['away'])]
    for rv in sorted(glob.glob(f'{W}/{season}/00_Team/Team/Depth_Chart/Reviews/*/review.json')):
        r = json.load(open(rv))
        on = r['as_of']
        tot = {}
        for d in miami:
            if d['game_date'] >= on:
                continue
            side = 'home' if d['home'] == 'Miami Heat' else 'away'
            for p in d['player_stats'][side]:
                if not (p.get('seconds') or 0) > 0:
                    continue
                t = tot.setdefault(p['player_id'], [0, 0.0, 0])
                t[0] += 1; t[1] += p['seconds'] / 60; t[2] += eff(p)
        for name, ev in r['evidence'].items():
            n += 1
            g, m, e = tot.get(name, [0, 0.0, 0])
            if ev['games'] != g or abs(ev['minutes'] - m) > 0.01 or ev['efficiency'] != e:
                bad.append((season, on, name, (ev['games'], round(ev['minutes'], 2), ev['efficiency']), (g, round(m, 2), e)))
            prior = ev['preseason_estimate']
            score = round((prior * r['prior_minutes'] + ev['efficiency'] * r['score_minutes']) / (r['prior_minutes'] + ev['minutes']), 6)
            if abs(score - ev['score']) > 1e-5 or abs(r['scores'][name] - ev['score']) > 1e-9:
                bad.append(('SCORE', season, on, name, ev['score'], score))
        # players who played for Miami before the review but are on the review's player list without evidence
        listed = {p['player'] for p in r['players']}
        for name in listed - set(r['evidence']):
            bad.append(('NO EVIDENCE', season, on, name))
print('player-review rows', n, 'issues', len(bad))
for b in bad[:30]:
    print(b)
