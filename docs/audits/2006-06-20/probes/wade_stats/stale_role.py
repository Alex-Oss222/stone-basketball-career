"""Pages whose identity cutoff is on/after Wade's first non-34-minute staff plan (2004-11-25) but still show 'staff plan 34 minutes'."""
import re
from pathlib import Path
C = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
n = 0; ex = []
for p in C.rglob('*.md'):
    t = p.read_text()
    for m in re.finditer(r'\| Role \| ([^|]+) \|', t):
        pass
    roles = re.findall(r'\| Role \| ([^|]+) \|', t)
    ids = re.findall(r'Identity as of (\d{4}-\d{2}-\d{2})', t)
    for r, d in zip(roles, ids):
        if 'staff plan 34 minutes' in r and d >= '2004-11-25':
            n += 1; ex.append((str(p.relative_to(C)), d)); break
print(n); print(ex[:5])
