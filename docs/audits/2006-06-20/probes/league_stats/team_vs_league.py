"""Miami Team_Stats.md (season) production rows vs independent aggregation of Miami-side lines."""
import sys, re
sys.path.insert(0, '.')
import indep
season = sys.argv[1]
mine, _ = indep.lines(season, rows=indep.results(season))
reg = {p['name']: p for p in indep.registry()}
page = (indep.ROOT / f'career/Dwyane_Wade/Stats_and_Awards/Team/{season}/Team_Stats.md').read_text()
rows = [l for l in page.splitlines() if l.startswith('| ')]
hdr = None; bad = 0; n = 0
for l in rows:
    c = [x.strip() for x in l.strip().strip('|').split('|')]
    if c[0] == 'Player': hdr = c; continue
    if c[0].startswith('---') or hdr is None: continue
    d = dict(zip(hdr, c))
    if 'PPG' not in d: continue
    name = d['Player']
    # team pages key by result player_id; map to registry through indep (same bbr)
    recs = [r for nm, rs in mine.items() for r in rs if r['club'] == 'Miami Heat' and r['appeared'] and (nm == name or indep.key(nm) == indep.key(name))]
    g = len(recs)
    pts = sum(r['pts'] for r in recs); mp = sum(r['seconds'] for r in recs) / 60
    exp = (str(g), f"{mp/g:.1f}" if g else 'N/A', f"{pts/g:.1f}" if g else 'N/A')
    got = (d['G'], d['MPG'], d['PPG'])
    n += 1
    if got != exp:
        bad += 1; print(name, got, exp)
print('rows', n, 'mismatch', bad)
