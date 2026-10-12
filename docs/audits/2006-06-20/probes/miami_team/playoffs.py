"""Miami Team_Playoff_Stats.md pages against Miami's closed playoff results."""
import sys, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *

TEAM = CAREER / 'Stats_and_Awards/Team'


def f1(x):
    return f'{x:.1f}'


def r3(m, a):
    return 'N/A' if not a else f'{m/a:.3f}'.removeprefix('0')


for s in SEASONS:
    games, probs = closed(s, '08_Playoffs', 'playoff')
    if probs:
        print('problems', probs)
    page = TEAM / s / 'Playoffs/Team_Playoff_Stats.md'
    text = page.read_text()
    print('==', s, len(games), 'games;', re.search(r'Through [^:]*: (\d+)', text).group(0))
    # games table
    gl = re.findall(r'^\| (\d{4}-\d{2}-\d{2}) \| (vs|at) ([^|]+) \| ([WL]) (\d+)-(\d+) \|$', text, re.M)
    exp = []
    for g in sorted(games, key=lambda g: g['result']['game_date']):
        r = g['result']; sd = g['side']; o = 'away' if sd == 'home' else 'home'
        fs = r['final_score']
        exp.append((r['game_date'], 'vs' if sd == 'home' else 'at', r[o], 'W' if fs[sd] > fs[o] else 'L', str(fs[sd]), str(fs[o])))
    got = [(a, b, c.strip(), d, e, f) for a, b, c, d, e, f in gl]
    print(' games table match:', got == exp)
    if got != exp:
        for x, y in zip(got, exp):
            if x != y: print('   ', x, y)
    # players
    per = {}
    for g in games:
        for r in g['result']['player_stats'][g['side']]:
            if appeared(r):
                per.setdefault(r['player_id'], []).append(r)
    m = re.search(r'\| Player \| Club \| G \|.*?\n((?:\|.*\|\n)+)', text)
    rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in m.group(1).splitlines()[1:]]
    shown = {r[0]: r for r in rows}
    for name in per:
        if name not in shown:
            print('  missing player', name)
    for name, row in shown.items():
        a = agg(per.get(name, []))
        g = a['g']
        if not g:
            print('  row without games', name, row[:4]); continue
        tsa = 2 * (a['fga'] + 0.44 * a['fta'])
        e = [str(g), str(a['gs']), f1(a['sec']/60/g), f1(a['pts']/g), f1((a['orb']+a['drb'])/g), f1(a['ast']/g), f1(a['stl']/g),
             f1(a['blk']/g), f1(a['tov']/g), f"{a['fgm']}-{a['fga']}", r3(a['fgm'], a['fga']), f"{a['tpm']}-{a['tpa']}", r3(a['tpm'], a['tpa']),
             f"{a['ftm']}-{a['fta']}", r3(a['ftm'], a['fta']), (f'{a["pts"]/tsa:.3f}'.removeprefix('0') if tsa else 'N/A')]
        if row[2:] != e:
            print('  mismatch', name, row[2:], e)
    # team totals
    pts = sum(g['result']['final_score'][g['side']] for g in games)
    pp = sum(r.get('pts', 0) for g in games for r in g['result']['player_stats'][g['side']])
    print(' team pts', pts, 'player pts sum', pp)
    # series
    print(' series rows:', re.findall(r'^\| (First round|Conference semifinals|Conference finals|Finals) \| ([^|]+) \| ([^|]+) \|$', text, re.M))
