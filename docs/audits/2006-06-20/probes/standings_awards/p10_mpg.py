import json, sys, io, contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
for s,names in [('2003-04',['Manu Ginóbili','Manu Ginobili']),('2004-05',['Anthony Johnson','Manu Ginóbili','Manu Ginobili','Kobe Bryant'])]:
    res=results(s)
    for nm in names:
        g=0;mins=0;sec=0
        for r in res.values():
            for side in('home','away'):
                for p in r['player_stats'][side]:
                    if p['player_id']==nm and p['minutes']>0:
                        g+=1;mins+=p['minutes'];sec+=p.get('seconds',0)
        if g: print(s,nm,g,'minutes field',round(mins/g,3),'seconds',round(sec/60/g,3))
