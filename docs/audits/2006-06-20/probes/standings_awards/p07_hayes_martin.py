import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
R='/home/user/stone-basketball-career'
from runtime import club_truth
res=results('2005-06')
def games(name,club,st,en):
    out=[]
    for r in sorted(res.values(),key=lambda r:r['game_date']):
        if not st<=r['game_date']<=en: continue
        for side in('home','away'):
            for p in r['player_stats'][side]:
                if p['player_id']==name: out.append((r['game_date'],r[side],p['minutes'],p['pts']))
    return out
def clubgames(club,st,en): return sum(1 for r in res.values() if st<=r['game_date']<=en and club in(r['home'],r['away']))
print('ATL Dec games',clubgames('Atlanta Hawks','2005-12-01','2005-12-31'))
for g in games('Chuck Hayes',None,'2005-11-01','2006-04-19'): print(' Hayes',g)
for d in ['2005-11-01','2005-12-01','2005-12-31','2006-01-15','2006-04-19']:
    print(' holder Hayes',d,club_truth.holder('hayesch01','Chuck Hayes',d,R))
print('Martin games Feb')
for g in games('Kevin Martin',None,'2006-01-25','2006-02-28'): print(' ',g)
for d in ['2005-11-01','2006-02-12','2006-02-19','2006-04-19']:
    print(' holder Martin',d,club_truth.holder('martike02','Kevin Martin',d,R))
