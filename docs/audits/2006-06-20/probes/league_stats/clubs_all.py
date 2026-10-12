"""For every league page of a season: rows with >=1 appearance in the period whose Club / rights cell names none of the clubs
he played for in that period (and is not his club_truth.holder on the cutoff)."""
import sys
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import parse_pages, indep
from compare_pages_lib import scope
from runtime import club_truth
season = sys.argv[1]; clock = '2006-06-20'
LEAGUE = indep.LEAGUE
reg = {p['name']: p for p in indep.registry()}
codes = {p['team_name']: p['team_code'] for p in reg.values() if p.get('team_code')}
codes.update({'New Orleans/Oklahoma City Hornets': 'NO', 'Charlotte Bobcats': 'CHA', 'Miami Heat': 'MIA'})
mine, _ = indep.lines(season, rows=indep.results(season, clock=clock))
tot_rows = tot_pages = 0
rights = []
for page in sorted((LEAGUE / season).rglob('League_Stats.md')):
    if 'Playoffs' in page.parts: continue
    s, e = scope(page, season); on = min(e, clock)
    text, groups = parse_pages.parse(page)
    n = 0
    for row in [r for g in groups.values() for r in g['rows']]:
        if row['Club / rights'].endswith('rights'): rights.append((str(page.relative_to(LEAGUE)), row['name'], row['Club / rights'], row['G']))
        apps = [r for r in mine.get(row['name'], []) if s <= r['date'] <= e and r['appeared']]
        if not apps: continue
        played = {codes.get(r['club'], r['club']) for r in apps}
        if row['Club / rights'] not in played:
            n += 1
    tot_rows += n; tot_pages += bool(n)
    print(page.relative_to(LEAGUE), n)
print('total rows', tot_rows, 'pages', tot_pages)
print('rights labels', len(rights), rights[:10])
