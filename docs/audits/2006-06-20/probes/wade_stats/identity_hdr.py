"""Identity header on every Wade page: age on report date vs the stated identity cutoff, and snapshot fields."""
import re, json
from collections import Counter
from compare import CAREER, age_on, pages
ident = json.load(open(CAREER / 'professional_identity.json'))
snaps = sorted(ident['snapshots'], key=lambda s: s['as_of'])
def snap(d):
    return [s for s in snaps if s['as_of'] <= d][-1]
probs = []; n = 0; jerseys = Counter()
for p in pages():
    t = p.read_text()
    for m in re.finditer(r'\| Dwyane Tyrone Wade Jr\. \| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', t):
        pass
    ids = re.findall(r'Identity as of (\d{4}-\d{2}-\d{2}); status snapshot dated (\d{4}-\d{2}-\d{2})', t)
    rows = re.findall(r'\| Dwyane Tyrone Wade Jr\. \| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', t)
    if not ids: continue
    n += 1
    for (asof, sd), row in zip(ids, rows):
        s = snap(asof)
        exp_j = str(s['jersey']) if s['jersey'] is not None else 'Not assigned'
        if int(row[0]) != age_on(asof) or sd != s['as_of'] or row[3].strip() != exp_j or row[4].strip() != s['roster_status']:
            probs.append((str(p.relative_to(CAREER)), asof, row, sd, s['as_of']))
        jerseys[(p.relative_to(CAREER).parts[0], row[3].strip())] += 1
print('pages', n, 'problems', len(probs)); [print(x) for x in probs[:10]]
print(jerseys)
