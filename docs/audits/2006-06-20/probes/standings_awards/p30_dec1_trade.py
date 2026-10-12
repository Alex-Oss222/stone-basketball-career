import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
from pathlib import Path
from itertools import groupby
R=Path('/home/user/stone-basketball-career')
from runtime import league_cards
reg={x['name']:x for x in json.load(open(R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
res=sorted(results('2003-04').values(),key=lambda r:r['game_date'])
for nm in ['Jalen Rose','Donyell Marshall','Lonny Baxter','Antonio Davis','Jerome Williams','Chris Jefferies']:
    rows=[(r['game_date'],r[side]) for r in res for side in('home','away') for q in r['player_stats'][side] if q['player_id']==nm and q['minutes']>0]
    segs=[(c,list(g)) for c,g in groupby(rows,key=lambda x:x[1])]
    p=reg.get(nm)
    cl=league_cards.club_on(p,'2004-01-15',root=R) if p else None
    print(nm,[(c,g[0][0],g[-1][0],len(g)) for c,g in segs],'| club_on 2004-01-15:',cl and (cl['club'],cl['basis']))
