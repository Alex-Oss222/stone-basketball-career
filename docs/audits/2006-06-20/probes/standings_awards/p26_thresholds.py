import json, sys, io, contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    res=list(results(s).values())
    dec=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/award_decisions.json'))['decisions']
    for d in dec:
        for x in d['shortlist']:
            cg=sum(1 for r in res if d['period_start']<=r['game_date']<=d['period_end'] and x['team'] in (r['home'],r['away']))
            share={'player_of_month':0.6,'rookie_of_month':0.5}.get(d['award'])
            if share and x['games']<share*cg: print(s,d['id'],x['player'],x['games'],'of',cg)
            if d['award']=='player_of_week' and x['games']<2: print(s,d['id'],x['player'],'games',x['games'])
            # score recompute
            if d['award']=='player_of_week': sc=x['game_score']*x['games']+3*x['wins']
            elif d['award']=='player_of_month': sc=x['game_score']+12*x['wins']/x['games']
            else: sc=x['game_score']+4*x['wins']/x['games']
            if abs(sc-x['score'])>0.02: print(s,d['id'],x['player'],'score',x['score'],'recomputed',round(sc,3))
        sl=d['shortlist']
        if [x['rank'] for x in sl]!=list(range(1,len(sl)+1)): print('rank seq',d['id'])
        if sl and d['winner']!=sl[0]['player']: print('winner not rank1',d['id'])
        sc=[round(x['score'],2) for x in sl]
        if sc!=sorted(sc,reverse=True) and not d.get('tie_draw'): print('order',d['id'],sc)
    print(s,'ok')
