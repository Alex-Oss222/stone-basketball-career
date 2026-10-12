"""Non-Miami season rows on Miami cards against the simulated League season_totals.json of that season."""
import sys, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *
tot = {}
for s in ('2003-04', '2004-05', '2005-06'):
    p = CAREER / f'Stats_and_Awards/League/{s}/season_totals.json'
    if p.is_file():
        tot[s] = {r['bbr_id']: r for r in json.loads(p.read_text())['records']}
print({k: len(v) for k, v in tot.items()})
n = 0
for season in SEASONS:
    roster = {p['name']: p for p in json.loads((CAREER / season / '00_Team/Team/Roster/roster.json').read_text())['players']}
    for card in sorted((CAREER / season / '00_Team/Team/Player_Cards').glob('*.md')):
        text = card.read_text()
        m = re.search(r'^# (.+?) \| (\S+) Player Profile', text, re.M)
        if not m: continue
        name = m.group(1); bbr = roster.get(name, {}).get('bbr_id')
        for line in text.splitlines():
            mm = re.match(r'^\| (200\d-\d\d) \| ([^|]+) \|(.*)$', line)
            if not mm: continue
            s, team = mm.group(1), mm.group(2).strip()
            if team in ('MIA', 'Miami Heat') or s not in tot or s == '2002-03':
                continue
            cells = [c.strip() for c in mm.group(3).strip().strip('|').split('|')]
            r = tot[s].get(bbr)
            if not r:
                print('no totals', card.relative_to(CAREER), s, team); continue
            t = r['totals']; g = t['games']
            exp = [str(g), str(t.get('games_started')), f"{t['minutes']/g:.1f}", f"{t['points']/g:.1f}",
                   f"{(t['offensive_rebounds']+t['defensive_rebounds'])/g:.1f}", f"{t['assists']/g:.1f}", f"{t['steals']/g:.1f}",
                   f"{t['blocks']/g:.1f}", f"{t['turnovers']/g:.1f}"]
            n += 1
            if cells[:9] != exp or ', '.join(r['team_codes']) != team:
                print('MISMATCH', card.relative_to(CAREER), s, team, cells[:9], '| expected', ', '.join(r['team_codes']), exp)
print('compared', n)
