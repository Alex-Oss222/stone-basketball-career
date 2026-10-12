"""Pages whose identity cutoff falls inside one of Wade's injured-list stints but still say 'No current restriction'."""
import re, json
from pathlib import Path
C = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
IL = []
for s in ('2003-04', '2004-05', '2005-06'):
    IL += [e for e in json.load(open(C / s / '00_Team/Transactions/injured_list.json'))['entries'] if e['player'] == 'Dwyane Wade']
hits = []
for p in C.rglob('*.md'):
    t = p.read_text()
    for d in set(re.findall(r'Identity as of (\d{4}-\d{2}-\d{2})', t)):
        if any(e['placed'] <= d < (e['activated'] or '9999') for e in IL) and 'No current restriction' in t:
            hits.append((str(p.relative_to(C)), d))
print(len(hits)); [print(h) for h in sorted(hits)]
