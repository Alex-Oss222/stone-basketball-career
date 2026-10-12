import json, sys, io, contextlib
from fractions import Fraction as F
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
def gs(p):
    return (F(p["pts"]) + F(2,5)*p["fgm"] - F(7,10)*p["fga"] - F(2,5)*(p["fta"]-p["ftm"]) + F(7,10)*p["orb"] + F(3,10)*p["drb"] + p["stl"] + F(7,10)*p["ast"] + F(7,10)*p["blk"] - F(2,5)*p["pf"] - p["tov"])
for s,name,st,en in [('2004-05','Vince Carter','2004-11-15','2004-11-21'),('2005-06','Dwyane Wade','2005-12-01','2005-12-31'),('2005-06','LeBron James','2006-01-09','2006-01-15')]:
    res=results(s); L=[]
    for r in res.values():
        if st<=r['game_date']<=en:
            for side in('home','away'):
                for p in r['player_stats'][side]:
                    if p['player_id']==name and p['minutes']>0: L.append(gs(p))
    print(s,name,len(L),float(sum(L)/len(L)), sum(L)/len(L))
