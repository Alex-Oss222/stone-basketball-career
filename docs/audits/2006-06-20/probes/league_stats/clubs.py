"""Club / rights cell vs club_truth.holder on min(page end, clock) and vs the club of the player's last appearance in the period."""
import sys, re, json
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import parse_pages, indep
from compare_pages_lib import scope
from pathlib import Path
from collections import Counter
from runtime import club_truth
season = sys.argv[1]; page_rel = sys.argv[2] if len(sys.argv) > 2 else 'League_Stats.md'
clock = '2006-06-20'
LEAGUE = indep.LEAGUE
reg = {p['name']: p for p in indep.registry()}
codes = {}
for p in reg.values():
    if p.get('team_code') and p.get('team_name'): codes[p['team_name']] = p['team_code']
codes.update({'New Orleans/Oklahoma City Hornets': 'NO', 'Charlotte Bobcats': 'CHA'})
mine, _ = indep.lines(season, rows=indep.results(season, clock=clock))
page = LEAGUE / season / page_rel
s, e = scope(page, season); on = min(e, clock)
text, groups = parse_pages.parse(page)
cnt = Counter(); ex = []
inv = {}
for row in [r for g in groups.values() for r in g['rows']]:
    p = reg[row['name']]
    club, basis = club_truth.holder(p['bbr_id'], p['name'], on)
    apps = [r for r in mine.get(row['name'], []) if s <= r['date'] <= e and r['appeared']]
    last = apps[-1]['club'] if apps else None
    cell = row['Club / rights']
    hc = codes.get(club, club) if club else None
    lc = codes.get(last, last) if last else None
    key = ('cell==holder' if cell == hc else 'cell!=holder', 'cell==lastapp' if cell == lc else ('noapp' if not lc else 'cell!=lastapp'))
    cnt[key] += 1
    if cell != hc and lc and cell != lc:
        ex.append((row['name'], 'cell', cell, 'holder', hc, 'last club played', lc, 'G', row['G']))
print(page_rel, 'on', on, dict(cnt))
print('cell differs from both holder and club of last appearance:', len(ex))
for x in ex[:40]: print('  ', x)
