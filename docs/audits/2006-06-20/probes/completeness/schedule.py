"""Each closed regular-season result against the season's real schedule: same event id, date, home and away;
every scheduled game closed exactly once; final score equals the sum of player points; period scores sum."""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import results
R = '/home/user/stone-basketball-career/library'
for season, path in (('2003-04', '2003/league/nba_2003_04_schedule.json'), ('2004-05', '2004/league/nba_2004_05_schedule.json'),
                     ('2005-06', '2005/league/nba_2005_06_schedule.json')):
    sched = {g['game_id']: g for g in json.load(open(f'{R}/{path}'))['games']}
    seen = {}
    bad = []
    for p, d, req in results(season, 'regular'):
        e = d['event_id']
        if e in seen:
            bad.append(('DUP', e))
        seen[e] = p
        g = sched.get(e)
        if not g:
            bad.append(('NOT SCHEDULED', e)); continue
        if (g['date'], g['home'], g['away']) != (d['game_date'], d['home'], d['away']):
            bad.append(('DIFF', e, (g['date'], g['home'], g['away']), (d['game_date'], d['home'], d['away'])))
        for side in ('home', 'away'):
            s = sum(x['pts'] for x in d['player_stats'][side])
            if s != d['final_score'][side]:
                bad.append(('PTS SUM', e, side, s, d['final_score'][side]))
            ps = d.get('period_scores', {}).get(side)
            if ps and sum(ps) != d['final_score'][side]:
                bad.append(('PERIOD SUM', e, side, sum(ps), d['final_score'][side]))
            # team stats vs player sums
            ts = d.get('team_stats', {}).get(side, {})
            for k in ('fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'pf'):
                if k in ts and sum(x[k] for x in d['player_stats'][side]) != ts[k]:
                    bad.append(('TEAM SUM', e, side, k)); break
        if d['final_score']['home'] == d['final_score']['away']:
            bad.append(('TIE', e))
        if not d.get('terminated'):
            bad.append(('NOT TERMINATED', e))
    missing = [e for e in sched if e not in seen]
    print(season, 'results', len(seen), 'scheduled', len(sched), 'missing', len(missing), missing[:3], 'issues', len(bad), bad[:8])
