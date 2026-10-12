import json, sys, io, contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    res=results(s).values()
    sa=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    end=[x for x in sa['decisions'] if x['award']=='dpoy'][0]['evidence_through']
    al={};po={};w={};g={}
    for r in res:
        if r['game_date']>end: continue
        for side,oth in (('home','away'),('away','home')):
            c=r[side]; al[c]=al.get(c,0)+r['final_score'][oth]; po[c]=po.get(c,0)+r['team_stats'][oth]['possessions']
            g[c]=g.get(c,0)+1; w[c]=w.get(c,0)+(r['final_score'][side]>r['final_score'][oth])
    for x in sa['decisions']:
        for t in x.get('tally',[]):
            if 'club_drtg' in t:
                e=round(al[t['team']]/po[t['team']]*100,1)
                if e!=t['club_drtg']: print(s,x['award'],t['player'],t['team'],t['club_drtg'],'recomputed',e)
            if 'club_pct' in t:
                e=round(w[t['team']]/g[t['team']],3)
                if e!=t['club_pct']: print(s,x['award'],t['player'],t['team'],t['club_pct'],'recomputed',e)
    print(s,'ok', 'games per club',set(g.values()))
