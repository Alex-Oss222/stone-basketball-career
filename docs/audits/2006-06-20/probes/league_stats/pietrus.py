import sys; sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/stone-basketball-career')
import indep
from pathlib import Path
from runtime import write_back as wb
root = Path('/home/user/stone-basketball-career')
gl, _ = wb.closed_lines(root, '2003-04')
reg = {p['registry_id']: p for p in wb.registry(root)['players']}
target = sys.argv[1]
rid = [k for k, p in reg.items() if p['name'] == target][0]
print(reg[rid])
recs = [r for r in gl[rid] if r['line'] and r['line']['appeared'] and '2004-01-01' <= r['date'] <= '2004-01-31']
print('gen Jan apps', len(recs), sorted({r['team'] for r in recs}))
mine, _ = indep.lines('2003-04')
m = [r for r in mine.get(target, []) if r['appeared'] and '2004-01-01' <= r['date'] <= '2004-01-31']
print('mine Jan apps', len(m), sorted({(r['club'], r['bbr_req']) for r in m}))
# which raw names map to target in gen
import collections
