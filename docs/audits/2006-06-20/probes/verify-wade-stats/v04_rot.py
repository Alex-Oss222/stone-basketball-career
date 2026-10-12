import json, glob
from pathlib import Path
R = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
files = sorted(glob.glob(str(R/'*/00_Team/Team/Depth_Chart/rotation.json'))) + sorted(glob.glob(str(R/'*/00_Team/Team/Depth_Chart/Reviews/*/rotation.json')))
out = []
for f in files:
    d = json.loads(Path(f).read_text())
    w = [p for p in d['players'] if p['player_id'] == 'Dwyane Wade']
    order = [p['player_id'] for p in d['players']]
    idx = order.index('Dwyane Wade') if w else None
    out.append((d['as_of'], w[0]['minutes'] if w else None, w[0]['position'] if w else None, idx, f.replace(str(R)+'/', '')))
for o in sorted(out): print(o)
