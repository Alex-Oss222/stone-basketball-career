"""League card 'Regular-season statistics by year' row for a season vs independent aggregation (G, GS, MIN, PTS, REB, AST, FG%)."""
import sys, re
sys.path.insert(0, '.')
import indep
season = sys.argv[1]
mine, _ = indep.lines(season, rows=indep.results(season))
reg = indep.registry()
bad = []; n = 0; missing = []
for p in reg:
    card = indep.LEAGUE / 'Players' / f"{p['registry_id']}.md"
    if not card.is_file(): missing.append(p['name']); continue
    text = card.read_text()
    sec = text.split('## Regular-season statistics by year', 1)
    if len(sec) < 2: continue
    sec = sec[1].split('\n## ', 1)[0]
    row = [l for l in sec.splitlines() if l.startswith(f'| {season} |')]
    g, gs, t = indep.agg(mine.get(p['name'], []), '0000', '9999')
    if not row:
        if g: bad.append((p['name'], 'no card row', g))
        continue
    c = [x.strip() for x in row[0].strip().strip('|').split('|')]
    n += 1
    if not g:
        bad.append((p['name'], 'card row but no appearance', c)); continue
    exp = [str(g), str(gs), f"{t['sec']/60/g:.1f}", f"{t['pts']/g:.1f}", f"{(t['orb']+t['drb'])/g:.1f}", f"{t['ast']/g:.1f}"]
    if c[2:8] != exp: bad.append((p['name'], c[2:8], exp))
print(season, 'card rows', n, 'missing cards', missing[:5], 'mismatch', len(bad))
for b in bad[:15]: print('  ', b)
