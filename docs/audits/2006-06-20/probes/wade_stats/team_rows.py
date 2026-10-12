import re
from compare import games, CAREER, agg
from league_rows import period
probs = []; n = 0
def f1(v): return 'N/A' if v is None else f'{v:.1f}'
def sh(v): return 'N/A' if v is None else f'{v:.3f}'.removeprefix('0')
for page in sorted((CAREER / 'Stats_and_Awards/Team').rglob('*.md')):
    rel = page.relative_to(CAREER / 'Stats_and_Awards/Team').parts
    if not re.fullmatch(r'\d{4}-\d{2}', rel[0]): continue
    t = page.read_text()
    if 'Playoffs' in rel:
        sel = [g for g in games if g['season'] == rel[0] and g['comp'] == 'playoff']
        if len(rel) > 3: sel = [g for g in sel if g['note'].split('/')[2] == rel[2]]
    else:
        sel, _ = period(('Team',) + rel)
    a = [g for g in sel if g['status'] == 'played' and g['cov'] == 'played']
    rows = [l for l in t.splitlines() if l.startswith('| Dwyane Wade |') or l.startswith('| [Dwyane Wade]')]
    if not rows: 
        if 'Team_Stats' in page.name or 'Playoff' in page.name: probs.append(('no row', str(page.relative_to(CAREER)))); 
        continue
    n += 1
    G = len(a); s = lambda k: sum(g['row'][k] for g in a)
    pg = lambda v: f1(v / G) if G else 'N/A'
    exp1 = [str(G), pg(s('seconds') / 60), pg(s('pts')), pg(s('orb') + s('drb')), pg(s('ast')), pg(s('stl')), pg(s('blk')), pg(s('tov'))]
    gs = sum(1 for g in a if g['row'].get('started'))
    exp2 = [str(gs) if G else 'N/A', f"{s('fgm')}/{s('fga')}", sh(s('fgm') / s('fga') if s('fga') else None), f"{s('tpm')}/{s('tpa')}", sh(s('tpm') / s('tpa') if s('tpa') else None),
            f"{s('ftm')}/{s('fta')}", sh(s('ftm') / s('fta') if s('fta') else None), str(s('orb')), str(s('drb'))]
    c1 = [x.strip() for x in rows[0].strip().strip('|').split('|')]
    if c1[2:10] != exp1: probs.append(('pg', str(page.relative_to(CAREER)), c1[2:10], exp1))
    if len(rows) > 1:
        c2 = [x.strip() for x in rows[1].strip().strip('|').split('|')]
        if c2[1:10] != exp2: probs.append(('detail', str(page.relative_to(CAREER)), c2[1:10], exp2))
print('team pages', n, 'problems', len(probs))
for p in probs[:20]: print(p)
