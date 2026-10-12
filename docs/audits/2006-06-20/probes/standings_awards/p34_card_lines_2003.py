import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime.award_decisions import registry_names
names=registry_names(R,'2003-04')
reg={p['registry_id']:p for p in json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
ros=json.load(open(R/'library/2003/league/nba_2003_04_team_rosters.json'))
ros=ros.get('clubs',ros)
code={c:v['code'] for c,v in ros.items() if isinstance(v,dict) and 'code' in v}
code['Miami Heat']='MIA'
for p in reg.values():
    if p.get('team_code') and p.get('team_name'): code[p['team_name']]=p['team_code']
clubs={}
for r in sorted(results('2003-04').values(),key=lambda r:r['game_date']):
    for side in('home','away'):
        for q in r['player_stats'][side]:
            if q['minutes']>0: clubs.setdefault(names.get(q['player_id'],q['player_id']),[]).append(r[side])
cl=json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/2003-04/card_lines.json'))['players']
n=0;bad=[]
for rid,e in cl.items():
    if 'regular' not in e: continue
    nm=reg.get(rid,{}).get('name'); played=clubs.get(nm)
    if not played: continue
    n+=1
    label=e['regular'][1]
    codes={code.get(c,c) for c in played}
    if label not in codes: bad.append((nm,label,sorted(set(played),key=played.index), len(played)))
print('2003-04 card_lines regular rows',n,'label is a club he never played for in 2003-04:',len(bad))
for b in bad[:12]: print('  ',b)
