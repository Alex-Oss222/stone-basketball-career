import json
from collections import Counter, defaultdict
from compare import age_on
rows = json.load(open('ages.json'))
c = Counter(); ex = defaultdict(list)
for rel, ln, heading, label, shown, ages, end, team, lg, pos in rows:
    shown = int(shown)
    if ages and shown not in ages:
        key = (rel.split('/')[1] if rel[0].isdigit() else rel.split('/')[0], heading, label if not label.startswith('[') else label.split('](')[0] + ']', shown, tuple(ages))
        c[key] += 1; ex[key].append(f'{rel}:{ln}')
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print(v, k, ex[k][:2])
print('teams', Counter(r[7] for r in rows)); print('lg', Counter(r[8] for r in rows)); print('pos', Counter(r[9] for r in rows))
