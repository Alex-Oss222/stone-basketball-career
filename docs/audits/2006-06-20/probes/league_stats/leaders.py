import sys, re
sys.path.insert(0, '.')
import indep
from compare_pages_lib import scope
season = sys.argv[1]
mine, _ = indep.lines(season, rows=indep.results(season))
cats = [('PPG', lambda t: t['pts']), ('RPG', lambda t: t['orb'] + t['drb']), ('APG', lambda t: t['ast']), ('SPG', lambda t: t['stl']), ('BPG', lambda t: t['blk'])]
bad = 0; n = 0
for page in sorted((indep.LEAGUE / season).rglob('League_Stats.md')):
    if 'Playoffs' in page.parts: continue
    s, e = scope(page, season)
    text = page.read_text()
    block = text.split('## Leaders', 1)[1].split('## Players by position', 1)[0]
    got = {}
    for l in block.splitlines():
        if l.startswith('| ') and not l.startswith('| Category') and not l.startswith('| ---'):
            c = [x.strip() for x in l.strip().strip('|').split('|')]
            got[c[0]] = c[1:]
    summ = {}
    for name, recs in mine.items():
        g, gs, t = indep.agg(recs, s, e)
        if g: summ[name] = (g, t)
    for label, f in cats:
        top = sorted(summ.items(), key=lambda kv: (-f(kv[1][1]) / kv[1][0], kv[0]))[:3]
        exp = [f"{nm} {f(t)/g:.1f} (G {g})" for nm, (g, t) in top]
        n += 1
        if got.get(label) != exp:
            bad += 1; print(page.relative_to(indep.LEAGUE), label, got.get(label), exp)
print('leader rows', n, 'mismatches', bad)
