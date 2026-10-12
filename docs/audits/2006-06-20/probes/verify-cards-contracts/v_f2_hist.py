import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
from runtime import write_back
from collections import Counter
reg = json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
code_of = {}
for p in reg:
    if p.get('team_name') and p.get('team_code'): code_of.setdefault(p['team_name'], p['team_code'])
for season, end in (('2003-04','2004-06-30'),('2004-05','2005-06-30')):
    cp = Path(f'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/lines_{season}.pkl')
    if cp.exists(): lines = pickle.load(open(cp,'rb'))
    else:
        lines,_ = write_back.closed_lines(ROOT, season, end); pickle.dump(lines, open(cp,'wb'))
    cl = json.load(open(f'career/Dwyane_Wade/Stats_and_Awards/League/{season}/card_lines.json'))['players']
    wrong=[]; multi=[]
    for pid, e in cl.items():
        if 'regular' not in e: continue
        team = e['regular'][1]
        recs=[r for r in lines.get(pid,[]) if r.get('line') and r['line'].get('appeared')]
        clubs=sorted({r['team'] for r in recs})
        g=len(recs)
        if not clubs: print('noclubs',pid); continue
        codes={code_of.get(c,c) for c in clubs}|set(clubs)
        if team not in codes: wrong.append((pid,team,clubs))
        elif len(clubs)>1: multi.append((pid,team,clubs))
        if str(g)!=e['regular'][2]: print('G mismatch',pid,g,e['regular'][2])
    print(season, 'wrong', len(wrong), 'multi', len(multi), 'total', len(wrong)+len(multi))
    for w in wrong[:20]: print('  ',w)
