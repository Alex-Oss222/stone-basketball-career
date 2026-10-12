import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
from p04_series import playoff_results
R='/home/user/stone-basketball-career'
def gs(p):
    return (p["pts"] + 0.4*p["fgm"] - 0.7*p["fga"] - 0.4*(p["fta"]-p["ftm"]) + 0.7*p["orb"] + 0.3*p["drb"] + p["stl"] + 0.7*p["ast"] + 0.7*p["blk"] - 0.4*p["pf"] - p["tov"])
for s in ['2003-04','2004-05','2005-06']:
    res=playoff_results(s)
    pj=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/playoffs.json'))
    fin=[x for x in pj['series'] if x['round']=='finals'][0]
    ids=[g['event_id'] for g in fin['games'] if g.get('result')]
    sa=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    fm=[x for x in sa['decisions'] if x['award']=='finals_mvp'][0]
    print(s,'finals games',len(ids),'record finals_games',fm.get('finals_games'),'winners',fm['winners'],'announced',fm['announced_on'],'clinched',fin.get('clinched_on'))
    tot={}
    for e in ids:
        d=res[e][1]
        for side in('home','away'):
            for p in d['player_stats'][side]:
                if p['minutes']>0:
                    t=tot.setdefault(p['player_id'],dict(g=0,team=d[side],min=0,pts=0,reb=0,ast=0,stl=0,blk=0,gs=0))
                    t['g']+=1;t['min']+=p['minutes'];t['pts']+=p['pts'];t['reb']+=p['orb']+p['drb'];t['ast']+=p['ast'];t['stl']+=p['stl'];t['blk']+=p['blk'];t['gs']+=gs(p)
    for t in fm['tally']:
        c=tot.get(t['player'])
        if not c: print('  no finals line',t['player']); continue
        g=c['g']
        exp=dict(games=g,mpg=round(c['min']/g,1),pts=round(c['pts']/g,1),reb=round(c['reb']/g,1),ast=round(c['ast']/g,1),stl=round(c['stl']/g,1),blk=round(c['blk']/g,1),game_score=round(c['gs']/g,2))
        diff={k:(t[k],v) for k,v in exp.items() if t[k]!=v}
        print('  ',t['player'],t['team'],c['team'],'points',t['points'],'diff',diff)
    # top by game score among champion
    champ=pj['champion']
    best=sorted(((v['gs']/v['g'],k) for k,v in tot.items() if v['team']==champ),reverse=True)[:3]
    print('   champion top GmSc',[(k,round(a,2)) for a,k in best])
