import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
R='/home/user/stone-basketball-career'
from runtime.seasons import conferences as align
for s in ['2003-04','2004-05','2005-06']:
    a=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/all_star.json'))
    st=[x for x in a['steps'] if x['step']=='coaches'][0]
    res=results(s)
    t={}
    for r in res.values():
        if r['game_date']>st['evidence_through']: continue
        hw=r['final_score']['home']>r['final_score']['away']
        for side,won in (('home',hw),('away',not hw)):
            x=t.setdefault(r[side],[0,0]); x[0 if won else 1]+=1
    conf={c:ts for c,ts in align(s,R).items()}
    print(s,'evidence',st['evidence_through'],'barred',st.get('riley_rule_barred'))
    for c,v in st['conferences'].items():
        best=sorted(conf[c],key=lambda k:-t[k][0]/sum(t[k]))[:3]
        print('  ',c,'chosen',v['coach'],v['team'],v['record'],'| recomputed top',[(b,t[b]) for b in best])
        for row in v['standings']:
            if [row['wins'],row['losses']]!=t[row['team']]: print('   standings row mismatch',row,t[row['team']])
