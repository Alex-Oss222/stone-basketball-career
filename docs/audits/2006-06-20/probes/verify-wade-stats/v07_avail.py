import re, json
from pathlib import Path
R = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
stints = []
for s in ['2003-04', '2004-05', '2005-06']:
    f = R/s/'00_Team/Transactions/injured_list.json'
    for e in json.loads(f.read_text())['entries']:
        if e['player'] == 'Dwyane Wade':
            stints.append((e['placed'], e.get('activated') or '9999'))
print(stints)
hits = []; total = 0
for p in R.rglob('*.md'):
    t = p.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'Identity as of (\d{4}-\d{2}-\d{2})', t)
    a = re.search(r'\| Availability \| ([^|]+) \|', t)
    if not m or not a: continue
    total += 1
    d = m.group(1)
    if any(lo <= d < hi for lo, hi in stints):
        hits.append((d, str(p.relative_to(R)), a.group(1).strip()))
print('pages with Availability row', total, 'inside a stint', len(hits))
from collections import Counter
print(Counter(h[2] for h in hits))
for h in sorted(hits): print(h[0], h[1])
