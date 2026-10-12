import sys, re, calendar, json
sys.path.insert(0, '.')
import indep, parse_pages
from pathlib import Path
from collections import Counter, defaultdict
season = sys.argv[1]
clock = sys.argv[2] if len(sys.argv) > 2 else '2006-06-20'
LEAGUE = indep.LEAGUE
reg = indep.registry()
regpos = {p['name']: p['position'] for p in reg}
mine, um = indep.lines(season, rows=indep.results(season, clock=clock))
STAT = ['G','GS','MP','FG','FGA','FG%','3P','3PA','3P%','2P','2PA','2P%','eFG%','FT','FTA','FT%','ORB','DRB','TRB','AST','STL','BLK','TOV','PF','PTS','TS% (est.)']

def scope(page):
    parts = page.relative_to(LEAGUE / season).parts
    y0 = int(season[:4])
    start, end = f"{y0}-06-01", f"{y0+1}-06-30"
    if len(parts) >= 2 and re.fullmatch(r"\d{2}_\w+", parts[0]):
        num = int(parts[0][:2]); year = y0 + (num < 7); last = calendar.monthrange(year, num)[1]
        start, end = f"{year}-{num:02d}-01", f"{year}-{num:02d}-{last:02d}"
        if parts[1].startswith('Week_'):
            w = int(parts[1][5:])
            start = f"{year}-{num:02d}-{1+(w-1)*7:02d}"; end = f"{year}-{num:02d}-{(w*7 if w < 4 else last):02d}"
    return start, end

problems = defaultdict(list)
pages = sorted((LEAGUE / season).rglob('League_Stats.md'))
pages = [p for p in pages if 'Playoffs' not in p.parts]
cellmis = Counter()
for page in pages:
    start, end = scope(page)
    text, groups = parse_pages.parse(page)
    seen = Counter()
    for pos, gd in groups.items():
        for row in gd['rows']:
            name = row['name']; seen[name] += 1
            if regpos.get(name) != pos:
                problems['group'].append((str(page), name, pos, regpos.get(name)))
            if row.get('Pos') != pos:
                problems['poscol'].append((str(page), name, pos, row.get('Pos')))
            g, gs, t = indep.agg(mine.get(name, []), start, end)
            exp = indep.fmt(g, gs, t)
            for k in STAT:
                if row.get(k) != exp[k]:
                    cellmis[(k)] += 1
                    problems['cell'].append((str(page.relative_to(LEAGUE)), name, k, row.get(k), exp[k]))
    missing = set(regpos) - set(seen)
    dup = [n for n, c in seen.items() if c > 1]
    extra = set(seen) - set(regpos)
    if missing: problems['missing'].append((str(page), len(missing), sorted(missing)[:5]))
    if dup: problems['dup'].append((str(page), dup))
    if extra: problems['extra'].append((str(page), extra))
print('pages', len(pages))
for k, v in problems.items():
    print(k, len(v))
    for x in v[:15]: print('   ', x)
print(cellmis)
