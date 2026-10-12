import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime import league_cards
reg=json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
p=[x for x in reg if x['name']=='Donyell Marshall'][0]
rows=[]
for r in sorted(results('2003-04').values(),key=lambda r:r['game_date']):
    for side in('home','away'):
        for q in r['player_stats'][side]:
            if q['player_id']=='Donyell Marshall' and q['minutes']>0: rows.append((r['game_date'],r[side]))
from itertools import groupby
for club,grp in groupby(rows,key=lambda x:x[1]):
    g=list(grp); print(club,g[0][0],'->',g[-1][0],len(g))
for d in ['2003-11-30','2003-12-02','2003-12-21','2004-01-18','2004-03-01','2004-04-14']:
    print(d, league_cards.club_on(p,d,root=R))
