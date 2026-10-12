import sys, re
sys.path.insert(0, '.')
import indep
from compare_pages_lib import scope
season = sys.argv[1]
dates = [r['game_date'] for r, *_ in indep.results(season)]
bad = 0; n = 0
for page in sorted((indep.LEAGUE / season).rglob('League_Stats.md')):
    if 'Playoffs' in page.parts: continue
    s, e = scope(page, season)
    text = page.read_text()
    m = re.search(r'· (\d+) closed games? in this record', text)
    exp = sum(1 for d in dates if s <= d <= e)
    n += 1
    if int(m.group(1)) != exp: bad += 1; print('header', page, m.group(1), exp)
    for row in re.findall(r'^\| \[[^\]]+\]\(([^)]+League_Stats.md)\) \| [^|]+ \| (\d+) \| ([^|]+) \|$', text, re.M):
        target = (page.parent / row[0]).resolve()
        s2, e2 = scope(target, season)
        exp2 = sum(1 for d in dates if s2 <= d <= e2)
        n += 1
        if int(row[1]) != exp2: bad += 1; print('period', page, row, exp2)
print(season, 'checked', n, 'bad', bad)
