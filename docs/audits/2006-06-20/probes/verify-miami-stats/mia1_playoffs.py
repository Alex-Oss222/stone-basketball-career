import sys, json, re, glob
from pathlib import Path
sys.path.insert(0, '/home/user/stone-basketball-career')
R = Path('/home/user/stone-basketball-career')
C = R/'career/Dwyane_Wade'
sums = {}
for s in ['2003-04','2004-05','2005-06']:
    files = sorted((C/s/'08_Playoffs').rglob('*.result.json'))
    # check declared by played note
    n=0
    for f in files:
        note = f.with_name(f.name.replace('.result.json','.md'))
        txt = note.read_text()
        if 'result_file' not in txt or 'played' not in txt:
            print('UNDECLARED?', f)
        d = json.loads(f.read_text())
        side = 'home' if d['home']=='Miami Heat' else ('away' if d['away']=='Miami Heat' else None)
        if side is None: print('not miami', f); continue
        n+=1
        for l in d['player_stats'][side]:
            app = (l.get('seconds') or 0) > 0 or l.get('appeared')
            if not app: continue
            k=(s,l['player_id'])
            a=sums.setdefault(k,{'g':0,'gs':0,'sec':0,'pts':0})
            a['g']+=1; a['gs']+=bool(l.get('started')); a['sec']+=l['seconds']; a['pts']+=l['pts']
    print(s, 'miami playoff games', n)
for k,v in sorted(sums.items()):
    print(k, v['g'], v['gs'], round(v['sec']/60/v['g'],1), round(v['pts']/v['g'],1))
json.dump({f'{k[0]}|{k[1]}':v for k,v in sums.items()}, open('mia1_sums.json','w'))
