import re, json
from pathlib import Path
from collections import Counter
R = Path('/home/user/stone-basketball-career')
L = R/'career/Dwyane_Wade/Stats_and_Awards/League'
reg = json.loads((L/'player_registry.json').read_text())['players']
print('registry entries', len(reg), Counter(p.get('cohort') for p in reg).most_common(6))
print('registry positions', Counter(p.get('position') or p.get('primary_position') for p in reg))
pages = sorted(L.glob('20*/**/League_Stats.md'))
print('pages', len(pages))
bad_head = 0; bad_sec = 0; heads = Counter(); totals = Counter()
for p in pages:
    t = p.read_text()
    m = re.search(r'^(\d+) tracked players', t, re.M)
    head = int(m.group(1)) if m else None
    heads[head] += 1
    rows = 0; secbad = False
    for sm in re.finditer(r'<summary>(PG|SG|SF|F|PF|C) · [^·]*· (\d+) players?</summary>\n(.*?)</details>', t, re.S):
        n = sum(1 for line in sm.group(3).splitlines() if line.startswith('| [') )
        rows += n
        if n != int(sm.group(2)): secbad = True
    totals[rows] += 1
    if head != rows: bad_head += 1
    if secbad: bad_sec += 1
print('header counts', heads, 'row totals', totals)
print('pages with header != rows', bad_head, '; pages with a wrong section count', bad_sec)
t = (L/'2005-06/League_Stats.md').read_text()
print([l for l in t.splitlines() if 'tracked players' in l][:1])
for sm in re.finditer(r'<summary>((PG|SG|SF|F|PF|C) · [^<]*)</summary>\n(.*?)</details>', t, re.S):
    print(sm.group(1), '| rows', sum(1 for line in sm.group(3).splitlines() if line.startswith('| [')))
