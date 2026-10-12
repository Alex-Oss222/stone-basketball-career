import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import defaultdict
R = Path('/home/user/stone-basketball-career')
from runtime import write_back
from runtime.player_stats import alias
def gs(p):
    return (p['pts'] + 0.4*p['fgm'] - 0.7*p['fga'] - 0.4*(p['fta']-p['ftm']) + 0.7*p['orb'] + 0.3*p['drb']
            + p['stl'] + 0.7*p['ast'] + 0.7*p['blk'] - 0.4*p['pf'] - p['tov'])
ends = {'2003-04': '2004-04-14', '2004-05': '2005-04-20', '2005-06': '2006-04-19'}
for season, names in (('2003-04', ['Dan Dickau']), ('2004-05', ['Kevin Martin', 'Boris Diaw', 'Smush Parker'])):
    rows = write_back.closed_results(R, season=season, now=ends[season])
    acc = defaultdict(lambda: [0, 0.0])
    for row in rows:
        r = row['result']
        for side in ('home', 'away'):
            for p in r['player_stats'][side]:
                if p.get('minutes', 0) > 0:
                    a = acc[alias(p['player_id'])]; a[0] += 1; a[1] += gs(p)
    for n in names:
        g, t = acc[alias(n)]
        print(season, n, 'games', g, 'GS/g', round(t / g, 2) if g else None)
# real 2002-03 rows for these players
for f in ['library/2003/league/nba_2003_end_of_season.json']:
    pass
