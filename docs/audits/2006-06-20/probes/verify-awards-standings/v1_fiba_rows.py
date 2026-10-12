import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R = Path('/home/user/stone-basketball-career')
d = R/'career/Dwyane_Wade/FIBA/Continental_Cups/2005'
rec = json.loads((d/'tournament.json').read_text())
print(list(rec.keys()))
bad = 0
for n, g in sorted(rec['games'].items(), key=lambda x: int(x[0])):
    p = d/'Games'/f'fiba-amc05-g{int(n):02d}.result.json'
    if not p.exists():
        print('missing', n); continue
    r = json.loads(p.read_text())
    if (g.get('home'), g.get('away')) != (r['home'], r['away']):
        bad += 1
        print(n, g['stage'], 'sched', g.get('home'), 'v', g.get('away'), '| result', r['home'], r['final_score']['home'], '-', r['away'], r['final_score']['away'])
print('mismatches', bad, 'of', len(rec['games']))
# also check requests
for n in ['12','18','27','34','37','39']:
    q = d/'Games'/f'fiba-amc05-g{int(n):02d}.request.json'
    if q.exists():
        j = json.loads(q.read_text()); print(n, 'request', j.get('home', {}) if not isinstance(j.get('home'), dict) else j['home'].get('team'), j.get('away') if not isinstance(j.get('away'), dict) else j['away'].get('team'))
