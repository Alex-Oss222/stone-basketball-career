import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime import league_cards
from runtime.award_decisions import registry_names
names=registry_names(R,'2003-04')
reg=json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
last={}
for r in sorted(results('2003-04').values(),key=lambda r:r['game_date']):
    for side in('home','away'):
        for q in r['player_stats'][side]:
            if q['minutes']>0: last[names.get(q['player_id'],q['player_id'])]=(r['game_date'],r[side])
tx=json.load(open(R/league_cards.TRANSACTIONS))
diff=[]
for p in reg:
    if p['name'] not in last: continue
    d,club=last[p['name']]
    c=league_cards.club_on(p,d,root=R,transactions=tx)['club']
    if c!=club: diff.append((p['name'],d,club,c))
print('players with 2003-04 games',sum(1 for p in reg if p['name'] in last),'club_on differs from last game club on that date',len(diff))
for x in diff[:40]: print('  ',x)
