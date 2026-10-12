"""Players with two appearances on one date, or appearances for club A after a later appearance for club B then back (stint interleaving)."""
import sys, collections
sys.path.insert(0, '.')
import indep
season = sys.argv[1]
mine, _ = indep.lines(season, rows=indep.results(season))
same = []; inter = []; over = []
for name, recs in mine.items():
    apps = sorted([r for r in recs if r['appeared']], key=lambda r: r['date'])
    allr = sorted(recs, key=lambda r: r['date'])
    d = collections.Counter(r['date'] for r in allr)
    if any(v > 1 for v in d.values()): same.append((name, [k for k, v in d.items() if v > 1][:3]))
    seq = [r['club'] for r in allr]
    stints = [c for i, c in enumerate(seq) if i == 0 or seq[i - 1] != c]
    if len(stints) != len(set(stints)): inter.append((name, stints))
    if len(apps) > 82: over.append((name, len(apps), stints))
print('same-date rows', len(same), same[:10])
print('interleaved stints (club returns)', len(inter), inter[:10])
print('G>82', over)
