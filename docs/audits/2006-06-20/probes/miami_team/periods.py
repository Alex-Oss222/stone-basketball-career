import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *
TEAM = CAREER / 'Stats_and_Awards/Team'
bad = 0; n = 0
for s in SEASONS:
    games, _ = closed(s)
    dates = [g['result']['game_date'] for g in games]
    for page in (TEAM / s).rglob('Team_Stats.md'):
        for m in re.finditer(r'^\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]+) \| (\d+) \| ([^|]+) \|$', page.read_text(), re.M):
            target = (page.parent / m.group(2)).resolve()
            st, en = scope_of_page(target.relative_to((TEAM / s).resolve()), s)
            k = sum(1 for d in dates if st <= d <= en)
            n += 1
            status = m.group(5).strip()
            exp_status = 'Not started' if not k else ('Complete' if en < CLOCK else 'x')
            if str(k) != m.group(4) or status != exp_status:
                bad += 1; print(page.relative_to(TEAM), m.group(1), m.group(4), status, '| expected', k, exp_status)
print('rows', n, 'bad', bad)
