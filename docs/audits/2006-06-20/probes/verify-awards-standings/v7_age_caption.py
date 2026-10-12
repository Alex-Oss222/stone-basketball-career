import sys, re, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import Counter
R = Path('/home/user/stone-basketball-career')
from runtime.stat_layout import scope_for
from runtime.league_cards import age_on
L = R/'career/Dwyane_Wade/Stats_and_Awards/League'
reg = json.loads((L/'player_registry.json').read_text())['players']
births = {p['name']: p.get('birth_date') for p in reg}
now = '2006-06-20'
pages = sorted(L.glob('20*/**/League_Stats.md'))
summary = Counter(); examples = []
for page in pages:
    t = page.read_text()
    m = re.search(r"identity cutoff \((\d{4}-\d{2}-\d{2})\)", t)
    cap = m.group(1) if m else None
    sc = scope_for(page.relative_to(R), [], now)
    label_on = min(sc['end'], now)
    match_cap = match_lbl = n = 0
    for line in t.splitlines():
        mm = re.match(r"\| \[([^\]]+)\]\([^)]*\) \| (\d+|N/A) \|", line)
        if not mm: continue
        name, age = mm.group(1), mm.group(2)
        b = births.get(name)
        if not b or age == 'N/A': continue
        n += 1
        if int(age) == age_on(b, cap): match_cap += 1
        if int(age) == age_on(b, label_on): match_lbl += 1
    summary[(cap, match_lbl == n, match_cap == n)] += 1
    if page.parent.name in ('2005-06', '04_April'):
        examples.append((str(page.relative_to(L)), cap, label_on, n, match_lbl, match_cap))
print(summary)
for e in examples: print(e)
for page, nm in [('2005-06/League_Stats.md', 'Chris Paul'), ('2005-06/04_April/League_Stats.md', 'Chris Paul'), ('2003-04/04_April/League_Stats.md', 'Dwyane Wade'), ('2005-06/League_Stats.md', 'Jason Williams')]:
    t = (L/page).read_text()
    line = next(l for l in t.splitlines() if l.startswith(f'| [{nm}]'))
    print(page, nm, line.split('|')[2].strip(), 'birth', births.get(nm), 'age at 2003-06-26', age_on(births.get(nm), '2003-06-26'))
