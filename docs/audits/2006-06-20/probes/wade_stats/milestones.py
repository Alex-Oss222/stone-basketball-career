"""Recompute every career milestone row from closed results."""
from datetime import date
from compare import games
BIRTH = date(1984, 1, 17)
def agestr(d):
    d = date.fromisoformat(d)
    y = d.year - BIRTH.year - ((d.month, d.day) < (BIRTH.month, BIRTH.day))
    last = date(BIRTH.year + y, BIRTH.month, BIRTH.day)
    return f'{y} years, {(d - last).days} days'
def stat(r, k):
    return {'reb': r['orb'] + r['drb'], 'gp': 1}.get(k, r.get(k))
for comp in ('regular', 'playoff'):
    sel = sorted([g for g in games if g['comp'] == comp and g['status'] == 'played' and g['cov'] == 'played'], key=lambda g: g['date'])
    tot = {k: 0 for k in ('pts', 'reb', 'ast', 'stl', 'blk', 'tpm', 'ftm', 'gp')}
    marks = {'pts': [100, 250, 500, 1000, 2000, 3000, 4000, 5000, 6000], 'reb': [100, 250, 500, 1000, 1500], 'ast': [100, 250, 500, 1000],
             'stl': [100, 250, 500], 'blk': [100, 250, 500], 'tpm': [100, 250, 500], 'ftm': [500, 1000, 2000], 'gp': [10, 25, 50, 100, 200, 300]}
    print('==', comp)
    for i, g in enumerate(sel, 1):
        for k in tot:
            before = tot[k]; tot[k] += stat(g['row'], k)
            for m in marks[k]:
                if before < m <= tot[k]:
                    print(f'{m} {k}', g['date'], agestr(g['date']), g['season'], 'game', i, g['meta']['opponent'], 'total', tot[k])
    print('current', tot)
sel = sorted([g for g in games if g['comp'] == 'regular' and g['status'] == 'played' and g['cov'] == 'played'], key=lambda g: g['date'])
firsts = {'20pt': lambda r: r['pts'] >= 20, '30pt': lambda r: r['pts'] >= 30, '40pt': lambda r: r['pts'] >= 40,
          'dd': lambda r: sum([r['pts'] >= 10, r['orb'] + r['drb'] >= 10, r['ast'] >= 10, r['stl'] >= 10, r['blk'] >= 10]) >= 2,
          '5stl': lambda r: r['stl'] >= 5, '10ast': lambda r: r['ast'] >= 10, '5blk': lambda r: r['blk'] >= 5, '10reb': lambda r: r['orb'] + r['drb'] >= 10}
print('debut', sel[0]['date'], agestr(sel[0]['date']), sel[0]['row']['pts'], sel[0]['row']['orb'] + sel[0]['row']['drb'], sel[0]['row']['ast'])
for k, f in firsts.items():
    g = next((g for g in sel if f(g['row'])), None)
    if g: print('first', k, g['date'], agestr(g['date']), g['meta']['opponent'], g['row']['pts'], g['row']['orb'] + g['row']['drb'], g['row']['ast'])
