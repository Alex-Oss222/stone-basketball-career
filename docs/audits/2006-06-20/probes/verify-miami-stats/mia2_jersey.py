import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime import jerseys, seasons
print('active', seasons.active(R))
print('wade_number', jerseys.wade_number(R))
nums = jerseys.miami_numbers(R)
print(nums)
from collections import Counter
print('dupes', [k for k,v in Counter(v for v in nums.values() if v).items() if v>1])
reg = json.loads((R/jerseys.register_path(R)).read_text())['players']
for p in reg:
    if p['name'] in ('Caron Butler',):
        print(p['name'], p.get('bbr_id'), jerseys.candidates(p.get('bbr_id'),'Miami Heat',R))
# per-season
orig = jerseys._season
for s in ['2003-04','2004-05','2005-06']:
    jerseys._season = lambda root=None, s=s: s
    n = jerseys.miami_numbers(R)
    print(s, 'Wade', n.get('Dwyane Wade'), {k:n[k] for k in ('Caron Butler','Donyell Marshall','Brian Grant','Eddie Jones','Mike James') if k in n})
jerseys._season = orig
