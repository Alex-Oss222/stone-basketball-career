import re, json, bisect
from pathlib import Path
R = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
# planned minutes by date
import glob
plan = []
for f in glob.glob(str(R/'*/00_Team/Team/Depth_Chart/rotation.json')) + glob.glob(str(R/'*/00_Team/Team/Depth_Chart/Reviews/*/rotation.json')):
    d = json.loads(Path(f).read_text())
    w = [p for p in d['players'] if p['player_id'] == 'Dwyane Wade']
    plan.append((d['as_of'], w[0]['minutes']))
plan.sort()
dates = [p[0] for p in plan]
def plan_on(day):
    i = bisect.bisect_right(dates, day) - 1
    return plan[i] if i >= 0 else None
stale = []; ok = 0; total = 0
for p in R.rglob('*.md'):
    t = p.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'Identity as of (\d{4}-\d{2}-\d{2})', t)
    r = re.search(r'\| Role \| ([^|]+) \|', t)
    if not m or not r: continue
    total += 1
    day = m.group(1); role = r.group(1).strip()
    pm = re.search(r'staff plan ([\d.]+) minutes', role)
    if not pm: continue
    shown = float(pm.group(1)); pl = plan_on(day)
    if pl and abs(pl[1] - shown) > 0.5:
        stale.append((day, str(p.relative_to(R)), role, pl))
    else:
        ok += 1
print('pages with Role row:', total, 'consistent:', ok, 'stale:', len(stale))
from collections import Counter
print(Counter(s[2] for s in stale))
print(min(s[0] for s in stale), max(s[0] for s in stale))
print(Counter(s[1].split('/')[0] for s in stale))
for s in sorted(stale)[:5]: print(s)
n = 0; win = []
for p in R.rglob('*.md'):
    t = p.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'Identity as of (\d{4}-\d{2}-\d{2})', t)
    r = re.search(r'\| Role \| ([^|]+) \|', t)
    if m and r and m.group(1) >= '2004-11-25' and 'staff plan 34 minutes' in r.group(1):
        n += 1
        if '2005-10-26' <= m.group(1) < '2005-11-09': win.append(m.group(1))
print('cutoff >= 2004-11-25 with 34:', n, '; of which in the 2005-10-26..11-08 window where 34 is correct:', len(win))
