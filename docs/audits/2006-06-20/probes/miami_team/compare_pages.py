"""Recompute every Miami Team_Stats.md page (regular season) from closed results and compare with disk."""
import sys, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *

TEAM = CAREER / 'Stats_and_Awards/Team'


def parse_tables(text):
    tables = []
    for m in re.finditer(r'(?:^\|[^\n]*\|\n)+', text, re.M):
        lines = m.group(0).strip('\n').splitlines()
        rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in lines]
        tables.append((rows[0], rows[2:]))
    return tables


def f1(x):
    return 'N/A' if x is None else f'{x:.1f}'


def r3(x):
    return 'N/A' if x is None else f'{x:.3f}'.removeprefix('0')


def expected_rows(games, start, end):
    per = {}
    team = []
    for g in games:
        d = g['result']['game_date']
        if not (start <= d <= end):
            continue
        team.append(g)
        for r in g['result']['player_stats'][g['side']]:
            per.setdefault(r['player_id'], [])
            if appeared(r):
                per[r['player_id']].append(r)
        for pid in g['result'].get('inactive', {}).get(g['side'], []):
            per.setdefault(pid, [])
    return per, team


def team_record(team):
    if not team:
        return ['0', '0', '0', 'N/A', 'N/A', 'N/A', 'N/A']
    w = 0; pts = opp = 0
    for g in team:
        s = g['side']; o = 'away' if s == 'home' else 'home'
        fs = g['result']['final_score']
        w += fs[s] > fs[o]; pts += fs[s]; opp += fs[o]
    n = len(team)
    return [str(n), str(w), str(n - w), r3(w / n), f1(pts / n), f1(opp / n), f'{(pts-opp)/n:+.1f}']


issues = []
summary = {}
for season in SEASONS:
    games_, probs = closed(season)
    for p in probs:
        issues.append(('closed-problem', season, p))
    for page in sorted((TEAM / season).rglob('Team_Stats.md')):
        start, end = scope_of_page(page.relative_to(TEAM / season), season)
        per, team = expected_rows(games_, start, end)
        text = page.read_text(encoding='utf-8')
        tables = parse_tables(text)
        rel = page.relative_to(CAREER)
        for headers, rows in tables:
            if headers[:2] == ['G', 'W']:
                exp = team_record(team)
                if rows[0] != exp:
                    issues.append(('team-record', str(rel), rows[0], exp))
            elif headers[:3] == ['Player', 'Pos', 'G']:
                shown = {r[0]: r for r in rows}
                for name, lines in per.items():
                    if lines and name not in shown:
                        issues.append(('missing-player', str(rel), name, len(lines)))
                for name, row in shown.items():
                    lines = per.get(name, [])
                    a = agg(lines)
                    g = a['g']
                    exp = [str(g)] + ([f1(a['sec'] / 60 / g)] + [f1(a[k] / g) for k in ('pts',)] + [f1((a['orb'] + a['drb']) / g)] + [f1(a[k] / g) for k in ('ast', 'stl', 'blk', 'tov')] if g else ['N/A'] * 7)
                    if row[2:] != exp:
                        issues.append(('production', str(rel), name, row[2:], exp))
                    if g == 0 and team:
                        issues.append(('g0-row', str(rel), name, 'in result rows' if name in per else 'not in any Miami result of period'))
            elif headers[:3] == ['Player', 'GS', 'FG']:
                for row in rows:
                    name = row[0]
                    a = agg(per.get(name, []))
                    g = a['g']
                    gs = (str(a['gs']) if a['gs_known'] else 'N/A') if g else 'N/A'
                    exp = [gs, f"{a['fgm']}/{a['fga']}", r3(a['fgm'] / a['fga']) if a['fga'] else 'N/A',
                           f"{a['tpm']}/{a['tpa']}", r3(a['tpm'] / a['tpa']) if a['tpa'] else 'N/A',
                           f"{a['ftm']}/{a['fta']}", r3(a['ftm'] / a['fta']) if a['fta'] else 'N/A', str(a['orb']), str(a['drb'])]
                    if row[1:] != exp:
                        issues.append(('shooting', str(rel), name, row[1:], exp))
        # team total checks: sum player points == team points
        tp = sum(r.get('pts', 0) for g in team for r in g['result']['player_stats'][g['side']])
        ts = sum(g['result']['final_score'][g['side']] for g in team)
        if tp != ts:
            issues.append(('team-points-sum', str(rel), tp, ts))
    summary[season] = len(games_)

print(summary)
from collections import Counter
print(Counter(i[0] for i in issues))
for i in issues:
    if i[0] != 'g0-row':
        print(i)
print('--- g0 rows')
g0 = [i for i in issues if i[0] == 'g0-row']
for i in g0:
    print(i)
