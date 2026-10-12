"""FIBA 2005 Americas: recompute leaders (>= half team games), MVP/All-Tournament (GmSc/g x finish, >= 3 games),
team box sums, and each player's games against the roster."""
import json, glob, collections
R = '/home/user/stone-basketball-career/career/Dwyane_Wade/FIBA/Continental_Cups/2005'
rec = json.load(open(R + '/tournament.json'))
lines = collections.defaultdict(lambda: collections.defaultdict(float))
team_games = collections.Counter()
gs = lambda p: (p["pts"] + 0.4 * p["fgm"] - 0.7 * p["fga"] - 0.4 * (p["fta"] - p["ftm"]) + 0.7 * p["orb"]
                + 0.3 * p["drb"] + p["stl"] + 0.7 * p["ast"] + 0.7 * p["blk"] - 0.4 * p["pf"] - p["tov"])
off_roster = []
for f in sorted(glob.glob(R + '/Games/*.result.json')):
    res = json.load(open(f))
    for side in ('home', 'away'):
        team = res[side]
        team_games[team] += 1
        ts = res['team_stats'][side]
        for k in ('pts', 'fgm', 'fga', 'ast', 'stl', 'blk', 'tov'):
            s = sum(p[k] for p in res['player_stats'][side])
            if s != ts[k] and k != 'tov':
                print('TEAM SUM', f[-30:], side, k, s, ts[k])
        for p in res['player_stats'][side]:
            if p['player_id'] not in rec['rosters'][team] and p['player_id'] not in [x if isinstance(x, str) else x.get('name') for x in rec['rosters'][team]]:
                off_roster.append((f[-30:], team, p['player_id']))
            if (p.get('seconds') or 0) <= 0:
                continue
            t = lines[(p['player_id'], team)]
            t['g'] += 1; t['gmsc'] += gs(p)
            for k in ('pts', 'ast', 'stl', 'blk'):
                t[k] += p[k]
            t['reb'] += p['orb'] + p['drb']
print('team games', dict(team_games))
print('off roster rows', off_roster[:5], len(off_roster))
for k in ('pts', 'reb', 'ast', 'stl', 'blk'):
    rows = sorted(((n, t, v['g'], v[k] / v['g']) for (n, t), v in lines.items() if v['g'] * 2 >= team_games[t]), key=lambda r: (-r[3], r[0]))[:6]
    print(k, [(n, t, int(g), round(x, 1)) for n, t, g, x in rows])
finish = {'Brazil': 1.0, 'United States': 0.85, 'Dominican Republic': 0.75}
ranked = sorted(((n, t, v) for (n, t), v in lines.items() if v['g'] >= 3), key=lambda r: (-r[2]['gmsc'] / r[2]['g'] * finish.get(r[1], 0.6), r[0]))
for n, t, v in ranked[:10]:
    print('  award', n, t, int(v['g']), round(v['gmsc'] / v['g'], 2), round(v['pts'] / v['g'], 1), round(v['gmsc'] / v['g'] * finish.get(t, 0.6), 3))
print('stored', [(x['player'], x['games'], x['game_score']) for x in rec['awards']['shortlist']])
