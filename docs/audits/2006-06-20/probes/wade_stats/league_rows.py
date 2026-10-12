"""Wade's row on every League_Stats.md and Team_Stats.md page vs his own closed games."""
import re, calendar
from pathlib import Path
from compare import games, CAREER, agg, expected_cells, age_on
from collections import Counter
probs = []; n = 0; ages = Counter()
def period(rel_parts):
    season = rel_parts[1]
    reg = [g for g in games if g['season'] == season and g['comp'] == 'regular']
    mf = next((p for p in rel_parts if re.fullmatch(r'\d{2}_[A-Za-z]+', p)), None)
    if not mf:
        return reg, max(g['date'] for g in reg)
    num = int(mf[:2]); year = int(season[:4]) + (num < 7); last = calendar.monthrange(year, num)[1]
    lo, hi = f'{year}-{num:02d}-01', f'{year}-{num:02d}-{last:02d}'
    wk = next((int(p[5:]) for p in rel_parts if re.fullmatch(r'Week_\d', p)), None)
    if wk:
        lo = f'{year}-{num:02d}-{1+(wk-1)*7:02d}'; hi = f'{year}-{num:02d}-{wk*7:02d}' if wk < 4 else hi
    return [g for g in reg if lo <= g['date'] <= hi], hi
for page in sorted((CAREER / 'Stats_and_Awards/League').rglob('League_Stats.md')):
    rel = page.relative_to(CAREER / 'Stats_and_Awards/League').parts
    if not re.fullmatch(r'\d{4}-\d{2}', rel[0]): continue
    rel = ('League',) + rel
    t = page.read_text()
    rows = [l for l in t.splitlines() if l.startswith('| [Dwyane Wade]') or l.startswith('| Dwyane Wade |')]
    sel, end = period(rel)
    if not rows:
        probs.append(('no wade row', str(page))); continue
    n += 1
    for l in rows:
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        exp = expected_cells(agg(sel))
        got = c[5:31]
        if not [g for g in sel if g['status']=='played' and g['cov']=='played']:
            exp = ['0'] + ['N/A'] * 25
        if got != exp:
            probs.append(('vals', str(page.relative_to(CAREER)), [(i, a, b) for i, (a, b) in enumerate(zip(got, exp)) if a != b][:5]))
        ages[(rel[1], c[1], age_on(end), age_on(min(end, '2006-06-20')))] += 1
print('league pages', n, 'problems', len(probs))
for p in probs[:20]: print(p)
for k, v in sorted(ages.items()): print(k, v)
