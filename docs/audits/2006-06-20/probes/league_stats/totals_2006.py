"""What season_evidence.compute_totals would write for 2005-06 at the rollover (in memory), vs the closed results/league page."""
import sys
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import indep
from pathlib import Path
from runtime import season_evidence as se
root = Path('/home/user/stone-basketball-career')
fresh = se.compute_totals('2005-06', root)
reg = {p['name']: p for p in indep.registry()}
mine, _ = indep.lines('2005-06', rows=indep.results('2005-06'))
diff = []; miss = []
for name, recs in mine.items():
    g, gs, t = indep.agg(recs, '0000', '9999')
    if not g: continue
    b = reg[name]['bbr_id']
    f = fresh.get(b)
    if not f: miss.append((name, g)); continue
    if f['totals']['games'] != g or f['totals']['points'] != t['pts']:
        diff.append((name, f['totals']['games'], g, f['totals']['points'], t['pts']))
print('missing', miss); print('differ', len(diff), diff)
