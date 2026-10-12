"""2004-05 trajectory feedback (from 2003-04) against write_back.closed_lines (the league pages' matcher, which the
league-stats audit verified against independent bbr matching)."""
import sys, json, inspect
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import write_back
from runtime.trajectories import load_trajectories
root = Path('/home/user/stone-basketball-career')
fn = [n for n, f in inspect.getmembers(write_back, inspect.isfunction) if 'lines, unmatched = {}, set()' in inspect.getsource(f)][0]
print('matcher', fn)
for frm, to in (('2003-04', '2004-05'), ('2004-05', '2005-06'), ('2005-06', '2006-07')):
    lines, unmatched = getattr(write_back, fn)(root, frm, None)
    reg = {p['registry_id']: p for p in write_back.registry(root)['players']}
    fb = json.load(open(root / f'career/Dwyane_Wade/{to}/trajectory_feedback.json'))['players']
    tr = load_trajectories(root, frm)
    missing, bad = [], []
    for rid, recs in lines.items():
        b = reg[rid].get('bbr_id')
        mins = sum(r['line']['seconds'] for r in recs if r.get('line') and r['line'].get('seconds')) / 60
        if not mins:
            continue
        if b not in fb:
            if b and tr.has(b, frm) and b not in ('wadedw01', 'boshch01'):
                missing.append((b, reg[rid]['name'], round(mins, 1), sum(1 for r in recs if r.get('line') and r['line'].get('seconds'))))
        elif abs(round(mins, 1) - fb[b]['minutes']) > 0.15:
            bad.append((b, round(mins, 1), fb[b]['minutes']))
    print(frm, '->', to, 'unmatched', unmatched[:5], 'missing', missing, 'minute mismatches', bad[:10])
